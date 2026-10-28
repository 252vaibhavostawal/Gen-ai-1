// Live Monitoring Cockpit script
let socket = null;
let currentSessionId = null;

function initLiveMonitor(sessionId) {
  currentSessionId = sessionId;
  const canvas = document.getElementById('tracking-canvas');
  const ctx = canvas ? canvas.getContext('2d') : null;

  // Establish local WebSocket connection via Socket.IO
  if (typeof io !== 'undefined') {
    socket = io('/live');

    socket.on('connect', () => {
      console.log('Connected to live telemetry stream');
      document.getElementById('stream-status-badge').textContent = 'CONNECTED';
      document.getElementById('stream-status-badge').className = 'badge badge-present';
    });

    socket.on('disconnect', () => {
      document.getElementById('stream-status-badge').textContent = 'DISCONNECTED';
      document.getElementById('stream-status-badge').className = 'badge badge-absent';
    });

    socket.on('session_update', (data) => {
      if (data.session_id === currentSessionId) {
        updateTelemetryUI(data);
        if (ctx && canvas) {
          drawTracks(ctx, canvas, data.tracks || []);
        }
      }
    });
  }

  // Periodic polling fallback if WebSockets are blocked
  setInterval(pollAttendanceStatus, 3000);
}

function updateTelemetryUI(data) {
  document.getElementById('live-elapsed').textContent = formatSeconds(data.elapsed_seconds || 0);
  document.getElementById('live-active-tracks').textContent = data.active_tracks_count || 0;

  if (data.attendance_stats) {
    const s = data.attendance_stats;
    document.getElementById('live-present-count').textContent = s.present_count || 0;
    document.getElementById('live-late-count').textContent = s.late_count || 0;
    document.getElementById('live-unconfirmed-count').textContent = s.unconfirmed_count || 0;
    document.getElementById('live-attendance-pct').textContent = (s.attendance_percentage || 0) + '%';
  }

  // Update simulated/measured audio meter
  const meterFill = document.getElementById('audio-meter-fill');
  if (meterFill) {
    // Generate gentle fluctuating energy between 20% and 75%
    const level = Math.min(100, Math.max(15, Math.floor(Math.random() * 55) + 20));
    meterFill.style.width = level + '%';
    document.getElementById('audio-level-text').textContent = level + '% Level';
  }
}

function drawTracks(ctx, canvas, tracks) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  tracks.forEach(t => {
    const [x, y, w, h] = t.bbox;
    // Scale coordinates to canvas width/height
    const scaleX = canvas.width / 640.0;
    const scaleY = canvas.height / 480.0;

    const sx = x * scaleX;
    const sy = y * scaleY;
    const sw = w * scaleX;
    const sh = h * scaleY;

    // Bounding Box
    ctx.strokeStyle = t.is_forward ? '#10b981' : '#f59e0b';
    ctx.lineWidth = 2;
    ctx.strokeRect(sx, sy, sw, sh);

    // Label Badge
    ctx.fillStyle = t.is_forward ? '#065f46' : '#78350f';
    ctx.fillRect(sx, sy - 22, sw, 22);

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 11px sans-serif';
    const label = `Track #${t.track_id} | ${t.is_forward ? 'Forward' : 'Turned'}`;
    ctx.fillText(label, sx + 4, sy - 6);
  });
}

function formatSeconds(secs) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

async function pollAttendanceStatus() {
  if (!currentSessionId) return;
  try {
    const res = await fetch(`/api/v1/sessions/${currentSessionId}/attendance`);
    if (res.ok) {
      const data = await res.json();
      renderLiveAttendanceTable(data.records || []);
    }
  } catch (err) {
    console.error('Polling error:', err);
  }
}

function renderLiveAttendanceTable(records) {
  const tbody = document.getElementById('live-attendance-tbody');
  if (!tbody) return;

  if (records.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#94a3b8;">Scanning for attendees...</td></tr>';
    return;
  }

  tbody.innerHTML = records.map(r => `
    <tr>
      <td><strong>#${r.anonymous_track_id}</strong></td>
      <td>${r.student_name}</td>
      <td><span class="badge badge-${r.attendance_status.toLowerCase()}">${r.attendance_status}</span></td>
      <td>${r.accumulated_duration}s</td>
      <td>
        <button class="btn btn-sm btn-secondary" onclick="openMapModal(${r.anonymous_track_id})">Map Student</button>
      </td>
    </tr>
  `).join('');
}

// Session Control Handlers
async function sendSessionAction(action) {
  if (!currentSessionId) return;
  try {
    const res = await fetch(`/api/v1/sessions/${currentSessionId}/${action}`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || `Session ${action}ed`, 'success');
      setTimeout(() => window.location.reload(), 800);
    } else {
      showToast(data.error || 'Action failed', 'error');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function openMapModal(trackId) {
  document.getElementById('modal-track-id').value = trackId;
  document.getElementById('modal-track-label').textContent = `#${trackId}`;
  openModal('map-student-modal');
}

async function submitStudentMapping(e) {
  e.preventDefault();
  const trackId = document.getElementById('modal-track-id').value;
  const studentId = document.getElementById('modal-student-select').value;

  try {
    const res = await fetch(`/api/v1/sessions/${currentSessionId}/map_track`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ track_id: trackId, student_id: studentId }),
    });
    const data = await res.json();
    if (res.ok) {
      showToast('Track successfully mapped to student', 'success');
      closeModal('map-student-modal');
      pollAttendanceStatus();
    } else {
      showToast(data.error || 'Failed to map student', 'error');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}
