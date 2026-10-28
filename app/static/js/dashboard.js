document.addEventListener('DOMContentLoaded', () => {
  loadDashboardData();
});

async function loadDashboardData() {
  try {
    const res = await fetch('/api/v1/dashboard/summary');
    if (!res.ok) throw new Error('Failed to load dashboard metrics');
    const data = await res.json();
    const m = data.metrics;

    document.getElementById('metric-registered').textContent = m.total_registered_students;
    document.getElementById('metric-sessions').textContent = m.total_classes_conducted;
    document.getElementById('metric-attendance-pct').textContent = m.overall_attendance_percentage + '%';
    document.getElementById('metric-engagement').textContent = m.average_engagement_score ? m.average_engagement_score + '/100' : 'N/A';

    const currSessEl = document.getElementById('metric-current-session');
    if (m.current_session) {
      currSessEl.innerHTML = `<span class="badge badge-running">Active</span> ${m.current_session.title} <a href="/live/${m.current_session.id}" class="btn btn-sm btn-primary" style="margin-left:8px;">Open Live</a>`;
    } else {
      currSessEl.textContent = 'None currently active';
    }

    // Render Recent Sessions
    const sessTbody = document.getElementById('recent-sessions-tbody');
    if (sessTbody) {
      if (data.recent_sessions && data.recent_sessions.length > 0) {
        sessTbody.innerHTML = data.recent_sessions.map(s => `
          <tr>
            <td><strong>#${s.id}</strong></td>
            <td><a href="/sessions/${s.id}" style="color:var(--primary); font-weight:600; text-decoration:none;">${s.title}</a></td>
            <td>${s.date || 'Today'}</td>
            <td><span class="badge badge-${s.status}">${s.status.toUpperCase()}</span></td>
            <td>
              <a href="/sessions/${s.id}" class="btn btn-sm btn-secondary">View</a>
              ${s.status === 'running' ? `<a href="/live/${s.id}" class="btn btn-sm btn-primary">Live</a>` : ''}
            </td>
          </tr>
        `).join('');
      } else {
        sessTbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#94a3b8;">No sessions conducted yet.</td></tr>';
      }
    }

    // Render Recent Suggestions
    const sugTbody = document.getElementById('recent-suggestions-tbody');
    if (sugTbody) {
      if (data.recent_suggestions && data.recent_suggestions.length > 0) {
        sugTbody.innerHTML = data.recent_suggestions.map(sg => `
          <div style="border-left: 4px solid var(--primary); padding: 10px 14px; margin-bottom: 12px; background: #f8fafc; border-radius: 4px;">
            <div style="font-size: 13px; font-weight: 600; color: #0f172a;">${sg.pattern_summary}</div>
            <ul style="margin: 6px 0 0 18px; font-size: 12.5px; color: #334155;">
              ${(sg.actionable_suggestions || []).map(a => `<li>${a}</li>`).join('')}
            </ul>
            <div style="margin-top: 6px; font-size: 11px; color: #64748b;">
              Confidence: <strong>${sg.confidence_level}</strong> | Engine: <code>${sg.source_engine}</code>
            </div>
          </div>
        `).join('');
      } else {
        sugTbody.innerHTML = '<div style="color:#94a3b8; font-size:13px; text-align:center; padding:16px;">No recent recommendations generated.</div>';
      }
    }

  } catch (err) {
    console.error(err);
    showToast('Failed to refresh dashboard: ' + err.message, 'error');
  }
}
