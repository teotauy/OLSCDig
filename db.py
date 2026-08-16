#!/usr/bin/env python3
"""
Postgres connection + schema bootstrap for the self-hosted membership DB.

No migration framework: schema.sql is applied idempotently
(CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS). When the schema
needs to change, add to schema.sql and re-run `python3 db.py`.

Requires DATABASE_URL in the environment (see .env), e.g. a Supabase
connection string.
"""
import base64
import hashlib
import os
import secrets
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg2
import psycopg2.extras
from cryptography.fernet import Fernet
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


def _wallet_token_fernet():
    """Symmetric key for encrypting (not hashing) the barcode token copy
    kept for PassKit web-service refreshes. Derived from FLASK_SECRET_KEY
    so no separate secret needs to be provisioned/rotated on Render."""
    secret = os.getenv('FLASK_SECRET_KEY', 'change-this-secret-key-in-production').encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(secret + b'olsc-wallet-token-enc-v1').digest())
    return Fernet(key)


def decrypt_wallet_token(token_encrypted):
    """Recover the raw barcode token from its encrypted-at-rest copy, for
    rebuilding an identical pass on a PassKit web-service refresh."""
    return _wallet_token_fernet().decrypt(token_encrypted.encode()).decode()


def issue_wallet_token(member_id, season_id, platform='apple'):
    """Issue (or rotate) a wallet token for member+season+platform.

    Only the SHA-256 hash is used for check-in lookups — resending a pass
    (`admin_member_resend_pass`) always mints a fresh token and invalidates
    the old one (safe default if a pass was screenshotted/shared).

    A separate, reversibly-encrypted copy of the same raw token is also
    stored (`token_encrypted`), used only so the PassKit web service can
    rebuild an *identical* pass when pushing a content-only refresh (e.g.
    next match changed) — without that, every background refresh would
    silently mint a new QR code and break the member's emailed pass link.
    `auth_token` is a separate, unrelated credential Apple uses to
    authenticate web-service requests for this specific pass.

    Returns (raw_token, serial_number, auth_token).
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token_encrypted = _wallet_token_fernet().encrypt(raw_token.encode()).decode()
    serial_number = f"OLSC-{member_id}-{season_id}-{secrets.token_hex(4)}"
    auth_token = secrets.token_urlsafe(24)
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO wallet_passes
                (member_id, season_id, token_hash, token_encrypted, serial_number, platform, auth_token)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (member_id, season_id, platform) DO UPDATE SET
                token_hash = EXCLUDED.token_hash,
                token_encrypted = EXCLUDED.token_encrypted,
                serial_number = EXCLUDED.serial_number,
                auth_token = EXCLUDED.auth_token,
                revoked_at = NULL
            """,
            (member_id, season_id, token_hash, token_encrypted, serial_number, platform, auth_token),
        )
    return raw_token, serial_number, auth_token


def find_wallet_pass_by_serial(serial_number):
    """Look up an active wallet pass (plus member/season) by its
    pass.json serialNumber — used by the PassKit web service, which
    identifies passes by serial number rather than by barcode token."""
    with cursor() as cur:
        cur.execute(
            """
            SELECT wp.*, m.first_name, m.last_name, s.name AS season_name
            FROM wallet_passes wp
            JOIN members m ON m.id = wp.member_id
            JOIN seasons s ON s.id = wp.season_id
            WHERE wp.serial_number = %s AND wp.revoked_at IS NULL
            """,
            (serial_number,),
        )
        return cur.fetchone()


def register_pass_device(device_library_identifier, wallet_pass_id, push_token):
    """Record that a device wants push updates for a given pass. Returns
    True if this is a brand-new registration (caller should respond 201),
    False if it already existed (caller should respond 200)."""
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO pass_devices (device_library_identifier, wallet_pass_id, push_token)
            VALUES (%s, %s, %s)
            ON CONFLICT (device_library_identifier, wallet_pass_id)
                DO UPDATE SET push_token = EXCLUDED.push_token
            RETURNING (xmax = 0) AS inserted
            """,
            (device_library_identifier, wallet_pass_id, push_token),
        )
        row = cur.fetchone()
        return bool(row and row['inserted'])


def unregister_pass_device(device_library_identifier, wallet_pass_id):
    with cursor() as cur:
        cur.execute(
            "DELETE FROM pass_devices WHERE device_library_identifier = %s AND wallet_pass_id = %s",
            (device_library_identifier, wallet_pass_id),
        )


def registered_serials_for_device(device_library_identifier):
    with cursor() as cur:
        cur.execute(
            """
            SELECT wp.serial_number
            FROM pass_devices pd
            JOIN wallet_passes wp ON wp.id = pd.wallet_pass_id
            WHERE pd.device_library_identifier = %s AND wp.revoked_at IS NULL
            """,
            (device_library_identifier,),
        )
        return [r['serial_number'] for r in cur.fetchall()]


def all_pass_device_push_tokens():
    """Every push token across all registered devices for non-revoked
    passes — used to fan out an APNs push after shared pass content
    (next match, theme) changes."""
    with cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT pd.push_token
            FROM pass_devices pd
            JOIN wallet_passes wp ON wp.id = pd.wallet_pass_id
            WHERE wp.revoked_at IS NULL
            """
        )
        return [r['push_token'] for r in cur.fetchall()]


def get_passes_updated_tag():
    with cursor() as cur:
        cur.execute("SELECT last_updated_tag FROM pass_update_state WHERE id = 1")
        row = cur.fetchone()
        return row['last_updated_tag'] if row else '0'


def bump_passes_updated_tag():
    """Mark shared pass content (next match / theme) as changed. Devices
    polling passesUpdatedSince will see this and re-fetch."""
    new_tag = str(int(time.time()))
    with cursor() as cur:
        cur.execute("UPDATE pass_update_state SET last_updated_tag = %s WHERE id = 1", (new_tag,))
    return new_tag


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
                   s.id AS season_id, s.name AS season_name,
                   wp.serial_number
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
