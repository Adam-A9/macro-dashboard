-- ─── Run this in Supabase SQL Editor ───────────────────────────────────────
-- Dashboard → SQL Editor → New query → paste and run

-- 1. Create the consensus estimates table
CREATE TABLE IF NOT EXISTS consensus (
  series_id     TEXT PRIMARY KEY,       -- FRED series ID e.g. 'CPIAUCSL'
  release_name  TEXT,                   -- Human readable e.g. 'Consumer Price Index'
  release_date  DATE,                   -- Next scheduled release date
  estimate      NUMERIC,               -- Wall Street consensus estimate
  actual        NUMERIC,               -- Actual result (filled in after release)
  unit          TEXT DEFAULT '',        -- '%', 'K', 'M$' etc
  source        TEXT DEFAULT '',        -- 'BLS', 'BEA', 'WSJ'
  updated_at    TIMESTAMPTZ DEFAULT now()
);

-- 2. Enable Row Level Security
ALTER TABLE consensus ENABLE ROW LEVEL SECURITY;

-- 3. Allow anyone to read (dashboard fetches without auth)
CREATE POLICY "public can read consensus"
ON consensus FOR SELECT
USING (true);

-- 4. Only authenticated users can write (you, logged in via Supabase dashboard)
CREATE POLICY "authenticated can write consensus"
ON consensus FOR ALL
USING (auth.role() = 'authenticated')
WITH CHECK (auth.role() = 'authenticated');

-- 5. Verify it worked
SELECT * FROM consensus LIMIT 5;


-- ─── OPTIONAL: seed with some test data to verify connection ─────────────────
INSERT INTO consensus (series_id, release_name, release_date, estimate, unit, source)
VALUES
  ('CPIAUCSL',       'Consumer Price Index',    '2026-04-10', 2.9,  '%', 'WSJ'),
  ('PAYEMS',         'Nonfarm Payrolls',         '2026-04-03', 185,  'K', 'WSJ'),
  ('GDP',            'GDP Advance Estimate',     '2026-04-29', 2.3,  '%', 'BEA'),
  ('PCEPILFE',       'Core PCE',                '2026-03-28', 2.7,  '%', 'BEA'),
  ('UNRATE',         'Unemployment Rate',        '2026-04-03', 4.1,  '%', 'BLS')
ON CONFLICT (series_id) DO UPDATE SET
  estimate = EXCLUDED.estimate,
  release_date = EXCLUDED.release_date,
  updated_at = now();
