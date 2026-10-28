// Charts and Analytics visualization script using Chart.js
function renderEngagementCharts(timeline) {
  if (!timeline || timeline.length === 0) return;

  const labels = timeline.map(w => `T+${Math.round(w.window_end)}s`);
  const fusedScores = timeline.map(w => w.fused_score);
  const visualScores = timeline.map(w => w.visual_score);
  const audioScores = timeline.map(w => w.audio_score);
  const confidences = timeline.map(w => (w.confidence * 100).toFixed(0));

  // 1. Fused Score Timeline Chart
  const fusedCtx = document.getElementById('fused-trend-chart');
  if (fusedCtx && typeof Chart !== 'undefined') {
    new Chart(fusedCtx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Estimated Multimodal Indicator (0-100)',
          data: fusedScores,
          borderColor: '#0f766e',
          backgroundColor: 'rgba(15, 118, 110, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6,
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: {
            min: 0,
            max: 100,
            title: { display: true, text: 'Indicator Index' }
          },
          x: {
            title: { display: true, text: 'Session Timeline' }
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              afterLabel: function(context) {
                const item = timeline[context.dataIndex];
                return [
                  `Status: ${item.status}`,
                  `Visual Score: ${item.visual_score || 'N/A'} (Weight ${item.visual_weight})`,
                  `Audio Score: ${item.audio_score || 'N/A'} (Weight ${item.audio_weight})`,
                  `Confidence: ${(item.confidence * 100).toFixed(0)}%`
                ];
              }
            }
          }
        }
      }
    });
  }

  // 2. Modality Comparison Chart (Visual vs Audio)
  const compCtx = document.getElementById('modality-comparison-chart');
  if (compCtx && typeof Chart !== 'undefined') {
    new Chart(compCtx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Visual Indicator (Posture & Movement)',
            data: visualScores,
            borderColor: '#3b82f6',
            borderDash: [4, 4],
            fill: false,
            tension: 0.2,
          },
          {
            label: 'Acoustic Interaction (Speech Density & Dynamics)',
            data: audioScores,
            borderColor: '#f59e0b',
            fill: false,
            tension: 0.2,
          }
        ]
      },
      options: {
        responsive: true,
        scales: {
          y: { min: 0, max: 100 }
        }
      }
    });
  }
}
