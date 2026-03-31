"""
Economic Calendar Scraper — Rebuilt for reliability and speed.

Strategy:
  1. FRED API        — Release dates for all tracked indicators (authoritative)
  2. FRED Observations — Prior values + actual values (authoritative)
  3. Investing.com    — Consensus estimates via hidden JSON API (aggressive)
  4. BLS schedule     — Backup release dates for key labor/inflation series

Runs via GitHub Actions 4x daily on weekdays.
Outputs to Supabase `consensus` table.
"""

import os
import re
import json
import time
import logging
import requests
from datetime import datetime, date, timedelta

# ─── LOGGING ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-7s  %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('scraper')

# ─── CONFIG ──────────────────────────────────────────────────
SUPABASE_URL = "https://ygcirhhnojzmprbomzxs.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
FRED_API_KEY = os.environ.get("FRED_API_KEY", "8eb474280a02991313279b06c726bba4")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
}

TODAY    = date.today()
LOOKBACK = TODAY - timedelta(days=14)   # 14-day lookback for past events
CUTOFF   = TODAY + timedelta(days=60)   # 60-day forward window

# ─── FRED RELEASE METADATA ──────────────────────────────────
# release_id → series info. This is the single source of truth for what we track.
RELEASES = {
    10:  {"sid": "CPIAUCSL",       "name": "Consumer Price Index (CPI)",      "source": "BLS",              "unit": "%",  "impact": "high",   "time": "08:30", "freq": "MoM"},
    11:  {"sid": "IR",             "name": "Import & Export Prices",           "source": "BLS",              "unit": "%",  "impact": "low",    "time": "08:30", "freq": "MoM"},
    15:  {"sid": "RSAFS",          "name": "Retail Sales",                     "source": "Census",           "unit": "%",  "impact": "high",   "time": "08:30", "freq": "MoM"},
    17:  {"sid": "CSCICP03USM665S","name": "Consumer Confidence",              "source": "Conference Board", "unit": "",   "impact": "medium", "time": "10:00", "freq": "MoM"},
    19:  {"sid": "EXHOSLUSM495S",  "name": "Existing Home Sales",             "source": "NAR",              "unit": "M",  "impact": "low",    "time": "10:00", "freq": "MoM"},
    21:  {"sid": "M2SL",           "name": "M2 Money Supply",                  "source": "Federal Reserve",  "unit": "B$", "impact": "low",    "time": "13:30", "freq": "MoM"},
    22:  {"sid": "DGORDER",        "name": "Durable Goods Orders",             "source": "Census",           "unit": "%",  "impact": "medium", "time": "08:30", "freq": "MoM"},
    31:  {"sid": "PPIACO",         "name": "Producer Price Index (PPI)",       "source": "BLS",              "unit": "%",  "impact": "medium", "time": "08:30", "freq": "MoM"},
    32:  {"sid": "CES0500000003",  "name": "Average Hourly Earnings",          "source": "BLS",              "unit": "%",  "impact": "medium", "time": "08:30", "freq": "MoM"},
    46:  {"sid": "PAYEMS",         "name": "Nonfarm Payrolls",                 "source": "BLS",              "unit": "K",  "impact": "high",   "time": "08:30", "freq": "MoM"},
    50:  {"sid": "ICSA",           "name": "Initial Jobless Claims",           "source": "Dept of Labor",    "unit": "K",  "impact": "medium", "time": "08:30", "freq": "WoW"},
    51:  {"sid": "JTSJOL",         "name": "JOLTS Job Openings",               "source": "BLS",              "unit": "K",  "impact": "medium", "time": "10:00", "freq": "MoM"},
    53:  {"sid": "GDP",            "name": "GDP",                              "source": "BEA",              "unit": "%",  "impact": "high",   "time": "08:30", "freq": "QoQ"},
    54:  {"sid": "HSN1F",          "name": "New Home Sales",                   "source": "Census",           "unit": "K",  "impact": "low",    "time": "10:00", "freq": "MoM"},
    55:  {"sid": "PCEPI",          "name": "PCE / Personal Income",            "source": "BEA",              "unit": "%",  "impact": "medium", "time": "08:30", "freq": "MoM"},
    56:  {"sid": "HOUST",          "name": "Housing Starts & Permits",         "source": "Census",           "unit": "K",  "impact": "medium", "time": "08:30", "freq": "MoM"},
    69:  {"sid": "BOPGSTB",        "name": "Trade Balance",                    "source": "Census/BEA",       "unit": "B$", "impact": "medium", "time": "08:30", "freq": "MoM"},
    82:  {"sid": "USSLIND",        "name": "Leading Economic Indicators",      "source": "Conference Board", "unit": "%",  "impact": "low",    "time": "10:00", "freq": "MoM"},
    83:  {"sid": "AMTMNO",         "name": "Factory Orders",                   "source": "Census",           "unit": "%",  "impact": "low",    "time": "10:00", "freq": "MoM"},
    86:  {"sid": "INDPRO",         "name": "Industrial Production",            "source": "Federal Reserve",  "unit": "%",  "impact": "low",    "time": "09:15", "freq": "MoM"},
    113: {"sid": "ECIWAG",         "name": "Employment Cost Index",            "source": "BLS",              "unit": "%",  "impact": "medium", "time": "08:30", "freq": "QoQ"},
    116: {"sid": "TCU",            "name": "Capacity Utilization",             "source": "Federal Reserve",  "unit": "%",  "impact": "low",    "time": "09:15", "freq": "MoM"},
    117: {"sid": "CCSA",           "name": "Continuing Jobless Claims",        "source": "Dept of Labor",    "unit": "K",  "impact": "low",    "time": "08:30", "freq": "WoW"},
    118: {"sid": "CSUSHPISA",      "name": "Case-Shiller Home Prices",         "source": "S&P/Case-Shiller", "unit": "%",  "impact": "low",    "time": "09:00", "freq": "MoM"},
    160: {"sid": "MANEMP",         "name": "ISM Manufacturing PMI",            "source": "ISM",              "unit": "",   "impact": "medium", "time": "10:00", "freq": "MoM"},
    161: {"sid": "NMFCI",          "name": "ISM Services PMI",                 "source": "ISM",              "unit": "",   "impact": "medium", "time": "10:00", "freq": "MoM"},
    175: {"sid": "TTLCONS",        "name": "Construction Spending",            "source": "Census",           "unit": "%",  "impact": "low",    "time": "10:00", "freq": "MoM"},
    180: {"sid": "UMCSENT",        "name": "Consumer Sentiment",               "source": "Univ of Michigan", "unit": "",   "impact": "low",    "time": "10:00", "freq": "MoM"},
    200: {"sid": "PHSI",           "name": "Pending Home Sales",               "source": "NAR",              "unit": "%",  "impact": "low",    "time": "10:00", "freq": "MoM"},
}

# Reverse lookup: series_id → release metadata
SID_META = {v["sid"]: v for v in RELEASES.values()}

# Series where FRED stores raw levels → we compute MoM % change
PCT_CHANGE = {"CPIAUCSL", "CPILFESL", "PPIACO", "PCEPI", "PCEPILFE", "RSAFS", "INDPRO"}

# Series where FRED stores levels → we compute MoM difference (thousands)
DIFF_SERIES = {"PAYEMS"}

# Series name fragments → FRED series ID (for matching Investing.com events)
NAME_MAP = {
    "nonfarm payrolls": "PAYEMS", "non-farm payrolls": "PAYEMS",
    "nonfarm employment": "PAYEMS", "employment change": "PAYEMS",
    "unemployment rate": "UNRATE",
    "consumer price index": "CPIAUCSL", "cpi (mom)": "CPIAUCSL",
    "cpi (yoy)": "CPIAUCSL", "cpi mom": "CPIAUCSL", "cpi yoy": "CPIAUCSL",
    "core cpi": "CPILFESL", "core consumer price": "CPILFESL",
    "producer price index": "PPIACO", "ppi (mom)": "PPIACO", "ppi mom": "PPIACO",
    "pce price": "PCEPI", "core pce": "PCEPILFE",
    "personal consumption": "PCEPI", "personal spending": "PCEPI",
    "personal income": "PCEPI",
    "retail sales": "RSAFS",
    "import price": "IR", "export price": "IR",
    "initial jobless claims": "ICSA", "initial claims": "ICSA",
    "continuing jobless claims": "CCSA", "continuing claims": "CCSA",
    "jolts job openings": "JTSJOL", "jolt": "JTSJOL", "job openings": "JTSJOL",
    "gdp (qoq)": "GDP", "gdp annualized": "GDP", "gdp growth": "GDP",
    "gross domestic product": "GDP",
    "industrial production": "INDPRO",
    "capacity utilization": "TCU",
    "durable goods": "DGORDER",
    "factory orders": "AMTMNO",
    "consumer confidence": "CSCICP03USM665S", "cb consumer confidence": "CSCICP03USM665S",
    "consumer sentiment": "UMCSENT", "michigan consumer": "UMCSENT",
    "housing starts": "HOUST", "building permits": "PERMIT",
    "existing home sales": "EXHOSLUSM495S",
    "new home sales": "HSN1F",
    "pending home sales": "PHSI",
    "case-shiller": "CSUSHPISA", "s&p/cs": "CSUSHPISA",
    "construction spending": "TTLCONS",
    "trade balance": "BOPGSTB", "trade deficit": "BOPGSTB",
    "ism manufacturing": "MANEMP", "ism manuf": "MANEMP",
    "ism non-manufacturing": "NMFCI", "ism services": "NMFCI",
    "leading indicators": "USSLIND", "leading economic": "USSLIND",
    "employment cost": "ECIWAG",
    "average hourly earnings": "CES0500000003",
    "m2 money": "M2SL",
    "fed interest rate": "FEDFUNDS", "federal funds rate": "FEDFUNDS",
}


def safe_get(url, timeout=20, retries=3, **kwargs):
    """HTTP GET with retries and exponential backoff."""
    merged = {**HEADERS, **kwargs.pop('headers', {})}
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=merged, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                log.warning(f"  Retry {attempt+1}/{retries}: {str(e)[:80]}… waiting {wait}s")
                time.sleep(wait)
            else:
                log.error(f"  Failed after {retries} tries: {str(e)[:100]}")
                return None
    return None


def in_window(d):
    """Check if a date string or date object falls within our scrape window."""
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, '%Y-%m-%d').date()
        except ValueError:
            return False
    return LOOKBACK <= d <= CUTOFF


def match_event_name(name):
    """Match an event name string to a FRED series ID."""
    n = name.lower().strip()
    for key, sid in NAME_MAP.items():
        if key in n:
            return sid
    return None


# ═══════════════════════════════════════════════════════════════
# 1. FRED RELEASES/DATES — Authoritative release schedule
# ═══════════════════════════════════════════════════════════════
def fetch_fred_dates():
    """Get all upcoming + recent release dates from FRED API."""
    log.info("── FRED Release Dates ───────────────────────────")
    records = {}  # (sid, date) → record

    url = (
        f"https://api.stlouisfed.org/fred/releases/dates"
        f"?api_key={FRED_API_KEY}&file_type=json"
        f"&realtime_start={LOOKBACK.isoformat()}"
        f"&realtime_end={CUTOFF.isoformat()}"
        f"&include_release_dates_with_no_data=false"
    )

    resp = safe_get(url)
    if not resp:
        log.error("  FRED API unavailable")
        return records

    try:
        data = resp.json()
    except (json.JSONDecodeError, ValueError):
        log.error("  FRED API: invalid JSON")
        return records

    for entry in data.get('release_dates', []):
        rid = entry.get('release_id')
        rd = entry.get('date')
        if rid not in RELEASES or not in_window(rd):
            continue

        meta = RELEASES[rid]
        sid = meta['sid']
        key = (sid, rd)
        if key in records:
            continue

        records[key] = {
            'series_id':    sid,
            'release_name': meta['name'],
            'release_date': rd,
            'estimate':     None,
            'actual':       None,
            'prior':        None,
            'unit':         meta['unit'],
            'source':       meta['source'],
            'impact':       meta['impact'],
            'frequency':    meta['freq'],
        }

    log.info(f"  Found {len(records)} release dates")
    return records


# ═══════════════════════════════════════════════════════════════
# 2. FRED OBSERVATIONS — Prior + Actual values
# ═══════════════════════════════════════════════════════════════
def _fred_transform(sid, observations):
    """
    Transform raw FRED observations into calendar-display values.
    Returns (latest_value, prior_value) tuple.
    """
    if not observations:
        return None, None

    vals = []
    for obs in observations:
        raw = obs.get('value', '').strip()
        if raw in ('', '.'):
            continue
        vals.append(float(raw))

    if not vals:
        return None, None

    if sid in PCT_CHANGE:
        if len(vals) >= 3:
            actual = round((vals[0] / vals[1] - 1) * 100, 1) if vals[1] != 0 else None
            prior = round((vals[1] / vals[2] - 1) * 100, 1) if vals[2] != 0 else None
            return actual, prior
        elif len(vals) >= 2:
            actual = round((vals[0] / vals[1] - 1) * 100, 1) if vals[1] != 0 else None
            return actual, None
    elif sid in DIFF_SERIES:
        if len(vals) >= 3:
            return round(vals[0] - vals[1], 1), round(vals[1] - vals[2], 1)
        elif len(vals) >= 2:
            return round(vals[0] - vals[1], 1), None
    else:
        actual = vals[0]
        prior = vals[1] if len(vals) >= 2 else None
        return actual, prior

    return vals[0] if vals else None, None


def fetch_fred_values(records):
    """Fetch prior + actual values from FRED for all series in records."""
    log.info("── FRED Observations (Priors + Actuals) ─────────")

    sids = sorted({r['series_id'] for r in records.values()})
    log.info(f"  Fetching {len(sids)} series...")

    value_map = {}  # sid → (actual, prior)

    for sid in sids:
        limit = 3 if sid in PCT_CHANGE or sid in DIFF_SERIES else 2
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={sid}&api_key={FRED_API_KEY}"
            f"&file_type=json&sort_order=desc&limit={limit}"
        )
        resp = safe_get(url, retries=2, timeout=10)
        if not resp:
            continue
        try:
            obs = resp.json().get('observations', [])
            actual, prior = _fred_transform(sid, obs)
            if actual is not None or prior is not None:
                value_map[sid] = (actual, prior)
        except Exception as e:
            log.warning(f"  {sid}: parse error: {e}")

    # Apply to records
    applied_act = 0
    applied_pri = 0
    for key, rec in records.items():
        sid = rec['series_id']
        if sid not in value_map:
            continue
        actual, prior = value_map[sid]

        # Only set actual for past/today events
        if actual is not None and rec['release_date'] <= TODAY.isoformat():
            rec['actual'] = actual
            applied_act += 1
        if prior is not None:
            rec['prior'] = prior
            applied_pri += 1

    log.info(f"  Values: {len(value_map)}/{len(sids)} series | "
             f"Actuals applied: {applied_act} | Priors applied: {applied_pri}")
    return records


# ═══════════════════════════════════════════════════════════════
# 3. INVESTING.COM — Consensus estimates (aggressive scraping)
# ═══════════════════════════════════════════════════════════════
def fetch_investing_estimates(records):
    """
    Scrape Investing.com economic calendar for consensus estimates.
    Uses their server-rendered HTML with aggressive headers.
    """
    log.info("── Investing.com Estimates ─────────────────────")
    estimates_found = 0

    # Build set of series that still need estimates
    needs_estimate = {rec['series_id'] for rec in records.values() if rec['estimate'] is None}
    if not needs_estimate:
        log.info("  All records already have estimates")
        return records

    # Scrape current week and next week
    for week_offset in range(3):
        target = TODAY + timedelta(weeks=week_offset)
        start = target - timedelta(days=target.weekday())  # Monday
        end = start + timedelta(days=6)  # Sunday

        url = "https://www.investing.com/economic-calendar/"
        resp = safe_get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            "Cache-Control": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
        })
        if not resp:
            continue

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for row in soup.find_all('tr', class_=re.compile(r'js-event-item')):
                # US events only
                flag = row.find('td', class_=re.compile(r'flag'))
                if flag:
                    span = flag.find('span')
                    if span and 'United States' not in span.get('title', ''):
                        continue

                event_cell = row.find('td', class_=re.compile(r'event'))
                if not event_cell:
                    continue

                event_name = event_cell.get_text(strip=True)
                sid = match_event_name(event_name)
                if not sid or sid not in needs_estimate:
                    continue

                # Extract forecast
                fore_cell = row.find('td', class_=re.compile(r'fore'))
                if fore_cell:
                    text = fore_cell.get_text(strip=True).replace(',', '')
                    m = re.search(r'(-?\d+\.?\d*)', text)
                    if m:
                        estimate = float(m.group(1))
                        # Apply to matching records
                        for rec in records.values():
                            if rec['series_id'] == sid and rec['estimate'] is None:
                                rec['estimate'] = estimate
                                estimates_found += 1
                        needs_estimate.discard(sid)

                # Extract actual if present
                act_cell = row.find('td', class_=re.compile(r'act'))
                if act_cell:
                    text = act_cell.get_text(strip=True).replace(',', '')
                    m = re.search(r'(-?\d+\.?\d*)', text)
                    if m:
                        actual = float(m.group(1))
                        for rec in records.values():
                            if rec['series_id'] == sid and rec['actual'] is None:
                                if rec['release_date'] <= TODAY.isoformat():
                                    rec['actual'] = actual

        except Exception as e:
            log.warning(f"  Investing.com parse error: {e}")

    log.info(f"  Estimates found: {estimates_found}")
    return records


# ═══════════════════════════════════════════════════════════════
# 4. MARKETWATCH — Backup consensus estimates
# ═══════════════════════════════════════════════════════════════
def fetch_marketwatch_estimates(records):
    """Backup: try MarketWatch for any remaining missing estimates."""
    log.info("── MarketWatch Estimates (backup) ────────────────")

    needs = {rec['series_id'] for rec in records.values() if rec['estimate'] is None}
    if not needs:
        log.info("  No missing estimates")
        return records

    found = 0
    for delta in range(0, 14, 7):
        target = TODAY + timedelta(days=delta)
        start = target - timedelta(days=target.weekday())
        date_str = start.strftime('%Y%m%d')

        resp = safe_get(
            f"https://www.marketwatch.com/economy-politics/calendar?date={date_str}",
            headers={
                "Referer": "https://www.marketwatch.com/",
                "User-Agent": HEADERS["User-Agent"],
            }
        )
        if not resp:
            continue

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue

                text = row.get_text(' ', strip=True)
                sid = match_event_name(text)
                if not sid or sid not in needs:
                    continue

                # Look for numeric values in cells
                for cell in cells:
                    cell_text = cell.get_text(strip=True).replace(',', '')
                    m = re.search(r'(-?\d+\.?\d*)', cell_text)
                    if m:
                        classes = cell.get('class', [])
                        if any('consensus' in c or 'forecast' in c or 'estimate' in c for c in classes):
                            estimate = float(m.group(1))
                            for rec in records.values():
                                if rec['series_id'] == sid and rec['estimate'] is None:
                                    rec['estimate'] = estimate
                                    found += 1
                            needs.discard(sid)

        except Exception as e:
            log.warning(f"  MarketWatch parse error: {e}")

    log.info(f"  Backup estimates found: {found}")
    return records


# ═══════════════════════════════════════════════════════════════
# 5. FOMC DATES — Hardcoded (announced a year in advance)
# ═══════════════════════════════════════════════════════════════
FOMC_DATES = [
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]


def add_fomc_dates(records):
    """Add FOMC meeting dates to the record set."""
    log.info("── FOMC Dates ─────────────────────────────────────")
    added = 0
    for d in FOMC_DATES:
        if not in_window(d):
            continue
        key = ("FEDFUNDS", d)
        if key not in records:
            records[key] = {
                'series_id':    'FEDFUNDS',
                'release_name': 'Fed Interest Rate Decision',
                'release_date': d,
                'estimate':     None,
                'actual':       None,
                'prior':        None,
                'unit':         '%',
                'source':       'Federal Reserve',
                'impact':       'high',
                'frequency':    'Fed',
            }
            added += 1
    log.info(f"  Added {added} FOMC dates")
    return records


# ═══════════════════════════════════════════════════════════════
# SUPABASE UPSERT
# ═══════════════════════════════════════════════════════════════
def _fetch_existing(sids_dates, headers):
    """Fetch existing rows to avoid overwriting good data with nulls."""
    existing = {}
    if not sids_dates:
        return existing

    sids = sorted({sd[0] for sd in sids_dates})
    dates = sorted({sd[1] for sd in sids_dates})
    params = (
        f"?select=series_id,release_date,estimate,actual,prior"
        f"&series_id=in.({','.join(sids)})"
        f"&release_date=in.({','.join(dates)})"
    )
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/consensus{params}",
            headers={"apikey": headers["apikey"], "Authorization": headers["Authorization"],
                     "Accept": "application/json"},
            timeout=10,
        )
        if res.status_code == 200:
            for row in res.json():
                existing[(row['series_id'], row['release_date'])] = row
    except requests.RequestException:
        pass
    return existing


def upsert_to_supabase(records):
    """Push all records to Supabase, preserving existing non-null values."""
    log.info("── Supabase Upsert ──────────────────────────────")
    if not records:
        log.info("  No records")
        return
    if not SUPABASE_KEY:
        log.warning("  SUPABASE_KEY not set — skipping")
        return

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    # Fetch existing to preserve non-null values
    existing = _fetch_existing(list(records.keys()), headers)

    rows = []
    for key, rec in records.items():
        prev = existing.get(key, {})
        rows.append({
            "series_id":    rec['series_id'],
            "release_name": rec['release_name'],
            "release_date": rec['release_date'],
            "estimate":     rec.get('estimate') or prev.get('estimate'),
            "actual":       rec.get('actual') or prev.get('actual'),
            "prior":        rec.get('prior') or prev.get('prior'),
            "unit":         rec.get('unit', ''),
            "source":       rec.get('source', ''),
            "impact":       rec.get('impact', 'low'),
            "frequency":    rec.get('frequency', 'MoM'),
            "updated_at":   datetime.utcnow().isoformat(),
        })

    # Batch upsert (Supabase handles up to 1000 rows)
    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/consensus",
            json=rows,
            headers=headers,
            timeout=15,
        )
        if res.status_code in (200, 201):
            log.info(f"  Upserted {len(rows)} records")
        else:
            log.error(f"  Supabase {res.status_code}: {res.text[:300]}")
    except requests.RequestException as e:
        log.error(f"  Supabase error: {e}")

    # Log to scrape_log
    log_rows = [{
        "series_id": r["series_id"], "release_date": r["release_date"],
        "estimate": r.get("estimate"), "actual": r.get("actual"),
        "source": r.get("source", ""), "scraped_at": datetime.utcnow().isoformat(),
    } for r in rows]

    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/scrape_log",
            json=log_rows, headers=headers, timeout=15,
        )
    except requests.RequestException:
        pass


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
def print_summary(records):
    """Print formatted summary of all data."""
    recs = sorted(records.values(), key=lambda x: x.get('release_date', ''))
    if not recs:
        log.info("No records found")
        return

    log.info(f"\n  {'Series':<22} {'Release':<35} {'Date':<12} {'Prior':<10} {'Est':<10} {'Actual':<10} Impact")
    log.info(f"  {'─'*115}")

    for r in recs:
        pri = str(r.get('prior', '')) if r.get('prior') is not None else '–'
        est = str(r.get('estimate', '')) if r.get('estimate') is not None else '–'
        act = str(r.get('actual', '')) if r.get('actual') is not None else '–'
        log.info(
            f"  {r['series_id']:<22} {r['release_name'][:35]:<35} "
            f"{r['release_date']:<12} {pri:<10} {est:<10} {act:<10} {r.get('impact','')}"
        )

    with_est = sum(1 for r in recs if r.get('estimate') is not None)
    with_act = sum(1 for r in recs if r.get('actual') is not None)
    with_pri = sum(1 for r in recs if r.get('prior') is not None)
    log.info(f"\n  Total: {len(recs)} records")
    log.info(f"  Priors: {with_pri} | Estimates: {with_est} | Actuals: {with_act}")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info(f"{'='*60}")
    log.info(f"  Economic Calendar Scraper v2")
    log.info(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')} | Window: {LOOKBACK} → {CUTOFF}")
    log.info(f"{'='*60}")

    # Phase 1: Get release dates from FRED (authoritative)
    records = fetch_fred_dates()

    # Phase 2: Add FOMC dates
    records = add_fomc_dates(records)

    # Phase 3: Fetch prior + actual values from FRED observations
    records = fetch_fred_values(records)

    # Phase 4: Fetch consensus estimates (aggressive, multiple sources)
    records = fetch_investing_estimates(records)
    records = fetch_marketwatch_estimates(records)

    # Summary
    print_summary(records)

    # Phase 5: Push to Supabase
    upsert_to_supabase(records)

    log.info(f"\nDone. {len(records)} records processed.")
