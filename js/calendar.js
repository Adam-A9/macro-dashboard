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
    const lastClass = isLast    ? ' cal-grid-last' : '';
    const fomc      = ev.freq === 'Fed';
    const fomcClass = fomc      ? ' cal-fomc'      : '';
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
        (ev.impact ? '<span class="cal-impact" style="margin-left:auto;">HIGH IMPACT</span>' : '') +
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
// Maps FRED release_id → { time, freq, source, impact }
// Used to enrich dynamically fetched release dates.
const RELEASE_META = {
  10:  { time: '08:30', freq: 'MoM', source: 'BLS',            impact: true  }, // CPI
  11:  { time: '08:30', freq: 'MoM', source: 'BLS',            impact: false }, // Import/Export Prices
  15:  { time: '08:30', freq: 'MoM', source: 'Census',         impact: true  }, // Retail Sales
  17:  { time: '10:00', freq: 'MoM', source: 'Conference Board',impact: false }, // Consumer Confidence
  19:  { time: '10:00', freq: 'MoM', source: 'NAR',            impact: false }, // Existing Home Sales
  21:  { time: '13:30', freq: 'MoM', source: 'Federal Reserve',impact: false }, // M2 / H.6 Money Stock
  31:  { time: '08:30', freq: 'MoM', source: 'BLS',            impact: false }, // PPI
  46:  { time: '08:30', freq: 'MoM', source: 'BLS',            impact: true  }, // Employment Situation
  50:  { time: '08:30', freq: 'WoW', source: 'Dept of Labor',  impact: false }, // Initial Jobless Claims
  51:  { time: '08:30', freq: 'MoM', source: 'BLS',            impact: false }, // JOLTS
  53:  { time: '08:30', freq: 'QoQ', source: 'BEA',            impact: true  }, // GDP
  54:  { time: '10:00', freq: 'MoM', source: 'Census',         impact: false }, // New Residential Sales
  55:  { time: '08:30', freq: 'MoM', source: 'BEA',            impact: false }, // Personal Income/Outlays (PCE)
  56:  { time: '08:30', freq: 'MoM', source: 'Census',         impact: false }, // Housing Starts & Permits
  82:  { time: '10:00', freq: 'MoM', source: 'Conference Board',impact: false }, // Leading Indicators
  86:  { time: '09:15', freq: 'MoM', source: 'Federal Reserve',impact: false }, // Industrial Production
  113: { time: '08:30', freq: 'QoQ', source: 'BLS',            impact: false }, // Employment Cost Index
  118: { time: '09:00', freq: 'MoM', source: 'S&P/Case-Shiller',impact: false }, // Case-Shiller HPI
  160: { time: '10:00', freq: 'MoM', source: 'ISM',            impact: false }, // ISM Manufacturing
  161: { time: '10:00', freq: 'MoM', source: 'ISM',            impact: false }, // ISM Services
  175: { time: '10:00', freq: 'MoM', source: 'Census',         impact: false }, // Construction Spending
  180: { time: '10:00', freq: 'MoM', source: 'Univ of Michigan',impact: false }, // Consumer Sentiment
  200: { time: '10:00', freq: 'MoM', source: 'NAR',            impact: false }, // Pending Home Sales
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
        .filter(r => r.date >= today && r.date <= future)
        .map(r => {
          const meta = RELEASE_META[r.release_id] || {};
          return {
            date:   r.date,
            time:   meta.time   || '',
            event:  r.release_name,
            freq:   meta.freq   || 'MoM',
            source: meta.source || 'FRED',
            impact: meta.impact || false
          };
        });
    }
  } catch (e) {
    // If FRED calendar fetch fails, continue with FOMC only
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
        impact: true
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
