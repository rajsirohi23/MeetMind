"""
utils/file_helpers.py — File validation and safe filename handling.
"""

import os
import uuid

ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'ogg', 'm4a', 'webm', 'flac'}


def allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed audio extension."""
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def secure_unique_filename(original_filename: str) -> str:
    """
    Generate a safe, unique filename to avoid collisions and path traversal.
    Example: 'My Meeting (1).mp3' → 'a3f7c2d1-….mp3'
    """
    ext = original_filename.rsplit('.', 1)[-1].lower()
    return f"{uuid.uuid4()}.{ext}"


def get_file_size_mb(file_path: str) -> float:
    """Return file size in megabytes."""
    size_bytes = os.path.getsize(file_path)
    return round(size_bytes / (1024 * 1024), 2)
