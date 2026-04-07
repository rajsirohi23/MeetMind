"""
routes/analysis_routes.py

API endpoints:
  POST /api/process         — transcribe + analyse a meeting
  GET  /api/results/<id>    — fetch stored analysis
  GET  /api/results         — list all analyses
"""

import os
from flask import Blueprint, request, jsonify, current_app
from models.database import (
    get_meeting_by_id,
    save_analysis,
    get_analysis_by_meeting,
    update_meeting_status,
    get_all_meetings,
    get_db,
)
from utils.speech_to_text import transcribe_audio, diarize_speakers
from utils.nlp_pipeline import run_full_pipeline

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/process', methods=['POST'])
def process():
    """
    Trigger the full AI pipeline for a previously uploaded meeting.

    Request body (JSON): { "meeting_id": "<id>" }

    Pipeline:
      1. Load audio from disk
      2. Whisper → transcript
      3. NLP → summary, tasks, decisions
      4. Persist to MongoDB
      5. Return structured JSON
    """
    data = request.get_json(silent=True) or {}
    meeting_id = data.get('meeting_id') or request.args.get('meeting_id')

    if not meeting_id:
        return jsonify({'error': 'meeting_id is required.'}), 400

    # ── Fetch meeting record ───────────────────────────────────────────────────
    meeting = get_meeting_by_id(meeting_id)
    if not meeting:
        return jsonify({'error': 'Meeting not found.'}), 404

    if meeting.get('status') == 'processing':
        return jsonify({'error': 'Already processing. Please wait.'}), 409

    # ── Mark as processing ─────────────────────────────────────────────────────
    update_meeting_status(meeting_id, 'processing')

    try:
        # ── Step 1: Locate audio file ──────────────────────────────────────────
        upload_dir = current_app.config['UPLOAD_FOLDER']
        file_path  = os.path.join(upload_dir, meeting['filename'])

        if not os.path.exists(file_path):
            update_meeting_status(meeting_id, 'error')
            return jsonify({'error': 'Audio file missing on disk.'}), 500

        # ── Step 2: Speech-to-text (Whisper) ──────────────────────────────────
        whisper_model = current_app.config.get('WHISPER_MODEL', 'base')
        stt_result    = transcribe_audio(file_path, model_size=whisper_model)

        transcript  = stt_result['text']
        segments    = stt_result['segments']
        language    = stt_result['language']

        # Basic speaker diarisation (heuristic)
        speaker_segments = diarize_speakers(segments)

        # ── Step 3: NLP pipeline ───────────────────────────────────────────────
        analysis = run_full_pipeline(transcript)

        # Enrich with speech metadata
        analysis['language']         = language
        analysis['speaker_segments'] = speaker_segments[:50]  # cap at 50 segs

        # ── Step 4: Persist ────────────────────────────────────────────────────
        analysis_id = save_analysis(meeting_id, analysis)

        analysis['analysis_id'] = analysis_id
        analysis['meeting_id']  = meeting_id

        return jsonify(analysis), 200

    except Exception as exc:
        update_meeting_status(meeting_id, 'error')
        return jsonify({'error': str(exc)}), 500


@analysis_bp.route('/results/<meeting_id>', methods=['GET'])
def get_results(meeting_id: str):
    """Fetch the stored analysis for a given meeting."""
    doc = get_analysis_by_meeting(meeting_id)
    if not doc:
        return jsonify({'error': 'No analysis found for this meeting.'}), 404
    return jsonify(doc), 200


@analysis_bp.route('/results', methods=['GET'])
def list_results():
    """
    Return a summary list of all analysed meetings.
    Each item includes: meeting_id, summary snippet, task count, decision count.
    """
    db = get_db()
    docs = list(db.analyses.find({}, {
        'meeting_id': 1,
        'summary': 1,
        'tasks': 1,
        'decisions': 1,
        'created_at': 1,
    }).sort('created_at', -1))

    results = []
    for doc in docs:
        results.append({
            'analysis_id':   str(doc['_id']),
            'meeting_id':    doc.get('meeting_id'),
            'summary_short': (doc.get('summary', '')[:150] + '…'),
            'task_count':    len(doc.get('tasks', [])),
            'decision_count': len(doc.get('decisions', [])),
            'created_at':    str(doc.get('created_at', '')),
        })

    return jsonify({'results': results, 'count': len(results)}), 200
