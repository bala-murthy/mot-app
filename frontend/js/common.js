const API = '/api/v1';

// Generate or retrieve a session ID (used for locking)
function getSessionId() {
  let sid = localStorage.getItem('mot_session_id');
  if (!sid) {
    sid = 'sess_' + Math.random().toString(36).substr(2, 12);
    localStorage.setItem('mot_session_id', sid);
  }
  return sid;
}

// Standard fetch wrapper
async function apiFetch(path, options = {}) {
  const url = API + path;
  const defaults = { headers: { 'Content-Type': 'application/json' } };
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    options.body = JSON.stringify(options.body);
  }
  if (options.body instanceof FormData) {
    delete defaults.headers['Content-Type'];
  }
  const res = await fetch(url, { ...defaults, ...options });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { const d = await res.json(); msg = d.detail || d.message || msg; } catch {}
    throw new Error(msg);
  }
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('json')) return res.json();
  return res;
}

// Format currency
function fmtCurrency(v) {
  if (!v && v !== 0) return '-';
  if (v >= 1_000_000) return `$${(v/1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `$${(v/1_000).toFixed(1)}K`;
  return `$${Number(v).toLocaleString()}`;
}

// Set active nav link
function setActiveNav(page) {
  document.querySelectorAll('.mot-sidebar .nav-link').forEach(el => {
    el.classList.remove('active');
    if (el.dataset.page === page) el.classList.add('active');
  });
}

// Status badge
function statusBadge(status) {
  if (!status) return '<span class="text-muted">—</span>';
  const cls = statusClass(status);
  return `<span class="status-badge ${cls}">${status}</span>`;
}
function statusClass(s) {
  if (!s) return '';
  const l = s.toLowerCase();
  if (l.includes('fulfill') || l.includes('won') || l.includes('closed won')) return 'status-fulfilled';
  if (l.includes('open') || l.includes('pending') || l.includes('in progress')) return 'status-pending';
  if (l.includes('closed') || l.includes('cancel')) return 'status-closed';
  if (l.includes('risk') || l.includes('breach')) return 'status-risk';
  return 'status-open';
}

// Toast notification
function showToast(msg, type = 'success') {
  const colors = { success: '#22c55e', danger: '#ef4444', warning: '#f59e0b', info: '#0dcaf0' };
  const div = document.createElement('div');
  div.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:9999;
    background:${colors[type]||colors.info};color:white;padding:.75rem 1.25rem;
    border-radius:8px;font-size:.9rem;box-shadow:0 4px 12px rgba(0,0,0,.2);
    animation:slideIn .3s ease;max-width:360px;`;
  div.innerHTML = `<i class="bi bi-${type==='success'?'check-circle':type==='danger'?'x-circle':'info-circle'} me-2"></i>${msg}`;
  document.body.appendChild(div);
  setTimeout(() => div.remove(), 4000);
}

// Load alert count in header
async function loadAlertCount() {
  try {
    const alerts = await apiFetch('/dashboard/alerts?unread_only=true');
    const badge = document.getElementById('alertBadge');
    if (badge) {
      badge.textContent = alerts.length;
      badge.style.display = alerts.length ? 'flex' : 'none';
    }
  } catch {}
}

document.addEventListener('DOMContentLoaded', () => {
  loadAlertCount();
  // Sidebar toggle for mobile
  const toggle = document.getElementById('sidebarToggle');
  if (toggle) toggle.addEventListener('click', () => {
    document.querySelector('.mot-sidebar')?.classList.toggle('open');
  });
});
