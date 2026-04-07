"""
config/settings.py — centralised settings loaded from environment variables.
Copy .env.example → .env and fill in your values.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True') == 'True'

    # MongoDB
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/meeting_analyzer')

    # File upload
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024          # 200 MB
    ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'ogg', 'm4a', 'webm', 'flac'}

    # ── Whisper ────────────────────────────────────────────────────────────────
    # Sizes: tiny | base | small | medium | large
    # "base" is the sweet-spot for local dev (fast, decent accuracy).
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')

    # ── Hugging Face models ────────────────────────────────────────────────────
    SUMMARIZATION_MODEL = os.getenv(
        'SUMMARIZATION_MODEL', 'facebook/bart-large-cnn'
    )
    NER_MODEL = os.getenv(
        'NER_MODEL', 'dbmdz/bert-large-cased-finetuned-conll03-english'
    )
    CLASSIFIER_MODEL = os.getenv(
        'CLASSIFIER_MODEL', 'facebook/bart-large-mnli'
    )

    # ── Email notifications (optional) ────────────────────────────────────────
    MAIL_SERVER   = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT     = int(os.getenv('MAIL_PORT', 587))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_USE_TLS  = True
