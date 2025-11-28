(() => {
  const apiBaseEl = document.getElementById('apiBaseScript');
  const apiBase = (apiBaseEl?.dataset.apiBase) || '';

  const tbl = document.getElementById('tbl');
  const tbody = tbl.querySelector('tbody');
  const updatedEl = document.getElementById('updated');
  const clearBtn = document.getElementById('clearBtn');
  const statsCanvas = document.getElementById('statsData');
  const ramLabel = document.getElementById('ramLabel');

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

  function toGiB(bytes) {
    if (bytes === null || bytes === undefined) return "";
    if (typeof bytes !== "number" || Number.isNaN(bytes) || bytes < 0) return "";

    const GiB = 1024 ** 3;
    return `${(bytes / GiB).toFixed(1)} GiB`;
  }


  const QUANT_BITS = {
    Q2: 3.0,
    Q3: 4.0,
    Q4: 5.0,
    Q5: 6.3,
    Q6: 7.0,
    Q8: 9.0,
    F16: 16.0,
    FP16: 16.0,
    F32: 32.0,
    FP32: 32.0,
  };

  const QUANT_TOKENS = Object.keys(QUANT_BITS).sort((a, b) => b.length - a.length);

  function quantToBits(q) {
    if (!q) return null;
    const s = String(q).toUpperCase();
    for (const tok of QUANT_TOKENS) {
      if (s.includes(tok)) return QUANT_BITS[tok];
    }
    return null;
  }

  function bytesPerParam(q) {
    const bits = quantToBits(q);
    if (bits == null) return null;
    return bits / 8.0;
  }

  function parseParams(param) {
    if (param === null || param === undefined) return null;
    if (typeof param === "number") {
      return Number.isFinite(param) && param > 0 ? param : null;
    }
    const s = String(param).trim().toUpperCase();
    if (!s) return null;

    const matchB = s.match(/^([0-9]+(?:\.[0-9]+)?)\s*B$/);
    if (matchB) {
      const v = Number(matchB[1]);
      return Number.isFinite(v) && v > 0 ? v * 1e9 : null;
    }

    const n = Number(s);
    return Number.isFinite(n) && n > 0 ? n : null;
  }
  
  function estimateRamGiB(meta) {
    if (!meta) return "";
    // --- primary: file size × overhead ---
    if (meta.size && Number.isFinite(meta.size) && meta.size > 0) {
      const est = meta.size * 1.2; // or 1.1
      return toGiB(est);
    }
    // --- fallback: params × quant ---
    const params = parseParams(meta.param);
    const bpp = bytesPerParam(meta.quant);
    if (params && bpp) {
      const bytes = params * bpp;
      if (Number.isFinite(bytes) && bytes > 0) {
        return toGiB(bytes * 1.1);
      }
    }
    // --- neither available ---
    return "";
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
          `<td>${model.provider || ''}</td>`,
          `<td class="nowrap">${meta.base_url || ''}</td>`,
          `<td class="num">${estimateRamGiB(meta)}</td>`,
          `<td>${
            Array.isArray(meta.types)
              ? meta.types.join(', ')
              : meta.types || ''
          }</td>`,
          `<td>${meta.model_family || ''}</td>`,
          `<td class="num">${meta.context_size || ''}</td>`,
          `<td>${meta.quant || ''}</td>`,
          `<td class="num">${meta.param || ''}</td>`,
          `<td class="num">${toGiB(meta.size)}</td>`,
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

  async function loadRamTotal() {
    if (!ramLabel) return;
    try {
      const res = await fetch(`${apiBase}/api/ram`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const totalBytes = typeof data.total_bytes === "number" ? data.total_bytes : null;
      const totalGiB = toGiB(totalBytes);
      if (totalGiB) {
        ramLabel.textContent = `% RAM (total: ${totalGiB})`;
      }
    } catch (err) {
      console.warn('RAM total fetch failed', err);
    }
  }

  function init() {
    initChart();
    loadModels();
    refreshStats();
    loadRamTotal();
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
