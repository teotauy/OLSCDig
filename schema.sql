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

-- google_object_id/google_class_id: the Generic Object/Class id a Google
-- Wallet save link was built with, persisted so a match-week update can
-- PATCH that exact object later (Google's equivalent of Apple's APNs
-- push-to-refetch) without recomputing it from a serial number that may
-- have since rotated on a resend.
ALTER TABLE wallet_passes ADD COLUMN IF NOT EXISTS google_object_id TEXT;
ALTER TABLE wallet_passes ADD COLUMN IF NOT EXISTS google_class_id TEXT;

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

-- Result ('win' | 'draw' | 'loss', from Liverpool's perspective), filled in
-- automatically once the match is finished, via football-data.org — used
-- to award check-in leaderboard points (3 / 1 / 0). NULL until known.
ALTER TABLE matches ADD COLUMN IF NOT EXISTS result TEXT;

-- Manual overrides for "next match" data (e.g. cup ties football-data.org
-- doesn't return, or a kickoff time it has wrong). Previously a JSON file
-- (match_overrides.json) that had to be edited and redeployed to change —
-- moved to the DB so admins can fix a wrong/missing match themselves,
-- without needing a code deploy, the same way everything else here works.
CREATE TABLE IF NOT EXISTS match_overrides (
    id SERIAL PRIMARY KEY,
    match_date DATE NOT NULL UNIQUE,   -- the date this override applies to
    opponent TEXT NOT NULL,
    display_date TEXT,                 -- e.g. "3/6", shown on the pass
    display_time TEXT,                 -- e.g. "3 PM", shown on the pass
    is_home BOOLEAN NOT NULL DEFAULT FALSE,
    venue TEXT,
    pass_display TEXT,                 -- full pre-formatted pass text; auto-generated if blank
    note TEXT,                         -- why this override exists, e.g. "FA Cup - not in API"
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Fingerprint of the last "next match" the auto-check saw, so a scheduled
-- job can tell when it changes (a cup tie announced, a fixture played,
-- etc.) and push pass updates automatically instead of waiting for an
-- admin to notice and click "Push Pass Updates Now".
ALTER TABLE pass_update_state ADD COLUMN IF NOT EXISTS last_next_match_key TEXT;

-- Last-known Resend quota/rate-limit state, captured from response headers
-- on every real send attempt (Resend has no separate "check my usage"
-- endpoint) -- powers a small admin-visible usage indicator and lets a
-- failed send be told apart from "you've hit today's/this month's limit"
-- rather than a generic, unhelpful failure message.
CREATE TABLE IF NOT EXISTS resend_usage_state (
    id INTEGER PRIMARY KEY DEFAULT 1,
    daily_quota_raw TEXT,
    monthly_quota_raw TEXT,
    ratelimit_remaining TEXT,
    reset_at TIMESTAMPTZ,
    last_status_code INTEGER,
    last_error_message TEXT,
    checked_at TIMESTAMPTZ,
    CHECK (id = 1)
);
INSERT INTO resend_usage_state (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- last_error_name: Resend's machine-readable error type (e.g.
-- "rate_limit_exceeded", "daily_quota_exceeded", "monthly_quota_exceeded")
-- from the failed response body. reset_at only ever reflects the
-- ratelimit-reset header -- the ~1-second burst-rate window, NOT the
-- daily/monthly quota (Resend documents no reset time for those at all) --
-- so this is needed to tell the two failure kinds apart correctly.
ALTER TABLE resend_usage_state ADD COLUMN IF NOT EXISTS last_error_name TEXT;

-- Idempotency log for the Squarespace-order-to-member webhook (via
-- Make.com's "Watch Orders" trigger, since Squarespace's Core plan has no
-- native webhooks). Recording order_id here lets a retried/duplicate
-- delivery no-op instead of re-emailing a welcome pass.
CREATE TABLE IF NOT EXISTS squarespace_orders_processed (
    order_id TEXT PRIMARY KEY,
    email TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Scoped, revocable access links for volunteer door staff -- grants only
-- /scanner and its check-in APIs, never the full admin session. Checked
-- fresh against the DB on every request (not just once at redemption),
-- so revoking one takes effect immediately even mid-shift.
CREATE TABLE IF NOT EXISTS door_passes (
    id SERIAL PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

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
