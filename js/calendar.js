// ─── CALENDAR DISPLAY HELPERS ────────────────────────────
const FREQ_COLORS = {
  DoD: '#00d4ff', WoW: '#a78bfa', MoM: '#00ff9d', QoQ: '#ffd700', Fed: '#ff3b5c'
};

function formatCalDate(dateStr) {
  const d = new Date(dateStr + 'T12:00:00'); // noon UTC avoids timezone shift
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatCalTime(timeStr) {
  if (!timeStr) return '';
  const [h, m] = timeStr.split(':');
  const hour = parseInt(h, 10);
  return (hour % 12 || 12) + ':' + m + ' ' + (hour >= 12 ? 'pm' : 'am') + ' ET';
}

function renderCalendar(events, from, to) {
  const sorted = [...events].sort((a, b) => new Date(a.date) - new Date(b.date));

  const rangeEl = document.getElementById('cal-range');
  if (rangeEl) rangeEl.textContent = formatCalDate(from) + ' — ' + formatCalDate(to);

  const grid = document.getElementById('calendarGrid');
  if (!grid) return;

  if (sorted.length === 0) {
    grid.innerHTML = '<div class="cal-empty">No events in the next 14 days.</div>';
    return;
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  let html = '';
  sorted.forEach((ev, idx) => {
    const isLast    = idx === sorted.length - 1;
    const lastClass = isLast  ? ' cal-grid-last' : '';
    const fomc      = ev.freq === 'Fed';
    const fomcClass = fomc    ? ' cal-fomc'      : '';
    const color     = FREQ_COLORS[ev.freq] || '#5a7a94';
    const dateStr   = formatCalDate(ev.date);
    const timeStr   = ev.time ? formatCalTime(ev.time) : '';

    const evParts  = ev.date.split('-').map(Number);
    const evDate   = new Date(evParts[0], evParts[1] - 1, evParts[2]);
    const daysAway = Math.round((evDate - today) / 86400000);
    const daysColor =
      daysAway === 0 ? 'var(--accent2)' :
      daysAway <= 3  ? 'var(--warn)'    : 'var(--text)';
    const daysLabel = daysAway === 0 ? 'today' : daysAway === 1 ? 'day' : 'days';

    // Impact badge — only render for high and medium; skip low
    let impactBadge = '';
    if (ev.impact === 'high' || ev.impact === true) {
      impactBadge = '<span class="cal-impact cal-impact-high" style="margin-left:auto;">HIGH</span>';
    } else if (ev.impact === 'medium') {
      impactBadge = '<span class="cal-impact cal-impact-medium" style="margin-left:auto;">MED</span>';
    }

    html +=
      '<div class="cal-date' + lastClass + fomcClass + '">' +
        '<div class="cal-date-day">' + dateStr + '</div>' +
        (timeStr ? '<div class="cal-date-time">' + timeStr + '</div>' : '') +
      '</div>' +

      '<div class="cal-days' + lastClass + fomcClass + '">' +
        '<div class="cal-days-num" style="color:' + daysColor + ';">' +
          (daysAway === 0 ? '–' : daysAway) +
        '</div>' +
        '<div class="cal-days-label">' + daysLabel + '</div>' +
      '</div>' +

      '<div class="cal-event' + fomcClass + lastClass + '">' +
        '<span class="cal-bar" style="background:' + color + ';"></span>' +
        '<div>' +
          '<div class="cal-name">' + ev.event + '</div>' +
          '<div class="cal-sub">' + ev.source + ' · ' + ev.freq + '</div>' +
        '</div>' +
        impactBadge +
      '</div>' +

      '<div class="cal-prev' + fomcClass + lastClass + '">' +
        '<div style="text-align:right;">' +
          '<div class="cal-prev-label">' + ev.freq + '</div>' +
        '</div>' +
      '</div>';
  });

  grid.innerHTML = html;
}

// ─── FRED RELEASE METADATA ───────────────────────────────
// Only releases listed here are shown in the calendar — everything else is
// filtered out. The FRED releases/dates API returns hundreds of obscure series;
// this allowlist keeps the calendar focused on market-moving events.
//
// impact: 'high' | 'medium' | 'low'
const RELEASE_META = {
  10:  { name: 'Consumer Price Index (CPI)',      time: '08:30', freq: 'MoM', source: 'BLS',             impact: 'high'   },
  11:  { name: 'Import & Export Prices',           time: '08:30', freq: 'MoM', source: 'BLS',             impact: 'low'    },
  15:  { name: 'Retail Sales',                     time: '08:30', freq: 'MoM', source: 'Census',          impact: 'high'   },
  17:  { name: 'Consumer Confidence',              time: '10:00', freq: 'MoM', source: 'Conference Board',impact: 'medium' },
  19:  { name: 'Existing Home Sales',              time: '10:00', freq: 'MoM', source: 'NAR',             impact: 'low'    },
  21:  { name: 'M2 Money Supply',                  time: '13:30', freq: 'MoM', source: 'Federal Reserve', impact: 'low'    },
  31:  { name: 'Producer Price Index (PPI)',       time: '08:30', freq: 'MoM', source: 'BLS',             impact: 'medium' },
  46:  { name: 'Nonfarm Payrolls',                 time: '08:30', freq: 'MoM', source: 'BLS',             impact: 'high'   },
  50:  { name: 'Initial Jobless Claims',           time: '08:30', freq: 'WoW', source: 'Dept of Labor',   impact: 'medium' },
  51:  { name: 'JOLTS Job Openings',               time: '10:00', freq: 'MoM', source: 'BLS',             impact: 'medium' },
  53:  { name: 'GDP',                              time: '08:30', freq: 'QoQ', source: 'BEA',             impact: 'high'   },
  54:  { name: 'New Home Sales',                   time: '10:00', freq: 'MoM', source: 'Census',          impact: 'low'    },
  55:  { name: 'PCE / Personal Income',            time: '08:30', freq: 'MoM', source: 'BEA',             impact: 'medium' },
  56:  { name: 'Housing Starts & Permits',         time: '08:30', freq: 'MoM', source: 'Census',          impact: 'medium' },
  82:  { name: 'Leading Economic Indicators',      time: '10:00', freq: 'MoM', source: 'Conference Board',impact: 'low'    },
  86:  { name: 'Industrial Production',            time: '09:15', freq: 'MoM', source: 'Federal Reserve', impact: 'low'    },
  113: { name: 'Employment Cost Index',            time: '08:30', freq: 'QoQ', source: 'BLS',             impact: 'medium' },
  118: { name: 'Case-Shiller Home Prices',         time: '09:00', freq: 'MoM', source: 'S&P/Case-Shiller',impact: 'low'    },
  160: { name: 'ISM Manufacturing PMI',            time: '10:00', freq: 'MoM', source: 'ISM',             impact: 'medium' },
  161: { name: 'ISM Services PMI',                 time: '10:00', freq: 'MoM', source: 'ISM',             impact: 'medium' },
  175: { name: 'Construction Spending',            time: '10:00', freq: 'MoM', source: 'Census',          impact: 'low'    },
  180: { name: 'Consumer Sentiment',               time: '10:00', freq: 'MoM', source: 'Univ of Michigan',impact: 'low'    },
  200: { name: 'Pending Home Sales',               time: '10:00', freq: 'MoM', source: 'NAR',             impact: 'low'    },
};

// FOMC meeting decision dates (announced ~1 year in advance by the Fed).
// Only the decision day (day 2 of each 2-day meeting) is listed.
const FOMC_DATES = [
  { date: '2025-01-29', time: '14:00' },
  { date: '2025-03-19', time: '14:00' },
  { date: '2025-05-07', time: '14:00' },
  { date: '2025-06-18', time: '14:00' },
  { date: '2025-07-30', time: '14:00' },
  { date: '2025-09-17', time: '14:00' },
  { date: '2025-10-29', time: '14:00' },
  { date: '2025-12-10', time: '14:00' },
  { date: '2026-01-28', time: '14:00' },
  { date: '2026-03-18', time: '14:00' },
  { date: '2026-04-29', time: '14:00' },
  { date: '2026-06-17', time: '14:00' },
  { date: '2026-07-29', time: '14:00' },
  { date: '2026-09-16', time: '14:00' },
  { date: '2026-10-28', time: '14:00' },
  { date: '2026-12-09', time: '14:00' },
];

// ─── DYNAMIC CALENDAR FETCH ──────────────────────────────
async function fetchCalendar() {
  const now    = new Date();
  const today  = now.toISOString().slice(0, 10);
  const future = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

  let events = [];

  try {
    const url = 'https://api.stlouisfed.org/fred/releases/dates' +
      '?api_key=' + FRED_API_KEY +
      '&file_type=json' +
      '&realtime_start=' + today +
      '&realtime_end='   + future +
      '&include_release_dates_with_no_data=false';

    const json = await fetchWithProxy(url);

    if (json.release_dates && Array.isArray(json.release_dates)) {
      events = json.release_dates
        .filter(r => r.date >= today && r.date <= future && RELEASE_META[r.release_id])
        .map(r => {
          const meta = RELEASE_META[r.release_id];
          return {
            date:   r.date,
            time:   meta.time,
            event:  meta.name,
            freq:   meta.freq,
            source: meta.source,
            impact: meta.impact
          };
        });
    }
  } catch (e) {
    console.warn('Calendar fetch failed:', e.message);
  }

  // Merge in FOMC dates
  FOMC_DATES.forEach(f => {
    if (f.date >= today && f.date <= future) {
      events.push({
        date:   f.date,
        time:   f.time,
        event:  'Fed Interest Rate Decision',
        freq:   'Fed',
        source: 'Federal Reserve',
        impact: 'high'
      });
    }
  });

  // De-duplicate by date+event name
  const seen = new Set();
  events = events.filter(ev => {
    const key = ev.date + '|' + ev.event;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  renderCalendar(events, today, future);
}
