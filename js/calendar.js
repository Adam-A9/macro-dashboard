// ─── CALENDAR DISPLAY HELPERS ────────────────────────────────
const FREQ_COLORS = {
  DoD: '#00d4ff', WoW: '#a78bfa', MoM: '#00ff9d', QoQ: '#ffd700', Fed: '#ff3b5c'
};

function formatCalDate(dateStr) {
  var d = new Date(dateStr + 'T12:00:00'); // noon UTC avoids timezone shift
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatCalTime(timeStr) {
  if (!timeStr) return '';
  var parts = timeStr.split(':');
  var hour = parseInt(parts[0], 10);
  return (hour % 12 || 12) + ':' + parts[1] + ' ' + (hour >= 12 ? 'pm' : 'am') + ' ET';
}

function renderCalendar(events, from, to) {
  var sorted = events.slice().sort(function(a, b) { return new Date(a.date) - new Date(b.date); });

  var rangeEl = document.getElementById('cal-range');
  if (rangeEl) rangeEl.textContent = formatCalDate(from) + ' — ' + formatCalDate(to);

  var grid = document.getElementById('calendarGrid');
  if (!grid) return;

  if (sorted.length === 0) {
    grid.innerHTML = '<div class="cal-empty">No recent or upcoming events found.</div>';
    return;
  }

  var today = new Date();
  today.setHours(0, 0, 0, 0);

  var html =
    '<div class="cal-hdr"></div>' +
    '<div class="cal-hdr"></div>' +
    '<div class="cal-hdr"></div>' +
    '<div class="cal-hdr cal-hdr-label">Previous</div>' +
    '<div class="cal-hdr cal-hdr-label">Estimate</div>' +
    '<div class="cal-hdr cal-hdr-label">Actual</div>';

  sorted.forEach(function(ev, idx) {
    var isLast    = idx === sorted.length - 1;
    var lastClass = isLast  ? ' cal-grid-last' : '';
    var fomc      = ev.freq === 'Fed';
    var fomcClass = fomc    ? ' cal-fomc'      : '';
    var color     = FREQ_COLORS[ev.freq] || '#5a7a94';
    var dateStr   = formatCalDate(ev.date);
    var timeStr   = ev.time ? formatCalTime(ev.time) : '';

    var evParts  = ev.date.split('-').map(Number);
    var evDate   = new Date(evParts[0], evParts[1] - 1, evParts[2]);
    var daysAway = Math.round((evDate - today) / 86400000);
    var isPast   = daysAway < 0;
    var pastClass = isPast ? ' cal-past' : '';
    var daysColor =
      isPast         ? 'var(--muted)'   :
      daysAway === 0 ? 'var(--accent2)' :
      daysAway <= 3  ? 'var(--warn)'    : 'var(--text)';
    var daysLabel =
      isPast         ? (daysAway === -1 ? 'day ago' : 'days ago') :
      daysAway === 0 ? 'today' :
      daysAway === 1 ? 'day' : 'days';
    var daysNum = isPast ? Math.abs(daysAway) : (daysAway === 0 ? '–' : daysAway);

    // Impact badge — only render for high and medium
    var impactBadge = '';
    if (ev.impact === 'high' || ev.impact === true) {
      impactBadge = '<span class="cal-impact cal-impact-high" style="margin-left:auto;">HIGH</span>';
    } else if (ev.impact === 'medium') {
      impactBadge = '<span class="cal-impact cal-impact-medium" style="margin-left:auto;">MED</span>';
    }

    html +=
      '<div class="cal-date' + lastClass + fomcClass + pastClass + '">' +
        '<div class="cal-date-day">' + dateStr + '</div>' +
        (timeStr ? '<div class="cal-date-time">' + timeStr + '</div>' : '') +
      '</div>' +

      '<div class="cal-days' + lastClass + fomcClass + pastClass + '">' +
        '<div class="cal-days-num" style="color:' + daysColor + ';">' +
          daysNum +
        '</div>' +
        '<div class="cal-days-label">' + daysLabel + '</div>' +
      '</div>' +

      '<div class="cal-event' + fomcClass + lastClass + pastClass + '">' +
        '<span class="cal-bar" style="background:' + color + ';' + (isPast ? 'opacity:0.4;' : '') + '"></span>' +
        '<div>' +
          '<div class="cal-name">' + ev.event + '</div>' +
          '<div class="cal-sub">' + ev.source + ' · ' + ev.freq + '</div>' +
        '</div>' +
        impactBadge +
      '</div>' +

      '<div class="cal-col-prev' + fomcClass + lastClass + pastClass + '">' +
        (ev.prior != null ? '<span class="cal-est-val cal-est-prior">' + ev.prior + (ev.unit || '') + '</span>' : '<span class="cal-est-dash">–</span>') +
      '</div>' +

      '<div class="cal-col-est' + fomcClass + lastClass + pastClass + '">' +
        (ev.estimate != null ? '<span class="cal-est-val">' + ev.estimate + (ev.unit || '') + '</span>' : '<span class="cal-est-dash">–</span>') +
      '</div>' +

      '<div class="cal-col-act' + fomcClass + lastClass + pastClass + '">' +
        (function() {
          if (ev.actual == null) return '<span class="cal-est-dash">–</span>';
          var surpriseClass = '';
          if (ev.estimate != null) {
            surpriseClass = ev.actual > ev.estimate ? ' cal-beat' : ev.actual < ev.estimate ? ' cal-miss' : ' cal-inline';
          }
          return '<span class="cal-est-val' + surpriseClass + '">' + ev.actual + (ev.unit || '') + '</span>';
        })() +
      '</div>';
  });

  grid.innerHTML = html;
}

// ─── SERIES METADATA ─────────────────────────────────────────
// Maps series_id → display metadata for Supabase rows
const SERIES_META = {
  'CPIAUCSL':       { name: 'Consumer Price Index (CPI)',      time: '08:30', freq: 'MoM' },
  'CPILFESL':       { name: 'Core CPI',                        time: '08:30', freq: 'MoM' },
  'IR':             { name: 'Import & Export Prices',           time: '08:30', freq: 'MoM' },
  'RSAFS':          { name: 'Retail Sales',                     time: '08:30', freq: 'MoM' },
  'CSCICP03USM665S':{ name: 'Consumer Confidence',              time: '10:00', freq: 'MoM' },
  'EXHOSLUSM495S':  { name: 'Existing Home Sales',             time: '10:00', freq: 'MoM' },
  'M2SL':           { name: 'M2 Money Supply',                  time: '13:30', freq: 'MoM' },
  'PPIACO':         { name: 'Producer Price Index (PPI)',       time: '08:30', freq: 'MoM' },
  'PAYEMS':         { name: 'Nonfarm Payrolls',                 time: '08:30', freq: 'MoM' },
  'ICSA':           { name: 'Initial Jobless Claims',           time: '08:30', freq: 'WoW' },
  'JTSJOL':         { name: 'JOLTS Job Openings',               time: '10:00', freq: 'MoM' },
  'GDP':            { name: 'GDP',                              time: '08:30', freq: 'QoQ' },
  'HSN1F':          { name: 'New Home Sales',                   time: '10:00', freq: 'MoM' },
  'PCEPI':          { name: 'PCE / Personal Income',            time: '08:30', freq: 'MoM' },
  'PCEPILFE':       { name: 'Core PCE',                         time: '08:30', freq: 'MoM' },
  'HOUST':          { name: 'Housing Starts & Permits',         time: '08:30', freq: 'MoM' },
  'USSLIND':        { name: 'Leading Economic Indicators',      time: '10:00', freq: 'MoM' },
  'INDPRO':         { name: 'Industrial Production',            time: '09:15', freq: 'MoM' },
  'ECIWAG':         { name: 'Employment Cost Index',            time: '08:30', freq: 'QoQ' },
  'CSUSHPISA':      { name: 'Case-Shiller Home Prices',         time: '09:00', freq: 'MoM' },
  'MANEMP':         { name: 'ISM Manufacturing PMI',            time: '10:00', freq: 'MoM' },
  'NMFCI':          { name: 'ISM Services PMI',                 time: '10:00', freq: 'MoM' },
  'TTLCONS':        { name: 'Construction Spending',            time: '10:00', freq: 'MoM' },
  'UMCSENT':        { name: 'Consumer Sentiment',               time: '10:00', freq: 'MoM' },
  'PHSI':           { name: 'Pending Home Sales',               time: '10:00', freq: 'MoM' },
  'DGORDER':        { name: 'Durable Goods Orders',            time: '08:30', freq: 'MoM' },
  'CES0500000003':  { name: 'Average Hourly Earnings',          time: '08:30', freq: 'MoM' },
  'BOPGSTB':        { name: 'Trade Balance',                    time: '08:30', freq: 'MoM' },
  'AMTMNO':         { name: 'Factory Orders',                   time: '10:00', freq: 'MoM' },
  'TCU':            { name: 'Capacity Utilization',             time: '09:15', freq: 'MoM' },
  'CCSA':           { name: 'Continuing Jobless Claims',        time: '08:30', freq: 'WoW' },
  'UNRATE':         { name: 'Unemployment Rate',                time: '08:30', freq: 'MoM' },
  'PERMIT':         { name: 'Building Permits',                 time: '08:30', freq: 'MoM' },
  'FEDFUNDS':       { name: 'Fed Interest Rate Decision',       time: '14:00', freq: 'Fed' },
};

// FRED release_id → metadata (used for FRED fallback only)
const RELEASE_META = {
  10:  { name: 'Consumer Price Index (CPI)',      time: '08:30', freq: 'MoM', source: 'BLS',             impact: 'high'   },
  11:  { name: 'Import & Export Prices',           time: '08:30', freq: 'MoM', source: 'BLS',             impact: 'low'    },
  15:  { name: 'Retail Sales',                     time: '08:30', freq: 'MoM', source: 'Census',          impact: 'high'   },
  17:  { name: 'Consumer Confidence',              time: '10:00', freq: 'MoM', source: 'Conference Board',impact: 'medium' },
  19:  { name: 'Existing Home Sales',              time: '10:00', freq: 'MoM', source: 'NAR',             impact: 'low'    },
  21:  { name: 'M2 Money Supply',                  time: '13:30', freq: 'MoM', source: 'Federal Reserve', impact: 'low'    },
  22:  { name: 'Durable Goods Orders',            time: '08:30', freq: 'MoM', source: 'Census',          impact: 'medium' },
  31:  { name: 'Producer Price Index (PPI)',       time: '08:30', freq: 'MoM', source: 'BLS',             impact: 'medium' },
  32:  { name: 'Average Hourly Earnings',          time: '08:30', freq: 'MoM', source: 'BLS',             impact: 'medium' },
  46:  { name: 'Nonfarm Payrolls',                 time: '08:30', freq: 'MoM', source: 'BLS',             impact: 'high'   },
  50:  { name: 'Initial Jobless Claims',           time: '08:30', freq: 'WoW', source: 'Dept of Labor',   impact: 'medium' },
  51:  { name: 'JOLTS Job Openings',               time: '10:00', freq: 'MoM', source: 'BLS',             impact: 'medium' },
  53:  { name: 'GDP',                              time: '08:30', freq: 'QoQ', source: 'BEA',             impact: 'high'   },
  54:  { name: 'New Home Sales',                   time: '10:00', freq: 'MoM', source: 'Census',          impact: 'low'    },
  55:  { name: 'PCE / Personal Income',            time: '08:30', freq: 'MoM', source: 'BEA',             impact: 'medium' },
  56:  { name: 'Housing Starts & Permits',         time: '08:30', freq: 'MoM', source: 'Census',          impact: 'medium' },
  69:  { name: 'Trade Balance',                    time: '08:30', freq: 'MoM', source: 'Census/BEA',      impact: 'medium' },
  82:  { name: 'Leading Economic Indicators',      time: '10:00', freq: 'MoM', source: 'Conference Board',impact: 'low'    },
  83:  { name: 'Factory Orders',                   time: '10:00', freq: 'MoM', source: 'Census',          impact: 'low'    },
  86:  { name: 'Industrial Production',            time: '09:15', freq: 'MoM', source: 'Federal Reserve', impact: 'low'    },
  113: { name: 'Employment Cost Index',            time: '08:30', freq: 'QoQ', source: 'BLS',             impact: 'medium' },
  116: { name: 'Capacity Utilization',             time: '09:15', freq: 'MoM', source: 'Federal Reserve', impact: 'low'    },
  117: { name: 'Continuing Jobless Claims',        time: '08:30', freq: 'WoW', source: 'Dept of Labor',   impact: 'low'    },
  118: { name: 'Case-Shiller Home Prices',         time: '09:00', freq: 'MoM', source: 'S&P/Case-Shiller',impact: 'low'    },
  160: { name: 'ISM Manufacturing PMI',            time: '10:00', freq: 'MoM', source: 'ISM',             impact: 'medium' },
  161: { name: 'ISM Services PMI',                 time: '10:00', freq: 'MoM', source: 'ISM',             impact: 'medium' },
  175: { name: 'Construction Spending',            time: '10:00', freq: 'MoM', source: 'Census',          impact: 'low'    },
  180: { name: 'Consumer Sentiment',               time: '10:00', freq: 'MoM', source: 'Univ of Michigan',impact: 'low'    },
  200: { name: 'Pending Home Sales',               time: '10:00', freq: 'MoM', source: 'NAR',             impact: 'low'    },
};

// FOMC meeting decision dates
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

// ─── SUPABASE FETCH (primary) ────────────────────────────────
// Fetches from `consensus` table with a wider window: 14 days back + 30 days forward
async function fetchFromSupabase(pastDate, futureDate) {
  if (!SUPABASE_ANON) return null;

  var url = SUPABASE_URL + '/rest/v1/consensus' +
    '?select=series_id,release_name,release_date,estimate,actual,prior,unit,source,impact,frequency' +
    '&release_date=gte.' + pastDate +
    '&release_date=lte.' + futureDate +
    '&order=release_date.asc';

  var res = await fetch(url, {
    headers: {
      'apikey': SUPABASE_ANON,
      'Authorization': 'Bearer ' + SUPABASE_ANON,
      'Accept': 'application/json'
    }
  });

  if (!res.ok) throw new Error('Supabase ' + res.status);
  var rows = await res.json();
  if (!Array.isArray(rows) || rows.length === 0) return null;

  return rows.map(function(r) {
    var meta = SERIES_META[r.series_id] || {};
    return {
      date:     r.release_date,
      time:     meta.time || '',
      event:    r.release_name || meta.name || r.series_id,
      freq:     r.frequency || meta.freq || 'MoM',
      source:   r.source || '',
      impact:   r.impact || 'low',
      estimate: r.estimate,
      actual:   r.actual,
      prior:    r.prior,
      unit:     r.unit || ''
    };
  });
}

// ─── FRED FALLBACK ───────────────────────────────────────────
async function fetchFromFRED(pastDate, futureDate) {
  var url = 'https://api.stlouisfed.org/fred/releases/dates' +
    '?api_key=' + FRED_API_KEY +
    '&file_type=json' +
    '&realtime_start=' + pastDate +
    '&realtime_end='   + futureDate +
    '&include_release_dates_with_no_data=false';

  var json = await fetchWithProxy(url);

  if (!json.release_dates || !Array.isArray(json.release_dates)) return [];

  return json.release_dates
    .filter(function(r) { return r.date >= pastDate && r.date <= futureDate && RELEASE_META[r.release_id]; })
    .map(function(r) {
      var meta = RELEASE_META[r.release_id];
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

// ─── DYNAMIC CALENDAR FETCH ──────────────────────────────────
// Shows: last 5 past events + up to 10 upcoming events
async function fetchCalendar() {
  var now       = new Date();
  var today     = now.toISOString().slice(0, 10);
  // Wide fetch window: 14 days back, 30 days forward
  var pastDate  = new Date(now.getTime() - 14 * 86400000).toISOString().slice(0, 10);
  var futureDate = new Date(now.getTime() + 30 * 86400000).toISOString().slice(0, 10);

  var events = [];

  // Try Supabase first, fall back to FRED
  try {
    var supabaseEvents = await fetchFromSupabase(pastDate, futureDate);
    if (supabaseEvents && supabaseEvents.length > 0) {
      events = supabaseEvents;
      console.info('Calendar: loaded ' + events.length + ' events from Supabase');
    } else {
      events = await fetchFromFRED(pastDate, futureDate);
      console.info('Calendar: loaded ' + events.length + ' events from FRED (fallback)');
    }
  } catch (e) {
    console.warn('Calendar: Supabase failed, trying FRED fallback:', e.message);
    try {
      events = await fetchFromFRED(pastDate, futureDate);
    } catch (e2) {
      console.warn('Calendar: FRED fallback also failed:', e2.message);
    }
  }

  // Merge in FOMC dates
  FOMC_DATES.forEach(function(f) {
    if (f.date >= pastDate && f.date <= futureDate) {
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
  var seen = new Set();
  events = events.filter(function(ev) {
    var key = ev.date + '|' + ev.event;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  // Split into past and upcoming
  var pastEvents = events
    .filter(function(ev) { return ev.date < today; })
    .sort(function(a, b) { return new Date(b.date) - new Date(a.date); }) // newest first
    .slice(0, 5)   // last 5 past events
    .reverse();     // back to chronological

  var upcoming = events
    .filter(function(ev) { return ev.date >= today; })
    .sort(function(a, b) { return new Date(a.date) - new Date(b.date); })
    .slice(0, 10);  // up to 10 upcoming events

  // Combine: 5 past + 10 upcoming (max 15 total)
  var display = pastEvents.concat(upcoming);

  // Final sort chronologically
  display.sort(function(a, b) { return new Date(a.date) - new Date(b.date); });

  renderCalendar(display, pastDate, futureDate);
}
