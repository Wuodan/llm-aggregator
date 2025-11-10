(function() {
  const apiBaseEl = document.getElementById('apiBaseScript');
  const apiBase = (apiBaseEl && apiBaseEl.dataset.apiBase) || '';

  const tbl = document.getElementById('tbl');
  const tbody = tbl.querySelector('tbody');
  const updatedEl = document.getElementById('updated');
  const clearBtn = document.getElementById('clearBtn');
  const statsCanvas = document.getElementById('statsData');

  let statsChart = null;

  function initChart() {
    if (!statsCanvas || typeof Chart === 'undefined') return;
    const ctx = statsCanvas.getContext('2d');
    statsChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          data: [],
          borderWidth: 1,
          tension: 0.3,
          fill: true,
          pointRadius: 0
        }]
      },
      options: {
        animation: false,
        scales: {
          x: { display: false },
          y: { display: false, min: 0, max: 100 }
        },
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        elements: { line: { borderJoinStyle: 'round' } }
      }
    });
  }

  async function loadModels() {
    try {
      const res = await fetch(apiBase + '/api/models');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      const rows = data.models || [];

      tbody.innerHTML = '';
      rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = [
          '<td>' + (row.id || '') + '</td>',
          '<td>' + (row.server_port || '') + '</td>',
          '<td>' + (
            Array.isArray(row.types)
              ? row.types.join(', ')
              : (row.types || '')
          ) + '</td>',
          '<td>' + (row.summary || '') + '</td>'
        ].join('');
        tbody.appendChild(tr);
      });

      tbl.style.display = rows.length ? '' : 'none';
      updatedEl.textContent = 'Last update: ' + new Date().toLocaleTimeString();
    } catch (err) {
      console.warn('loadModels failed', err);
      updatedEl.textContent = 'Failed to load models';
      tbl.style.display = 'none';
    }
  }

  async function refreshStats() {
    if (!statsChart) return;
    try {
      const res = await fetch(apiBase + '/api/stats');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      if (!Array.isArray(data)) return;

      statsChart.data.labels = data.map((_, i) => i);
      statsChart.data.datasets[0].data = data;
      statsChart.update();
    } catch (err) {
      console.warn('Stats chart fetch failed', err);
    }
  }

  async function clearData() {
    if (!confirm('Clear all model data?')) return;
    try {
      const res = await fetch(apiBase + '/api/clear', { method: 'POST' });
      if (!res.ok) {
        alert('Failed to clear data (' + res.status + ')');
        return;
      }
      await loadModels();
    } catch (err) {
      console.error('Error clearing data', err);
      alert('Error clearing data (see console)');
    }
  }

  function init() {
    initChart();
    loadModels();
    refreshStats();
    setInterval(loadModels, 10000);
    setInterval(refreshStats, 5000);

    if (clearBtn) clearBtn.addEventListener('click', clearData);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
