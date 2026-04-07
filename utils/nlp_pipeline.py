"""
utils/nlp_pipeline.py — Full NLP processing pipeline.

Steps:
  1. Summarisation   (facebook/bart-large-cnn)
  2. NER             (bert-large-cased CoNLL03)
  3. Task extraction (rule-based regex + ML zero-shot)
  4. Sentence classification → Task / Decision / General
  5. Priority tagging
  6. Deadline extraction
"""

import re
from transformers import pipeline
from typing import Optional

# ── Priority keywords ──────────────────────────────────────────────────────────
PRIORITY_HIGH   = ['urgent', 'asap', 'immediately', 'critical', 'today', 'right away']
PRIORITY_MEDIUM = ['soon', 'this week', 'next week', 'important', 'priority']
PRIORITY_LOW    = ['eventually', 'when possible', 'later', 'someday', 'low priority']

# ── Task verbs that trigger extraction ────────────────────────────────────────
TASK_VERBS = [
    r'\b(need|needs) to\b',
    r'\bwill\b',
    r'\bshould\b',
    r'\bmust\b',
    r'\bhas to\b',
    r'\bhave to\b',
    r'\bresponsible for\b',
    r'\bassigned to\b',
    r'\btake care of\b',
    r'\bfollow up\b',
    r'\baction item\b',
    r'\bto-do\b',
    r'\bplease\b',
    r'\bcomplete\b',
    r'\bfinish\b',
    r'\bdeliver\b',
    r'\bsend\b',
    r'\bprepare\b',
    r'\bschedule\b',
    r'\bbook\b',
    r'\bset up\b',
]

# ── Deadline patterns ──────────────────────────────────────────────────────────
DEADLINE_PATTERNS = [
    r'\b(by\s)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
    r'\b(by\s)?(next\s)?(week|month|quarter)\b',
    r'\b(by\s)?(end of (day|week|month))\b',
    r'\b(by\s)?(\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?)\b',
    r'\b(by\s)?(today|tomorrow)\b',
    r'\b(within\s\d+\s(day|days|week|weeks|hour|hours))\b',
    r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}\b',
    r'\bQ[1-4]\b',
    r'\b(asap|immediately|urgent)\b',
]

# ── Singleton model cache ──────────────────────────────────────────────────────
_summariser  = None
_ner         = None
_classifier  = None


def _load_models():
    """Lazy-load all HuggingFace pipelines once."""
    global _summariser, _ner, _classifier

    if _summariser is None:
        print("⏳  Loading summarisation model …")
        _summariser = pipeline(
            'summarization',
            model='facebook/bart-large-cnn',
            device=-1   # -1 = CPU; set to 0 for GPU
        )
        print("✅  Summariser ready")

    if _ner is None:
        print("⏳  Loading NER model …")
        _ner = pipeline(
            'ner',
            model='dbmdz/bert-large-cased-finetuned-conll03-english',
            aggregation_strategy='simple',
            device=-1
        )
        print("✅  NER ready")

    if _classifier is None:
        print("⏳  Loading zero-shot classifier …")
        _classifier = pipeline(
            'zero-shot-classification',
            model='facebook/bart-large-mnli',
            device=-1
        )
        print("✅  Classifier ready")


# ── Public API ─────────────────────────────────────────────────────────────────

def summarise(text: str, max_len: int = 200, min_len: int = 60) -> str:
    """
    Generate a concise summary of the meeting transcript.
    BART is limited to ~1024 tokens, so we chunk long transcripts.
    """
    _load_models()

    # Split into chunks of ~900 words to stay within model token limits
    words   = text.split()
    chunks  = [' '.join(words[i:i+900]) for i in range(0, len(words), 900)]
    summaries = []

    for chunk in chunks:
        if len(chunk.strip()) < 50:
            continue
        result = _summariser(
            chunk,
            max_length=max_len,
            min_length=min_len,
            do_sample=False
        )
        summaries.append(result[0]['summary_text'])

    return ' '.join(summaries)


def extract_entities(text: str) -> dict:
    """
    Run Named Entity Recognition → return persons and dates/times.

    Returns:
        { 'persons': [str], 'dates': [str], 'organisations': [str] }
    """
    _load_models()

    entities = _ner(text[:1000])  # NER is slow on very long text; sample first 1k chars

    persons = []
    dates   = []
    orgs    = []

    for ent in entities:
        word  = ent['word'].strip()
        label = ent['entity_group']
        if label == 'PER'  and word not in persons: persons.append(word)
        if label == 'ORG'  and word not in orgs:    orgs.append(word)
        if label == 'MISC' and word not in dates:   dates.append(word)

    # Also grab dates via regex (more reliable for deadline parsing)
    regex_dates = []
    for pattern in DEADLINE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            date_str = m if isinstance(m, str) else ' '.join(m).strip()
            if date_str and date_str not in regex_dates:
                regex_dates.append(date_str)

    return {
        'persons':       persons,
        'dates':         list(set(dates + regex_dates)),
        'organisations': orgs,
    }


def extract_tasks(text: str, persons: list) -> list:
    """
    Extract action items using:
      1. Regex patterns on each sentence
      2. Zero-shot classification to confirm it's a task

    Returns:
        [{ person, task, deadline, priority }, …]
    """
    _load_models()

    sentences = _split_sentences(text)
    tasks = []

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue

        # Check if any task verb pattern appears in this sentence
        has_task_verb = any(
            re.search(p, sentence, re.IGNORECASE) for p in TASK_VERBS
        )
        if not has_task_verb:
            continue

        # Zero-shot: is this really a task / action item?
        try:
            clf_result = _classifier(
                sentence,
                candidate_labels=['task', 'decision', 'general discussion'],
            )
            top_label = clf_result['labels'][0]
            top_score = clf_result['scores'][0]

            if top_label != 'task' or top_score < 0.40:
                continue   # Not confident enough → skip
        except Exception:
            pass            # If classifier fails, still add from regex signal

        person   = _find_person(sentence, persons)
        deadline = _extract_deadline(sentence)
        priority = _classify_priority(sentence)

        tasks.append({
            'person':   person,
            'task':     sentence,
            'deadline': deadline,
            'priority': priority,
        })

    return tasks


def classify_sentences(text: str) -> dict:
    """
    Classify every sentence as Task / Decision / General.

    Returns:
        { 'tasks': [str], 'decisions': [str], 'general': [str] }
    """
    _load_models()

    sentences = _split_sentences(text)
    result = {'tasks': [], 'decisions': [], 'general': []}

    LABELS = ['task or action item', 'decision made', 'general discussion']

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 15:
            continue
        try:
            clf = _classifier(sentence, candidate_labels=LABELS)
            top = clf['labels'][0]
            if 'task' in top:
                result['tasks'].append(sentence)
            elif 'decision' in top:
                result['decisions'].append(sentence)
            else:
                result['general'].append(sentence)
        except Exception:
            result['general'].append(sentence)

    return result


def run_full_pipeline(transcript: str) -> dict:
    """
    Run the complete NLP pipeline on a transcript.

    Returns the structured JSON that will be stored in MongoDB and
    returned to the frontend.
    """
    print("🧠  Running NLP pipeline …")

    # 1. Summarise
    summary = summarise(transcript)
    print("   ✅  Summary done")

    # 2. NER
    entities = extract_entities(transcript)
    print(f"   ✅  Entities: {entities}")

    # 3. Classify all sentences
    classified = classify_sentences(transcript)
    print(f"   ✅  Classification done — {len(classified['tasks'])} tasks, "
          f"{len(classified['decisions'])} decisions")

    # 4. Deep-extract tasks with person + deadline + priority
    tasks = extract_tasks(transcript, entities['persons'])
    print(f"   ✅  {len(tasks)} tasks extracted")

    # 5. Format decisions
    decisions = [
        {'decision': d, 'context': ''}
        for d in classified['decisions']
    ]

    return {
        'summary':        summary,
        'tasks':          tasks,
        'decisions':      decisions,
        'entities':       entities,
        'full_transcript': transcript,
    }


# ── Private helpers ────────────────────────────────────────────────────────────

def _split_sentences(text: str) -> list:
    """Simple sentence splitter (avoids heavy NLTK dependency)."""
    # Split on period / exclamation / question mark followed by space + capital
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    # Also split on newlines
    result = []
    for s in sentences:
        result.extend(s.split('\n'))
    return [s.strip() for s in result if s.strip()]


def _find_person(sentence: str, persons: list) -> Optional[str]:
    """Return the first known person name found in a sentence."""
    for person in persons:
        if person.lower() in sentence.lower():
            return person
    # Fallback: look for capitalised single word (likely a name)
    match = re.search(r'\b([A-Z][a-z]{2,})\b', sentence)
    if match and match.group(1) not in ('The', 'This', 'That', 'We', 'They'):
        return match.group(1)
    return 'Unassigned'


def _extract_deadline(sentence: str) -> Optional[str]:
    """Extract the first deadline-like phrase from a sentence."""
    for pattern in DEADLINE_PATTERNS:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def _classify_priority(sentence: str) -> str:
    """Tag priority based on keyword presence."""
    lower = sentence.lower()
    if any(kw in lower for kw in PRIORITY_HIGH):
        return 'High'
    if any(kw in lower for kw in PRIORITY_MEDIUM):
        return 'Medium'
    return 'Low'
