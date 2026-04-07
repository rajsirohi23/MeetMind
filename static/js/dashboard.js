/**
 * dashboard.js — Meeting list sidebar + results panel
 *
 * On load:
 *   1. Fetch all meetings from GET /api/meetings
 *   2. If ?id= param present, auto-load that meeting
 *   3. Clicking a meeting → fetch its analysis from GET /api/results/<id>
 *   4. Render tabs: Summary, Tasks, Decisions, Transcript, Entities
 */

const API_BASE = '';

/* ── State ───────────────────────────────────────────────────── */
let allMeetings  = [];
let currentData  = null;
let activeMeetingId = null;

/* ── DOM refs ──────────────────────────────────────────────────  */
const meetingList  = document.getElementById('meetingList');
const emptyState   = document.getElementById('emptyState');
const resultsPanel = document.getElementById('resultsPanel');

/* ── Boot ────────────────────────────────────────────────────── */
(async function init() {
  await loadMeetingList();

  // Auto-select from URL ?id=
  const params = new URLSearchParams(window.location.search);
  const autoId = params.get('id');
  if (autoId) {
    await loadAnalysis(autoId);
  }
})();

/* ── Load meeting list ───────────────────────────────────────── */
async function loadMeetingList() {
  try {
    const res  = await fetch(`${API_BASE}/api/meetings`);
    const data = await res.json();
    allMeetings = data.meetings || [];
    renderMeetingList(allMeetings);
  } catch (e) {
    meetingList.innerHTML = `<p class="list-empty">Could not load meetings.<br/>Is the Flask server running?</p>`;
  }
}

function renderMeetingList(meetings) {
  if (!meetings.length) {
    meetingList.innerHTML = `<p class="list-empty">No meetings yet.<br/><a href="/" style="color:var(--accent)">Upload one →</a></p>`;
    return;
  }

  meetingList.innerHTML = meetings.map(m => `
    <div class="meeting-item ${m._id === activeMeetingId ? 'active' : ''}"
         data-id="${m._id}">
      <div class="meeting-item-name">${escHtml(m.original_name || m.filename)}</div>
      <div class="meeting-item-meta">
        <span class="status-dot ${m.status}"></span>
        <span>${m.status}</span>
        <span>·</span>
        <span>${timeAgo(m.created_at)}</span>
      </div>
    </div>
  `).join('');

  // Click handlers
  meetingList.querySelectorAll('.meeting-item').forEach(el => {
    el.addEventListener('click', () => loadAnalysis(el.dataset.id));
  });
}

/* ── Load & render analysis ──────────────────────────────────── */
async function loadAnalysis(meetingId) {
  activeMeetingId = meetingId;
  renderMeetingList(allMeetings);   // refresh active highlight

  try {
    const res  = await fetch(`${API_BASE}/api/results/${meetingId}`);
    if (!res.ok) {
      // Meeting might not be analysed yet
      const meeting = allMeetings.find(m => m._id === meetingId);
      if (meeting && meeting.status !== 'done') {
        showPanel({
          full_transcript: '(Processing not yet complete)',
          summary: `This meeting is still "${meeting.status}". Refresh after processing.`,
          tasks: [], decisions: [], entities: {},
        }, meeting);
      }
      return;
    }
    const data = await res.json();
    currentData = data;

    const meeting = allMeetings.find(m => m._id === meetingId) || {};
    showPanel(data, meeting);

    // Update URL without reload
    history.replaceState(null, '', `?id=${meetingId}`);
  } catch (e) {
    console.error(e);
  }
}

function showPanel(data, meeting) {
  emptyState.classList.add('hidden');
  resultsPanel.classList.remove('hidden');

  /* Header */
  document.getElementById('resultsTitle').textContent =
    meeting.original_name || meeting.filename || 'Meeting';
  document.getElementById('resultsMeta').textContent =
    `Analysed ${formatDate(data.created_at || meeting.created_at)} · Language: ${(data.language || 'en').toUpperCase()}`;

  document.getElementById('badgeTasks').textContent     = `${(data.tasks||[]).length} tasks`;
  document.getElementById('badgeDecisions').textContent = `${(data.decisions||[]).length} decisions`;

  /* Render all tabs */
  renderSummary(data);
  renderTasks(data.tasks || []);
  renderDecisions(data.decisions || []);
  renderTranscript(data.full_transcript || '', data.speaker_segments || []);
  renderEntities(data.entities || {});
}

/* ── Summary ─────────────────────────────────────────────────── */
function renderSummary(data) {
  document.getElementById('summaryText').textContent =
    data.summary || 'No summary generated.';

  const tasks     = data.tasks     || [];
  const decisions = data.decisions || [];
  const words     = (data.full_transcript || '').split(/\s+/).length;

  document.getElementById('summaryStats').innerHTML = `
    <div class="stat-chip"><span class="stat-val">${tasks.length}</span><span class="stat-label">Action Items</span></div>
    <div class="stat-chip"><span class="stat-val">${decisions.length}</span><span class="stat-label">Decisions</span></div>
    <div class="stat-chip"><span class="stat-val">${words.toLocaleString()}</span><span class="stat-label">Words</span></div>
    <div class="stat-chip"><span class="stat-val">${tasks.filter(t=>t.priority==='High').length}</span><span class="stat-label">High Priority</span></div>
  `;
}

/* ── Tasks ───────────────────────────────────────────────────── */
let _allTasks = [];

function renderTasks(tasks) {
  _allTasks = tasks;
  renderFilteredTasks('');

  document.getElementById('priorityFilter').addEventListener('change', e => {
    renderFilteredTasks(e.target.value);
  });

  document.getElementById('exportTasksBtn').addEventListener('click', exportTasksCSV);
}

function renderFilteredTasks(priority) {
  const filtered = priority
    ? _allTasks.filter(t => t.priority === priority)
    : _allTasks;

  const container = document.getElementById('taskList');
  if (!filtered.length) {
    container.innerHTML = `<p class="list-empty">No tasks found.</p>`;
    return;
  }

  container.innerHTML = filtered.map((t, i) => {
    const initials = (t.person || 'U').split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase();
    return `
      <div class="task-card priority-${t.priority || 'Low'}">
        <div class="task-avatar">${initials}</div>
        <div class="task-body">
          <p class="task-text">${escHtml(t.task)}</p>
          <div class="task-meta">
            ${t.person   ? `<span class="task-chip person">👤 ${escHtml(t.person)}</span>` : ''}
            ${t.deadline ? `<span class="task-chip deadline">📅 ${escHtml(t.deadline)}</span>` : ''}
          </div>
        </div>
        <span class="priority-badge ${t.priority || 'Low'}">${t.priority || 'Low'}</span>
      </div>
    `;
  }).join('');
}

function exportTasksCSV() {
  const header = 'Person,Task,Deadline,Priority';
  const rows   = _allTasks.map(t =>
    `"${t.person||''}","${(t.task||'').replace(/"/g,'""')}","${t.deadline||''}","${t.priority||''}"`
  );
  const csv  = [header, ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'tasks.csv'; a.click();
  URL.revokeObjectURL(url);
}

/* ── Decisions ───────────────────────────────────────────────── */
function renderDecisions(decisions) {
  const container = document.getElementById('decisionList');
  if (!decisions.length) {
    container.innerHTML = `<p class="list-empty">No decisions detected.</p>`;
    return;
  }
  container.innerHTML = decisions.map(d => `
    <div class="decision-card">
      <span class="decision-icon">✅</span>
      <p class="decision-text">${escHtml(typeof d === 'string' ? d : d.decision)}</p>
    </div>
  `).join('');
}

/* ── Transcript ──────────────────────────────────────────────── */
function renderTranscript(text, segments) {
  const box = document.getElementById('transcriptBox');
  box.textContent = text || 'No transcript available.';

  // Search highlight
  const searchInput = document.getElementById('transcriptSearch');
  searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim();
    if (!q) { box.textContent = text; return; }
    const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const highlighted = text.replace(
      new RegExp(escaped, 'gi'),
      m => `<mark>${m}</mark>`
    );
    box.innerHTML = highlighted;
  });

  // Speaker segments
  const speakerSection = document.getElementById('speakerSection');
  const speakerList    = document.getElementById('speakerList');

  if (segments && segments.length) {
    speakerSection.classList.remove('hidden');
    speakerList.innerHTML = segments.slice(0, 30).map(seg => `
      <div class="speaker-segment">
        <span class="speaker-label">${escHtml(seg.speaker || 'Speaker')}</span>
        <span class="speaker-time">${formatTime(seg.start)}</span>
        <span class="speaker-text">${escHtml(seg.text || '')}</span>
      </div>
    `).join('');
  }
}

/* ── Entities ────────────────────────────────────────────────── */
function renderEntities(entities) {
  const grid = document.getElementById('entitiesGrid');
  const groups = [
    { key: 'persons',       label: 'People',        icon: '👤' },
    { key: 'organisations', label: 'Organisations',  icon: '🏢' },
    { key: 'dates',         label: 'Dates & Times',  icon: '📅' },
  ];

  grid.innerHTML = groups.map(g => {
    const items = (entities[g.key] || []).filter(Boolean);
    return `
      <div class="entity-group">
        <div class="entity-group-title">${g.icon} ${g.label}</div>
        <div class="entity-tags">
          ${items.length
            ? items.map(e => `<span class="entity-tag">${escHtml(e)}</span>`).join('')
            : `<span style="font-size:0.78rem;color:var(--text-dim)">None detected</span>`
          }
        </div>
      </div>
    `;
  }).join('');
}

/* ── Tabs ─────────────────────────────────────────────────────── */
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    tab.classList.add('active');
    document.getElementById(`tab-${tab.dataset.tab}`).classList.remove('hidden');
  });
});

/* ── Utils ───────────────────────────────────────────────────── */
function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function timeAgo(isoStr) {
  if (!isoStr) return '';
  const diff = (Date.now() - new Date(isoStr)) / 1000;
  if (diff < 60)   return 'just now';
  if (diff < 3600) return Math.floor(diff/60) + 'm ago';
  if (diff < 86400)return Math.floor(diff/3600) + 'h ago';
  return Math.floor(diff/86400) + 'd ago';
}

function formatDate(isoStr) {
  if (!isoStr) return '—';
  return new Date(isoStr).toLocaleString();
}

function formatTime(seconds) {
  if (seconds == null) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2,'0')}`;
}
