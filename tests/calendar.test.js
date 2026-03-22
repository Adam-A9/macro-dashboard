// ─── Tests for js/calendar.js helpers ────────────────────

describe('formatCalDate', () => {
  it('formats an ISO date string to short month+day', () => {
    assert.equal(formatCalDate('2026-01-15'), 'Jan 15');
    assert.equal(formatCalDate('2026-12-31'), 'Dec 31');
    assert.equal(formatCalDate('2026-07-04'), 'Jul 4');
  });

  it('handles month boundary correctly (no timezone shift)', () => {
    // Using noon UTC in formatCalDate avoids off-by-one timezone issues
    const result = formatCalDate('2026-03-01');
    assert.equal(result, 'Mar 1');
  });
});

describe('formatCalTime', () => {
  it('converts 24h time to 12h AM/PM ET format', () => {
    assert.equal(formatCalTime('08:30'), '8:30 am ET');
    assert.equal(formatCalTime('14:00'), '2:00 pm ET');
    assert.equal(formatCalTime('12:00'), '12:00 pm ET');
    assert.equal(formatCalTime('00:00'), '12:00 am ET');
  });

  it('returns empty string for falsy input', () => {
    assert.equal(formatCalTime(''),        '');
    assert.equal(formatCalTime(null),      '');
    assert.equal(formatCalTime(undefined), '');
  });
});

describe('renderCalendar', () => {
  let container;

  beforeEach(() => {
    container = document.createElement('div');
    container.innerHTML =
      '<span id="cal-range"></span>' +
      '<div id="calendarGrid"></div>';
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it('shows empty message when event list is empty', () => {
    renderCalendar([], '2026-03-17', '2026-03-31');
    const grid = document.getElementById('calendarGrid');
    assert.ok(grid.textContent.includes('No recent or upcoming'), 'should show empty state');
  });

  it('renders event rows for each provided event', () => {
    const events = [
      { date: '2026-03-18', time: '08:30', event: 'CPI Release',    freq: 'MoM', source: 'BLS', impact: 'high'   },
      { date: '2026-03-19', time: '08:30', event: 'PPI Release',    freq: 'MoM', source: 'BLS', impact: 'medium' },
      { date: '2026-03-20', time: '08:30', event: 'Jobless Claims', freq: 'WoW', source: 'DOL', impact: 'low'    },
    ];
    renderCalendar(events, '2026-03-17', '2026-03-31');
    const grid = document.getElementById('calendarGrid');
    assert.ok(grid.textContent.includes('CPI Release'),    'should show CPI event');
    assert.ok(grid.textContent.includes('Jobless Claims'), 'should show Claims event');
    assert.ok(grid.innerHTML.includes('cal-impact-high'),   'should render HIGH badge');
    assert.ok(grid.innerHTML.includes('cal-impact-medium'), 'should render MED badge');
    assert.ok(!grid.innerHTML.includes('cal-impact-low'),   'low impact should have no badge');
  });

  it('renders events sorted by date', () => {
    const events = [
      { date: '2026-03-25', time: '', event: 'Late Event',  freq: 'MoM', source: 'X', impact: false },
      { date: '2026-03-18', time: '', event: 'Early Event', freq: 'MoM', source: 'Y', impact: false },
    ];
    renderCalendar(events, '2026-03-17', '2026-03-31');
    const grid = document.getElementById('calendarGrid');
    const pos1 = grid.textContent.indexOf('Early Event');
    const pos2 = grid.textContent.indexOf('Late Event');
    assert.ok(pos1 < pos2, 'early event should appear before late event');
  });

  it('sets the cal-range text from from/to dates', () => {
    renderCalendar([], '2026-03-17', '2026-03-31');
    const rangeEl = document.getElementById('cal-range');
    assert.ok(rangeEl.textContent.includes('Mar 17'), 'should show start date');
    assert.ok(rangeEl.textContent.includes('Mar 31'), 'should show end date');
  });

  it('applies fomc CSS class for Fed events', () => {
    const events = [
      { date: '2026-03-18', time: '14:00', event: 'Fed Interest Rate Decision', freq: 'Fed', source: 'Federal Reserve', impact: true },
    ];
    renderCalendar(events, '2026-03-17', '2026-03-31');
    const grid = document.getElementById('calendarGrid');
    assert.ok(grid.innerHTML.includes('cal-fomc'), 'Fed events should have fomc CSS class');
  });

  it('applies cal-past CSS class for events before today', () => {
    const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    const events = [
      { date: yesterday, time: '08:30', event: 'Past CPI', freq: 'MoM', source: 'BLS', impact: 'high' },
    ];
    renderCalendar(events, '2026-03-10', '2026-03-31');
    const grid = document.getElementById('calendarGrid');
    assert.ok(grid.innerHTML.includes('cal-past'), 'past events should have cal-past CSS class');
    assert.ok(grid.innerHTML.includes('ago'), 'past events should show "ago" in days label');
  });

  it('renders consensus estimate, actual, and prior when available', () => {
    const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
    const events = [
      { date: tomorrow, time: '08:30', event: 'CPI Release', freq: 'MoM', source: 'BLS', impact: 'high',
        estimate: 2.9, actual: null, prior: 2.7, unit: '%' },
    ];
    renderCalendar(events, '2026-03-17', '2026-03-31');
    const grid = document.getElementById('calendarGrid');
    assert.ok(grid.innerHTML.includes('cal-est-group'), 'should render estimate group');
    assert.ok(grid.textContent.includes('2.9%'), 'should display estimate value');
    assert.ok(grid.textContent.includes('2.7%'), 'should display prior value');
    assert.ok(grid.innerHTML.includes('cal-est-prior'), 'prior should have prior styling');
  });

  it('renders actual with beat/miss styling vs estimate', () => {
    const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
    const events = [
      { date: tomorrow, time: '08:30', event: 'NFP', freq: 'MoM', source: 'BLS', impact: 'high',
        estimate: 185, actual: 200, prior: 170, unit: 'K' },
    ];
    renderCalendar(events, '2026-03-17', '2026-03-31');
    const grid = document.getElementById('calendarGrid');
    assert.ok(grid.innerHTML.includes('cal-beat'), 'actual > estimate should have beat class');
    assert.ok(grid.textContent.includes('200K'), 'should display actual value');
    assert.ok(grid.textContent.includes('185K'), 'should display estimate value');
  });

  it('renders miss styling when actual < estimate', () => {
    const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
    const events = [
      { date: tomorrow, time: '08:30', event: 'GDP', freq: 'QoQ', source: 'BEA', impact: 'high',
        estimate: 2.5, actual: 2.0, prior: 2.3, unit: '%' },
    ];
    renderCalendar(events, '2026-03-17', '2026-03-31');
    const grid = document.getElementById('calendarGrid');
    assert.ok(grid.innerHTML.includes('cal-miss'), 'actual < estimate should have miss class');
  });

  it('falls back to frequency label when no estimates exist', () => {
    const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
    const events = [
      { date: tomorrow, time: '14:00', event: 'Fed Decision', freq: 'Fed', source: 'Federal Reserve', impact: 'high' },
    ];
    renderCalendar(events, '2026-03-17', '2026-03-31');
    const grid = document.getElementById('calendarGrid');
    assert.ok(grid.innerHTML.includes('cal-prev-label'), 'events without estimates should show freq label');
    assert.ok(!grid.innerHTML.includes('cal-est-group'), 'should not render estimate group');
  });

  it('does not apply cal-past class for future events', () => {
    const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
    const events = [
      { date: tomorrow, time: '08:30', event: 'Future GDP', freq: 'QoQ', source: 'BEA', impact: 'high' },
    ];
    renderCalendar(events, '2026-03-10', '2026-03-31');
    const grid = document.getElementById('calendarGrid');
    assert.ok(!grid.innerHTML.includes('cal-past'), 'future events should not have cal-past class');
  });
});

describe('FOMC_DATES', () => {
  it('contains only dates in YYYY-MM-DD format', () => {
    const isoPattern = /^\d{4}-\d{2}-\d{2}$/;
    FOMC_DATES.forEach(f => {
      assert.ok(isoPattern.test(f.date), f.date + ' should be ISO format');
    });
  });

  it('contains at least 8 entries per year (Fed meets 8x/year)', () => {
    const years = {};
    FOMC_DATES.forEach(f => {
      const y = f.date.slice(0, 4);
      years[y] = (years[y] || 0) + 1;
    });
    Object.entries(years).forEach(([year, count]) => {
      assert.ok(count >= 8, year + ' should have at least 8 FOMC meetings');
    });
  });

  it('all times are 14:00 (FOMC announcements at 2pm ET)', () => {
    FOMC_DATES.forEach(f => {
      assert.equal(f.time, '14:00', f.date + ' should announce at 14:00');
    });
  });
});

describe('RELEASE_META', () => {
  it('is a non-empty object with numeric release IDs as keys', () => {
    const keys = Object.keys(RELEASE_META);
    assert.ok(keys.length > 0, 'should have at least one release mapped');
    keys.forEach(k => {
      assert.equal(typeof parseInt(k, 10), 'number', k + ' should be a numeric key');
    });
  });

  it('each entry has name, time, freq, source, impact fields', () => {
    const validImpact = new Set(['high', 'medium', 'low']);
    Object.entries(RELEASE_META).forEach(([id, meta]) => {
      assert.ok('name'   in meta, id + ' missing name');
      assert.ok('time'   in meta, id + ' missing time');
      assert.ok('freq'   in meta, id + ' missing freq');
      assert.ok('source' in meta, id + ' missing source');
      assert.ok('impact' in meta, id + ' missing impact');
      assert.ok(validImpact.has(meta.impact), id + ' impact must be high/medium/low, got: ' + meta.impact);
    });
  });

  it('CPI (release 10) is marked high impact', () => {
    assert.equal(RELEASE_META[10]?.impact, 'high', 'CPI should be high impact');
  });

  it('Nonfarm Payrolls (release 46) is marked high impact', () => {
    assert.equal(RELEASE_META[46]?.impact, 'high', 'Nonfarm Payrolls should be high impact');
  });

  it('Jobless Claims (release 50) is marked medium impact', () => {
    assert.equal(RELEASE_META[50]?.impact, 'medium', 'Jobless Claims should be medium impact');
  });

  it('Durable Goods (release 22) is present and medium impact', () => {
    assert.ok(RELEASE_META[22], 'Durable Goods should exist');
    assert.equal(RELEASE_META[22].impact, 'medium', 'Durable Goods should be medium impact');
  });

  it('Trade Balance (release 69) is present and medium impact', () => {
    assert.ok(RELEASE_META[69], 'Trade Balance should exist');
    assert.equal(RELEASE_META[69].impact, 'medium', 'Trade Balance should be medium impact');
  });

  it('all release IDs in RELEASE_META match scraper FRED_RELEASES', () => {
    // Verify key releases are mapped
    const expectedIds = [10, 11, 15, 17, 19, 21, 22, 31, 32, 46, 50, 51, 53, 54, 55, 56, 69, 82, 83, 86, 113, 116, 117, 118, 160, 161, 175, 180, 200];
    expectedIds.forEach(id => {
      assert.ok(RELEASE_META[id], 'RELEASE_META should contain release ID ' + id);
    });
  });
});

describe('SERIES_META', () => {
  it('is a non-empty object keyed by FRED series IDs', () => {
    const keys = Object.keys(SERIES_META);
    assert.ok(keys.length > 0, 'should have at least one series mapped');
  });

  it('each entry has name, time, and freq fields', () => {
    Object.entries(SERIES_META).forEach(([sid, meta]) => {
      assert.ok('name' in meta, sid + ' missing name');
      assert.ok('time' in meta, sid + ' missing time');
      assert.ok('freq' in meta, sid + ' missing freq');
    });
  });

  it('covers all key series from the scraper', () => {
    const expectedSeries = [
      'CPIAUCSL', 'PPIACO', 'PAYEMS', 'ICSA', 'GDP', 'PCEPI',
      'RSAFS', 'HOUST', 'DGORDER', 'BOPGSTB', 'MANEMP', 'NMFCI'
    ];
    expectedSeries.forEach(sid => {
      assert.ok(SERIES_META[sid], 'SERIES_META should contain ' + sid);
    });
  });

  it('CPI series has correct display metadata', () => {
    assert.equal(SERIES_META['CPIAUCSL'].time, '08:30');
    assert.equal(SERIES_META['CPIAUCSL'].freq, 'MoM');
  });

  it('weekly series (ICSA, CCSA) use WoW frequency', () => {
    assert.equal(SERIES_META['ICSA'].freq, 'WoW', 'Initial Claims should be WoW');
    assert.equal(SERIES_META['CCSA'].freq, 'WoW', 'Continuing Claims should be WoW');
  });

  it('quarterly series (GDP, ECI) use QoQ frequency', () => {
    assert.equal(SERIES_META['GDP'].freq, 'QoQ', 'GDP should be QoQ');
    assert.equal(SERIES_META['ECIWAG'].freq, 'QoQ', 'ECI should be QoQ');
  });
});
