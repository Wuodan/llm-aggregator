(() => {
  const apiBaseEl = document.getElementById('apiBaseScript');
  const apiBase = (apiBaseEl?.dataset.apiBase) || '';

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
      const res = await fetch(`${apiBase}/v1/models`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const models = json.data || [];

      tbody.innerHTML = '';
      models.forEach(model => {
        const tr = document.createElement('tr');
        const id = model.id || '';
        const meta = model.meta || {};
        tr.innerHTML = [
          `<td>${id}</td>`,
          `<td>${meta.base_url || ''}</td>`,
          `<td>${
            Array.isArray(meta.types)
              ? meta.types.join(', ')
              : meta.types || ''
          }</td>`,
          `<td>${meta.model_family || ''}</td>`,
          `<td>${meta.context_size || ''}</td>`,
          `<td>${meta.quant || ''}</td>`,
          `<td>${meta.param || ''}</td>`,
          `<td>${meta.summary || ''}</td>`
        ].join('');
        tbody.appendChild(tr);
      });

      tbl.style.display = models.length ? '' : 'none';
      updatedEl.textContent = `Last update: ${new Date().toLocaleTimeString()}`;
    } catch (err) {
      console.warn('loadModels failed', err);
      updatedEl.textContent = 'Failed to load models';
      tbl.style.display = 'none';
    }
  }

  async function refreshStats() {
    if (!statsChart) return;
    try {
      const res = await fetch(`${apiBase}/api/stats`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
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
    if (!confirm('Try it!\nWatch AI recreate the info!')) return;
    try {
      const res = await fetch(`${apiBase}/api/clear`, { method: 'POST' });
      if (!res.ok) {
        alert(`Failed to clear data (${res.status})`);
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
    setInterval(loadModels, 20000);
    setInterval(refreshStats, 10000);

    if (clearBtn) clearBtn.addEventListener('click', clearData);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
