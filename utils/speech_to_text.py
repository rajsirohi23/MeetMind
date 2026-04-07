"""
utils/speech_to_text.py — Whisper-based audio transcription.

Whisper model is loaded ONCE (singleton pattern) to avoid reloading
on every request (which would be very slow).
"""

import os
import whisper
import torch

# ── Singleton model cache ──────────────────────────────────────────────────────
_model = None


def _get_model(model_size: str = 'base'):
    """Load Whisper model once and cache it in memory."""
    global _model
    if _model is None:
        print(f"⏳  Loading Whisper '{model_size}' model …")
        _model = whisper.load_model(model_size)
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"✅  Whisper loaded on {device.upper()}")
    return _model


def transcribe_audio(file_path: str, model_size: str = 'base') -> dict:
    """
    Transcribe an audio file using OpenAI Whisper.

    Returns:
        {
            'text':     str   — full transcript
            'segments': list  — [{id, start, end, text}, …]
            'language': str   — detected language code
        }

    Raises:
        FileNotFoundError  – if audio file doesn't exist
        RuntimeError       – if Whisper fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    model = _get_model(model_size)

    print(f"🎙️  Transcribing: {file_path}")
    result = model.transcribe(
        file_path,
        fp16=False,          # fp16=True is faster on GPU; CPU needs fp16=False
        verbose=False
    )

    print(f"✅  Transcription complete — {len(result['text'])} chars")

    return {
        'text':     result['text'].strip(),
        'segments': result.get('segments', []),
        'language': result.get('language', 'en'),
    }


def diarize_speakers(segments: list) -> list:
    """
    Basic speaker diarisation using silence gaps between segments.

    Real diarisation (pyannote-audio) requires a Hugging Face token and GPU.
    This is a lightweight heuristic: long pauses → new "speaker".

    Returns the segments list with an added 'speaker' key.
    """
    PAUSE_THRESHOLD = 1.5   # seconds — gaps longer than this → new speaker
    speaker_idx  = 0
    prev_end     = 0.0
    speaker_map  = []

    for seg in segments:
        start = seg.get('start', 0)
        if start - prev_end > PAUSE_THRESHOLD:
            speaker_idx += 1          # Assume speaker changed after a pause
        speaker_map.append({
            **seg,
            'speaker': f"Speaker {speaker_idx + 1}",
        })
        prev_end = seg.get('end', start)

    return speaker_map
