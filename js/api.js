// ─── SHARED STATE ────────────────────────────────────────
let charts      = {};
let sparklines  = {};
let refreshTimer;
const seriesRawData = {};

// ─── UTILITIES ───────────────────────────────────────────
const sleep = ms => new Promise(r => setTimeout(r, ms));

function filterToTwoYears(obs) {
  const cutoff = (new Date().getFullYear() - 2) + '-01-01';
  return obs.filter(d => d.date >= cutoff);
}

function parseFREDJson(json) {
  if (!json.observations) throw new Error('No observations in response');
  return json.observations
    .filter(o => o.value !== '.' && o.value !== '')
    .map(o => ({ date: o.date, value: parseFloat(o.value) }))
    .reverse();
}

// ─── FETCH ───────────────────────────────────────────────
async function fetchWithProxy(url) {
  const res = await fetch(PROXY_URL + encodeURIComponent(url));
  if (!res.ok) throw new Error('proxy failed: HTTP ' + res.status);
  return res.json();
}

async function fetchFRED(seriesId, limit = 60) {
  const url = 'https://api.stlouisfed.org/fred/series/observations' +
    '?series_id=' + seriesId +
    '&api_key=' + FRED_API_KEY +
    '&file_type=json&sort_order=desc&limit=' + limit;
  return parseFREDJson(await fetchWithProxy(url));
}

async function fetchVintage(seriesId, vintageDates) {
  const url = 'https://api.stlouisfed.org/fred/series/observations' +
    '?series_id=' + seriesId +
    '&api_key=' + FRED_API_KEY +
    '&file_type=json&sort_order=desc&limit=5' +
    '&vintage_dates=' + vintageDates.join(',');
  const j = await fetchWithProxy(url);
  if (!j.observations) return null;
  const valid = j.observations.filter(o => o.value !== '.' && o.value !== '');
  return valid.length > 0 ? parseFloat(valid[0].value) : null;
}

async function fetchMarket(symbol) {
  const url = 'https://query1.finance.yahoo.com/v8/finance/chart/' +
    symbol.replace('^', '%5E') +
    '?range=3y&interval=1d&events=history';
  const j = await fetchWithProxy(url);
  if (!j.chart || !j.chart.result || !j.chart.result[0]) {
    const err = j.chart?.error?.description || j['Error Message'] || 'no data returned';
    throw new Error(symbol + ': ' + err);
  }
  const result  = j.chart.result[0];
  const closes  = result.indicators.quote[0].close;
  return result.timestamp
    .map((t, i) => ({ date: new Date(t * 1000).toISOString().slice(0, 10), value: closes[i] }))
    .filter(d => d.value != null);
}
