-- ═══════════════════════════════════════════════════════════════════════════════
-- Economic Dashboard — Comprehensive Supabase Schema
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── 1. CONSENSUS ESTIMATES TABLE ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS consensus (
  series_id      TEXT NOT NULL,
  release_name   TEXT,
  release_date   DATE NOT NULL,
  estimate       NUMERIC,
  actual         NUMERIC,
  prior          NUMERIC,
  unit           TEXT DEFAULT '',
  source         TEXT DEFAULT '',
  impact         TEXT DEFAULT 'low',
  frequency      TEXT DEFAULT 'MoM',
  updated_at     TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (series_id, release_date)
);
ALTER TABLE consensus ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public can read consensus" ON consensus;
CREATE POLICY "public can read consensus" ON consensus FOR SELECT USING (true);
DROP POLICY IF EXISTS "authenticated can write consensus" ON consensus;
CREATE POLICY "authenticated can write consensus" ON consensus FOR ALL
  USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');

-- ─── 2. SCRAPE LOG TABLE ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scrape_log (
  id             BIGSERIAL PRIMARY KEY,
  series_id      TEXT NOT NULL,
  release_date   DATE,
  estimate       NUMERIC,
  actual         NUMERIC,
  source         TEXT DEFAULT '',
  scraped_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_scrape_log_series ON scrape_log (series_id);
CREATE INDEX IF NOT EXISTS idx_scrape_log_date   ON scrape_log (scraped_at);
ALTER TABLE scrape_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public can read scrape_log" ON scrape_log;
CREATE POLICY "public can read scrape_log" ON scrape_log FOR SELECT USING (true);
DROP POLICY IF EXISTS "authenticated can write scrape_log" ON scrape_log;
CREATE POLICY "authenticated can write scrape_log" ON scrape_log FOR ALL
  USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');

-- ─── 3. ECONOMIC EVENTS TABLE ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS economic_events (
  id             BIGSERIAL PRIMARY KEY,
  event_type     TEXT NOT NULL,
  event_name     TEXT NOT NULL,
  event_date     DATE NOT NULL,
  event_time     TIME,
  description    TEXT DEFAULT '',
  impact         TEXT DEFAULT 'medium',
  source         TEXT DEFAULT '',
  url            TEXT DEFAULT '',
  created_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_events_date ON economic_events (event_date);
CREATE INDEX IF NOT EXISTS idx_events_type ON economic_events (event_type);
ALTER TABLE economic_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public can read economic_events" ON economic_events;
CREATE POLICY "public can read economic_events" ON economic_events FOR SELECT USING (true);
DROP POLICY IF EXISTS "authenticated can write economic_events" ON economic_events;
CREATE POLICY "authenticated can write economic_events" ON economic_events FOR ALL
  USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');

-- ─── 4. TREASURY AUCTIONS TABLE ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS treasury_auctions (
  id               BIGSERIAL PRIMARY KEY,
  security_type    TEXT NOT NULL,
  auction_date     DATE NOT NULL,
  settlement_date  DATE,
  offering_amount  NUMERIC,
  high_yield       NUMERIC,
  bid_to_cover     NUMERIC,
  source           TEXT DEFAULT 'Treasury',
  updated_at       TIMESTAMPTZ DEFAULT now(),
  UNIQUE (security_type, auction_date)
);
CREATE INDEX IF NOT EXISTS idx_auctions_date ON treasury_auctions (auction_date);
ALTER TABLE treasury_auctions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public can read treasury_auctions" ON treasury_auctions;
CREATE POLICY "public can read treasury_auctions" ON treasury_auctions FOR SELECT USING (true);
DROP POLICY IF EXISTS "authenticated can write treasury_auctions" ON treasury_auctions;
CREATE POLICY "authenticated can write treasury_auctions" ON treasury_auctions FOR ALL
  USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');

-- ─── 5. MARKET SNAPSHOTS TABLE ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_snapshots (
  symbol         TEXT PRIMARY KEY,
  name           TEXT,
  price          NUMERIC,
  change_pct     NUMERIC,
  snapshot_at    TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE market_snapshots ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public can read market_snapshots" ON market_snapshots;
CREATE POLICY "public can read market_snapshots" ON market_snapshots FOR SELECT USING (true);
DROP POLICY IF EXISTS "authenticated can write market_snapshots" ON market_snapshots;
CREATE POLICY "authenticated can write market_snapshots" ON market_snapshots FOR ALL
  USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');

-- ─── 6. HISTORICAL ESTIMATES TABLE ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS estimate_history (
  id             BIGSERIAL PRIMARY KEY,
  series_id      TEXT NOT NULL,
  release_date   DATE NOT NULL,
  estimate       NUMERIC NOT NULL,
  source         TEXT DEFAULT '',
  observed_at    TIMESTAMPTZ DEFAULT now(),
  UNIQUE (series_id, release_date, source, observed_at)
);
CREATE INDEX IF NOT EXISTS idx_est_hist_series ON estimate_history (series_id, release_date);
ALTER TABLE estimate_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public can read estimate_history" ON estimate_history;
CREATE POLICY "public can read estimate_history" ON estimate_history FOR SELECT USING (true);
DROP POLICY IF EXISTS "authenticated can write estimate_history" ON estimate_history;
CREATE POLICY "authenticated can write estimate_history" ON estimate_history FOR ALL
  USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');

-- ─── 7. INTERNATIONAL MACRO TABLE ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS international_macro (
  id             BIGSERIAL PRIMARY KEY,
  country        TEXT NOT NULL,
  indicator      TEXT NOT NULL,
  indicator_name TEXT,
  value          NUMERIC,
  period         TEXT,
  unit           TEXT DEFAULT '%',
  source         TEXT DEFAULT '',
  updated_at     TIMESTAMPTZ DEFAULT now(),
  UNIQUE (country, indicator, period, source)
);
CREATE INDEX IF NOT EXISTS idx_intl_country ON international_macro (country);
CREATE INDEX IF NOT EXISTS idx_intl_indicator ON international_macro (indicator);
ALTER TABLE international_macro ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public can read international_macro" ON international_macro;
CREATE POLICY "public can read international_macro" ON international_macro FOR SELECT USING (true);
DROP POLICY IF EXISTS "authenticated can write international_macro" ON international_macro;
CREATE POLICY "authenticated can write international_macro" ON international_macro FOR ALL
  USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');

-- ─── 8. YIELD CURVE TABLE ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS yield_curve (
  curve_date     DATE PRIMARY KEY,
  m1             NUMERIC,
  m2             NUMERIC,
  m3             NUMERIC,
  m6             NUMERIC,
  y1             NUMERIC,
  y2             NUMERIC,
  y3             NUMERIC,
  y5             NUMERIC,
  y7             NUMERIC,
  y10            NUMERIC,
  y20            NUMERIC,
  y30            NUMERIC,
  spread_2s10s   NUMERIC GENERATED ALWAYS AS (y10 - y2) STORED,
  spread_3m10y   NUMERIC GENERATED ALWAYS AS (y10 - m3) STORED,
  updated_at     TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE yield_curve ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public can read yield_curve" ON yield_curve;
CREATE POLICY "public can read yield_curve" ON yield_curve FOR SELECT USING (true);
DROP POLICY IF EXISTS "authenticated can write yield_curve" ON yield_curve;
CREATE POLICY "authenticated can write yield_curve" ON yield_curve FOR ALL
  USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');

-- ─── 9. SERIES METADATA TABLE ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS series_metadata (
  series_id      TEXT PRIMARY KEY,
  release_name   TEXT NOT NULL,
  source_agency  TEXT NOT NULL,
  frequency      TEXT DEFAULT 'monthly',
  unit           TEXT DEFAULT '%',
  seasonal_adj   BOOLEAN DEFAULT true,
  description    TEXT DEFAULT '',
  fred_release_id INTEGER,
  impact         TEXT DEFAULT 'low',
  higher_is_good BOOLEAN DEFAULT true,
  created_at     TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE series_metadata ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public can read series_metadata" ON series_metadata;
CREATE POLICY "public can read series_metadata" ON series_metadata FOR SELECT USING (true);
DROP POLICY IF EXISTS "authenticated can write series_metadata" ON series_metadata;
CREATE POLICY "authenticated can write series_metadata" ON series_metadata FOR ALL
  USING (auth.role() = 'authenticated')
  WITH CHECK (auth.role() = 'authenticated');

-- ─── 10. SEED SERIES METADATA ──────────────────────────────────────────────
INSERT INTO series_metadata (series_id, release_name, source_agency, frequency, unit, fred_release_id, impact, higher_is_good) VALUES
  ('CPIAUCSL',       'Consumer Price Index (CPI)',           'BLS',              'monthly',   '%',  10,  'high',   false),
  ('CPILFESL',       'Core CPI (ex Food & Energy)',          'BLS',              'monthly',   '%',  10,  'high',   false),
  ('PPIACO',         'Producer Price Index (PPI)',           'BLS',              'monthly',   '%',  31,  'medium', false),
  ('PCEPI',          'PCE Price Index',                      'BEA',              'monthly',   '%',  55,  'medium', false),
  ('PCEPILFE',       'Core PCE Price Index',                 'BEA',              'monthly',   '%',  55,  'high',   false),
  ('IR',             'Import Price Index',                   'BLS',              'monthly',   '%',  11,  'low',    false),
  ('PAYEMS',         'Nonfarm Payrolls',                     'BLS',              'monthly',   'K',  46,  'high',   true),
  ('UNRATE',         'Unemployment Rate',                    'BLS',              'monthly',   '%',  46,  'high',   false),
  ('JTSJOL',         'JOLTS Job Openings',                   'BLS',              'monthly',   'K',  51,  'medium', true),
  ('ICSA',           'Initial Jobless Claims',               'Dept of Labor',    'weekly',    'K',  50,  'medium', false),
  ('CCSA',           'Continuing Jobless Claims',            'Dept of Labor',    'weekly',    'K',  117, 'low',    false),
  ('ECIWAG',         'Employment Cost Index',                'BLS',              'quarterly', '%',  113, 'medium', false),
  ('CES0500000003',  'Average Hourly Earnings',              'BLS',              'monthly',   '%',  32,  'medium', true),
  ('GDP',            'Gross Domestic Product',               'BEA',              'quarterly', '%',  53,  'high',   true),
  ('INDPRO',         'Industrial Production',                'Federal Reserve',  'monthly',   '%',  86,  'low',    true),
  ('TCU',            'Capacity Utilization',                 'Federal Reserve',  'monthly',   '%',  116, 'low',    true),
  ('DGORDER',        'Durable Goods Orders',                 'Census',           'monthly',   '%',  22,  'medium', true),
  ('AMTMNO',         'Factory Orders',                       'Census',           'monthly',   '%',  83,  'low',    true),
  ('RSAFS',          'Retail Sales',                         'Census',           'monthly',   '%',  15,  'high',   true),
  ('UMCSENT',        'Consumer Sentiment (Michigan)',        'Univ of Michigan', 'monthly',   '',   180, 'low',    true),
  ('CSCICP03USM665S','Consumer Confidence (Conf Board)',     'Conference Board', 'monthly',   '',   17,  'medium', true),
  ('HOUST',          'Housing Starts',                       'Census',           'monthly',   'K',  56,  'medium', true),
  ('PERMIT',         'Building Permits',                     'Census',           'monthly',   'K',  56,  'medium', true),
  ('HSN1F',          'New Home Sales',                       'Census',           'monthly',   'K',  54,  'low',    true),
  ('EXHOSLUSM495S',  'Existing Home Sales',                  'NAR',              'monthly',   'M',  19,  'low',    true),
  ('PHSI',           'Pending Home Sales Index',             'NAR',              'monthly',   '%',  200, 'low',    true),
  ('CSUSHPISA',      'S&P/Case-Shiller Home Price Index',   'S&P',              'monthly',   '%',  118, 'low',    true),
  ('TTLCONS',        'Construction Spending',                'Census',           'monthly',   '%',  175, 'low',    true),
  ('BOPGSTB',        'Trade Balance',                        'Census/BEA',       'monthly',   'B$', 69,  'medium', true),
  ('MANEMP',         'ISM Manufacturing PMI',                'ISM',              'monthly',   '',   160, 'medium', true),
  ('NMFCI',          'ISM Services PMI',                     'ISM',              'monthly',   '',   161, 'medium', true),
  ('USSLIND',        'Leading Economic Indicators',          'Conference Board', 'monthly',   '%',  82,  'low',    true),
  ('FEDFUNDS',       'Federal Funds Rate',                   'Federal Reserve',  'daily',     '%',  NULL,'high',   false),
  ('M2SL',           'M2 Money Supply',                      'Federal Reserve',  'monthly',   'B$', 21,  'low',    true),
  ('DGS10',          '10-Year Treasury Yield',               'Treasury',         'daily',     '%',  NULL,'medium', false)
ON CONFLICT (series_id) DO UPDATE SET
  release_name   = EXCLUDED.release_name,
  source_agency  = EXCLUDED.source_agency,
  frequency      = EXCLUDED.frequency,
  unit           = EXCLUDED.unit,
  fred_release_id = EXCLUDED.fred_release_id,
  impact         = EXCLUDED.impact,
  higher_is_good = EXCLUDED.higher_is_good;

-- ─── 11. SEED CONSENSUS TEST DATA ─────────────────────────────────────────
INSERT INTO consensus (series_id, release_name, release_date, estimate, unit, source, impact) VALUES
  ('CPIAUCSL',       'Consumer Price Index',       '2026-04-10', 2.9,   '%', 'BLS',           'high'),
  ('CPILFESL',       'Core CPI',                   '2026-04-10', 3.2,   '%', 'BLS',           'high'),
  ('PAYEMS',         'Nonfarm Payrolls',            '2026-04-03', 185,   'K', 'BLS',           'high'),
  ('UNRATE',         'Unemployment Rate',           '2026-04-03', 4.1,   '%', 'BLS',           'high'),
  ('GDP',            'GDP Advance Estimate',        '2026-04-29', 2.3,   '%', 'BEA',           'high'),
  ('PCEPI',          'PCE Price Index',             '2026-03-28', 2.6,   '%', 'BEA',           'medium'),
  ('PCEPILFE',       'Core PCE',                    '2026-03-28', 2.7,   '%', 'BEA',           'high'),
  ('PPIACO',         'Producer Price Index',        '2026-04-11', 3.1,   '%', 'BLS',           'medium'),
  ('RSAFS',          'Retail Sales',                '2026-04-15', 0.4,   '%', 'Census',        'high'),
  ('ICSA',           'Initial Jobless Claims',      '2026-03-27', 220,   'K', 'Dept of Labor', 'medium'),
  ('JTSJOL',         'JOLTS Job Openings',          '2026-04-01', 8800,  'K', 'BLS',           'medium'),
  ('HOUST',          'Housing Starts',              '2026-04-16', 1400,  'K', 'Census',        'medium'),
  ('PERMIT',         'Building Permits',            '2026-04-16', 1450,  'K', 'Census',        'medium'),
  ('HSN1F',          'New Home Sales',              '2026-04-23', 680,   'K', 'Census',        'low'),
  ('INDPRO',         'Industrial Production',       '2026-04-15', 0.3,   '%', 'Federal Reserve','low'),
  ('UMCSENT',        'Consumer Sentiment',          '2026-04-11', 67.5,  '',  'Univ of Michigan','low'),
  ('DGORDER',        'Durable Goods Orders',        '2026-04-24', 1.2,   '%', 'Census',        'medium'),
  ('MANEMP',         'ISM Manufacturing PMI',       '2026-04-01', 50.5,  '',  'ISM',           'medium'),
  ('NMFCI',          'ISM Services PMI',            '2026-04-03', 52.0,  '',  'ISM',           'medium'),
  ('BOPGSTB',        'Trade Balance',               '2026-04-03', -68.5, 'B$','Census/BEA',    'medium'),
  ('FEDFUNDS',       'Fed Funds Rate',              '2026-04-29', 4.50,  '%', 'Federal Reserve','high'),
  ('ECIWAG',         'Employment Cost Index',       '2026-04-30', 1.0,   '%', 'BLS',           'medium'),
  ('EXHOSLUSM495S',  'Existing Home Sales',         '2026-04-22', 4.10,  'M', 'NAR',           'low'),
  ('PHSI',           'Pending Home Sales Index',    '2026-04-28', 1.5,   '%', 'NAR',           'low')
ON CONFLICT (series_id) DO UPDATE SET
  estimate     = EXCLUDED.estimate,
  release_date = EXCLUDED.release_date,
  impact       = EXCLUDED.impact,
  updated_at   = now();

-- ─── 12. SEED FOMC EVENTS ─────────────────────────────────────────────────
INSERT INTO economic_events (event_type, event_name, event_date, event_time, impact, source) VALUES
  ('FOMC', 'FOMC Interest Rate Decision', '2026-01-28', '14:00', 'high', 'Federal Reserve'),
  ('FOMC', 'FOMC Interest Rate Decision', '2026-03-18', '14:00', 'high', 'Federal Reserve'),
  ('FOMC', 'FOMC Interest Rate Decision', '2026-04-29', '14:00', 'high', 'Federal Reserve'),
  ('FOMC', 'FOMC Interest Rate Decision', '2026-06-17', '14:00', 'high', 'Federal Reserve'),
  ('FOMC', 'FOMC Interest Rate Decision', '2026-07-29', '14:00', 'high', 'Federal Reserve'),
  ('FOMC', 'FOMC Interest Rate Decision', '2026-09-16', '14:00', 'high', 'Federal Reserve'),
  ('FOMC', 'FOMC Interest Rate Decision', '2026-10-28', '14:00', 'high', 'Federal Reserve'),
  ('FOMC', 'FOMC Interest Rate Decision', '2026-12-09', '14:00', 'high', 'Federal Reserve')
ON CONFLICT DO NOTHING;

-- ─── 13. HELPFUL VIEWS ─────────────────────────────────────────────────────
CREATE OR REPLACE VIEW upcoming_releases AS
SELECT
  c.series_id,
  c.release_name,
  c.release_date,
  c.estimate,
  c.actual,
  c.unit,
  c.source,
  c.impact,
  sm.frequency,
  sm.higher_is_good,
  c.release_date - CURRENT_DATE AS days_away
FROM consensus c
LEFT JOIN series_metadata sm ON c.series_id = sm.series_id
WHERE c.release_date >= CURRENT_DATE
ORDER BY c.release_date ASC;

CREATE OR REPLACE VIEW surprise_tracker AS
SELECT
  sl.series_id,
  sm.release_name,
  sl.release_date,
  sl.estimate,
  sl.actual,
  CASE
    WHEN sl.estimate IS NOT NULL AND sl.actual IS NOT NULL
    THEN sl.actual - sl.estimate
    ELSE NULL
  END AS surprise,
  CASE
    WHEN sl.estimate IS NOT NULL AND sl.actual IS NOT NULL AND sl.estimate != 0
    THEN ROUND(((sl.actual - sl.estimate) / ABS(sl.estimate)) * 100, 2)
    ELSE NULL
  END AS surprise_pct,
  sl.source,
  sl.scraped_at
FROM scrape_log sl
LEFT JOIN series_metadata sm ON sl.series_id = sm.series_id
WHERE sl.actual IS NOT NULL AND sl.estimate IS NOT NULL
ORDER BY sl.scraped_at DESC;

CREATE OR REPLACE VIEW full_calendar AS
SELECT
  release_date AS event_date,
  release_name AS event_name,
  'release' AS event_type,
  source,
  impact,
  estimate::TEXT AS detail
FROM consensus
WHERE release_date >= CURRENT_DATE
UNION ALL
SELECT
  event_date,
  event_name,
  event_type,
  source,
  impact,
  description AS detail
FROM economic_events
WHERE event_date >= CURRENT_DATE
UNION ALL
SELECT
  auction_date AS event_date,
  security_type || ' Auction' AS event_name,
  'auction' AS event_type,
  'Treasury' AS source,
  'low' AS impact,
  COALESCE('$' || offering_amount || 'B', '') AS detail
FROM treasury_auctions
WHERE auction_date >= CURRENT_DATE
ORDER BY event_date ASC;

CREATE OR REPLACE VIEW latest_yield_curve AS
SELECT
  curve_date,
  m1, m2, m3, m6, y1, y2, y3, y5, y7, y10, y20, y30,
  spread_2s10s,
  spread_3m10y,
  CASE WHEN spread_2s10s < 0 THEN true ELSE false END AS inverted_2s10s,
  CASE WHEN spread_3m10y < 0 THEN true ELSE false END AS inverted_3m10y
FROM yield_curve
ORDER BY curve_date DESC
LIMIT 30;

-- ─── 14. VERIFY ─────────────────────────────────────────────────────────────
SELECT 'consensus'          AS table_name, COUNT(*) AS rows FROM consensus
UNION ALL
SELECT 'series_metadata',   COUNT(*) FROM series_metadata
UNION ALL
SELECT 'economic_events',   COUNT(*) FROM economic_events
UNION ALL
SELECT 'scrape_log',        COUNT(*) FROM scrape_log
UNION ALL
SELECT 'treasury_auctions', COUNT(*) FROM treasury_auctions
UNION ALL
SELECT 'market_snapshots',  COUNT(*) FROM market_snapshots
UNION ALL
SELECT 'estimate_history',  COUNT(*) FROM estimate_history
UNION ALL
SELECT 'international_macro',COUNT(*) FROM international_macro
UNION ALL
SELECT 'yield_curve',       COUNT(*) FROM yield_curve;
