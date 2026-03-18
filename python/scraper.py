"""
Economic Calendar Scraper
Sources:
  - BLS  (bls.gov)      — release dates for CPI, PPI, NFP
  - BEA  (bea.gov)      — release dates for GDP, PCE
  - Econoday            — event names and dates (consensus is JS-rendered, not available)

NOTE: Consensus estimates are not freely available via scraping.
      Econoday loads consensus via JavaScript after page load, which requires
      a headless browser. This scraper gets release dates from BLS/BEA
      and you manually add consensus estimates to Supabase.

Setup:
  C:/Users/adama/AppData/Local/Programs/Python/Python39/python.exe -m pip install requests beautifulsoup4

Run:
  C:/Users/adama/AppData/Local/Programs/Python/Python39/python.exe scraper.py
"""

import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
import re

# ─── CONFIG ───────────────────────────────────────────────────
SUPABASE_URL = "https://ygcirhhnojzmprbomzxs.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")   # Settings → API → anon public key

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.5",
}

SERIES_MAP = {
    "consumer price index":    "CPIAUCSL",
    "employment situation":    "PAYEMS",
    "producer price index":    "PPIACO",
    "job openings":            "JTSJOL",
    "gdp":                     "GDP",
    "gross domestic product":  "GDP",
    "personal income":         "PCEPI",
    "personal income and outlays": "PCEPI",
    "gdp (":                   "GDP",
    "gdp (advance":            "GDP",
    "gdp (second":             "GDP",
    "gdp (third":              "GDP",
    "retail sales":            "RSAFS",
    "housing starts":          "HOUST",
    "initial jobless claims":  "ICSA",
    "unemployment":            "UNRATE",
    "housing starts":          "HOUST",
    "building permits":        "PERMIT",
    "existing home sales":     "EXHOSLUSM495S",
}

def match_series(name):
    n = name.lower().strip()
    for key, sid in SERIES_MAP.items():
        if key in n:
            return sid
    return None

def parse_bls_date(s, year=None):
    """Parse BLS abbreviated dates like 'Apr. 10, 2026' or 'Apr. 10'"""
    s = s.strip().replace('.', '')
    if not year:
        year = date.today().year
    for fmt in ('%b %d, %Y', '%b %d %Y', '%b %d'):
        try:
            d = datetime.strptime(s, fmt)
            if d.year == 1900:
                d = d.replace(year=year)
            return d.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def parse_bea_date(month_day, year=None):
    """Parse BEA dates like 'April 9' or 'March 25'"""
    if not year:
        year = date.today().year
    s = f"{month_day.strip()} {year}"
    for fmt in ('%B %d %Y', '%b %d %Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


# ─── BLS SCRAPER ──────────────────────────────────────────────
def scrape_bls():
    """
    BLS Table 2 structure:
      Reference Month | Release Date | Release Time
      e.g. "March 2026 | Apr. 10, 2026 | 08:30 AM"
    """
    print("\n── BLS ──────────────────────────────────────────")
    results = []
    today = date.today()
    cutoff = today + timedelta(days=60)

    pages = [
        ("https://www.bls.gov/schedule/news_release/cpi.htm",    "Consumer Price Index", "CPIAUCSL"),
        ("https://www.bls.gov/schedule/news_release/ppi.htm",    "Producer Price Index", "PPIACO"),
        ("https://www.bls.gov/schedule/news_release/empsit.htm", "Employment Situation", "PAYEMS"),
        ("https://www.bls.gov/schedule/news_release/jolts.htm",  "Job Openings (JOLTS)", "JTSJOL"),
    ]

    for url, release_name, series_id in pages:
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')

            # Table 2 is the schedule table — skip table 1 (navigation)
            tables = soup.find_all('table')
            if len(tables) < 2:
                print(f"  {series_id}: table not found")
                continue

            schedule_table = tables[1]
            rows = schedule_table.find_all('tr')

            for row in rows[1:]:  # skip header
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue

                # Cell 0: "March 2026", Cell 1: "Apr. 10, 2026", Cell 2: "08:30 AM"
                release_date_str = cells[1].get_text(strip=True)
                rd = parse_bls_date(release_date_str)
                if not rd:
                    continue

                try:
                    d = datetime.strptime(rd, '%Y-%m-%d').date()
                    if d < today or d > cutoff:
                        continue
                except ValueError:
                    continue

                results.append({
                    'series_id':    series_id,
                    'release_name': release_name,
                    'release_date': rd,
                    'estimate':     None,
                    'actual':       None,
                    'unit':         '',
                    'source':       'BLS',
                })
                print(f"  {series_id}: {release_name} → {rd}")
                break  # only next upcoming date

        except requests.RequestException as e:
            print(f"  {series_id} error: {e}")

    return results


# ─── BEA SCRAPER ──────────────────────────────────────────────
def scrape_bea():
    """
    BEA table structure (from debug output):
      "April 9 8:30 AM News GDP (Third Estimate)..."
      "April 9 8:30 AM News Personal Income and Outlays..."
    """
    print("\n── BEA ──────────────────────────────────────────")
    results = []
    today = date.today()
    cutoff = today + timedelta(days=60)
    year = today.year

    try:
        res = requests.get("https://www.bea.gov/news/schedule", headers=HEADERS, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        tables = soup.find_all('table')
        if not tables:
            print("  BEA: no table found")
            return results

        table = tables[0]
        text = table.get_text(' ', strip=True)

        # Pattern: "Month Day Time AM/PM News Release Name"
        # e.g. "April 9 8:30 AM N ews GDP..."
        # Split by finding month names and parsing forward
        month_names = ['January','February','March','April','May','June',
                       'July','August','September','October','November','December']

        # Find all occurrences of "Month Day" patterns
        pattern = re.compile(
            r'((?:' + '|'.join(month_names) + r')\s+\d{1,2})\s+'  # Month Day
            r'[\d:]+\s+[AP]M\s+'                                    # Time
            r'(?:N\s*ews\s+|D\s*ata\s+|V\s*isual\s+|A\s*rticle\s+)*'  # BEA label (split by spaces)
            r'([A-Z][^\d]{5,100}?)(?=\s+(?:' + '|'.join(month_names) + r')|\s*$)',  # Release name
            re.IGNORECASE
        )

        for m in pattern.finditer(text):
            month_day = m.group(1).strip()
            release_name = m.group(2).strip()

            rd = parse_bea_date(month_day, year)
            # If parsed date is in the past, try next year
            if rd:
                try:
                    if datetime.strptime(rd, '%Y-%m-%d').date() < date.today():
                        rd = parse_bea_date(month_day, year + 1)
                except ValueError:
                    pass
            if not rd:
                rd = parse_bea_date(month_day, year + 1)
            if not rd:
                continue

            try:
                d = datetime.strptime(rd, '%Y-%m-%d').date()
                if d < today or d > cutoff:
                    continue
            except ValueError:
                continue

            series_id = match_series(release_name)
            if not series_id:
                continue

            # Avoid duplicates
            if any(r['series_id'] == series_id for r in results):
                continue

            results.append({
                'series_id':    series_id,
                'release_name': release_name[:60].strip(),
                'release_date': rd,
                'estimate':     None,
                'actual':       None,
                'unit':         '',
                'source':       'BEA',
            })
            print(f"  {series_id}: {release_name[:50]} → {rd}")

    except requests.RequestException as e:
        print(f"  BEA error: {e}")

    if not results:
        print("  BEA: no matching releases found")
    return results


# ─── MERGE ────────────────────────────────────────────────────
def merge_results(*source_lists):
    merged = {}
    for source in source_lists:
        for item in source:
            sid = item['series_id']
            if sid not in merged:
                merged[sid] = item
            else:
                if item.get('estimate') is not None and merged[sid].get('estimate') is None:
                    merged[sid].update(item)
    return list(merged.values())


# ─── SUPABASE UPSERT ──────────────────────────────────────────
def upsert_to_supabase(records):
    print(f"\n── Supabase ──────────────────────────────────────")
    if not records:
        print("  No records to upsert")
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
            print(f"  ✓ Upserted {len(rows)} records")
            for r in rows:
                est = r['estimate'] if r['estimate'] is not None else '—'
                print(f"    {r['series_id']:<22} date={r['release_date']} est={est}")
        else:
            print(f"  ✗ Supabase error {res.status_code}: {res.text[:300]}")
    except requests.RequestException as e:
        print(f"  ✗ Request failed: {e}")


# ─── SUMMARY ──────────────────────────────────────────────────
def print_summary(records):
    print(f"\n── Summary ───────────────────────────────────────")
    if not records:
        print("  No records found")
        print("\n  NOTE: Consensus estimates (est column) will be blank.")
        print("  Econoday loads consensus via JavaScript — not accessible")
        print("  via simple scraping. To add estimates:")
        print("  1. Go to https://us.econoday.com/byweek.asp?cust=us")
        print("  2. Note the consensus for each upcoming release")
        print("  3. Update directly in Supabase Table Editor, or")
        print("     edit the MANUAL_ESTIMATES dict at the top of this script")
        return
    print(f"  {'Series':<22} {'Release Date':<14} {'Est':<10} Source")
    print(f"  {'-'*55}")
    for r in sorted(records, key=lambda x: x.get('release_date', '')):
        est = str(r['estimate']) if r.get('estimate') is not None else '—'
        print(f"  {r['series_id']:<22} {r.get('release_date',''):<14} {est:<10} {r.get('source','')}")
    print(f"\n  ⚠  Estimates are blank — add them manually in Supabase")
    print(f"     or paste from https://us.econoday.com/byweek.asp?cust=us")


# ─── MANUAL ESTIMATES ─────────────────────────────────────────
# Fill these in each week from Econoday or any other source.
# Format: 'FRED_SERIES_ID': estimate_as_float
# Leave blank ({}) if not updating this week.
MANUAL_ESTIMATES = {
    # 'CPIAUCSL': 2.9,
    # 'PAYEMS':   185,
    # 'GDP':      2.3,
    # 'PCEPI':    2.6,
    # 'PPIACO':   3.1,
}

def apply_manual_estimates(records):
    for r in records:
        if r['series_id'] in MANUAL_ESTIMATES:
            r['estimate'] = MANUAL_ESTIMATES[r['series_id']]
            print(f"  Manual estimate applied: {r['series_id']} = {r['estimate']}")
    return records


# ─── MAIN ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Economic Calendar Scraper")
    print(f"Running: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    bls = scrape_bls()
    bea = scrape_bea()

    merged = merge_results(bls, bea)

    print("\n── Manual Estimates ─────────────────────────────")
    if MANUAL_ESTIMATES:
        merged = apply_manual_estimates(merged)
    else:
        print("  None set — edit MANUAL_ESTIMATES dict to add them")

    print_summary(merged)

    if SUPABASE_URL != "https://YOUR_PROJECT.supabase.co":
        upsert_to_supabase(merged)
    else:
        print("\n  ⚠  Set SUPABASE_URL and SUPABASE_KEY to push to database")

    print(f"\nDone. {len(merged)} releases processed.")
