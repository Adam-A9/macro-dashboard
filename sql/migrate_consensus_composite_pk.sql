-- Migration: Change consensus primary key from series_id to (series_id, release_date)
-- This allows multiple release dates per indicator, so past actuals are preserved.
--
-- Run this once against your Supabase database.

-- 1. Drop the old primary key
ALTER TABLE consensus DROP CONSTRAINT consensus_pkey;

-- 2. Ensure release_date is NOT NULL (required for composite PK)
UPDATE consensus SET release_date = '1970-01-01' WHERE release_date IS NULL;
ALTER TABLE consensus ALTER COLUMN release_date SET NOT NULL;

-- 3. Add composite primary key
ALTER TABLE consensus ADD PRIMARY KEY (series_id, release_date);
