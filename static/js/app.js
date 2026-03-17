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
  }, 3000);
}

/* ── Create Trip Overlay ────────────────────────────────── */
let createdJoinCode = null;

function showCreateOverlay() {
  document.getElementById('createOverlay').classList.add('show');
  document.getElementById('createFormState').style.display = '';
  document.getElementById('createSuccessState').style.display = 'none';
  document.getElementById('createTripName').value = '';
  document.getElementById('createOrgName').value = '';
  setTimeout(() => document.getElementById('createTripName').focus(), 50);
}

function hideCreateOverlay() {
  document.getElementById('createOverlay').classList.remove('show');
  createdJoinCode = null;
}

function handleOverlayClick(e) {
  if (e.target === document.getElementById('createOverlay')) hideCreateOverlay();
}

async function submitCreateTrip() {
  const tripName = document.getElementById('createTripName').value.trim();
  const orgName  = document.getElementById('createOrgName').value.trim();
  if (!tripName || !orgName) { toast('Please fill in all fields', 'error'); return; }

  const btn = document.querySelector('#createFormState .btn-primary');
  btn.disabled = true;
  btn.textContent = 'Creating…';

  try {
    const res = await fetch('/create-trip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trip_name: tripName, organizer_name: orgName })
    });
    if (!res.ok) throw new Error('Failed to create trip');
    const data = await res.json();
    createdJoinCode = data.join_code;

    // Generate shareable link
    const shareLink = `${window.location.origin}/dashboard/${data.join_code}`;

    document.getElementById('createFormState').style.display = 'none';
    document.getElementById('createSuccessState').style.display = '';
    document.getElementById('displayJoinCode').textContent = data.join_code;
    document.getElementById('displayShareLink').textContent = shareLink;
    document.getElementById('goDashboardBtn').onclick = () => {
      window.location.href = `/dashboard/${data.join_code}`;
    };
    toast('Trip created!');
  } catch (err) {
    toast('Failed to create trip. Try again.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Create Trip';
  }
}

function copyJoinCode() {
  if (!createdJoinCode) return;
  navigator.clipboard.writeText(createdJoinCode).then(() => {
    const btn = document.getElementById('copyCodeBtn');
    btn.innerHTML = `<svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>`;
    toast('Code copied!');
    setTimeout(() => {
      btn.innerHTML = `<svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`;
    }, 2000);
  });
}

function copyShareLink() {
  const shareLink = document.getElementById('displayShareLink').textContent;
  if (!shareLink) return;
  navigator.clipboard.writeText(shareLink).then(() => {
    const btn = document.getElementById('copyLinkBtnHome');
    btn.innerHTML = `<svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>`;
    toast('Link copied!');
    setTimeout(() => {
      btn.innerHTML = `<svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`;
    }, 2000);
  });
}

/* ── Join Trip ───────────────────────────────────────────── */
async function handleJoin() {
  const code = document.getElementById('joinCodeInput').value.trim().toUpperCase();
  if (code.length !== 6) { toast('Join codes are 6 characters', 'error'); return; }
  try {
    const res = await fetch(`/trip/${code}`);
    if (!res.ok) { toast('Trip not found', 'error'); return; }
    window.location.href = `/dashboard/${code}`;
  } catch {
    toast('Could not connect. Try again.', 'error');
  }
}

/* ── Keyboard: Escape closes overlay ───────────────────── */
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') hideCreateOverlay();
});
