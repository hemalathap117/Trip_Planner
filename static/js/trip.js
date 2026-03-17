/* ── Toast ──────────────────────────────────────────────── */
function toast(msg, type = 'success') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => {
    el.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => el.remove(), 300);
  }, 3200);
}

/* ── SVG Icons ──────────────────────────────────────────── */
const ICONS = {
  mapPin:    `<svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--accent)"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
  checkCirc: `<svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="M22 4 12 14.01l-3-3"/></svg>`,
  medal:     `<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--muted-fg)"><path d="M7.21 15 2.66 7.14a2 2 0 0 1 .13-2.2L4.4 2.8A2 2 0 0 1 6 2h12a2 2 0 0 1 1.6.8l1.6 2.14a2 2 0 0 1 .14 2.2L16.79 15"/><path d="M11 12 5.12 2.2"/><path d="m13 12 5.88-9.8"/><path d="M8 7h8"/><circle cx="12" cy="17" r="5"/><path d="M12 18v-2h-.5"/></svg>`,
  copy:      `<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`,
  check:     `<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>`,
};

/* ── Constants ──────────────────────────────────────────── */
const INTERESTS = [
  'Beach','Mountains','Culture','Food','Nightlife','Adventure',
  'History','Nature','Shopping','Relaxation','Photography','Art',
];

/* ── State ──────────────────────────────────────────────── */
let tripData         = null;
let selectedRec      = null;
let selectedInterests= [];
let prefFormOpen     = false;
let currentVoterName = null;  // Track current participant's name
let pollTimer        = null;

/* ── Boot ───────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', init);

async function init() {
  // Restore voter name from localStorage if available
  const savedVoterName = localStorage.getItem(`voter_${JOIN_CODE}`);
  if (savedVoterName) {
    currentVoterName = savedVoterName;
    const voterNameInput = document.getElementById('voterName');
    if (voterNameInput) {
      voterNameInput.value = savedVoterName;
    }
  }
  
  await loadTrip();
}

/* ── Data loading ───────────────────────────────────────── */
async function loadTrip() {
  try {
    const res = await fetch(`/trip-data/${JOIN_CODE}`);
    if (res.status === 404) { showNotFound(); return; }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      toast(err.detail || 'Failed to load trip data', 'error');
      return;
    }
    tripData = await res.json();
    if (!tripData.id) { showNotFound(); return; }
    render();
  } catch {
    showNotFound();
  }
}

function showNotFound() {
  document.getElementById('notFoundState').style.display = '';
  document.getElementById('tripContent').style.display = 'none';
}

/* ── Render ─────────────────────────────────────────────── */
function render() {
  document.getElementById('tripContent').style.display = '';
  document.getElementById('notFoundState').style.display = 'none';

  document.getElementById('tripName').textContent    = tripData.name || '';
  document.getElementById('tripOrg').textContent     = `Organised by ${tripData.organiser_name || ''}`;
  document.getElementById('tripJoinCode').textContent = tripData.join_code || '';
  
  // Set shareable link
  const shareLink = `${window.location.origin}/dashboard/${tripData.join_code}`;
  document.getElementById('tripShareLink').textContent = shareLink;

  renderStatusBadge();

  // Hide all phases, show correct one
  ['phaseCollecting', 'phaseGenerating', 'phaseVoting', 'phaseClosed'].forEach(id => {
    document.getElementById(id).style.display = 'none';
  });

  const status = tripData.status;
  if (status === 'collecting') {
    renderCollecting();
    document.getElementById('phaseCollecting').style.display = '';
    stopPoll();
  } else if (status === 'generating') {
    document.getElementById('phaseGenerating').style.display = '';
    startPoll();
  } else if (status === 'voting') {
    renderVoting();
    document.getElementById('phaseVoting').style.display = '';
    stopPoll();
  } else if (status === 'closed') {
    renderClosed();
    document.getElementById('phaseClosed').style.display = '';
    stopPoll();
  }
}

/* ── Status badge ───────────────────────────────────────── */
const STATUS_CFG = {
  collecting: { label: 'Collecting Preferences', cls: 'badge-primary' },
  generating: { label: 'Generating...',           cls: 'badge-accent'  },
  voting:     { label: 'Votings',             cls: 'badge-primary' },
  closed:     { label: 'Closed',            cls: 'badge-accent'  },
};
function renderStatusBadge() {
  const cfg = STATUS_CFG[tripData.status] || STATUS_CFG.collecting;
  document.getElementById('statusBadge').innerHTML =
    `<span class="badge ${cfg.cls}">${cfg.label}</span>`;
}

/* ══════════════════════════════════════════════════════════
   COLLECTING PHASE
══════════════════════════════════════════════════════════ */
function renderCollecting() {
  const prefs = tripData.preferences || [];
  document.getElementById('prefCount').textContent = `Preferences (${prefs.length})`;

  // Preference list
  const list = document.getElementById('prefList');
  if (prefs.length === 0) {
    list.innerHTML = `<div class="empty-state">No preferences yet. Share the join code and add yours!</div>`;
  } else {
    list.innerHTML = prefs.map(p => `
      <div class="pref-row">
        <span class="pref-row-name">${esc(p.participant_name)}</span>
        <div class="pref-row-badges">
          <span class="badge badge-secondary">${esc(p.budget)}</span>
          <span class="badge badge-secondary">${(p.interests || []).length} interests</span>
        </div>
      </div>`).join('<div style="height:0.5rem"></div>');
  }

  // Generate button
  const genBtn = document.getElementById('generateBtn');
  genBtn.disabled = prefs.length === 0;

  // Build interest tags (only once)
  const grid = document.getElementById('interestsGrid');
  if (!grid.children.length) {
    grid.innerHTML = INTERESTS.map(i =>
      `<span class="interest-tag" data-interest="${i}" onclick="toggleInterest(this)">${i}</span>`
    ).join('');
  }
}

function togglePrefForm() {
  prefFormOpen = !prefFormOpen;
  document.getElementById('prefFormWrap').classList.toggle('open', prefFormOpen);
  if (prefFormOpen) {
    setTimeout(() => document.getElementById('pfName').focus(), 50);
  }
}

function toggleInterest(el) {
  const interest = el.dataset.interest;
  if (selectedInterests.includes(interest)) {
    selectedInterests = selectedInterests.filter(i => i !== interest);
    el.classList.remove('active');
  } else {
    selectedInterests.push(interest);
    el.classList.add('active');
  }
}

async function submitPreferences() {
  const name   = document.getElementById('pfName').value.trim();
  const budget = document.getElementById('pfBudget').value;
  const from   = document.getElementById('pfDateFrom').value;
  const to     = document.getElementById('pfDateTo').value;

  if (!name)                    { toast('Please enter your name', 'error'); return; }
  if (!from || !to)             { toast('Please select dates', 'error'); return; }
  if (to < from)                { toast('End date must be after start date', 'error'); return; }
  if (!selectedInterests.length){ toast('Select at least one interest', 'error'); return; }

  const btn = document.getElementById('prefFormWrap').querySelector('.btn-accent');
  btn.disabled = true; btn.textContent = 'Submitting...';

  try {
    const res = await fetch(`/submit-preferences/${JOIN_CODE}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        participant_name: name, budget,
        date_from: from, date_to: to,
        interests: selectedInterests,
      }),
    });
    const data = await res.json();
    if (!res.ok) { toast(data.detail || 'Failed to submit', 'error'); return; }

    toast('Preferences added!');
    // Reset form fields
    document.getElementById('pfName').value     = '';
    document.getElementById('pfDateFrom').value = '';
    document.getElementById('pfDateTo').value   = '';
    selectedInterests = [];
    document.querySelectorAll('#interestsGrid .interest-tag.active')
      .forEach(t => t.classList.remove('active'));

    // Close form
    prefFormOpen = false;
    document.getElementById('prefFormWrap').classList.remove('open');
    await loadTrip();
  } catch {
    toast('Failed to submit preferences', 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Submit Preferences';
  }
}

async function generateRecs() {
  const btn     = document.getElementById('generateBtn');
  const spinner = document.getElementById('generateSpinner');
  const icon    = document.getElementById('sparklesIcon');
  btn.disabled  = true;
  spinner.style.display = '';
  icon.style.display    = 'none';

  try {
    const res = await fetch(`/generate/${JOIN_CODE}`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      toast(err.detail || 'Failed to generate', 'error');
      return;
    }
    toast('Recommendations generated!');
    await loadTrip();
  } catch {
    toast('Failed to generate recommendations', 'error');
    btn.disabled  = false;
    spinner.style.display = 'none';
    icon.style.display    = '';
  }
}

/* ══════════════════════════════════════════════════════════
   VOTING PHASE
══════════════════════════════════════════════════════════ */
function renderVoting() {
  const recs  = tripData.recommendations || [];
  const votes = tripData.votes || [];
  const total = votes.length;

  // Check if current participant has voted
  const hasCurrentUserVoted = currentVoterName && 
    votes.some(v => v.participant_name === currentVoterName);

  // Render recommendation cards
  document.getElementById('recCards').innerHTML = recs.map((rec, i) => {
    const count = votes.filter(v => v.recommendation_id === rec.id).length;
    const pct   = total > 0 ? Math.round((count / total) * 100) : 0;
    const isSel = selectedRec === rec.id;
    return `
      <div class="rec-card${isSel ? ' selected' : ''}"
           onclick="${hasCurrentUserVoted ? '' : `selectRec('${rec.id}')`}"
           style="animation-delay:${i * 0.1}s; cursor:${hasCurrentUserVoted ? 'default' : 'pointer'}">
        <div class="rec-card-top">
          <div class="rec-card-name">${ICONS.mapPin}<h3>${esc(rec.destination_name)}</h3></div>
          ${isSel ? ICONS.checkCirc : ''}
        </div>
        <p>${esc(rec.rationale)}</p>
        <div class="rec-progress-row">
          <div class="rec-progress-bar">
            <div class="rec-progress-fill" style="width:${pct}%"></div>
          </div>
          <span class="badge badge-secondary">${count} vote${count !== 1 ? 's' : ''} (${pct}%)</span>
        </div>
      </div>`;
  }).join('');

  // Show/hide vote form based on whether current user has voted
  document.getElementById('voteFormCard').style.display = hasCurrentUserVoted ? 'none' : '';
  
  // If user has voted, show a message
  if (hasCurrentUserVoted) {
    const existingMsg = document.getElementById('votedMessage');
    if (!existingMsg) {
      const voteFormCard = document.getElementById('voteFormCard');
      const votedMsg = document.createElement('div');
      votedMsg.id = 'votedMessage';
      votedMsg.className = 'card';
      votedMsg.innerHTML = `
        <div class="card-full" style="text-align: center; color: var(--muted-fg);">
          ${ICONS.checkCirc}
          <p style="margin: 0.5rem 0 0 0;">You have already voted as <strong>${esc(currentVoterName)}</strong></p>
        </div>`;
      voteFormCard.parentNode.insertBefore(votedMsg, voteFormCard.nextSibling);
    }
  } else {
    // Remove voted message if it exists
    const existingMsg = document.getElementById('votedMessage');
    if (existingMsg) existingMsg.remove();
  }
  
  updateCastVoteBtn();
}

function selectRec(id) {
  // Check if current user has already voted
  const hasCurrentUserVoted = currentVoterName && 
    tripData.votes.some(v => v.participant_name === currentVoterName);
  
  if (hasCurrentUserVoted) return;
  
  selectedRec = (selectedRec === id) ? null : id;
  // Re-render just the cards portion, preserving the voter name
  const recs  = tripData.recommendations || [];
  const votes = tripData.votes || [];
  const total = votes.length;
  document.getElementById('recCards').innerHTML = recs.map((rec, i) => {
    const count = votes.filter(v => v.recommendation_id === rec.id).length;
    const pct   = total > 0 ? Math.round((count / total) * 100) : 0;
    const isSel = selectedRec === rec.id;
    return `
      <div class="rec-card${isSel ? ' selected' : ''}"
           onclick="selectRec('${rec.id}')"
           style="animation:none; opacity:1;">
        <div class="rec-card-top">
          <div class="rec-card-name">${ICONS.mapPin}<h3>${esc(rec.destination_name)}</h3></div>
          ${isSel ? ICONS.checkCirc : ''}
        </div>
        <p>${esc(rec.rationale)}</p>
        <div class="rec-progress-row">
          <div class="rec-progress-bar">
            <div class="rec-progress-fill" style="width:${pct}%"></div>
          </div>
          <span class="badge badge-secondary">${count} vote${count !== 1 ? 's' : ''} (${pct}%)</span>
        </div>
      </div>`;
  }).join('');
  updateCastVoteBtn();
}

function updateCastVoteBtn() {
  const name = (document.getElementById('voterName')?.value || '').trim();
  const btn  = document.getElementById('castVoteBtn');
  if (btn) {
    // Update currentVoterName when user types and save to localStorage
    if (name) {
      currentVoterName = name;
      localStorage.setItem(`voter_${JOIN_CODE}`, name);
    }
    
    // Check if this participant has already voted
    const hasCurrentUserVoted = name && 
      tripData.votes.some(v => v.participant_name === name);
    
    if (hasCurrentUserVoted) {
      btn.disabled = true;
      btn.textContent = 'Already Voted';
    } else {
      btn.disabled = !(selectedRec && name);
      btn.textContent = 'Cast Your Vote';
    }
  }
}

// Wire voter name input to updateCastVoteBtn
document.addEventListener('DOMContentLoaded', () => {
  const nameInput = document.getElementById('voterName');
  if (nameInput) {
    nameInput.addEventListener('input', updateCastVoteBtn);
    nameInput.addEventListener('blur', updateCastVoteBtn);
  }
});

async function castVote() {
  const name = document.getElementById('voterName').value.trim();
  if (!name)        { toast('Enter your name to vote', 'error'); return; }
  if (!selectedRec) { toast('Select a destination first', 'error'); return; }

  // Check if user has already voted
  const hasCurrentUserVoted = tripData.votes.some(v => v.participant_name === name);
  if (hasCurrentUserVoted) {
    toast('You have already voted!', 'error');
    return;
  }

  const btn = document.getElementById('castVoteBtn');
  btn.disabled = true; btn.textContent = 'Voting...';

  try {
    const res = await fetch(`/vote/${JOIN_CODE}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ participant_name: name, recommendation_id: selectedRec }),
    });
    const data = await res.json();
    if (!res.ok) { toast(data.detail || 'Failed to vote', 'error'); return; }
    
    // Set current voter name and reload trip data
    currentVoterName = name;
    toast('Vote cast!');
    await loadTrip();
  } catch {
    toast('Failed to cast vote', 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Cast Your Vote';
  }
}

async function closeVoting() {
  if (!confirm('Close voting and reveal the winner?')) return;
  try {
    const res = await fetch(`/close-voting/${JOIN_CODE}`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      toast(err.detail || 'Failed to close voting', 'error'); return;
    }
    toast('Voting closed! Winner announced.');
    await loadTrip();
  } catch {
    toast('Failed to close voting', 'error');
  }
}

/* ══════════════════════════════════════════════════════════
   CLOSED / RESULTS PHASE
══════════════════════════════════════════════════════════ */
function renderClosed() {
  const recs  = tripData.recommendations || [];
  const votes = tripData.votes || [];
  const total = votes.length;

  if (!recs.length) {
    document.getElementById('phaseClosed').innerHTML = '<div class="empty-state">No results yet.</div>';
    return;
  }

  // Sort by vote count desc, tie-break by first vote time
  const sorted = [...recs].sort((a, b) => {
    const ca = votes.filter(v => v.recommendation_id === a.id).length;
    const cb = votes.filter(v => v.recommendation_id === b.id).length;
    if (cb !== ca) return cb - ca;
    const ta = votes.find(v => v.recommendation_id === a.id)?.created_at || 'z';
    const tb = votes.find(v => v.recommendation_id === b.id)?.created_at || 'z';
    return ta.localeCompare(tb);
  });

  const winner  = sorted[0];
  const runners = sorted.slice(1);

  // Winner card body
  if (winner) {
    const wCount = votes.filter(v => v.recommendation_id === winner.id).length;
    const wPct   = total > 0 ? Math.round((wCount / total) * 100) : 0;
    document.getElementById('winnerBody').innerHTML = `
      <div class="winner-name">${ICONS.mapPin}<h2>${esc(winner.destination_name)}</h2></div>
      <p style="color:var(--muted-fg);margin-bottom:1rem;line-height:1.6;">${esc(winner.rationale)}</p>
      <span class="badge badge-primary">${wCount} vote${wCount !== 1 ? 's' : ''} &mdash; ${wPct}%</span>`;
  }
  document.getElementById('winnerCard').style.display = winner ? '' : 'none';

  // All results (runners-up)
  document.getElementById('allResults').innerHTML = runners.length ? runners.map((rec, i) => {
    const count = votes.filter(v => v.recommendation_id === rec.id).length;
    const pct   = total > 0 ? Math.round((count / total) * 100) : 0;
    return `
      <div class="card" style="margin-bottom:0.75rem;animation:fadeUp 0.4s ease ${0.3 + i * 0.1}s forwards;opacity:0">
        <div class="card-full">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.375rem">
            <div style="display:flex;align-items:center;gap:0.5rem">${ICONS.medal}
              <span style="font-weight:600">${esc(rec.destination_name)}</span>
            </div>
            <span class="badge badge-secondary">${count} vote${count !== 1 ? 's' : ''} (${pct}%)</span>
          </div>
          <p style="font-size:0.875rem;color:var(--muted-fg)">${esc(rec.rationale)}</p>
        </div>
      </div>`;
  }).join('') : '<div class="empty-state">No other destinations.</div>';

  // Vote summary bars
  document.getElementById('voteSummary').innerHTML = sorted.map(rec => {
    const count = votes.filter(v => v.recommendation_id === rec.id).length;
    const pct   = total > 0 ? Math.round((count / total) * 100) : 0;
    const isWin = winner && rec.id === winner.id;
    return `
      <div class="summary-row">
        <span class="summary-label">${esc(rec.destination_name)}</span>
        <div class="summary-bar">
          <div class="summary-fill ${isWin ? 'is-winner' : 'is-other'}" style="width:${pct}%"></div>
        </div>
        <span class="summary-pct">${pct}%</span>
      </div>`;
  }).join('');

  document.getElementById('totalVotesLabel').textContent =
    `${total} total vote${total !== 1 ? 's' : ''}`;
}

/* ── Copy join code ─────────────────────────────────────── */
function copyCode() {
  const code = document.getElementById('tripJoinCode').textContent;
  navigator.clipboard.writeText(code).then(() => {
    document.getElementById('copyBarBtn').innerHTML = ICONS.check;
    toast('Code copied!');
    setTimeout(() => { document.getElementById('copyBarBtn').innerHTML = ICONS.copy; }, 2000);
  }).catch(() => toast('Could not copy', 'error'));
}

/* ── Copy shareable link ───────────────────────────────── */
function copyLink() {
  const link = document.getElementById('tripShareLink').textContent;
  navigator.clipboard.writeText(link).then(() => {
    document.getElementById('copyLinkBtn').innerHTML = ICONS.check;
    toast('Link copied!');
    setTimeout(() => { 
      document.getElementById('copyLinkBtn').innerHTML = `<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
      </svg>`; 
    }, 2000);
  }).catch(() => toast('Could not copy link', 'error'));
}

/* ── Polling (generating phase) ─────────────────────────── */
function startPoll() {
  if (pollTimer) return;
  pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/trip-data/${JOIN_CODE}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.status !== 'generating') {
        tripData = data;
        render();
      }
    } catch { /* ignore poll errors */ }
  }, 2500);
}
function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

/* ── HTML escape ────────────────────────────────────────── */
function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
