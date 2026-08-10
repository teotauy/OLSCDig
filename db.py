#!/usr/bin/env python3
"""
Postgres connection + schema bootstrap for the self-hosted membership DB.

No migration framework: schema.sql is applied idempotently
(CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS). When the schema
needs to change, add to schema.sql and re-run `python3 db.py`.

Requires DATABASE_URL in the environment (see .env), e.g. a Supabase
connection string.
"""
import hashlib
import os
import secrets
from contextlib import contextmanager
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set (see .env)")
    return psycopg2.connect(DATABASE_URL)


@contextmanager
def cursor():
    """Dict-row cursor. Commits on success, rolls back on exception."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema():
    """Apply schema.sql. Safe to run repeatedly."""
    sql = SCHEMA_PATH.read_text()
    with cursor() as cur:
        cur.execute(sql)


def ensure_default_season(name, starts_on=None, ends_on=None):
    """Return the current season, creating `name` as current if none exists yet."""
    with cursor() as cur:
        cur.execute("SELECT id, name FROM seasons WHERE is_current")
        existing = cur.fetchone()
        if existing:
            return existing
        cur.execute(
            """
            INSERT INTO seasons (name, starts_on, ends_on, is_current)
            VALUES (%s, %s, %s, TRUE)
            RETURNING id, name
            """,
            (name, starts_on, ends_on),
        )
        return cur.fetchone()


def get_current_season():
    with cursor() as cur:
        cur.execute("SELECT id, name FROM seasons WHERE is_current")
        return cur.fetchone()


def get_current_match():
    with cursor() as cur:
        cur.execute("SELECT * FROM matches WHERE is_current")
        return cur.fetchone()


def issue_wallet_token(member_id, season_id, platform='apple'):
    """Issue (or rotate) a wallet token for member+season+platform.

    Only the SHA-256 hash is ever stored in `wallet_passes` — the raw token
    is returned once, for immediately building/emailing a pass, and then
    forgotten. This means there's no way to recover a previously-issued
    token: resending a pass always mints a fresh one and invalidates the
    old one (safe default if a pass was screenshotted/shared).

    Returns (raw_token, serial_number).
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    serial_number = f"OLSC-{member_id}-{season_id}-{secrets.token_hex(4)}"
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO wallet_passes (member_id, season_id, token_hash, serial_number, platform)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (member_id, season_id, platform) DO UPDATE SET
                token_hash = EXCLUDED.token_hash,
                serial_number = EXCLUDED.serial_number,
                revoked_at = NULL
            """,
            (member_id, season_id, token_hash, serial_number, platform),
        )
    return raw_token, serial_number


def find_active_wallet_pass_by_token(raw_token):
    """Look up the member+season behind a raw wallet token.

    Hashes the token the same way issue_wallet_token stores it, so this
    never sees or logs a plaintext token beyond the single incoming request.
    Returns None for an unknown or revoked token — callers should show a
    generic "invalid or expired" message, not distinguish the two.
    """
    token_hash = hashlib.sha256((raw_token or "").encode()).hexdigest()
    with cursor() as cur:
        cur.execute(
            """
            SELECT m.id AS member_id, m.first_name, m.last_name,
                   s.id AS season_id, s.name AS season_name
            FROM wallet_passes wp
            JOIN members m ON m.id = wp.member_id
            JOIN seasons s ON s.id = wp.season_id
            WHERE wp.token_hash = %s AND wp.revoked_at IS NULL
            """,
            (token_hash,),
        )
        return cur.fetchone()


if __name__ == "__main__":
    init_schema()
    season = ensure_default_season("2026/27")
    print(f"Schema applied. Current season: {season['name']} (id={season['id']})")
