"""
Economic Calendar Scraper — Comprehensive Edition
Sources:
  - BLS  (bls.gov)              — CPI, PPI, NFP, JOLTS, Employment Cost Index
  - BEA  (bea.gov)              — GDP, PCE, Personal Income
  - Census (census.gov)         — Retail Sales, Housing Starts, Building Permits,
                                   New Home Sales, Construction Spending, Trade Balance
  - FRED API (stlouisfed.org)   — Release dates for ALL tracked series
  - Treasury (treasury.gov)     — Auction schedule, yield curve
  - Dept of Labor (dol.gov)     — Initial/Continuing Jobless Claims
  - ISM (ismworld.org)          — Manufacturing PMI, Services PMI
  - Univ of Michigan            — Consumer Sentiment (via FRED)
  - Conference Board            — Leading Indicators, Consumer Confidence (via FRED)
  - NAR (nar.realtor)           — Existing Home Sales, Pending Home Sales
  - Federal Reserve             — Industrial Production, Capacity Utilization,
                                   FOMC minutes, Beige Book, H.4.1, G.17
  - MarketWatch                 — Economic calendar / consensus estimates
  - Investing.com               — Economic calendar / consensus estimates
  - TradingEconomics            — Consensus forecasts
  - ForexFactory                — Economic calendar
  - Yahoo Finance               — Market data snapshots (S&P, Nasdaq, 10Y, DXY, VIX)
  - OECD (stats.oecd.org)       — CLI, GDP forecasts
  - World Bank                  — Global macro indicators
  - IMF (imf.org)               — WEO data
  - ECB (ecb.europa.eu)         — Euro-area rates and policy
  - Eurostat                    — Euro-area CPI, GDP, unemployment

NOTE: Some consensus estimates require JavaScript rendering. This scraper
      attempts multiple free sources for consensus data and falls back to
      manual entry where automated scraping isn't possible.

Setup:
  pip install requests beautifulsoup4 lxml python-dotenv

Run:
  python scraper.py
"""

import os
import re
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
from urllib.parse import urlencode, quote

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
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
}

TODAY  = date.today()
CUTOFF = TODAY + timedelta(days=90)   # 90-day forward window

# ─── SERIES MAP ──────────────────────────────────────────────
# Maps lowercase release name fragments → FRED series ID
SERIES_MAP = {
    # Inflation
    "consumer price index":         "CPIAUCSL",
    "cpi":                          "CPIAUCSL",
    "core cpi":                     "CPILFESL",
    "producer price index":         "PPIACO",
    "ppi":                          "PPIACO",
    "pce price":                    "PCEPI",
    "core pce":                     "PCEPILFE",
    "import price":                 "IR",
    "export price":                 "IQ",
    # Labor
    "employment situation":         "PAYEMS",
    "nonfarm payrolls":             "PAYEMS",
    "nonfarm":                      "PAYEMS",
    "unemployment rate":            "UNRATE",
    "unemployment":                 "UNRATE",
    "job openings":                 "JTSJOL",
    "jolts":                        "JTSJOL",
    "initial claims":               "ICSA",
    "initial jobless":              "ICSA",
    "jobless claims":               "ICSA",
    "continuing claims":            "CCSA",
    "employment cost":              "ECIWAG",
    "average hourly earnings":      "CES0500000003",
    # GDP & Output
    "gross domestic product":       "GDP",
    "gdp":                          "GDP",
    "gdp (":                        "GDP",
    "gdp (advance":                 "GDP",
    "gdp (second":                  "GDP",
    "gdp (third":                   "GDP",
    "industrial production":        "INDPRO",
    "capacity utilization":         "TCU",
    "durable goods":                "DGORDER",
    "factory orders":               "AMTMNO",
    # Consumer
    "retail sales":                 "RSAFS",
    "personal income":              "PCEPI",
    "personal income and outlays":  "PCEPI",
    "consumer confidence":          "CSCICP03USM665S",
    "consumer sentiment":           "UMCSENT",
    "michigan sentiment":           "UMCSENT",
    # Housing
    "housing starts":               "HOUST",
    "building permits":             "PERMIT",
    "existing home sales":          "EXHOSLUSM495S",
    "new home sales":               "HSN1F",
    "pending home sales":           "PHSI",
    "case-shiller":                 "CSUSHPISA",
    "home price":                   "CSUSHPISA",
    "construction spending":        "TTLCONS",
    # Trade & Business
    "trade balance":                "BOPGSTB",
    "trade deficit":                "BOPGSTB",
    "ism manufacturing":            "MANEMP",
    "ism services":                 "NMFCI",
    "pmi manufacturing":            "MANEMP",
    "pmi services":                 "NMFCI",
    "leading indicators":           "USSLIND",
    "leading economic":             "USSLIND",
    # Money & Rates
    "federal funds":                "FEDFUNDS",
    "fed funds":                    "FEDFUNDS",
    "m2 money":                     "M2SL",
    "treasury":                     "DGS10",
    "beige book":                   "BEIGE_BOOK",
    "fomc minutes":                 "FOMC_MINUTES",
}

# FRED release IDs → metadata  (aligns with calendar.js RELEASE_META)
FRED_RELEASES = {
    10:  {"series_id": "CPIAUCSL",       "name": "Consumer Price Index (CPI)",      "source": "BLS",              "unit": "%",  "impact": "high"},
    11:  {"series_id": "IR",             "name": "Import & Export Prices",           "source": "BLS",              "unit": "%",  "impact": "low"},
    15:  {"series_id": "RSAFS",          "name": "Retail Sales",                     "source": "Census",           "unit": "%",  "impact": "high"},
    17:  {"series_id": "CSCICP03USM665S","name": "Consumer Confidence",              "source": "Conference Board", "unit": "",   "impact": "medium"},
    19:  {"series_id": "EXHOSLUSM495S",  "name": "Existing Home Sales",             "source": "NAR",              "unit": "M",  "impact": "low"},
    21:  {"series_id": "M2SL",           "name": "M2 Money Supply",                  "source": "Federal Reserve",  "unit": "B$", "impact": "low"},
    31:  {"series_id": "PPIACO",         "name": "Producer Price Index (PPI)",       "source": "BLS",              "unit": "%",  "impact": "medium"},
    46:  {"series_id": "PAYEMS",         "name": "Nonfarm Payrolls",                 "source": "BLS",              "unit": "K",  "impact": "high"},
    50:  {"series_id": "ICSA",           "name": "Initial Jobless Claims",           "source": "Dept of Labor",    "unit": "K",  "impact": "medium"},
    51:  {"series_id": "JTSJOL",         "name": "JOLTS Job Openings",               "source": "BLS",              "unit": "K",  "impact": "medium"},
    53:  {"series_id": "GDP",            "name": "GDP",                              "source": "BEA",              "unit": "%",  "impact": "high"},
    54:  {"series_id": "HSN1F",          "name": "New Home Sales",                   "source": "Census",           "unit": "K",  "impact": "low"},
    55:  {"series_id": "PCEPI",          "name": "PCE / Personal Income",            "source": "BEA",              "unit": "%",  "impact": "medium"},
    56:  {"series_id": "HOUST",          "name": "Housing Starts & Permits",         "source": "Census",           "unit": "K",  "impact": "medium"},
    82:  {"series_id": "USSLIND",        "name": "Leading Economic Indicators",      "source": "Conference Board", "unit": "%",  "impact": "low"},
    86:  {"series_id": "INDPRO",         "name": "Industrial Production",            "source": "Federal Reserve",  "unit": "%",  "impact": "low"},
    113: {"series_id": "ECIWAG",         "name": "Employment Cost Index",            "source": "BLS",              "unit": "%",  "impact": "medium"},
    118: {"series_id": "CSUSHPISA",      "name": "Case-Shiller Home Prices",         "source": "S&P/Case-Shiller", "unit": "%",  "impact": "low"},
    160: {"series_id": "MANEMP",         "name": "ISM Manufacturing PMI",            "source": "ISM",              "unit": "",   "impact": "medium"},
    161: {"series_id": "NMFCI",          "name": "ISM Services PMI",                 "source": "ISM",              "unit": "",   "impact": "medium"},
    175: {"series_id": "TTLCONS",        "name": "Construction Spending",            "source": "Census",           "unit": "%",  "impact": "low"},
    180: {"series_id": "UMCSENT",        "name": "Consumer Sentiment",               "source": "Univ of Michigan", "unit": "",   "impact": "low"},
    200: {"series_id": "PHSI",           "name": "Pending Home Sales",               "source": "NAR",              "unit": "%",  "impact": "low"},
    # Additional releases
    22:  {"series_id": "DGORDER",        "name": "Durable Goods Orders",             "source": "Census",           "unit": "%",  "impact": "medium"},
    32:  {"series_id": "CES0500000003",  "name": "Average Hourly Earnings",          "source": "BLS",              "unit": "%",  "impact": "medium"},
    69:  {"series_id": "BOPGSTB",        "name": "Trade Balance",                    "source": "Census/BEA",       "unit": "B$", "impact": "medium"},
    83:  {"series_id": "AMTMNO",         "name": "Factory Orders",                   "source": "Census",           "unit": "%",  "impact": "low"},
    116: {"series_id": "TCU",            "name": "Capacity Utilization",             "source": "Federal Reserve",  "unit": "%",  "impact": "low"},
    117: {"series_id": "CCSA",           "name": "Continuing Jobless Claims",        "source": "Dept of Labor",    "unit": "K",  "impact": "low"},
}


def match_series(name):
    """Match a release name to a FRED series ID."""
    n = name.lower().strip()
    for key, sid in SERIES_MAP.items():
        if key in n:
            return sid
    return None


def parse_date_flexible(s, year=None):
    """Parse dates in many common US formats."""
    if not s:
        return None
    s = s.strip().replace('.', '').replace(',', ', ')
    s = re.sub(r'\s+', ' ', s).strip()
    if not year:
        year = TODAY.year
    formats = [
        '%B %d, %Y', '%B %d %Y', '%b %d, %Y', '%b %d %Y',
        '%B %d', '%b %d', '%m/%d/%Y', '%m-%d-%Y',
        '%Y-%m-%d', '%d %B %Y', '%d %b %Y',
    ]
    for fmt in formats:
        try:
            d = datetime.strptime(s, fmt)
            if d.year == 1900:
                d = d.replace(year=year)
            return d.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def in_window(date_str):
    """Check if a date string falls within TODAY → CUTOFF."""
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        return TODAY <= d <= CUTOFF
    except (ValueError, TypeError):
        return False


def safe_get(url, timeout=20, retries=3, **kwargs):
    """HTTP GET with retries and exponential backoff."""
    merged_headers = {**HEADERS, **kwargs.pop('headers', {})}
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=merged_headers, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                log.warning(f"  Retry {attempt+1}/{retries} for {url[:80]}... waiting {wait}s")
                time.sleep(wait)
            else:
                log.error(f"  Failed after {retries} attempts: {e}")
                return None
    return None


# ═══════════════════════════════════════════════════════════════
# 1. FRED API — Release Dates  (single authoritative source)
# ═══════════════════════════════════════════════════════════════
def scrape_fred_releases():
    """
    Use the FRED releases/dates API to get upcoming release dates
    for ALL tracked indicators. This is the most reliable source.
    """
    log.info("── FRED API ─────────────────────────────────────")
    results = []

    url = (
        f"https://api.stlouisfed.org/fred/releases/dates"
        f"?api_key={FRED_API_KEY}"
        f"&file_type=json"
        f"&realtime_start={TODAY.isoformat()}"
        f"&realtime_end={CUTOFF.isoformat()}"
        f"&include_release_dates_with_no_data=false"
    )

    resp = safe_get(url)
    if not resp:
        return results

    try:
        data = resp.json()
    except (json.JSONDecodeError, ValueError):
        log.error("  FRED API: invalid JSON response")
        return results

    release_dates = data.get('release_dates', [])
    seen = set()  # (release_id, date) to deduplicate

    for entry in release_dates:
        rid = entry.get('release_id')
        rd  = entry.get('date')
        if rid not in FRED_RELEASES or not in_window(rd):
            continue

        key = (rid, rd)
        if key in seen:
            continue
        seen.add(key)

        meta = FRED_RELEASES[rid]
        sid  = meta['series_id']

        results.append({
            'series_id':    sid,
            'release_name': meta['name'],
            'release_date': rd,
            'estimate':     None,
            'actual':       None,
            'unit':         meta.get('unit', ''),
            'source':       meta.get('source', 'FRED'),
            'impact':       meta.get('impact', 'low'),
        })
        log.info(f"  {sid:<22} {meta['name']:<40} → {rd}")

    log.info(f"  Total: {len(results)} releases from FRED API")
    return results


# ═══════════════════════════════════════════════════════════════
# 2. BLS — Bureau of Labor Statistics
# ═══════════════════════════════════════════════════════════════
def scrape_bls():
    """Scrape BLS release schedule pages for CPI, PPI, NFP, JOLTS, ECI."""
    log.info("── BLS ──────────────────────────────────────────")
    results = []

    pages = [
        ("https://www.bls.gov/schedule/news_release/cpi.htm",    "Consumer Price Index",    "CPIAUCSL", "%",  "high"),
        ("https://www.bls.gov/schedule/news_release/ppi.htm",    "Producer Price Index",    "PPIACO",   "%",  "medium"),
        ("https://www.bls.gov/schedule/news_release/empsit.htm", "Employment Situation",    "PAYEMS",   "K",  "high"),
        ("https://www.bls.gov/schedule/news_release/jolts.htm",  "Job Openings (JOLTS)",    "JTSJOL",   "K",  "medium"),
        ("https://www.bls.gov/schedule/news_release/eci.htm",    "Employment Cost Index",   "ECIWAG",   "%",  "medium"),
        ("https://www.bls.gov/schedule/news_release/ximpim.htm", "Import/Export Prices",    "IR",       "%",  "low"),
    ]

    for url, release_name, series_id, unit, impact in pages:
        try:
            resp = safe_get(url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, 'html.parser')

            tables = soup.find_all('table')
            if len(tables) < 2:
                log.warning(f"  {series_id}: table not found at {url}")
                continue

            schedule_table = tables[1]
            for row in schedule_table.find_all('tr')[1:]:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue

                release_date_str = cells[1].get_text(strip=True)
                rd = parse_date_flexible(release_date_str)
                if not rd or not in_window(rd):
                    continue

                results.append({
                    'series_id':    series_id,
                    'release_name': release_name,
                    'release_date': rd,
                    'estimate':     None,
                    'actual':       None,
                    'unit':         unit,
                    'source':       'BLS',
                    'impact':       impact,
                })
                log.info(f"  {series_id:<22} {release_name} → {rd}")
                break  # only next upcoming

        except Exception as e:
            log.error(f"  {series_id} error: {e}")

    return results


# ═══════════════════════════════════════════════════════════════
# 3. BEA — Bureau of Economic Analysis
# ═══════════════════════════════════════════════════════════════
def scrape_bea():
    """Scrape BEA release schedule for GDP, PCE, Personal Income, Trade."""
    log.info("── BEA ──────────────────────────────────────────")
    results = []
    year = TODAY.year

    resp = safe_get("https://www.bea.gov/news/schedule")
    if not resp:
        return results

    soup = BeautifulSoup(resp.text, 'html.parser')
    tables = soup.find_all('table')
    if not tables:
        log.warning("  BEA: no table found")
        return results

    text = tables[0].get_text(' ', strip=True)

    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    month_pat = '|'.join(month_names)

    pattern = re.compile(
        r'((?:' + month_pat + r')\s+\d{1,2})\s+'
        r'[\d:]+\s+[AP]M\s+'
        r'(?:N\s*ews\s+|D\s*ata\s+|V\s*isual\s+|A\s*rticle\s+)*'
        r'([A-Z][^\d]{5,100}?)(?=\s+(?:' + month_pat + r')|\s*$)',
        re.IGNORECASE
    )

    for m in pattern.finditer(text):
        month_day    = m.group(1).strip()
        release_name = m.group(2).strip()

        rd = parse_date_flexible(month_day, year)
        if rd and not in_window(rd):
            rd = parse_date_flexible(month_day, year + 1)
        if not rd or not in_window(rd):
            continue

        series_id = match_series(release_name)
        if not series_id:
            continue

        if any(r['series_id'] == series_id for r in results):
            continue

        results.append({
            'series_id':    series_id,
            'release_name': release_name[:60].strip(),
            'release_date': rd,
            'estimate':     None,
            'actual':       None,
            'unit':         '%' if series_id in ('GDP', 'PCEPI', 'PCEPILFE') else '',
            'source':       'BEA',
            'impact':       'high' if series_id == 'GDP' else 'medium',
        })
        log.info(f"  {series_id:<22} {release_name[:50]} → {rd}")

    if not results:
        log.warning("  BEA: no matching releases found")
    return results


# ═══════════════════════════════════════════════════════════════
# 4. Census Bureau — Retail Sales, Housing, Trade, Construction
# ═══════════════════════════════════════════════════════════════
def scrape_census():
    """Scrape Census Bureau economic indicator release schedule."""
    log.info("── Census Bureau ────────────────────────────────")
    results = []

    resp = safe_get("https://www.census.gov/economic-indicators/calendar-listview.html")
    if not resp:
        return results

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Census lists releases in a structured list/table on the calendar page
    seen = set()
    for item in soup.find_all(['tr', 'li', 'div']):
        text = item.get_text(' ', strip=True)
        if len(text) < 10 or len(text) > 500:
            continue

        # Try to find a date pattern
        date_match = re.search(
            r'((?:January|February|March|April|May|June|July|August|September|'
            r'October|November|December)\s+\d{1,2},?\s*\d{4})',
            text, re.IGNORECASE
        )
        if not date_match:
            continue

        rd = parse_date_flexible(date_match.group(1))
        if not rd or not in_window(rd):
            continue

        series_id = match_series(text)
        if not series_id or series_id in seen:
            continue
        seen.add(series_id)

        release_name = text[:80].split('\n')[0].strip()
        results.append({
            'series_id':    series_id,
            'release_name': release_name[:60],
            'release_date': rd,
            'estimate':     None,
            'actual':       None,
            'unit':         '%',
            'source':       'Census',
            'impact':       'high' if series_id == 'RSAFS' else 'low',
        })
        log.info(f"  {series_id:<22} {release_name[:50]} → {rd}")

    return results


# ═══════════════════════════════════════════════════════════════
# 5. Treasury.gov — Auction Schedule & Yield Data
# ═══════════════════════════════════════════════════════════════
def scrape_treasury():
    """Scrape Treasury auction schedule and yield curve data."""
    log.info("── Treasury.gov ─────────────────────────────────")
    results = []

    # Treasury auction schedule
    resp = safe_get("https://www.treasurydirect.gov/auctions/upcoming/")
    if resp:
        soup = BeautifulSoup(resp.text, 'html.parser')
        auctions = []

        for table in soup.find_all('table'):
            for row in table.find_all('tr')[1:]:
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
                text = ' '.join(c.get_text(strip=True) for c in cells)
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
                if date_match:
                    rd = parse_date_flexible(date_match.group(1))
                    if rd and in_window(rd):
                        security_type = cells[0].get_text(strip=True) if cells else 'Treasury'
                        auctions.append({
                            'security_type': security_type[:60],
                            'auction_date':  rd,
                            'raw_text':      text[:200],
                        })

        if auctions:
            log.info(f"  Found {len(auctions)} upcoming Treasury auctions")
            for a in auctions[:10]:
                log.info(f"    {a['security_type']:<30} → {a['auction_date']}")
    else:
        log.warning("  Treasury auction page unavailable")

    # Treasury yield curve data (XML feed)
    resp = safe_get(
        "https://data.treasury.gov/feed.svc/DailyTreasuryYieldCurveRateData?"
        "$filter=month(NEW_DATE)%20eq%20" + str(TODAY.month) +
        "%20and%20year(NEW_DATE)%20eq%20" + str(TODAY.year) +
        "&$orderby=NEW_DATE%20desc&$top=5"
    )
    if resp:
        try:
            soup = BeautifulSoup(resp.text, 'xml')
            entries = soup.find_all('entry')
            for entry in entries[:3]:
                props = entry.find('m:properties') or entry.find('properties')
                if not props:
                    continue
                bc_10y = props.find('BC_10YEAR') or props.find('d:BC_10YEAR')
                bc_2y  = props.find('BC_2YEAR')  or props.find('d:BC_2YEAR')
                bc_30y = props.find('BC_30YEAR') or props.find('d:BC_30YEAR')
                new_date = props.find('NEW_DATE') or props.find('d:NEW_DATE')
                if bc_10y and new_date:
                    log.info(f"  Yield curve: 2Y={bc_2y.text if bc_2y else '?'}  "
                             f"10Y={bc_10y.text}  30Y={bc_30y.text if bc_30y else '?'}  "
                             f"date={new_date.text[:10]}")
        except Exception as e:
            log.warning(f"  Yield curve parse error: {e}")

    return results


# ═══════════════════════════════════════════════════════════════
# 6. MarketWatch — Economic Calendar with Consensus Estimates
# ═══════════════════════════════════════════════════════════════
def scrape_marketwatch():
    """
    Scrape MarketWatch economic calendar for consensus estimates.
    This is one of the best free sources for consensus data.
    """
    log.info("── MarketWatch ──────────────────────────────────")
    results = []

    for delta in range(0, 14, 7):  # This week and next week
        target = TODAY + timedelta(days=delta)
        # MarketWatch calendar URL uses start-of-week dates
        start_of_week = target - timedelta(days=target.weekday())
        date_str = start_of_week.strftime('%Y%m%d')

        resp = safe_get(
            f"https://www.marketwatch.com/economy-politics/calendar?date={date_str}",
            headers={"Referer": "https://www.marketwatch.com/"}
        )
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Parse calendar table rows
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 3:
                continue

            text = row.get_text(' ', strip=True)
            series_id = match_series(text)
            if not series_id:
                continue

            # Try to extract date from the row or parent
            date_match = re.search(
                r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2})',
                text, re.IGNORECASE
            )
            rd = None
            if date_match:
                rd = parse_date_flexible(date_match.group(1))

            # Try to extract consensus estimate
            estimate = None
            for cell in cells:
                cell_text = cell.get_text(strip=True)
                num_match = re.search(r'(-?\d+\.?\d*)\s*(%|K|M|B)?', cell_text)
                if num_match and 'consensus' in (cell.get('class', []) + [cell.get('data-field', '')]):
                    try:
                        estimate = float(num_match.group(1))
                    except ValueError:
                        pass

            if rd and in_window(rd) and not any(r['series_id'] == series_id for r in results):
                results.append({
                    'series_id':    series_id,
                    'release_name': text[:60].split('\n')[0].strip(),
                    'release_date': rd,
                    'estimate':     estimate,
                    'actual':       None,
                    'unit':         '',
                    'source':       'MarketWatch',
                    'impact':       'medium',
                })
                est_str = str(estimate) if estimate else '—'
                log.info(f"  {series_id:<22} est={est_str:<10} → {rd}")

    return results


# ═══════════════════════════════════════════════════════════════
# 7. Investing.com — Economic Calendar
# ═══════════════════════════════════════════════════════════════
def scrape_investing():
    """Scrape Investing.com economic calendar for US events."""
    log.info("── Investing.com ────────────────────────────────")
    results = []

    resp = safe_get(
        "https://www.investing.com/economic-calendar/",
        headers={
            **HEADERS,
            "Referer": "https://www.investing.com/",
        }
    )
    if not resp:
        return results

    soup = BeautifulSoup(resp.text, 'html.parser')

    for row in soup.find_all('tr', class_=re.compile(r'js-event-item')):
        # Country filter — US only
        flag = row.find('td', class_=re.compile(r'flag'))
        if flag:
            flag_span = flag.find('span')
            if flag_span and 'United States' not in flag_span.get('title', ''):
                continue

        event_cell = row.find('td', class_=re.compile(r'event'))
        if not event_cell:
            continue

        event_name = event_cell.get_text(strip=True)
        series_id = match_series(event_name)
        if not series_id:
            continue

        # Extract date
        date_attr = row.get('data-event-datetime', '')
        rd = None
        if date_attr:
            rd = date_attr[:10] if len(date_attr) >= 10 else None

        # Extract consensus/forecast
        estimate = None
        forecast_cell = row.find('td', class_=re.compile(r'fore'))
        if forecast_cell:
            num_match = re.search(r'(-?\d+\.?\d*)', forecast_cell.get_text(strip=True))
            if num_match:
                try:
                    estimate = float(num_match.group(1))
                except ValueError:
                    pass

        # Extract actual value if released
        actual = None
        actual_cell = row.find('td', class_=re.compile(r'act'))
        if actual_cell:
            num_match = re.search(r'(-?\d+\.?\d*)', actual_cell.get_text(strip=True))
            if num_match:
                try:
                    actual = float(num_match.group(1))
                except ValueError:
                    pass

        if rd and in_window(rd) and not any(r['series_id'] == series_id for r in results):
            results.append({
                'series_id':    series_id,
                'release_name': event_name[:60],
                'release_date': rd,
                'estimate':     estimate,
                'actual':       actual,
                'unit':         '',
                'source':       'Investing.com',
                'impact':       'medium',
            })
            est_str = str(estimate) if estimate else '—'
            log.info(f"  {series_id:<22} est={est_str:<10} → {rd}")

    return results


# ═══════════════════════════════════════════════════════════════
# 8. ForexFactory — Economic Calendar
# ═══════════════════════════════════════════════════════════════
def scrape_forexfactory():
    """Scrape ForexFactory economic calendar for US events."""
    log.info("── ForexFactory ─────────────────────────────────")
    results = []

    resp = safe_get(
        "https://www.forexfactory.com/calendar?week=this",
        headers={
            **HEADERS,
            "Referer": "https://www.forexfactory.com/",
        }
    )
    if not resp:
        return results

    soup = BeautifulSoup(resp.text, 'html.parser')

    current_date = None
    for row in soup.find_all('tr', class_=re.compile(r'calendar__row')):
        # Date header
        date_cell = row.find('td', class_=re.compile(r'calendar__date'))
        if date_cell:
            date_text = date_cell.get_text(strip=True)
            if date_text:
                date_match = re.search(
                    r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+'
                    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2})',
                    date_text, re.IGNORECASE
                )
                if date_match:
                    current_date = parse_date_flexible(date_match.group(1))

        # Currency filter — USD only
        currency = row.find('td', class_=re.compile(r'calendar__currency'))
        if currency and 'USD' not in currency.get_text(strip=True):
            continue

        event_cell = row.find('td', class_=re.compile(r'calendar__event'))
        if not event_cell:
            continue

        event_name = event_cell.get_text(strip=True)
        series_id = match_series(event_name)
        if not series_id:
            continue

        # Forecast/consensus
        estimate = None
        forecast_cell = row.find('td', class_=re.compile(r'calendar__forecast'))
        if forecast_cell:
            num_match = re.search(r'(-?\d+\.?\d*)', forecast_cell.get_text(strip=True))
            if num_match:
                try:
                    estimate = float(num_match.group(1))
                except ValueError:
                    pass

        rd = current_date or TODAY.isoformat()
        if in_window(rd) and not any(r['series_id'] == series_id for r in results):
            results.append({
                'series_id':    series_id,
                'release_name': event_name[:60],
                'release_date': rd,
                'estimate':     estimate,
                'actual':       None,
                'unit':         '',
                'source':       'ForexFactory',
                'impact':       'medium',
            })
            est_str = str(estimate) if estimate else '—'
            log.info(f"  {series_id:<22} est={est_str:<10} → {rd}")

    return results


# ═══════════════════════════════════════════════════════════════
# 9. Trading Economics — Consensus Forecasts
# ═══════════════════════════════════════════════════════════════
def scrape_tradingeconomics():
    """Scrape Trading Economics calendar for consensus estimates."""
    log.info("── Trading Economics ─────────────────────────────")
    results = []

    resp = safe_get(
        "https://tradingeconomics.com/united-states/calendar",
        headers={
            **HEADERS,
            "Referer": "https://tradingeconomics.com/",
        }
    )
    if not resp:
        return results

    soup = BeautifulSoup(resp.text, 'html.parser')

    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 5:
            continue

        text = row.get_text(' ', strip=True)
        series_id = match_series(text)
        if not series_id:
            continue

        # Date extraction
        date_cell = cells[0].get_text(strip=True) if cells else ''
        rd = parse_date_flexible(date_cell)
        if not rd:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(row))
            if date_match:
                rd = date_match.group(1)

        # Forecast column (usually column index 3 or 4)
        estimate = None
        for idx in [3, 4, 5]:
            if idx < len(cells):
                num_match = re.search(r'(-?\d+\.?\d*)', cells[idx].get_text(strip=True))
                if num_match:
                    try:
                        estimate = float(num_match.group(1))
                        break
                    except ValueError:
                        pass

        if rd and in_window(rd) and not any(r['series_id'] == series_id for r in results):
            results.append({
                'series_id':    series_id,
                'release_name': text[:60].split('\n')[0].strip(),
                'release_date': rd,
                'estimate':     estimate,
                'actual':       None,
                'unit':         '',
                'source':       'TradingEconomics',
                'impact':       'medium',
            })
            est_str = str(estimate) if estimate else '—'
            log.info(f"  {series_id:<22} est={est_str:<10} → {rd}")

    return results


# ═══════════════════════════════════════════════════════════════
# 10. Federal Reserve — FOMC, Beige Book, H.4.1, G.17
# ═══════════════════════════════════════════════════════════════
def scrape_federal_reserve():
    """Scrape Federal Reserve for FOMC, Beige Book, and other releases."""
    log.info("── Federal Reserve ──────────────────────────────")
    results = []

    # ── FOMC meeting dates ──
    resp = safe_get("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    if resp:
        soup = BeautifulSoup(resp.text, 'html.parser')
        for panel in soup.find_all(['div', 'tr', 'td']):
            text = panel.get_text(' ', strip=True)
            # Look for date patterns like "January 28-29" or "March 18-19"
            fomc_match = re.search(
                r'((?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December)\s+\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?',
                text
            )
            if fomc_match:
                # Decision date is the last day of the meeting
                month_day = fomc_match.group(1)
                last_day = fomc_match.group(2)
                if last_day:
                    parts = month_day.split()
                    month_day = f"{parts[0]} {last_day}"
                rd = parse_date_flexible(month_day)
                if rd and in_window(rd) and not any(
                    r.get('release_name', '').startswith('FOMC') and r['release_date'] == rd
                    for r in results
                ):
                    results.append({
                        'series_id':    'FEDFUNDS',
                        'release_name': 'FOMC Interest Rate Decision',
                        'release_date': rd,
                        'estimate':     None,
                        'actual':       None,
                        'unit':         '%',
                        'source':       'Federal Reserve',
                        'impact':       'high',
                    })
                    log.info(f"  FOMC decision → {rd}")

    # ── Beige Book dates ──
    resp = safe_get("https://www.federalreserve.gov/monetarypolicy/beige-book-default.htm")
    if resp:
        soup = BeautifulSoup(resp.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            date_match = re.search(
                r'((?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December)\s+\d{1,2},?\s*\d{4})',
                text, re.IGNORECASE
            )
            if date_match:
                rd = parse_date_flexible(date_match.group(1))
                if rd and in_window(rd):
                    results.append({
                        'series_id':    'BEIGE_BOOK',
                        'release_name': 'Beige Book',
                        'release_date': rd,
                        'estimate':     None,
                        'actual':       None,
                        'unit':         '',
                        'source':       'Federal Reserve',
                        'impact':       'medium',
                    })
                    log.info(f"  Beige Book → {rd}")
                    break

    # ── Fed speeches calendar ──
    resp = safe_get("https://www.federalreserve.gov/newsevents/speech.htm")
    if resp:
        soup = BeautifulSoup(resp.text, 'html.parser')
        speech_count = 0
        for item in soup.find_all(['div', 'li'], class_=re.compile(r'row|item|speech')):
            text = item.get_text(' ', strip=True)
            date_match = re.search(
                r'((?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December)\s+\d{1,2},?\s*\d{4})',
                text, re.IGNORECASE
            )
            if date_match:
                rd = parse_date_flexible(date_match.group(1))
                if rd and in_window(rd):
                    speech_count += 1
        if speech_count:
            log.info(f"  Found {speech_count} upcoming Fed speeches")

    return results


# ═══════════════════════════════════════════════════════════════
# 11. Yahoo Finance — Market Data Snapshots
# ═══════════════════════════════════════════════════════════════
def scrape_yahoo_markets():
    """Fetch current market snapshot from Yahoo Finance."""
    log.info("── Yahoo Finance Markets ────────────────────────")
    market_data = []

    symbols = {
        '^GSPC':   'S&P 500',
        '^IXIC':   'Nasdaq Composite',
        '^DJI':    'Dow Jones',
        '^TNX':    '10-Year Treasury Yield',
        '^VIX':    'VIX Volatility Index',
        'DX-Y.NYB':'US Dollar Index (DXY)',
        'GC=F':    'Gold Futures',
        'CL=F':    'Crude Oil (WTI)',
        'BTC-USD': 'Bitcoin',
    }

    for symbol, name in symbols.items():
        resp = safe_get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}"
            f"?range=5d&interval=1d",
            headers={"User-Agent": HEADERS["User-Agent"]}
        )
        if not resp:
            continue

        try:
            data = resp.json()
            result = data.get('chart', {}).get('result', [{}])[0]
            meta = result.get('meta', {})
            price = meta.get('regularMarketPrice')
            prev  = meta.get('chartPreviousClose') or meta.get('previousClose')
            if price:
                change = ((price - prev) / prev * 100) if prev else 0
                market_data.append({
                    'symbol': symbol,
                    'name':   name,
                    'price':  round(price, 2),
                    'change': round(change, 2),
                })
                log.info(f"  {name:<30} {price:>12,.2f}  ({change:+.2f}%)")
        except Exception as e:
            log.warning(f"  {symbol} parse error: {e}")

    return market_data


# ═══════════════════════════════════════════════════════════════
# 12. OECD — Composite Leading Indicators & Forecasts
# ═══════════════════════════════════════════════════════════════
def scrape_oecd():
    """Fetch OECD Composite Leading Indicator for the US."""
    log.info("── OECD ─────────────────────────────────────────")
    results = []

    resp = safe_get(
        "https://stats.oecd.org/sdmx-json/data/DP_LIVE/.CLI.../OECD"
        "?contentType=csv&detail=code&separator=comma&csv-lang=en"
        "&startPeriod=" + str(TODAY.year - 1),
        timeout=30
    )
    if resp and resp.status_code == 200:
        lines = resp.text.strip().split('\n')
        us_lines = [l for l in lines if ',USA,' in l or ',US,' in l]
        if us_lines:
            latest = us_lines[-1]
            log.info(f"  OECD CLI (US): {latest[:120]}")
    else:
        log.info("  OECD data: using FRED proxy (USALOLITONOSTSAM)")

    # Fallback: get CLI via FRED
    resp = safe_get(
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id=USALOLITONOSTSAM&api_key={FRED_API_KEY}"
        f"&file_type=json&sort_order=desc&limit=3"
    )
    if resp:
        try:
            data = resp.json()
            obs = data.get('observations', [])
            if obs:
                latest = obs[0]
                log.info(f"  OECD CLI via FRED: {latest.get('value')} ({latest.get('date')})")
        except Exception as e:
            log.warning(f"  OECD FRED parse error: {e}")

    return results


# ═══════════════════════════════════════════════════════════════
# 13. World Bank — Global Macro Indicators
# ═══════════════════════════════════════════════════════════════
def scrape_worldbank():
    """Fetch key World Bank indicators for the US."""
    log.info("── World Bank ───────────────────────────────────")

    indicators = {
        'NY.GDP.MKTP.CD':     'GDP (current US$)',
        'NY.GDP.MKTP.KD.ZG':  'GDP Growth (%)',
        'FP.CPI.TOTL.ZG':     'Inflation (CPI %)',
        'SL.UEM.TOTL.ZS':     'Unemployment (%)',
        'NE.TRD.GNFS.ZS':     'Trade (% of GDP)',
        'BN.CAB.XOKA.GD.ZS':  'Current Account (% of GDP)',
        'GC.DOD.TOTL.GD.ZS':  'Govt Debt (% of GDP)',
    }

    for ind_id, name in indicators.items():
        resp = safe_get(
            f"https://api.worldbank.org/v2/country/US/indicator/{ind_id}"
            f"?format=json&per_page=3&date={TODAY.year-2}:{TODAY.year}",
            timeout=15
        )
        if not resp:
            continue

        try:
            data = resp.json()
            if len(data) > 1 and data[1]:
                for entry in data[1]:
                    val = entry.get('value')
                    if val is not None:
                        log.info(f"  {name:<35} {val:>12,.2f}  ({entry.get('date')})")
                        break
        except Exception as e:
            log.warning(f"  {ind_id} parse error: {e}")


# ═══════════════════════════════════════════════════════════════
# 14. IMF — World Economic Outlook Data
# ═══════════════════════════════════════════════════════════════
def scrape_imf():
    """Fetch IMF WEO projections for the US."""
    log.info("── IMF ──────────────────────────────────────────")

    # IMF WEO API
    resp = safe_get(
        "https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH/USA",
        timeout=20
    )
    if resp:
        try:
            data = resp.json()
            values = data.get('values', {}).get('NGDP_RPCH', {}).get('USA', {})
            recent = {k: v for k, v in values.items()
                      if int(k) >= TODAY.year - 1}
            for yr in sorted(recent.keys()):
                log.info(f"  US GDP Growth forecast ({yr}): {recent[yr]}%")
        except Exception as e:
            log.warning(f"  IMF parse error: {e}")


# ═══════════════════════════════════════════════════════════════
# 15. ECB — Euro-area Rates (for global context)
# ═══════════════════════════════════════════════════════════════
def scrape_ecb():
    """Fetch ECB key interest rates."""
    log.info("── ECB ──────────────────────────────────────────")

    resp = safe_get(
        "https://data.ecb.europa.eu/data-detail/FM.D.U2.EUR.4F.KR.MRR_FR.LEV",
        timeout=15
    )
    if resp:
        # ECB page — extract latest rate from structured data
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup.find_all(['span', 'td', 'div']):
            text = tag.get_text(strip=True)
            if re.match(r'^\d+\.\d+$', text) and float(text) < 10:
                log.info(f"  ECB Main Refinancing Rate: {text}%")
                break

    # ECB via FRED
    resp = safe_get(
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id=ECBMRRFR&api_key={FRED_API_KEY}"
        f"&file_type=json&sort_order=desc&limit=1"
    )
    if resp:
        try:
            data = resp.json()
            obs = data.get('observations', [])
            if obs:
                log.info(f"  ECB rate via FRED: {obs[0].get('value')}% ({obs[0].get('date')})")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# 16. Eurostat — Euro-area Macro (for global context)
# ═══════════════════════════════════════════════════════════════
def scrape_eurostat():
    """Fetch Eurostat headline indicators via their JSON API."""
    log.info("── Eurostat ─────────────────────────────────────")

    datasets = {
        'prc_hicp_manr': 'Euro-area HICP Inflation',
        'namq_10_gdp':   'Euro-area GDP',
        'une_rt_m':      'Euro-area Unemployment',
    }

    for ds_id, name in datasets.items():
        resp = safe_get(
            f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{ds_id}"
            f"?format=JSON&lang=en&geo=EA&sinceTimePeriod={TODAY.year - 1}M01",
            timeout=20
        )
        if resp:
            try:
                data = resp.json()
                values = data.get('value', {})
                if values:
                    # Get last non-null value
                    latest_key = max(values.keys(), key=int)
                    log.info(f"  {name}: {values[latest_key]}")
            except Exception as e:
                log.warning(f"  {ds_id}: {e}")


# ═══════════════════════════════════════════════════════════════
# 17. ISM — Manufacturing & Services PMI (direct)
# ═══════════════════════════════════════════════════════════════
def scrape_ism():
    """Attempt to scrape ISM release dates from ismworld.org."""
    log.info("── ISM ──────────────────────────────────────────")
    results = []

    resp = safe_get("https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/")
    if resp:
        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text(' ', strip=True)

        # Try to find next release date
        date_matches = re.findall(
            r'((?:January|February|March|April|May|June|July|August|September|'
            r'October|November|December)\s+\d{1,2},?\s*\d{4})',
            text, re.IGNORECASE
        )
        for dm in date_matches:
            rd = parse_date_flexible(dm)
            if rd and in_window(rd):
                if not any(r['series_id'] == 'MANEMP' for r in results):
                    results.append({
                        'series_id':    'MANEMP',
                        'release_name': 'ISM Manufacturing PMI',
                        'release_date': rd,
                        'estimate':     None,
                        'actual':       None,
                        'unit':         '',
                        'source':       'ISM',
                        'impact':       'medium',
                    })
                    log.info(f"  ISM Manufacturing PMI → {rd}")
                    break

    return results


# ═══════════════════════════════════════════════════════════════
# 18. NAR — National Association of Realtors
# ═══════════════════════════════════════════════════════════════
def scrape_nar():
    """Scrape NAR for Existing Home Sales and Pending Home Sales dates."""
    log.info("── NAR (Realtors) ─────────────────────────────")
    results = []

    resp = safe_get("https://www.nar.realtor/research-and-statistics")
    if resp:
        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text(' ', strip=True)

        for keyword, sid, name in [
            ('existing home sales',  'EXHOSLUSM495S', 'Existing Home Sales'),
            ('pending home sales',   'PHSI',          'Pending Home Sales'),
        ]:
            idx = text.lower().find(keyword)
            if idx < 0:
                continue
            context = text[idx:idx+200]
            date_match = re.search(
                r'((?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December)\s+\d{1,2},?\s*\d{4})',
                context, re.IGNORECASE
            )
            if date_match:
                rd = parse_date_flexible(date_match.group(1))
                if rd and in_window(rd):
                    results.append({
                        'series_id':    sid,
                        'release_name': name,
                        'release_date': rd,
                        'estimate':     None,
                        'actual':       None,
                        'unit':         '%',
                        'source':       'NAR',
                        'impact':       'low',
                    })
                    log.info(f"  {sid:<22} {name} → {rd}")

    return results


# ═══════════════════════════════════════════════════════════════
# 19. Dept of Labor — Weekly Claims
# ═══════════════════════════════════════════════════════════════
def scrape_dol():
    """Scrape Department of Labor for jobless claims schedule."""
    log.info("── Dept of Labor ──────────────────────────────")
    results = []

    resp = safe_get("https://www.dol.gov/ui/data.pdf", timeout=10)
    # DOL doesn't have a clean HTML schedule — rely on FRED API for claims dates
    # But we can still try the news page
    resp = safe_get("https://www.dol.gov/newsroom/economicdata")
    if resp:
        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.find_all(['li', 'div', 'tr']):
            text = item.get_text(' ', strip=True)
            if 'claims' not in text.lower():
                continue
            date_match = re.search(
                r'((?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December)\s+\d{1,2},?\s*\d{4})',
                text, re.IGNORECASE
            )
            if date_match:
                rd = parse_date_flexible(date_match.group(1))
                if rd and in_window(rd):
                    if not any(r['series_id'] == 'ICSA' for r in results):
                        results.append({
                            'series_id':    'ICSA',
                            'release_name': 'Initial Jobless Claims',
                            'release_date': rd,
                            'estimate':     None,
                            'actual':       None,
                            'unit':         'K',
                            'source':       'Dept of Labor',
                            'impact':       'medium',
                        })
                        log.info(f"  ICSA: Initial Jobless Claims → {rd}")
                        break

    return results


# ═══════════════════════════════════════════════════════════════
# 20. Conference Board — LEI & Consumer Confidence
# ═══════════════════════════════════════════════════════════════
def scrape_conference_board():
    """Attempt to scrape Conference Board release schedule."""
    log.info("── Conference Board ─────────────────────────────")
    results = []

    resp = safe_get("https://www.conference-board.org/us/")
    if resp:
        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text(' ', strip=True)

        for keyword, sid, name in [
            ('consumer confidence', 'CSCICP03USM665S', 'Consumer Confidence'),
            ('leading economic',    'USSLIND',         'Leading Economic Indicators'),
        ]:
            idx = text.lower().find(keyword)
            if idx < 0:
                continue
            context = text[max(0, idx-50):idx+200]
            date_match = re.search(
                r'((?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December)\s+\d{1,2},?\s*\d{4})',
                context, re.IGNORECASE
            )
            if date_match:
                rd = parse_date_flexible(date_match.group(1))
                if rd and in_window(rd):
                    results.append({
                        'series_id':    sid,
                        'release_name': name,
                        'release_date': rd,
                        'estimate':     None,
                        'actual':       None,
                        'unit':         '',
                        'source':       'Conference Board',
                        'impact':       'medium',
                    })
                    log.info(f"  {sid:<22} {name} → {rd}")

    return results


# ═══════════════════════════════════════════════════════════════
# MERGE & DEDUPLICATE
# ═══════════════════════════════════════════════════════════════
def merge_results(*source_lists):
    """
    Merge records from multiple sources, keyed by (series_id, release_date).
    A single series can have multiple upcoming dates (e.g. weekly claims).
    Priority:
    1. Prefer records with consensus estimates over those without
    2. Prefer government sources (BLS/BEA/Census) for metadata
    3. Prefer market sources (MarketWatch/Investing) for estimates
    """
    merged = {}
    PRIORITY_SOURCES = ['BLS', 'BEA', 'Census', 'FRED', 'Federal Reserve', 'Dept of Labor']

    for source in source_lists:
        for item in source:
            key = (item['series_id'], item.get('release_date', ''))
            if key not in merged:
                merged[key] = item.copy()
            else:
                existing = merged[key]
                # If new item has an estimate and existing doesn't, take the estimate
                if item.get('estimate') is not None and existing.get('estimate') is None:
                    existing['estimate'] = item['estimate']
                # If new item has an actual and existing doesn't, take the actual
                if item.get('actual') is not None and existing.get('actual') is None:
                    existing['actual'] = item['actual']
                # Prefer government source metadata
                if (item.get('source') in PRIORITY_SOURCES and
                        existing.get('source') not in PRIORITY_SOURCES):
                    existing['source'] = item['source']
                    existing['impact'] = item.get('impact', existing.get('impact'))

    return list(merged.values())


# ═══════════════════════════════════════════════════════════════
# MANUAL ESTIMATES
# ═══════════════════════════════════════════════════════════════
# Fill these in each week from Econoday or Bloomberg or any other source.
# Format: 'FRED_SERIES_ID': estimate_as_float
MANUAL_ESTIMATES = {
    # 'CPIAUCSL':  2.9,       # CPI YoY %
    # 'CPILFESL':  3.2,       # Core CPI YoY %
    # 'PAYEMS':    185,        # NFP change in thousands
    # 'UNRATE':    4.1,        # Unemployment rate %
    # 'GDP':       2.3,        # GDP growth % QoQ annualized
    # 'PCEPI':     2.6,        # PCE price index YoY %
    # 'PCEPILFE':  2.7,        # Core PCE YoY %
    # 'PPIACO':    3.1,        # PPI YoY %
    # 'RSAFS':     0.4,        # Retail Sales MoM %
    # 'ICSA':      220,        # Initial Claims thousands
    # 'JTSJOL':    8800,       # JOLTS openings thousands
    # 'HOUST':     1400,       # Housing Starts thousands annualized
    # 'PERMIT':    1450,       # Building Permits thousands annualized
    # 'HSN1F':     680,        # New Home Sales thousands annualized
    # 'INDPRO':    0.3,        # Industrial Production MoM %
    # 'UMCSENT':   67.5,       # Michigan Consumer Sentiment
    # 'DGORDER':   1.2,        # Durable Goods MoM %
    # 'MANEMP':    50.5,       # ISM Manufacturing PMI
    # 'NMFCI':     52.0,       # ISM Services PMI
    # 'BOPGSTB':  -68.5,       # Trade Balance billions
}


def apply_manual_estimates(records):
    """Apply manually entered consensus estimates to records."""
    applied = 0
    for r in records:
        if r['series_id'] in MANUAL_ESTIMATES:
            r['estimate'] = MANUAL_ESTIMATES[r['series_id']]
            applied += 1
            log.info(f"  Manual estimate: {r['series_id']} = {r['estimate']}")
    if applied:
        log.info(f"  Applied {applied} manual estimates")
    return records


# ═══════════════════════════════════════════════════════════════
# SUPABASE UPSERT
# ═══════════════════════════════════════════════════════════════
def upsert_to_supabase(records):
    """Upsert economic calendar records to Supabase."""
    log.info("── Supabase Upsert ──────────────────────────────")
    if not records:
        log.info("  No records to upsert")
        return

    if not SUPABASE_KEY:
        log.warning("  SUPABASE_KEY not set — skipping upsert")
        return

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    rows = [{
        "series_id":    r['series_id'],
        "release_name": r.get('release_name', ''),
        "release_date": r['release_date'],
        "estimate":     r.get('estimate'),
        "actual":       r.get('actual'),
        "unit":         r.get('unit', ''),
        "source":       r.get('source', ''),
        "impact":       r.get('impact', 'low'),
        "updated_at":   datetime.utcnow().isoformat(),
    } for r in records]

    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/consensus",
            json=rows,
            headers=headers,
            timeout=15,
        )
        if res.status_code in (200, 201):
            log.info(f"  Upserted {len(rows)} records to consensus table")
            for r in rows:
                est = r['estimate'] if r['estimate'] is not None else '—'
                log.info(f"    {r['series_id']:<22} date={r['release_date']}  est={est}")
        else:
            log.error(f"  Supabase error {res.status_code}: {res.text[:300]}")
    except requests.RequestException as e:
        log.error(f"  Supabase request failed: {e}")

    # Also upsert to scrape_log table
    log_rows = [{
        "series_id":    r['series_id'],
        "release_date": r['release_date'],
        "estimate":     r.get('estimate'),
        "actual":       r.get('actual'),
        "source":       r.get('source', ''),
        "scraped_at":   datetime.utcnow().isoformat(),
    } for r in records]

    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/scrape_log",
            json=log_rows,
            headers=headers,
            timeout=15,
        )
        if res.status_code in (200, 201):
            log.info(f"  Logged {len(log_rows)} entries to scrape_log")
        else:
            log.warning(f"  scrape_log upsert: {res.status_code} (table may not exist yet)")
    except requests.RequestException:
        pass

    # Upsert market data if available
    return


def upsert_market_data(market_data):
    """Upsert market snapshot data to Supabase."""
    if not market_data or not SUPABASE_KEY:
        return

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    rows = [{
        "symbol":     m['symbol'],
        "name":       m['name'],
        "price":      m['price'],
        "change_pct": m['change'],
        "snapshot_at": datetime.utcnow().isoformat(),
    } for m in market_data]

    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/market_snapshots",
            json=rows,
            headers=headers,
            timeout=15,
        )
        if res.status_code in (200, 201):
            log.info(f"  Upserted {len(rows)} market snapshots")
        else:
            log.warning(f"  market_snapshots upsert: {res.status_code} (table may not exist yet)")
    except requests.RequestException:
        pass


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
def print_summary(records, market_data=None):
    """Print a formatted summary of all scraped data."""
    log.info("── Summary ───────────────────────────────────────")
    if not records:
        log.info("  No records found")
        return

    log.info(f"  {'Series':<22} {'Release':<30} {'Date':<14} {'Est':<10} {'Source':<18} Impact")
    log.info(f"  {'─'*110}")

    for r in sorted(records, key=lambda x: x.get('release_date', '')):
        est = str(r['estimate']) if r.get('estimate') is not None else '—'
        impact = r.get('impact', '')
        log.info(
            f"  {r['series_id']:<22} {r.get('release_name','')[:30]:<30} "
            f"{r.get('release_date',''):<14} {est:<10} {r.get('source',''):<18} {impact}"
        )

    # Stats
    with_est = sum(1 for r in records if r.get('estimate') is not None)
    sources  = set(r.get('source', '') for r in records)
    log.info(f"\n  Total: {len(records)} indicators from {len(sources)} sources")
    log.info(f"  With consensus estimate: {with_est}/{len(records)}")
    log.info(f"  Sources: {', '.join(sorted(sources))}")

    if with_est < len(records):
        log.info(f"\n  To add missing estimates, edit MANUAL_ESTIMATES dict or update Supabase directly.")
        log.info(f"  Consensus sources: https://us.econoday.com/byweek.asp?cust=us")
        log.info(f"                     https://www.marketwatch.com/economy-politics/calendar")

    if market_data:
        log.info(f"\n  ── Market Snapshot ──")
        for m in market_data:
            log.info(f"    {m['name']:<30} {m['price']:>12,.2f}  ({m['change']:+.2f}%)")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info(f"{'='*60}")
    log.info(f"  Economic Calendar Scraper — Comprehensive Edition")
    log.info(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info(f"  Window: {TODAY} → {CUTOFF} ({(CUTOFF - TODAY).days} days)")
    log.info(f"{'='*60}")

    # ── Phase 1: Government sources (most reliable for dates) ──
    fred    = scrape_fred_releases()
    bls     = scrape_bls()
    bea     = scrape_bea()
    census  = scrape_census()
    fed     = scrape_federal_reserve()
    dol     = scrape_dol()
    treasury = scrape_treasury()

    # ── Phase 2: Industry sources ──
    ism     = scrape_ism()
    nar     = scrape_nar()
    confb   = scrape_conference_board()

    # ── Phase 3: Market calendars (best for consensus estimates) ──
    mw      = scrape_marketwatch()
    inv     = scrape_investing()
    ff      = scrape_forexfactory()
    te      = scrape_tradingeconomics()

    # ── Phase 4: International / macro context ──
    scrape_oecd()
    scrape_worldbank()
    scrape_imf()
    scrape_ecb()
    scrape_eurostat()

    # ── Phase 5: Market data snapshot ──
    market_data = scrape_yahoo_markets()

    # ── Merge all sources ──
    log.info("\n── Merging Sources ──────────────────────────────")
    merged = merge_results(
        fred, bls, bea, census, fed, dol, ism, nar, confb,
        mw, inv, ff, te
    )
    log.info(f"  Merged to {len(merged)} unique indicators")

    # ── Apply manual overrides ──
    log.info("\n── Manual Estimates ─────────────────────────────")
    if MANUAL_ESTIMATES:
        merged = apply_manual_estimates(merged)
    else:
        log.info("  None set — edit MANUAL_ESTIMATES dict to add them")

    # ── Print results ──
    print_summary(merged, market_data)

    # ── Push to database ──
    upsert_to_supabase(merged)
    upsert_market_data(market_data)

    log.info(f"\nDone. {len(merged)} indicators + {len(market_data)} market snapshots processed.")
