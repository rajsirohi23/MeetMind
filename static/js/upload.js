/**
 * upload.js — handles file selection, drag-drop, upload, and polling
 *
 * Flow:
 *   1. User selects / drops file → preview shown
 *   2. "Analyse Meeting" clicked → POST /api/upload → get meeting_id
 *   3. POST /api/process with meeting_id → NLP pipeline runs
 *   4. On success → redirect to /dashboard?id=<meeting_id>
 */

const API_BASE = '';   // empty = same origin; set to 'http://localhost:5000' if serving frontend separately

/* ── DOM refs ──────────────────────────────────────────────── */
const dropZone      = document.getElementById('dropZone');
const fileInput     = document.getElementById('fileInput');
const filePreview   = document.getElementById('filePreview');
const fileName      = document.getElementById('fileName');
const fileSize      = document.getElementById('fileSize');
const clearBtn      = document.getElementById('clearFile');
const uploadBtn     = document.getElementById('uploadBtn');
const progressCard  = document.getElementById('progressCard');
const progressBar   = document.getElementById('progressBar');
const progressLabel = document.getElementById('progressLabel');
const errorCard     = document.getElementById('errorCard');
const errorMsg      = document.getElementById('errorMsg');
const retryBtn      = document.getElementById('retryBtn');

let selectedFile = null;

/* ── Step helpers ────────────────────────────────────────────── */
const STEPS = ['step-upload', 'step-transcribe', 'step-nlp', 'step-save'];
const STEP_PROGRESS = [15, 40, 85, 100];
const STEP_LABELS   = [
  'Uploading audio file…',
  'Transcribing with Whisper (this may take a minute)…',
  'Running NLP pipeline — summarisation, NER, classification…',
  'Saving results to database…',
];

function setStep(idx) {
  STEPS.forEach((id, i) => {
    const el = document.getElementById(id);
    el.classList.remove('active', 'done');
    if (i < idx)  el.classList.add('done');
    if (i === idx) el.classList.add('active');
  });
  progressBar.style.width = STEP_PROGRESS[idx] + '%';
  progressLabel.textContent = STEP_LABELS[idx];
}

/* ── File selection ──────────────────────────────────────────── */
function showPreview(file) {
  selectedFile = file;
  fileName.textContent = file.name;
  fileSize.textContent = formatBytes(file.size);
  dropZone.classList.add('hidden');
  filePreview.classList.remove('hidden');
  errorCard.classList.add('hidden');
}

function clearSelection() {
  selectedFile = null;
  fileInput.value = '';
  filePreview.classList.add('hidden');
  dropZone.classList.remove('hidden');
}

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) showPreview(fileInput.files[0]);
});

clearBtn.addEventListener('click', clearSelection);
retryBtn.addEventListener('click', () => {
  errorCard.classList.add('hidden');
  progressCard.classList.add('hidden');
  clearSelection();
});

/* ── Drag-and-drop ───────────────────────────────────────────── */
['dragenter', 'dragover'].forEach(evt =>
  dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.add('over'); })
);
['dragleave', 'drop'].forEach(evt =>
  dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.remove('over'); })
);
dropZone.addEventListener('drop', e => {
  const file = e.dataTransfer.files[0];
  if (file) showPreview(file);
});

/* ── Upload + Process ────────────────────────────────────────── */
uploadBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  // Show progress UI
  filePreview.classList.add('hidden');
  progressCard.classList.remove('hidden');
  errorCard.classList.add('hidden');
  setStep(0);

  try {
    /* ── Step 1: Upload ──────────────────────────────────────── */
    const formData = new FormData();
    formData.append('audio', selectedFile);

    const uploadRes = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!uploadRes.ok) {
      const err = await uploadRes.json();
      throw new Error(err.error || 'Upload failed');
    }

    const { meeting_id } = await uploadRes.json();
    setStep(1);

    /* ── Step 2: Trigger processing ──────────────────────────── */
    // Note: /api/process is a long-running call — Whisper + HF models can take
    // 30s-3min depending on file length and hardware.
    setStep(2);

    const processRes = await fetch(`${API_BASE}/api/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ meeting_id }),
    });

    if (!processRes.ok) {
      const err = await processRes.json();
      throw new Error(err.error || 'Processing failed');
    }

    setStep(3);

    // Small pause so user can see the final step
    await sleep(600);

    /* ── Step 3: Redirect to dashboard ───────────────────────── */
    window.location.href = `/dashboard?id=${meeting_id}`;

  } catch (err) {
    progressCard.classList.add('hidden');
    errorCard.classList.remove('hidden');
    errorMsg.textContent = err.message || 'An unexpected error occurred.';
    console.error('Pipeline error:', err);
  }
});

/* ── Utils ───────────────────────────────────────────────────── */
function formatBytes(bytes) {
  if (bytes < 1024)        return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
