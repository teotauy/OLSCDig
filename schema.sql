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
    UNIQUE (member_id, season_id, platform),
    -- Below: support for Apple's PassKit web service (push updates to
    -- passes already installed in Wallet, e.g. when "next match" changes).
    -- auth_token is the pass.json `authenticationToken` Apple sends back on
    -- every web-service request — stored in plain text on purpose, it's a
    -- webhook credential between Apple's servers and ours, not the
    -- check-in QR value (that's still token_hash-only, unchanged).
    auth_token TEXT,
    -- token_encrypted is a reversibly-encrypted copy of the *same* raw
    -- barcode token behind token_hash, used only so a background content
    -- refresh (next match / theme) can rebuild an identical pass without
    -- silently rotating the member's QR code and breaking their emailed
    -- mobile-pass link. Encrypted (not plain) so a DB-only compromise still
    -- doesn't expose working QR values; the key lives in FLASK_SECRET_KEY.
    token_encrypted TEXT
);

-- Devices that have registered (via the PassKit web service) to receive
-- push notifications when a specific installed pass should refresh.
CREATE TABLE IF NOT EXISTS pass_devices (
    id SERIAL PRIMARY KEY,
    device_library_identifier TEXT NOT NULL,
    wallet_pass_id INTEGER NOT NULL REFERENCES wallet_passes(id) ON DELETE CASCADE,
    push_token TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (device_library_identifier, wallet_pass_id)
);

-- Single-row table tracking the last time shared pass content (next match,
-- home/away theme) changed, so the web service can tell devices whether
-- they need to re-fetch. Opaque string tag (we use a unix timestamp).
CREATE TABLE IF NOT EXISTS pass_update_state (
    id INTEGER PRIMARY KEY DEFAULT 1,
    last_updated_tag TEXT NOT NULL DEFAULT '0',
    CHECK (id = 1)
);
INSERT INTO pass_update_state (id, last_updated_tag)
    VALUES (1, '0') ON CONFLICT (id) DO NOTHING;

-- Migration: wallet_passes existed before auth_token/token_encrypted were
-- added, so CREATE TABLE IF NOT EXISTS above is a no-op against a
-- pre-existing production table. Add the columns explicitly.
ALTER TABLE wallet_passes ADD COLUMN IF NOT EXISTS auth_token TEXT;
ALTER TABLE wallet_passes ADD COLUMN IF NOT EXISTS token_encrypted TEXT;

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
