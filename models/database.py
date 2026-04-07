"""
models/database.py — MongoDB connection & helper functions.

Collections used:
  • meetings   – metadata (filename, status, created_at)
  • analyses   – full analysis results (transcript, summary, tasks …)
"""

from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import os

# Module-level client (initialised once)
_client = None
_db = None


def init_db(app=None):
    """Connect to MongoDB. Call once at app startup."""
    global _client, _db
    uri = (
        app.config.get('MONGO_URI')
        if app
        else os.getenv('MONGO_URI', 'mongodb://localhost:27017/meeting_analyzer')
    )
    _client = MongoClient(uri)
    _db = _client.get_database()          # database name is part of the URI
    print(f"✅  MongoDB connected → {uri}")
    return _db


def get_db():
    """Return the database handle (lazy initialisation for standalone use)."""
    global _db
    if _db is None:
        init_db()
    return _db


# ── Helper functions ───────────────────────────────────────────────────────────

def save_meeting(filename: str, original_name: str) -> str:
    """Insert a new meeting record and return its string ID."""
    db = get_db()
    doc = {
        'filename': filename,
        'original_name': original_name,
        'status': 'uploaded',          # uploaded → processing → done | error
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
    }
    result = db.meetings.insert_one(doc)
    return str(result.inserted_id)


def update_meeting_status(meeting_id: str, status: str):
    """Flip the status field of a meeting document."""
    db = get_db()
    db.meetings.update_one(
        {'_id': ObjectId(meeting_id)},
        {'$set': {'status': status, 'updated_at': datetime.utcnow()}}
    )


def save_analysis(meeting_id: str, analysis: dict) -> str:
    """Save the full NLP analysis linked to a meeting."""
    db = get_db()
    doc = {
        'meeting_id': meeting_id,
        'full_transcript': analysis.get('full_transcript', ''),
        'summary':         analysis.get('summary', ''),
        'tasks':           analysis.get('tasks', []),
        'decisions':       analysis.get('decisions', []),
        'entities':        analysis.get('entities', {}),
        'created_at':      datetime.utcnow(),
    }
    result = db.analyses.insert_one(doc)

    # Mark meeting as done
    update_meeting_status(meeting_id, 'done')

    return str(result.inserted_id)


def get_all_meetings():
    """Return all meetings (newest first), with string IDs."""
    db = get_db()
    meetings = list(
        db.meetings.find().sort('created_at', -1)
    )
    for m in meetings:
        m['_id'] = str(m['_id'])
    return meetings


def get_analysis_by_meeting(meeting_id: str):
    """Fetch the analysis document for a given meeting ID."""
    db = get_db()
    doc = db.analyses.find_one({'meeting_id': meeting_id})
    if doc:
        doc['_id'] = str(doc['_id'])
    return doc


def get_meeting_by_id(meeting_id: str):
    """Fetch a single meeting by its ID."""
    db = get_db()
    doc = db.meetings.find_one({'_id': ObjectId(meeting_id)})
    if doc:
        doc['_id'] = str(doc['_id'])
    return doc
