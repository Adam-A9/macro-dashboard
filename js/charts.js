// ─── CHART.JS DEFAULTS ───────────────────────────────────
Chart.defaults.color       = '#d8eaf5';
Chart.defaults.font.family = "'Space Mono', monospace";
Chart.defaults.font.size   = 10;

// ─── LINE CHART ──────────────────────────────────────────
function makeLineChart(canvasId, labels, data, color, fill = true) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  if (charts[canvasId]) charts[canvasId].destroy();

  const gradient = ctx.createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0, color + '33');
  gradient.addColorStop(1, color + '00');

  charts[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data,
        borderColor: color,
        borderWidth: 1.5,
        backgroundColor: fill ? gradient : 'transparent',
        fill,
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBackgroundColor: color,
        pointHoverBorderColor: '#080c10',
        pointHoverBorderWidth: 2,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800, easing: 'easeInOutQuart' },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          backgroundColor: '#0d1117',
          borderColor: color,
          borderWidth: 1,
          titleColor: '#d8eaf5',
          bodyColor: '#e8edf2',
          padding: 10,
          displayColors: false,
          titleFont: { family: "'Space Mono', monospace", size: 10 },
          bodyFont:  { family: "'DM Mono', monospace",   size: 15, weight: '700' },
          callbacks: {
            title: items => items[0].label,
            label: item  => ' ' + Number(item.parsed.y).toLocaleString(undefined, { maximumFractionDigits: 2 })
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(30,45,61,0.6)', drawBorder: false },
          ticks: { maxTicksLimit: 6, maxRotation: 0 }
        },
        y: {
          grid: { color: 'rgba(30,45,61,0.6)', drawBorder: false },
          ticks: { maxTicksLimit: 5 },
          position: 'right'
        }
      }
    }
  });
}

// ─── SPARKLINE ───────────────────────────────────────────
function makeSparkline(canvasId, data, color) {
  const ctx = document.getElementById(canvasId)?.getContext('2d');
  if (!ctx) return;
  if (sparklines[canvasId]) sparklines[canvasId].destroy();

  sparklines[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(() => ''),
      datasets: [{
        data: data.map(d => d.value),
        borderColor: color,
        borderWidth: 1.5,
        backgroundColor: 'transparent',
        fill: false,
        pointRadius: 0,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          backgroundColor: '#0d1117',
          borderColor: color,
          borderWidth: 1,
          titleColor: '#d8eaf5',
          bodyColor: '#e8edf2',
          padding: 8,
          displayColors: false,
          titleFont: { family: "'Space Mono', monospace", size: 9 },
          bodyFont:  { family: "'DM Mono', monospace",   size: 12, weight: '700' },
          callbacks: {
            title: items => data[items[0].dataIndex]?.date ?? '',
            label: item  => ' ' + Number(item.parsed.y).toLocaleString(undefined, { maximumFractionDigits: 2 })
          }
        }
      },
      scales: {
        x: { display: false },
        y: { display: false }
      }
    }
  });
}
