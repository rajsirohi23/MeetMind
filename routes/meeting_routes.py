"""
routes/meeting_routes.py

API endpoints:
  POST /api/upload   — upload an audio file, returns meeting_id
  GET  /api/meetings — list all past meetings
  GET  /api/meetings/<id> — single meeting metadata
"""

import os
from flask import Blueprint, request, jsonify, current_app
from models.database import save_meeting, get_all_meetings, get_meeting_by_id
from utils.file_helpers import allowed_file, secure_unique_filename, get_file_size_mb

meeting_bp = Blueprint('meeting', __name__)


@meeting_bp.route('/upload', methods=['POST'])
def upload():
    """
    Accept a multipart audio file upload.

    Form-data key: 'audio'
    Returns: { meeting_id, filename, size_mb, message }
    """
    # ── Validate request ───────────────────────────────────────────────────────
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file in request. Use key "audio".'}), 400

    file = request.files['audio']

    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    if not allowed_file(file.filename):
        return jsonify({
            'error': 'Unsupported file type.',
            'allowed': ['mp3', 'mp4', 'wav', 'ogg', 'm4a', 'webm', 'flac']
        }), 400

    # ── Save file ──────────────────────────────────────────────────────────────
    safe_name = secure_unique_filename(file.filename)
    upload_dir = current_app.config['UPLOAD_FOLDER']
    file_path  = os.path.join(upload_dir, safe_name)
    file.save(file_path)

    size_mb = get_file_size_mb(file_path)

    # ── Persist metadata in MongoDB ────────────────────────────────────────────
    meeting_id = save_meeting(
        filename=safe_name,
        original_name=file.filename
    )

    return jsonify({
        'meeting_id':   meeting_id,
        'filename':     safe_name,
        'original_name': file.filename,
        'size_mb':      size_mb,
        'message':      'File uploaded successfully. Call /api/process to analyse.',
    }), 201


@meeting_bp.route('/meetings', methods=['GET'])
def list_meetings():
    """Return all meetings, newest first."""
    meetings = get_all_meetings()
    return jsonify({'meetings': meetings, 'count': len(meetings)}), 200


@meeting_bp.route('/meetings/<meeting_id>', methods=['GET'])
def get_meeting(meeting_id: str):
    """Return metadata for a single meeting."""
    meeting = get_meeting_by_id(meeting_id)
    if not meeting:
        return jsonify({'error': 'Meeting not found.'}), 404
    return jsonify(meeting), 200
