-- OLSC Brooklyn self-hosted membership / check-in schema.
-- Plain SQL, no migration framework. Safe to re-run (CREATE TABLE IF NOT EXISTS).
-- To change the schema later: add an ALTER TABLE block below and re-run db.py init.

CREATE TABLE IF NOT EXISTS seasons (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,               -- e.g. '2026/27'
    starts_on DATE,
    ends_on DATE,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Only one season may be current at a time.
CREATE UNIQUE INDEX IF NOT EXISTS one_current_season
    ON seasons (is_current)
    WHERE is_current;

CREATE TABLE IF NOT EXISTS members (
    id SERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    passkit_member_id TEXT,                  -- legacy external id, kept for migration reference only
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS member_seasons (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (member_id, season_id)
);

-- The QR payload token is never stored in plain text, only its hash.
-- serial_number is the pass.json serialNumber (safe to be semi-public, used for lookups/logs).
CREATE TABLE IF NOT EXISTS wallet_passes (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    serial_number TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL DEFAULT 'apple',  -- 'apple' | 'google' (later)
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (member_id, season_id, platform)
);

CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    opponent TEXT NOT NULL,
    is_home BOOLEAN NOT NULL DEFAULT TRUE,
    competition TEXT,
    kickoff_at TIMESTAMPTZ NOT NULL,
    venue TEXT,
    final_score TEXT,
    external_source_id TEXT,                 -- e.g. football-data.org fixture id
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Only one match may be "current" (the scanner's default target) at a time.
CREATE UNIQUE INDEX IF NOT EXISTS one_current_match
    ON matches (is_current)
    WHERE is_current;

CREATE TABLE IF NOT EXISTS checkins (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    checked_in_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    scanner_admin_id TEXT,
    source TEXT NOT NULL DEFAULT 'scanner',  -- 'scanner' | 'manual' | 'import'
    notes TEXT,
    UNIQUE (member_id, match_id)             -- one check-in per member per match
);
