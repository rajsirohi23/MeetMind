# 🎙️ MeetMind — AI-Powered Smart Meeting Analyzer

> Upload any meeting audio → get transcript, summary, action items, decisions, and deadlines — automatically.

---

## 📁 Project Structure

```
meeting-analyzer/
│
├── app.py                      # Flask app factory & entry point
│
├── config/
│   ├── __init__.py
│   └── settings.py             # All config (env vars, model names, limits)
│
├── models/
│   ├── __init__.py
│   └── database.py             # MongoDB helpers (save/get meetings & analyses)
│
├── routes/
│   ├── __init__.py
│   ├── meeting_routes.py       # /api/upload  /api/meetings  /api/meetings/<id>
│   └── analysis_routes.py     # /api/process  /api/results  /api/results/<id>
│
├── utils/
│   ├── __init__.py
│   ├── speech_to_text.py       # Whisper wrapper + basic speaker diarisation
│   ├── nlp_pipeline.py         # Summarisation, NER, task extraction, classification
│   ├── file_helpers.py         # Validation, secure filenames
│   └── notifications.py       # Optional email alerts
│
├── templates/
│   ├── index.html              # Upload page
│   └── dashboard.html          # Results dashboard
│
├── static/
│   ├── css/
│   │   ├── main.css            # Global styles (dark editorial theme)
│   │   └── dashboard.css      # Dashboard layout & components
│   └── js/
│       ├── upload.js           # Upload flow + progress steps
│       └── dashboard.js        # Meeting list + results tabs
│
├── uploads/                    # Audio files land here (gitignored)
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## ⚙️ How to Run Locally (Mac Terminal)

### Step 1 — Prerequisites

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install ffmpeg (required by Whisper for audio decoding)
brew install ffmpeg

# Install MongoDB Community Edition
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community

# Verify MongoDB is running
mongosh --eval "db.runCommand({ connectionStatus: 1 })"
```

### Step 2 — Clone & set up Python environment

```bash
# Navigate to project directory
cd meeting-analyzer

# Create virtual environment (keeps dependencies isolated)
python3 -m venv venv

# Activate it
source venv/bin/activate    # Mac/Linux
# venv\Scripts\activate     # Windows

# Upgrade pip first
pip install --upgrade pip
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ First install takes 5-15 minutes — Whisper, PyTorch, and HuggingFace models are large.

### Step 4 — Configure environment

```bash
# Copy the example env file
cp .env.example .env

# Open and edit (optional — defaults work for local dev)
nano .env
```

### Step 5 — Run the app

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload audio file (form-data key: `audio`) |
| `POST` | `/api/process` | Run AI pipeline `{ "meeting_id": "..." }` |
| `GET`  | `/api/meetings` | List all meetings |
| `GET`  | `/api/meetings/<id>` | Single meeting metadata |
| `GET`  | `/api/results/<id>` | Full analysis for a meeting |
| `GET`  | `/api/results` | Summary list of all analyses |

### Example API call (curl)

```bash
# 1. Upload
curl -X POST http://localhost:5000/api/upload \
  -F "audio=@/path/to/meeting.mp3"

# 2. Process (use meeting_id from step 1)
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"meeting_id": "664abc..."}'

# 3. Get results
curl http://localhost:5000/api/results/664abc...
```

---

## 📊 Output JSON Format

```json
{
  "summary": "The team discussed Q3 roadmap priorities...",
  "tasks": [
    {
      "person": "Rahul",
      "task": "Rahul will complete the backend API by Monday.",
      "deadline": "Monday",
      "priority": "High"
    }
  ],
  "decisions": [
    {
      "decision": "The team decided to launch on Friday.",
      "context": ""
    }
  ],
  "entities": {
    "persons": ["Rahul", "Priya"],
    "dates": ["Monday", "Friday"],
    "organisations": ["Engineering"]
  },
  "language": "en",
  "full_transcript": "Rahul: We need to complete...",
  "speaker_segments": [
    { "speaker": "Speaker 1", "start": 0.0, "end": 4.2, "text": "..." }
  ]
}
```

---

## 🧠 AI Pipeline Explained

```
Audio File
    │
    ▼
[Whisper] ─────────────────── speech-to-text
    │
    ▼
Transcript
    │
    ├──[BART large-cnn] ────── summarisation
    │
    ├──[BERT CoNLL03] ─────── Named Entity Recognition
    │                          (persons, organisations, dates)
    │
    ├──[BART MNLI] ────────── zero-shot sentence classification
    │                          (Task / Decision / General)
    │
    └──[Regex + ML] ────────── task extraction
                               + priority tagging
                               + deadline extraction
```

---

## 🐛 Common Errors & Fixes

### ❌ `ModuleNotFoundError: No module named 'whisper'`
```bash
pip install openai-whisper
```

### ❌ `RuntimeError: ffmpeg not found`
```bash
# Mac
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# Windows — download from https://ffmpeg.org/download.html
# Add to PATH
```

### ❌ `pymongo.errors.ServerSelectionTimeoutError`
MongoDB is not running.
```bash
# Mac
brew services start mongodb-community

# Linux
sudo systemctl start mongod
```

### ❌ HuggingFace model download very slow
The first run downloads model weights (~1.6 GB total). They are cached in `~/.cache/huggingface/`. Subsequent runs are instant.

### ❌ `torch.cuda.OutOfMemoryError`
You're running on GPU and ran out of VRAM. Switch to CPU:
- In `utils/nlp_pipeline.py`, change `device=0` to `device=-1`
- In `utils/speech_to_text.py`, add `fp16=False` to `model.transcribe()`

### ❌ `413 Request Entity Too Large`
Increase `MAX_CONTENT_LENGTH` in `config/settings.py`.

### ❌ Process endpoint times out in browser
For very long audio files (>30 min), the request can take 3-5 minutes. Consider:
1. Using `threading` to run processing in the background
2. Returning immediately with a job ID, then polling `/api/meetings/<id>` for status

### ❌ `transformers` version conflicts
```bash
pip install transformers==4.41.2 accelerate==0.30.1
```

---

## 🚀 Hackathon Winning Tips

### Performance
- **Cache Whisper model** — already done via singleton pattern. Don't reload on every request.
- **Smaller Whisper model** for demo: `tiny` or `base` — much faster, slightly less accurate.
- **Background tasks**: Use `threading.Thread` to process audio asynchronously and show a live status page.

### Features that impress judges
1. **Live progress steps** — already implemented in the UI (Uploading → Transcribing → NLP → Done)
2. **Speaker identification** — basic diarisation is in `speech_to_text.py`
3. **Export to CSV** — already in the Tasks tab
4. **Email notifications** — `utils/notifications.py` is ready, just needs SMTP credentials
5. **Priority classification** — colour-coded High / Medium / Low cards

### Upgrade ideas
| Idea | How |
|------|-----|
| Real speaker diarisation | Add `pyannote-audio` (requires HuggingFace token) |
| Notion / Jira export | Add API calls in a new `utils/integrations.py` |
| Calendar deadline sync | Use Google Calendar API |
| Multi-language support | Whisper auto-detects language — already working! |
| Real-time transcription | Use Whisper streaming API |
| Sentiment analysis | Add HuggingFace sentiment pipeline |
| Action item assignment AI | Prompt LLM to suggest who should own which task |

### For demo day
```bash
# Use a small, punchy test audio (30-60 seconds works best for live demo)
# Record yourself saying:
# "Hi team. Rahul needs to finish the backend by Monday — this is urgent.
#  We decided to launch on Friday. Priya will send the design assets by tomorrow.
#  The mobile app is still in progress."

# Then upload and show the full pipeline in action.
```

---

## 🗄️ MongoDB Collections

**`meetings`** — file metadata
```json
{
  "_id": "ObjectId",
  "filename": "a3f7c2d1.mp3",
  "original_name": "standup.mp3",
  "status": "done",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**`analyses`** — full NLP results
```json
{
  "_id": "ObjectId",
  "meeting_id": "...",
  "full_transcript": "...",
  "summary": "...",
  "tasks": [...],
  "decisions": [...],
  "entities": {...},
  "created_at": "ISODate"
}
```

---

## 🏗️ Production Deployment

```bash
# Use Gunicorn instead of Flask dev server
gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"

# Or with Docker (add Dockerfile if needed)
```

For MongoDB in production, use **MongoDB Atlas** (free tier available):
```
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/meeting_analyzer
```

---

Built with ❤️ using Flask · Whisper · HuggingFace · MongoDB
