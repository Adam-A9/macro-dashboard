// ─── HEATMAP HELPERS ─────────────────────────────────────
// These reference HIGHER_IS_GOOD defined per-page in the inline script.

function cellColor(val, sName, isChange) {
  if (sName === 'Spread') return val >= 0 ? 'rgba(0,190,90,0.38)' : 'rgba(220,40,60,0.38)';
  if (isChange) {
    const good = HIGHER_IS_GOOD.includes(sName) ? val >= 0 : val <= 0;
    return good ? 'rgba(0,190,90,0.38)' : 'rgba(220,40,60,0.38)';
  }
  return null;
}

function gradientColor(t, higherIsGood) {
  const g = higherIsGood ? t : 1 - t;
  if (g < 0.5) {
    const r = Math.round(180 + (0.5 - g) * 2 * 75);
    return 'rgba(' + r + ',40,60,0.4)';
  }
  const gr = Math.round(80 + (g - 0.5) * 2 * 150);
  return 'rgba(0,' + gr + ',60,0.4)';
}

// ─── UPDATE KPI CARD ─────────────────────────────────────
// References globals: FRED_SERIES, HIGHER_IS_GOOD, DUAL_ROW, seriesRawData
function updateCard(name, rawObs) {
  seriesRawData[name] = rawObs;
  const obs = filterToTwoYears(rawObs);
  if (obs.length < 2) return;

  const cfg    = FRED_SERIES[name];
  const latest = obs[obs.length - 1];
  const prior  = obs[obs.length - 2];
  const change = latest.value - prior.value;
  const pct    = (change / Math.abs(prior.value)) * 100;
  const pos    = change >= 0;

  const valEl  = document.getElementById('val-'  + name);
  const chgEl  = document.getElementById('chg-'  + name);
  const dateEl = document.getElementById('date-' + name);
  const tipEl  = document.getElementById('tip-'  + name);

  if (tipEl) tipEl.textContent = cfg.desc || '';
  valEl.classList.remove('loading-text');
  valEl.innerHTML = latest.value.toLocaleString(undefined, { maximumFractionDigits: cfg.decimals }) +
    '<span class="kpi-unit">' + cfg.unit + '</span>';
  chgEl.className  = 'kpi-change neutral';
  chgEl.textContent = '';
  dateEl.textContent = cfg.freq;

  // Sparkline — use cfg.bar colour if defined, otherwise cyan default
  makeSparkline('spark-' + name, obs, cfg.bar || '#00d4ff');

  // ── Mini heatmap table ────────────────────────────────
  const tableObs9 = obs.slice(-9);
  const wrap = document.getElementById('mini-table-' + name);
  if (!wrap || tableObs9.length < 2) return;

  const displayObs = tableObs9.slice(-8);
  const headers    = displayObs.map(d => {
    const p = d.date.split('-');
    return '<th>' + p[1] + '/' + p[2].slice(0, 2) + '/' + p[0].slice(2) + '</th>';
  }).join('');

  if (DUAL_ROW.includes(name)) {
    // Show YoY % change row
    const fullObs = seriesRawData[name] || obs;
    const yoyVals = displayObs.map(d => {
      const priorDate = (parseInt(d.date.slice(0, 4)) - 1) + d.date.slice(4);
      const pr = fullObs.find(p => p.date === priorDate) ||
        fullObs.filter(p => p.date < d.date && p.date >= priorDate).slice(-1)[0];
      return pr ? ((d.value - pr.value) / Math.abs(pr.value)) * 100 : null;
    });
    const yoyCells = yoyVals.map((v, i) => {
      if (v === null) return '<td style="color:var(--muted)">–</td>';
      return '<td>' + (v >= 0 ? '+' : '') + v.toFixed(2) + '%</td>';
    }).join('');
    wrap.innerHTML =
      '<table class="mini-table"><thead><tr><th></th>' + headers + '</tr></thead>' +
      '<tbody><tr>' +
        '<td style="color:var(--muted);font-size:8px;padding-right:6px;white-space:nowrap;">YoY</td>' +
        yoyCells +
      '</tr></tbody></table>';
  } else {
    // Show raw value row
    const cells = displayObs.map((d, i) => {
      return '<td>' +
        d.value.toLocaleString(undefined, { maximumFractionDigits: cfg.decimals }) + cfg.unit + '</td>';
    }).join('');
    wrap.innerHTML =
      '<table class="mini-table"><thead><tr>' + headers + '</tr></thead>' +
      '<tbody><tr>' + cells + '</tr></tbody></table>';
  }
}

// ─── STANDARD FETCH ALL ──────────────────────────────────
// References globals: FRED_SERIES, MARKET (both defined per-page).
// index.html overrides this function to add ALFRED revision logic.
async function fetchAll() {
  const btn   = document.getElementById('refreshBtn');
  const errEl = document.getElementById('errorMsg');
  btn.classList.add('loading');
  btn.textContent    = '⟳ Loading…';
  errEl.style.display = 'none';

  const errors = [];

  // FRED series
  const fredNames = Object.keys(FRED_SERIES);
  for (let i = 0; i < fredNames.length; i++) {
    if (i > 0) await sleep(300);
    const name = fredNames[i];
    try {
      const obs = await fetchFRED(FRED_SERIES[name].id, 80);
      updateCard(name, obs);
    } catch (e) {
      errors.push('FRED ' + FRED_SERIES[name].id + ': ' + e.message);
      const el = document.getElementById('val-' + name);
      if (el) { el.textContent = 'Error'; el.classList.add('loading-text'); }
    }
  }

  // Market / Yahoo Finance
  const marketSymbols = Object.keys(MARKET);
  for (let i = 0; i < marketSymbols.length; i++) {
    if (i > 0) await sleep(600);
    const sym = marketSymbols[i];
    const cfg = MARKET[sym];
    try {
      const obs    = await fetchMarket(sym);
      if (obs.length > 1) {
        const latest = obs[obs.length - 1];
        const prior  = obs[obs.length - 2];
        const pct    = ((latest.value - prior.value) / Math.abs(prior.value)) * 100;
        const pos    = pct >= 0;
        document.getElementById(cfg.valId).textContent =
          latest.value.toLocaleString(undefined, { maximumFractionDigits: 2 });
        const chgEl = document.getElementById(cfg.chgId);
        if (chgEl) {
          chgEl.textContent = (pos ? '+' : '') + pct.toFixed(2) + '%';
          chgEl.style.color = pos ? 'var(--green)' : 'var(--red)';
        }
        makeLineChart(cfg.canvasId, obs.map(d => d.date), obs.map(d => d.value), cfg.color);
      }
    } catch (e) {
      errors.push('Market (' + cfg.label + '): ' + e.message);
      document.getElementById(cfg.valId).textContent = 'N/A';
      const chgEl = document.getElementById(cfg.chgId);
      if (chgEl) chgEl.textContent = '–';
    }
  }

  _finishFetch(errors);
}

// Shared post-fetch housekeeping (timestamp, error display, auto-refresh timer)
function _finishFetch(errors) {
  const btn   = document.getElementById('refreshBtn');
  const errEl = document.getElementById('errorMsg');
  const now   = new Date();
  const ts    = now.toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
  document.getElementById('last-updated').textContent = 'Updated ' + ts;
  const footer = document.getElementById('footer-ts');
  if (footer) footer.textContent = 'Last fetch: ' + ts;

  if (errors.length > 0) {
    errEl.innerHTML     = errors.map(e => '⚠ ' + e).join('<br>');
    errEl.style.display = 'block';
  }
  btn.classList.remove('loading');
  btn.textContent = '↻ Refresh';

  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(fetchAll, REFRESH_INTERVAL);
}

// ─── EXPAND MODAL ───────────────────────────────────────
function openModal(name) {
  const cfg = FRED_SERIES[name];
  if (!cfg) return;
  const obs = seriesRawData[name];
  if (!obs || obs.length < 2) return;

  const modal   = document.getElementById('kpi-modal');
  const overlay = document.getElementById('kpi-modal-overlay');
  if (!modal || !overlay) return;

  // Header info
  document.getElementById('modal-title').textContent = cfg.label;
  document.getElementById('modal-series').textContent = cfg.id;
  document.getElementById('modal-freq').textContent = cfg.freq;

  const latest = obs[obs.length - 1];
  const prior  = obs[obs.length - 2];
  const change = latest.value - prior.value;
  const pct    = (change / Math.abs(prior.value)) * 100;
  const pos    = change >= 0;

  document.getElementById('modal-value').innerHTML =
    latest.value.toLocaleString(undefined, { maximumFractionDigits: cfg.decimals }) +
    '<span style="font-size:16px;color:var(--muted);font-weight:400;margin-left:4px;">' + cfg.unit + '</span>';

  const chgEl = document.getElementById('modal-change');
  chgEl.textContent = (pos ? '▲' : '▼') + ' ' +
    Math.abs(change).toLocaleString(undefined, { maximumFractionDigits: cfg.decimals }) +
    ' (' + pct.toFixed(2) + '%)';
  chgEl.className = 'kpi-change ' + (pos ? 'pos' : 'neg');

  // Full chart
  makeModalChart('modal-chart-canvas', obs.map(d => d.date), obs.map(d => d.value), cfg.bar || '#00d4ff', cfg.unit);

  // Enlarged heatmap table
  const tableWrap = document.getElementById('modal-table');
  const srcTable = document.getElementById('mini-table-' + name);
  tableWrap.innerHTML = srcTable ? srcTable.innerHTML : '';

  // Recession legend — show only if recession bands overlap
  const firstDate = obs[0].date, lastDate = obs[obs.length - 1].date;
  const hasRecession = NBER_RECESSIONS.some(([s, e]) => s <= lastDate && e >= firstDate);
  document.getElementById('modal-recession-legend').style.display = hasRecession ? 'flex' : 'none';

  // Description
  document.getElementById('modal-desc').textContent = cfg.desc || '';

  // Show
  overlay.classList.add('active');
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  const modal   = document.getElementById('kpi-modal');
  const overlay = document.getElementById('kpi-modal-overlay');
  if (modal) modal.classList.remove('active');
  if (overlay) overlay.classList.remove('active');
  document.body.style.overflow = '';
  if (modalChart) { modalChart.destroy(); modalChart = null; }
}

// ─── PAGE INIT ───────────────────────────────────────────
// Called on DOMContentLoaded. Populates tooltips and kicks off the first fetch.
// Also calls fetchCalendar() if it is defined (only loaded on index.html).
function initPage() {
  Object.keys(FRED_SERIES).forEach(name => {
    const tip = document.getElementById('tip-' + name);
    if (tip && FRED_SERIES[name].desc) tip.textContent = FRED_SERIES[name].desc;
  });
  document.querySelectorAll('.kpi-info').forEach(icon => {
    const card = icon.closest('.kpi-card');
    icon.addEventListener('mouseenter', () => card.classList.add('show-tip'));
    icon.addEventListener('mouseleave', () => card.classList.remove('show-tip'));
  });
  // Click-to-expand modal on KPI cards
  document.querySelectorAll('.kpi-card').forEach(card => {
    card.style.cursor = 'pointer';
    card.addEventListener('click', (e) => {
      // Don't open modal if clicking the info icon
      if (e.target.closest('.kpi-info')) return;
      const name = card.id.replace('card-', '');
      openModal(name);
    });
  });

  // Modal close handlers
  const overlay = document.getElementById('kpi-modal-overlay');
  const closeBtn = document.getElementById('modal-close-btn');
  if (overlay) overlay.addEventListener('click', closeModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });

  fetchAll();
  if (typeof fetchCalendar === 'function') fetchCalendar();
}

window.addEventListener('DOMContentLoaded', initPage);
