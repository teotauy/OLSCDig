#!/usr/bin/env python3
"""
Simple web interface for Liverpool OLSC PassKit management.
Provides mobile-friendly buttons for bulk checkout and live headcount.

✅ WORKING VERSION with correct pub2 endpoints and NDJSON parsing.
"""

import os
import requests
import json
import csv
import io
import hashlib
import smtplib
import time
import secrets
import base64
import qrcode
from urllib.parse import urlparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_file, Response
from dotenv import load_dotenv
import pytz
import bcrypt
from team_abbreviations import format_match_display, abbreviate_team_name
from match_updates import get_next_match
from wallet_pass import AppleWalletConfigError, MemberPassData, build_member_pkpass, PASS_THEMES
from google_wallet import GoogleWalletConfigError, build_google_wallet_save_url, google_wallet_configured
import db
# Notifications feature removed

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-secret-key-in-production')
# Secure session cookies
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

# Auth: stored hash file (gitignored); fallback to env
HASH_FILE = os.path.join(os.path.dirname(__file__), '.admin_hash')
ADMIN_USERNAME = (os.getenv('ADMIN_USERNAME') or '').strip()
MEMBERSHIP_SHOP_URL = "https://olscbrooklyn.com/shop/p/lfc-brooklyn-2627-membership"
LOGIN_RATE_LIMIT_WINDOW = 900   # 15 minutes
LOGIN_RATE_LIMIT_MAX = 5
_login_attempts = {}  # ip -> [timestamp, ...]

RECOVERY_RATE_LIMIT_WINDOW = 900   # 15 minutes
RECOVERY_RATE_LIMIT_MAX = 5
_recovery_attempts = {}  # ip -> [timestamp, ...]

def _is_recovery_rate_limited(ip):
    now = time.time()
    if ip not in _recovery_attempts:
        return False
    _recovery_attempts[ip] = [t for t in _recovery_attempts[ip] if now - t < RECOVERY_RATE_LIMIT_WINDOW]
    return len(_recovery_attempts[ip]) >= RECOVERY_RATE_LIMIT_MAX

def _record_recovery_attempt(ip):
    now = time.time()
    _recovery_attempts.setdefault(ip, [])
    _recovery_attempts[ip].append(now)
    _recovery_attempts[ip] = [t for t in _recovery_attempts[ip] if now - t < RECOVERY_RATE_LIMIT_WINDOW]

def _get_stored_hash():
    """Read admin password hash from file or env. File takes precedence."""
    if os.path.isfile(HASH_FILE):
        try:
            with open(HASH_FILE, 'r') as f:
                return f.read().strip()
        except Exception:
            pass
    return os.getenv('ADMIN_PASSWORD_HASH')

def _verify_password(password):
    """Verify password against stored hash or plain ADMIN_PASSWORD."""
    if not password:
        return False
    stored_hash = _get_stored_hash()
    if stored_hash:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
        except Exception:
            return False
    plain = os.getenv('ADMIN_PASSWORD')
    if plain:
        return secrets.compare_digest(password, plain)
    return False

def _set_password_hash(bcrypt_hash_bytes):
    """Write hash to file (for recovery flow). Caller passes bytes from bcrypt.hashpw."""
    try:
        with open(HASH_FILE, 'w') as f:
            f.write(bcrypt_hash_bytes.decode('ascii'))
        return True
    except Exception:
        return False

def _is_login_rate_limited(ip):
    """True if this IP has exceeded login attempts in the window."""
    now = time.time()
    if ip not in _login_attempts:
        return False
    # Keep only attempts within the window
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < LOGIN_RATE_LIMIT_WINDOW]
    return len(_login_attempts[ip]) >= LOGIN_RATE_LIMIT_MAX

def _record_login_attempt(ip, success):
    if success:
        _login_attempts.pop(ip, None)
        return
    now = time.time()
    _login_attempts.setdefault(ip, [])
    _login_attempts[ip].append(now)
    # Prune old
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < LOGIN_RATE_LIMIT_WINDOW]

# Configuration (strip env values so trailing newlines from Render/dashboards don't break headers)
def _env(key, default=""):
    v = os.getenv(key, default)
    return v.strip() if isinstance(v, str) else (v.decode("utf-8").strip() if isinstance(v, bytes) else str(v))
def _headcount_refresh_seconds():
    """Headcount refresh interval in seconds (10–300). Set HEADCOUNT_REFRESH_SECONDS in env to override default 60."""
    try:
        s = _env("HEADCOUNT_REFRESH_SECONDS", "60")
        return max(10, min(300, int(s)))
    except ValueError:
        return 60


def _public_base_url():
    """Canonical public URL used in emails, wallet assets, and save links."""
    base_url = _env("PUBLIC_BASE_URL") or request.url_root.rstrip("/")
    if base_url.startswith("http://") and "onrender.com" in base_url:
        base_url = "https://" + base_url[len("http://"):]
    return base_url.rstrip("/")

config = {
    "PROGRAM_ID": _env("PROGRAM_ID", "3yyTsbqwmtXaiKZ5qWhqTP"),
    "API_BASE": _env("API_BASE", "https://api.pub2.passkit.io"),
    "API_KEY": _env("PASSKIT_API_KEY"),
    "PROJECT_KEY": _env("PASSKIT_PROJECT_KEY"),
    "TIMEZONE": _env("TIMEZONE", "America/New_York"),
}

@app.context_processor
def inject_headcount_refresh():
    """Make headcount refresh interval (seconds) available in all templates."""
    return {"headcount_refresh_seconds": _headcount_refresh_seconds()}

def _clean_header_value(v):
    """Ensure header value is a clean string (no newlines, no bytes)."""
    if v is None:
        return ""
    if isinstance(v, bytes):
        v = v.decode("utf-8", errors="replace")
    return str(v).strip()

def get_passkit_headers():
    """Get headers for PassKit API requests."""
    api_key = _clean_header_value(config.get("API_KEY"))
    project_key = _clean_header_value(config.get("PROJECT_KEY"))
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Project-Key": project_key,
    }

def parse_ndjson(response_text):
    """Parse newline-delimited JSON response from PassKit API."""
    members = []
    for line in response_text.strip().split('\n'):
        if line:
            try:
                data = json.loads(line)
                # Each line has a "result" key with the member data
                if 'result' in data:
                    members.append(data['result'])
            except json.JSONDecodeError:
                pass  # Skip invalid lines
    return members

def check_member_exists(email):
    """Check if a member already exists in PassKit by email."""
    try:
        url = f"{config['API_BASE']}/members/member/list/{config['PROGRAM_ID']}"
        
        payload = {
            "filters": {
                "limit": 500,
                "offset": 0,
                "orderBy": "created",
                "orderAsc": False
            }
        }
        
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        response.raise_for_status()
        
        email_lower = email.lower()
        for line in response.text.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    member = None
                    if 'result' in data:
                        member = data['result']
                    elif 'person' in data:
                        member = data
                    
                    if member:
                        member_email = member.get('person', {}).get('emailAddress', '')
                        if member_email.lower() == email_lower:
                            return member
                except json.JSONDecodeError:
                    pass
        
        return None
    except Exception as e:
        print(f"Error checking member existence: {e}")
        return None

def create_member(first_name, last_name, email, phone=""):
    """Create a new member in PassKit."""
    # Check if member already exists
    existing_member = check_member_exists(email)
    
    if existing_member:
        return {
            "success": True,
            "member_id": existing_member.get("id"),
            "already_exists": True,
            "message": "Member already exists"
        }
    
    # Create new member
    url = f"{config['API_BASE']}/members/member"
    
    external_id = f"manual_{email}_{int(datetime.now().timestamp())}"
    
    payload = {
        "programId": config["PROGRAM_ID"],
        "externalId": external_id,
        "tierId": "base",
        "person": {
            "forename": first_name,
            "surname": last_name,
            "displayName": f"{first_name} {last_name}".strip(),
            "emailAddress": email,
            "mobileNumber": phone
        },
        "metaData": {
            "nextMatch": "Some inferior side",
            "membershipType": "Standard",
            "joinDate": datetime.now().strftime("%Y-%m-%d"),
            "source": "Web Interface"
        },
        "sendWelcomeEmail": True
    }
    
    try:
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API Error {response.status_code}: {response.text}"
            }
        
        response.raise_for_status()
        result = response.json()
        member_id = result.get("id")
        
        pass_url = f"https://pub2.passkit.io/pass/{config['PROGRAM_ID']}/{member_id}"
        
        return {
            "success": True,
            "member_id": member_id,
            "pass_url": pass_url,
            "email": email,
            "name": f"{first_name} {last_name}"
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "email": email
        }

def get_checked_in_members():
    """Fetch all CHECKED_IN members from PassKit API."""
    url = f"{config['API_BASE']}/members/member/list/{config['PROGRAM_ID']}"
    
    # POST body with filter for CHECKED_IN status
    payload = {
        "filters": {
            "limit": 1000,  # Adjust if you have more members
            "offset": 0,
            "orderBy": "created",
            "orderAsc": True,
            "filterGroups": [{
                "condition": "AND",
                "fieldFilters": [{
                    "filterField": "status",  # Correct field name
                    "filterValue": "CHECKED_IN",
                    "filterOperator": "eq"
                }]
            }]
        }
    }
    
    response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
    response.raise_for_status()
    
    return parse_ndjson(response.text)

def require_password():
    """Check if user is authenticated (password or Google OAuth)."""
    return bool(session.get('authenticated'))

@app.route('/')
def index():
    """Public landing page with headcount display."""
    return render_template('landing.html')

@app.route('/admin')
def admin_index():
    """Admin page with headcount display and checkout button."""
    return render_template('index.html', wordmark_data_uri=_current_theme_wordmark_data_uri())

@app.route('/add-member')
def add_member_page():
    """Legacy PassKit add-member page. Redirect to the DB-backed member admin."""
    if not require_password():
        return redirect(url_for('login'))
    return redirect(url_for('admin_members'))

@app.route('/legacy/passkit/add-member')
def legacy_passkit_add_member_page():
    """Fallback-only PassKit add-member page for emergency PassKit season."""
    if not require_password():
        return redirect(url_for('login'))
    return render_template('add_member.html')

@app.route('/update-match')
def update_match_page():
    """Page for updating match info (password protected)."""
    if not require_password():
        return redirect(url_for('login'))
    return render_template('update_match.html')

@app.route('/resend-welcome')
def resend_welcome_page():
    """Page to resend welcome email with pass link (password protected)."""
    if not require_password():
        return redirect(url_for('login'))
    return render_template('resend_welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for member addition. Rate-limited; supports password hash or plain env."""
    ip = request.remote_addr or 'unknown'
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        if _is_login_rate_limited(ip):
            return render_template('login.html', error='Too many attempts. Try again in 15 minutes.')
        # If ADMIN_USERNAME is set, require it to match (case-insensitive)
        if ADMIN_USERNAME and username.lower() != ADMIN_USERNAME.lower():
            _record_login_attempt(ip, success=False)
            return render_template('login.html', error='Incorrect username or password')
        password = request.form.get('password', '')
        if _verify_password(password):
            _record_login_attempt(ip, success=True)
            session['authenticated'] = True
            next_page = request.args.get('next', url_for('add_member_page'))
            return redirect(next_page)
        _record_login_attempt(ip, success=False)
        return render_template('login.html', error='Incorrect password')
    error = request.args.get('error')
    return render_template('login.html', google_enabled=bool(os.getenv('GOOGLE_CLIENT_ID')), reset=request.args.get('reset'), error=error)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password: show instructions (Render) or recovery-code form (local)."""
    recovery_code = os.getenv('ADMIN_RECOVERY_CODE')
    if request.method == 'POST' and recovery_code:
        code = (request.form.get('recovery_code') or '').strip()
        new_password = request.form.get('new_password') or ''
        confirm = request.form.get('confirm_password') or ''
        if not secrets.compare_digest(code, recovery_code):
            return render_template('forgot_password.html', recovery_enabled=True, error='Invalid recovery code')
        if len(new_password) < 8:
            return render_template('forgot_password.html', recovery_enabled=True, error='Password must be at least 8 characters')
        if new_password != confirm:
            return render_template('forgot_password.html', recovery_enabled=True, error='Passwords do not match')
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        if _set_password_hash(hashed):
            return redirect(url_for('login', reset='1'))
        return render_template('forgot_password.html', recovery_enabled=True, error='Could not save new password (e.g. read-only filesystem). Set ADMIN_PASSWORD or ADMIN_PASSWORD_HASH in your host\'s Environment (Render, Vercel, etc.).')
    return render_template('forgot_password.html', recovery_enabled=bool(recovery_code))

@app.route('/login/google')
def login_google():
    """Redirect to Google OAuth. Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    if not client_id:
        return redirect(url_for('login'))
    redirect_uri = url_for('login_google_callback', _external=True)
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    url = (
        'https://accounts.google.com/o/oauth2/v2/auth'
        '?client_id={}&redirect_uri={}&response_type=code&scope=openid%20email&state={}'
    ).format(client_id, redirect_uri, state)
    return redirect(url)

@app.route('/login/callback')
def login_google_callback():
    """Handle Google OAuth callback; set session and redirect."""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    if not client_id or not client_secret:
        return redirect(url_for('login', error='Google login not configured'))
    state = request.args.get('state')
    if not state or state != session.get('oauth_state'):
        session.pop('oauth_state', None)
        return redirect(url_for('login', error='Invalid state'))
    session.pop('oauth_state', None)
    code = request.args.get('code')
    if not code:
        return redirect(url_for('login', error='Missing code'))
    redirect_uri = url_for('login_google_callback', _external=True)
    token_resp = requests.post(
        'https://oauth2.googleapis.com/token',
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=10,
    )
    if token_resp.status_code != 200:
        return redirect(url_for('login', error='Google sign-in failed'))
    token_data = token_resp.json()
    access_token = token_data.get('access_token')
    if not access_token:
        return redirect(url_for('login', error='Google sign-in failed'))
    user_resp = requests.get(
        'https://www.googleapis.com/oauth2/v2/userinfo',
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=10,
    )
    if user_resp.status_code != 200:
        session['authenticated'] = True
        return redirect(request.args.get('next', url_for('add_member_page')))
    user_data = user_resp.json()
    allowed = os.getenv('ALLOWED_GOOGLE_EMAILS', '').strip()
    if allowed:
        email = (user_data.get('email') or '').lower()
        if email not in [e.strip().lower() for e in allowed.split(',') if e.strip()]:
            return redirect(url_for('login', error='This Google account is not allowed'))
    session['authenticated'] = True
    next_page = request.args.get('next', url_for('add_member_page'))
    return redirect(next_page)

@app.route('/logout')
def logout():
    """Logout and clear session."""
    session.pop('authenticated', None)
    session.pop('oauth_state', None)
    return redirect(url_for('index'))

# Notifications page removed

@app.route('/api/headcount')
def api_headcount():
    """API endpoint to get current headcount."""
    try:
        members = get_checked_in_members()
        
        tz = pytz.timezone(config["TIMEZONE"])
        now = datetime.now(tz)
        
        return jsonify({
            "count": len(members),
            "updated_at": now.isoformat(),
            "status": "success"
        })
    
    except Exception as e:
        return jsonify({
            "count": 0,
            "error": str(e),
            "status": "error"
        }), 500

def _member_check_in_time(member):
    """Try to get check-in timestamp from PassKit member object if available."""
    for key in ('currentCheckInStartedAt', 'checkInTime', 'lastCheckInAt', 'checkedInAt'):
        val = member.get(key)
        if val:
            try:
                if isinstance(val, str) and 'T' in val:
                    dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                    tz = pytz.timezone(config.get('TIMEZONE', 'America/New_York'))
                    return dt.astimezone(tz).strftime('%Y-%m-%d %I:%M %p')
                return str(val)
            except Exception:
                return str(val)
    return ""

def _build_checkout_report(members, checked_out_at_str):
    """Build CSV of who was checked out (name, email, check-in time if any, checked_out_at)."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Name", "Email", "Checked in at", "Checked out at"])
    for m in members:
        person = m.get("person") or {}
        name = person.get("displayName") or (person.get("forename", "") + " " + person.get("surname", "")).strip() or "Unknown"
        email = person.get("emailAddress") or ""
        check_in = _member_check_in_time(m)
        w.writerow([name, email, check_in, checked_out_at_str])
    return out.getvalue()


def _email_from_address(smtp_user=None):
    return (
        os.getenv("RESEND_FROM_EMAIL")
        or os.getenv("EMAIL_FROM")
        or smtp_user
        or os.getenv("SMTP_USER")
        or "OLSC Brooklyn <DIGITALIDS@OLSCBROOKLYN.COM>"
    ).strip()


def _send_email_resend(to_email, subject, html=None, text=None, attachments=None):
    """Send an email through Resend's HTTP API. Returns True if accepted."""
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    from_addr = _email_from_address()
    if not api_key or not from_addr:
        return False

    payload = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
    }
    if html:
        payload["html"] = html
    if text:
        payload["text"] = text

    reply_to = (os.getenv("RESEND_REPLY_TO") or "OLSC_BK@olscbrooklyn.com").strip()
    if reply_to:
        payload["reply_to"] = reply_to

    if attachments:
        payload["attachments"] = attachments

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        return 200 <= response.status_code < 300
    except Exception:
        return False


def _send_welcome_email_smtp(to_email, first_name, pass_url):
    """Send 'resend welcome' email with pass link using SMTP from env. Returns True if sent."""
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    if not all([host, user, password]):
        return False
    port = int(os.getenv("SMTP_PORT", "587"))
    from_addr = os.getenv("EMAIL_FROM", user)
    subject = "OLSC Brooklyn – Your membership pass link"
    name = first_name or "Member"
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
body {{ font-family: Arial, sans-serif; color: #333; }}
.header {{ background: linear-gradient(135deg, #c8102e 0%, #00a65a 100%); color: white; padding: 20px; text-align: center; }}
.content {{ padding: 20px; }}
.button {{ background: #c8102e; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 15px 0; }}
.footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
</style></head>
<body>
<div class="header"><h1>⚽ OLSC Brooklyn</h1></div>
<div class="content">
<p>Hi {name},</p>
<p>Here’s your membership pass link again. Tap the button below to add your digital card to your phone’s wallet.</p>
<p><a href="{pass_url}" class="button">📱 Add to Wallet</a></p>
<p>If you have any questions, reply to this email or reach out at the bar.</p>
<p>You’ll Never Walk Alone!<br>— OLSC Brooklyn</p>
</div>
<div class="footer"><p>This email was sent to {to_email}.</p></div>
</body>
</html>"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
        return True
    except Exception:
        return False

def _send_signup_nudge_email(to_email):
    """Email someone who asked for a pass but isn't a current-season member.
    Points them at the real membership signup page. Returns True if sent."""
    wordmark_uri = _asset_data_uri(PASS_THEMES["home"]["wordmark_path"])
    signup_url = "https://olscbrooklyn.com/shop/p/lfc-brooklyn-2627-membership"
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; color: #333; margin: 0; padding: 0; background: #f4f4f4; }}
.wrapper {{ max-width: 480px; margin: 0 auto; background: white; }}
.header {{ background: #c8102e; padding: 28px 20px; text-align: center; }}
.header img {{ max-width: 220px; height: auto; display: block; margin: 0 auto; }}
.content {{ padding: 28px 24px; }}
.content p {{ line-height: 1.5; }}
.footer {{ background: #f8f9fa; padding: 16px; text-align: center; font-size: 12px; color: #888; }}
</style></head>
<body>
<div class="wrapper">
<div class="header"><img src="{wordmark_uri}" alt="OLSC Brooklyn — Official Supporters Club"></div>
<div class="content">
<p>Hi,</p>
<p>We looked for an active OLSC Brooklyn membership under this email and didn't find one.</p>
<p>Membership renews every season, so if you joined previously but not yet for 2026/27, this would be why. If that's the case, you can join here:</p>
<p style="text-align:center; margin: 24px 0;">
<a href="{signup_url}" style="display:inline-block; background:#c8102e; color:#ffffff; padding:14px 28px; text-decoration:none; border-radius:8px; font-weight:600; font-size:14px;">Join OLSC Brooklyn</a>
</p>
<p style="font-size:13px; color:#888;">If you believe this is a mistake and you already have a current membership, reply to this email and we'll sort it out.</p>
<p>You'll Never Walk Alone!<br>— OLSC Brooklyn</p>
</div>
<div class="footer">This email was sent to {to_email}.</div>
</div>
</body>
</html>"""
    if _send_email_resend(to_email, "Join OLSC Brooklyn for 2026/27", html=html):
        return True

    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    if not all([host, user, password]):
        return False
    port = int(os.getenv("SMTP_PORT", "587"))
    from_addr = os.getenv("EMAIL_FROM", user)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Join OLSC Brooklyn for 2026/27"
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
        return True
    except Exception:
        return False


def _send_pkpass_email(to_email, first_name, pkpass_bytes, mobile_pass_url=None, google_wallet_url=None):
    """Email a signed .pkpass attachment to a member. Returns True if sent.

    Rebuilt (Aug 16) around one goal: people skim emails and miss things,
    so this needs to work even if they only read the bold line. Two
    clearly separated, device-specific instructions instead of a paragraph
    plus multiple buttons/caveats to parse. Google Wallet's button is
    deliberately left out for now — it's real and configured, but only
    approved test accounts can actually use it while demo mode is active,
    and a third option that's broken for almost everyone works directly
    against "very very very clear." `google_wallet_url` is still accepted
    (harmless if passed) so call sites don't need to change when it's
    reintroduced later; it's just not rendered.
    """
    if os.getenv('EMAIL_SENDING_ENABLED', 'true').strip().lower() == 'false':
        print(f"EMAIL_SENDING_ENABLED=false — not sending pass email to {to_email} (pass was still generated).")
        return False

    name = first_name or "Member"
    wordmark_uri = _asset_data_uri(PASS_THEMES["home"]["wordmark_path"])
    android_step_html = (
        f'<div class="step">'
        f'<div class="step-label">🤖&nbsp; IF YOU HAVE AN ANDROID PHONE</div>'
        f'<p class="step-text">Do not open the attachment — it will not work. Tap this button instead:</p>'
        f'<a href="{mobile_pass_url}" class="step-button">Get My Pass</a>'
        f'</div>'
        if mobile_pass_url else ""
    )
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; color: #333; margin: 0; padding: 0; background: #f4f4f4; }}
.wrapper {{ max-width: 480px; margin: 0 auto; background: white; }}
.header {{ background: #c8102e; padding: 28px 20px; text-align: center; }}
.header img {{ max-width: 220px; height: auto; display: block; margin: 0 auto; }}
.content {{ padding: 28px 24px; }}
.content > p {{ line-height: 1.5; }}
.step {{ border: 2px solid #eee; border-radius: 12px; padding: 18px; margin: 18px 0; text-align: center; }}
.step-label {{ font-size: 13px; font-weight: 800; letter-spacing: 0.5px; color: #c8102e; margin-bottom: 8px; }}
.step-text {{ font-size: 15px; margin-bottom: 12px; }}
.step-text strong {{ color: #111; }}
.step-button {{ display: inline-block; background: #c8102e; color: #ffffff !important; padding: 14px 30px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 15px; }}
.fine-print {{ font-size: 12px; color: #999; text-align: center; margin-top: 20px; }}
.footer {{ background: #f8f9fa; padding: 16px; text-align: center; font-size: 12px; color: #888; }}
</style></head>
<body>
<div class="wrapper">
<div class="header"><img src="{wordmark_uri}" alt="OLSC Brooklyn — Official Supporters Club"></div>
<div class="content">
<p>Hi {name},</p>
<div class="step">
<div class="step-label">📱&nbsp; IF YOU HAVE AN IPHONE</div>
<p class="step-text">Open the attachment on this email, then tap <strong>Add to Apple Wallet</strong>.</p>
</div>
{android_step_html}
<p class="fine-print">Already had a pass? This one replaces it — the old one stops working next time it's scanned.</p>
<p>You'll Never Walk Alone!<br>— OLSC Brooklyn</p>
</div>
<div class="footer">This email was sent to {to_email}.</div>
</div>
</body>
</html>"""
    if _send_email_resend(
        to_email,
        "[ACTION NEEDED] - Your Digital ID",
        html=html,
        attachments=[{
            "filename": "olsc-membership.pkpass",
            "content": base64.b64encode(pkpass_bytes).decode("ascii"),
        }],
    ):
        return True

    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    if not all([host, user, password]):
        return False
    port = int(os.getenv("SMTP_PORT", "587"))
    from_addr = os.getenv("EMAIL_FROM", user)

    msg = MIMEMultipart("mixed")
    msg["Subject"] = "[ACTION NEEDED] - Your Digital ID"
    msg["From"] = from_addr
    msg["To"] = to_email
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html"))
    msg.attach(alt)
    part = MIMEBase("application", "vnd.apple.pkpass")
    part.set_payload(pkpass_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename="olsc-membership.pkpass")
    msg.attach(part)
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
        return True
    except Exception:
        return False

def _send_checkout_report_email(to_email, csv_content, filename):
    """Email the checkout CSV to to_email using SMTP from env. Returns True if sent."""
    subject = f"Checkout report: {filename}"
    if _send_email_resend(
        to_email,
        subject,
        text=f"Checkout report attached ({filename}).",
        attachments=[{
            "filename": filename,
            "content": base64.b64encode(csv_content.encode("utf-8")).decode("ascii"),
        }],
    ):
        return True

    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    if not all([host, user, password]):
        return False
    port = int(os.getenv("SMTP_PORT", "587"))
    from_addr = os.getenv("EMAIL_FROM", user)
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.attach(MIMEText(f"Checkout report attached ({filename}).", "plain"))
    part = MIMEBase("application", "octet-stream")
    part.set_payload(csv_content.encode("utf-8"))
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(part)
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [to_email], msg.as_string())
        return True
    except Exception:
        return False

@app.route('/api/checkout', methods=['POST'])
def api_checkout():
    """API endpoint to checkout all CHECKED_IN members. Generates a report of who was checked out."""
    try:
        # Get all checked-in members
        members = get_checked_in_members()
        
        if not members:
            return jsonify({
                "status": "success",
                "message": "No members to checkout",
                "checked_out": 0,
                "report_filename": None,
                "report_csv": None,
            })
        
        tz = pytz.timezone(config.get("TIMEZONE", "America/New_York"))
        checked_out_at = datetime.now(tz)
        checked_out_at_str = checked_out_at.strftime("%Y-%m-%d %I:%M %p")
        report_csv = _build_checkout_report(members, checked_out_at_str)
        report_filename = f"checkout_{checked_out_at.strftime('%Y-%m-%d_%H-%M-%S')}.csv"

        report_email_sent = False
        to_email = os.getenv("CHECKOUT_REPORT_EMAIL", "").strip()
        if to_email:
            report_email_sent = _send_checkout_report_email(to_email, report_csv, report_filename)

        # Optionally write to disk (e.g. for local runs)
        try:
            report_dir = os.path.join(os.path.dirname(__file__), "checkout_reports")
            os.makedirs(report_dir, exist_ok=True)
            path = os.path.join(report_dir, report_filename)
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(report_csv)
        except Exception:
            pass

        # Checkout each member using the checkOut endpoint
        checkout_url = f"{config['API_BASE']}/members/member/checkOut"
        success_count = 0
        failed = []

        for member in members:
            member_id = member.get("id")
            checkout_payload = {"memberId": member_id}
            try:
                checkout_response = requests.post(
                    checkout_url,
                    headers=get_passkit_headers(),
                    json=checkout_payload,
                    timeout=30
                )
                checkout_response.raise_for_status()
                success_count += 1
            except Exception as e:
                person = member.get('person', {})
                name = person.get('displayName', 'Unknown')
                failed.append({"name": name, "id": member_id, "error": str(e)})

        return jsonify({
            "status": "success",
            "checked_out": success_count,
            "total": len(members),
            "failed": failed,
            "report_filename": report_filename,
            "report_csv": report_csv,
            "report_email_sent": report_email_sent,
            "report_email_to": to_email if report_email_sent else None,
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

def _trigger_passkit_welcome_email(member):
    """Ask PassKit to resend the welcome email for this member (PUT with sendWelcomeEmail). Returns True if accepted."""
    member_id = member.get("id")
    person = member.get("person") or {}
    update_url = f"{config['API_BASE']}/members/member"
    payload = {
        "programId": config["PROGRAM_ID"],
        "id": member_id,
        "person": {
            "forename": person.get("forename", ""),
            "surname": person.get("surname", ""),
            "displayName": person.get("displayName", ""),
            "emailAddress": person.get("emailAddress", ""),
            "mobileNumber": person.get("mobileNumber", ""),
        },
        "sendWelcomeEmail": True,
    }
    if member.get("externalId"):
        payload["externalId"] = member["externalId"]
    try:
        r = requests.put(update_url, headers=get_passkit_headers(), json=payload, timeout=30)
        return r.status_code == 200
    except Exception:
        return False

@app.route('/api/resend-welcome-email', methods=['POST'])
def api_resend_welcome_email():
    """Resend welcome email: try PassKit's built-in resend first; fall back to our SMTP email if needed."""
    if not require_password():
        return jsonify({"status": "error", "error": "Authentication required"}), 401
    try:
        data = request.get_json() or {}
        email = (data.get("email") or "").strip()
        if not email:
            return jsonify({"status": "error", "error": "Email is required"}), 400
        member = check_member_exists(email)
        if not member:
            return jsonify({"status": "error", "error": "No member found with that email"}), 404
        member_id = member.get("id")
        person = member.get("person") or {}
        to_email = person.get("emailAddress") or email
        first_name = person.get("forename") or person.get("displayName") or "Member"
        if isinstance(first_name, str) and " " in first_name:
            first_name = first_name.split()[0]
        pass_url = f"https://pub2.passkit.io/pass/{config['PROGRAM_ID']}/{member_id}"

        # Prefer PassKit's own welcome email if the API supports it
        if _trigger_passkit_welcome_email(member):
            return jsonify({
                "status": "success",
                "message": f"PassKit welcome email triggered for {to_email}",
                "email": to_email,
                "via": "passkit",
            })

        # Fallback: send ourselves via SMTP
        if not all([os.getenv("SMTP_HOST"), os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")]):
            return jsonify({
                "status": "error",
                "error": "PassKit did not send the email and SMTP is not configured. Set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD to use the fallback welcome email."
            }), 503
        sent = _send_welcome_email_smtp(to_email, first_name, pass_url)
        if not sent:
            return jsonify({"status": "error", "error": "Failed to send email"}), 500
        return jsonify({
            "status": "success",
            "message": f"Welcome email sent to {to_email} (via SMTP)",
            "email": to_email,
            "via": "smtp",
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/add-member', methods=['POST'])
def api_add_member():
    """API endpoint to add a new member."""
    if not require_password():
        return jsonify({
            "status": "error",
            "error": "Authentication required"
        }), 401
    
    try:
        data = request.get_json()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        
        if not first_name or not last_name or not email:
            return jsonify({
                "status": "error",
                "error": "First name, last name, and email are required"
            }), 400
        
        result = create_member(first_name, last_name, email, phone)
        
        if result['success']:
            if result.get('already_exists'):
                return jsonify({
                    "status": "success",
                    "message": "Member already exists",
                    "member_id": result.get('member_id'),
                    "already_exists": True
                })
            else:
                return jsonify({
                    "status": "success",
                    "message": "Member created successfully",
                    "member_id": result.get('member_id'),
                    "pass_url": result.get('pass_url'),
                    "name": result.get('name'),
                    "email": result.get('email')
                })
        else:
            return jsonify({
                "status": "error",
                "error": result.get('error', 'Unknown error')
            }), 500
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/next-match')
def api_next_match():
    """API endpoint to get next match info. Uses same logic as match_updates.py (overrides + UK time)."""
    if not require_password():
        return jsonify({"status": "error", "error": "Authentication required"}), 401
    
    try:
        next_match = get_next_match()
        if next_match:
            return jsonify({"status": "success", "match": next_match})
        return jsonify({"status": "error", "error": "No upcoming matches found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/update-match', methods=['POST'])
def api_update_match():
    """API endpoint to update all passes with next match. Uses same logic as match_updates.py."""
    if not require_password():
        return jsonify({"status": "error", "error": "Authentication required"}), 401
    
    try:
        match_data = get_next_match()
        if not match_data:
            return jsonify({"status": "error", "error": "No upcoming matches found"}), 404

        # Get all passes
        url = f"{config['API_BASE']}/members/member/list/{config['PROGRAM_ID']}"
        payload = {
            "filters": {
                "limit": 1000,
                "offset": 0,
                "orderBy": "created",
                "orderAsc": True
            }
        }
        
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        response.raise_for_status()
        
        passes = parse_ndjson(response.text)
        update_url = f"{config['API_BASE']}/members/member"
        
        success_count = 0
        failed_count = 0
        
        for pass_data in passes:
            member_id = pass_data.get("id")
            if not member_id:
                failed_count += 1
                continue
            
            person_data = pass_data.get("person", {})
            update_payload = {
                "programId": config["PROGRAM_ID"],
                "id": member_id,
                "person": {
                    "displayName": person_data.get("displayName", "Unknown"),
                    "emailAddress": person_data.get("emailAddress", ""),
                    "surname": person_data.get("surname", ""),
                    "forename": person_data.get("forename", "")
                },
                "metaData": {
                    "nextMatch": match_data['pass_display']
                }
            }
            
            if pass_data.get("externalId"):
                update_payload["externalId"] = pass_data.get("externalId")
            
            try:
                update_response = requests.put(update_url, headers=get_passkit_headers(), json=update_payload, timeout=30)
                update_response.raise_for_status()
                success_count += 1
            except Exception as e:
                failed_count += 1
        
        return jsonify({
            "status": "success",
            "message": f"Updated {success_count} passes",
            "match": match_data,
            "success_count": success_count,
            "failed_count": failed_count
        })
    
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/match-override', methods=['POST'])
def api_match_override():
    """Create or update a manual match override entry used for 'next match'."""
    if not require_password():
        return jsonify({"status": "error", "error": "Authentication required"}), 401

    try:
        data = request.get_json() or {}
        opponent = (data.get("opponent") or "").strip()
        date_iso = (data.get("date") or "").strip()  # Expected format: YYYY-MM-DD
        time_str = (data.get("time") or "").strip()
        pass_display = (data.get("pass_display") or "").strip()
        note = (data.get("note") or "Created via web override").strip()

        if not opponent or not date_iso or not time_str:
            return jsonify({
                "status": "error",
                "error": "Opponent, date, and time are required"
            }), 400

        try:
            override_date = datetime.strptime(date_iso, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({
                "status": "error",
                "error": "Date must be in YYYY-MM-DD format"
            }), 400

        # Display date on the pass (e.g. 3/6)
        display_date = f"{override_date.month}/{override_date.day}"

        if not pass_display:
            # Use shared formatting helper so overrides match automatic fixtures
            pass_display = format_match_display(opponent, display_date, time_str)

        override_file = os.path.join(os.path.dirname(__file__), "match_overrides.json")
        overrides_data = {"overrides": {}, "enabled": True}
        if os.path.exists(override_file):
            try:
                with open(override_file, "r") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    overrides_data.update(loaded)
            except Exception:
                # If the file is unreadable, start fresh but don't crash
                pass

        overrides = overrides_data.get("overrides") or {}
        overrides[date_iso] = {
            "opponent": opponent,
            "time": time_str,
            "date": display_date,
            "pass_display": pass_display,
            "note": note,
        }
        overrides_data["overrides"] = overrides
        overrides_data["enabled"] = True

        persisted = True
        try:
            with open(override_file, "w") as f:
                json.dump(overrides_data, f, indent=2)
        except (OSError, PermissionError):
            persisted = False

        return jsonify({
            "status": "success",
            "message": "Override saved" if persisted else (
                "Override applied for this session only. On Vercel, file writes are not persisted—edit match_overrides.json in your repo and redeploy to save permanently."
            ),
            "persisted": persisted,
            "override": {
                "opponent": opponent,
                "date_key": date_iso,
                "display_date": display_date,
                "time": time_str,
                "pass_display": pass_display,
            },
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/wallet/test-pass')
def wallet_test_pass_alias():
    """Friendly URL that redirects to the .pkpass download route."""
    return redirect(url_for('wallet_test_pass_download', **request.args))

@app.route('/wallet/test-pass.pkpass')
def wallet_test_pass_download():
    """Admin-only Apple Wallet test pass download served from this Flask app."""
    if not require_password():
        return redirect(url_for('login'))

    try:
        display_name = (request.args.get("name") or "OLSC Test Member").strip()[:80]
        season = (request.args.get("season") or os.getenv("OLSC_SEASON") or "2026/27").strip()[:20]
        serial = f"TEST-{int(time.time())}"
        token = "spike-test-token"
        barcode_url = f"{request.url_root.rstrip('/')}/checkin/t/{token}"

        next_match_text = ""
        try:
            next_match = get_next_match()
            if next_match:
                next_match_text = next_match.get("pass_display") or ""
        except Exception:
            next_match_text = ""

        pkpass_bytes = build_member_pkpass(MemberPassData(
            display_name=display_name,
            season=season,
            serial_number=serial,
            barcode_message=barcode_url,
            next_match=next_match_text,
            description="OLSC Brooklyn Membership Test Pass",
        ))

        return send_file(
            io.BytesIO(pkpass_bytes),
            mimetype="application/vnd.apple.pkpass",
            as_attachment=True,
            download_name="olsc-test.pkpass",
            max_age=0,
        )
    except AppleWalletConfigError as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "hint": "Set APPLE_TEAM_ID, APPLE_PASS_TYPE_ID, APPLE_CERT_PASSWORD, plus either APPLE_PASS_CERT_PATH/APPLE_WWDR_CERT_PATH files or APPLE_PASS_CERT_P12_BASE64/APPLE_WWDR_PEM_BASE64 env vars.",
        }), 500
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# Notification APIs removed

# ---- Self-hosted DB-backed admin: members & matches (schema.sql / db.py) ----
# Separate from the PassKit-backed add-member/update-match routes above.
# Writes go to our own Postgres, not PassKit.

def _split_name(display_name):
    display_name = (display_name or "").strip()
    if not display_name:
        return "", ""
    parts = display_name.split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def _localize_kickoff(value):
    """value: 'YYYY-MM-DDTHH:MM' from a datetime-local input, in app TIMEZONE."""
    tz = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))
    naive = datetime.strptime(value, '%Y-%m-%dT%H:%M')
    return tz.localize(naive)


def _extract_scan_token(raw_value):
    """Accept a raw wallet token, a full /checkin/t/<token> URL (what's
    actually embedded in the QR), or a /pass/<token> URL (the mobile pass
    page / the link that's actually in the resend/recovery emails — this is
    the one realistic thing a person might have as copyable text, so it
    needs to work here too, not just the QR-only URL shape).
    """
    value = (raw_value or "").strip()
    if not value:
        return ""
    try:
        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 3 and parts[-3:-1] == ["checkin", "t"]:
                return parts[-1].strip()
            if len(parts) >= 2 and parts[-2] in ("t", "pass"):
                return parts[-1].strip()
    except Exception:
        pass
    if "/checkin/t/" in value:
        return value.rsplit("/checkin/t/", 1)[-1].split("?", 1)[0].split("#", 1)[0].strip()
    if "/pass/" in value:
        return value.rsplit("/pass/", 1)[-1].split("?", 1)[0].split("#", 1)[0].strip()
    return value


def _format_match_for_scan(match):
    if not match:
        return None
    kickoff = match.get('kickoff_at')
    if kickoff:
        try:
            tz = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))
            kickoff = kickoff.astimezone(tz).strftime('%a %b %-d, %-I:%M %p')
        except Exception:
            kickoff = str(kickoff)
    return {
        "id": match.get("id"),
        "opponent": match.get("opponent"),
        "is_home": bool(match.get("is_home")),
        "competition": match.get("competition") or "",
        "kickoff": kickoff or "",
        "label": f"{'vs' if match.get('is_home') else '@'} {match.get('opponent')}",
    }


def _upsert_member_in_season(cur, first_name, last_name, email, phone, season_id):
    cur.execute(
        """
        INSERT INTO members (first_name, last_name, email, phone)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (email) DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            phone = EXCLUDED.phone
        RETURNING id
        """,
        (first_name, last_name, email, phone),
    )
    member_id = cur.fetchone()['id']
    cur.execute(
        """
        INSERT INTO member_seasons (member_id, season_id)
        VALUES (%s, %s)
        ON CONFLICT (member_id, season_id) DO NOTHING
        """,
        (member_id, season_id),
    )
    return member_id


@app.route('/admin/members', methods=['GET', 'POST'])
def admin_members():
    if not require_password():
        return redirect(url_for('login'))

    season = db.get_current_season()
    error = None
    added = None

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()

        if not first_name or not last_name or not email:
            error = "First name, last name, and email are required."
        else:
            try:
                with db.cursor() as cur:
                    member_id = _upsert_member_in_season(cur, first_name, last_name, email, phone, season['id'])
                added = f"{first_name} {last_name}"

                new_member = {"id": member_id, "first_name": first_name, "last_name": last_name, "email": email}
                pass_ok, pass_message = _issue_and_email_pass(new_member, season)
                if pass_ok:
                    added += " — pass emailed."
                else:
                    added += f" (pass not sent: {pass_message})"
            except Exception as e:
                error = f"Could not add member: {e}"

    imported = request.args.get('imported')
    skipped = request.args.get('skipped')
    info = None
    if imported is not None:
        info = f"Imported {imported} member(s)." + (f" Skipped {skipped}." if skipped and skipped != '0' else "")

    resent = request.args.get('resent')
    resend_error = request.args.get('resend_error')
    if resent:
        info = f"Pass resent to {resent}."
    if resend_error:
        error = resend_error

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT m.id, m.first_name, m.last_name, m.email, m.phone, m.created_at,
                   (SELECT COUNT(*) FROM checkins c
                    JOIN matches mt ON mt.id = c.match_id
                    WHERE c.member_id = m.id AND mt.season_id = %s) AS checkins_this_season,
                   EXISTS (
                    SELECT 1 FROM wallet_passes wp
                    WHERE wp.member_id = m.id
                      AND wp.season_id = %s
                      AND wp.platform = 'apple'
                      AND wp.revoked_at IS NULL
                   ) AS has_active_pass
            FROM members m
            JOIN member_seasons ms ON ms.member_id = m.id
            WHERE ms.season_id = %s
            ORDER BY m.last_name, m.first_name
            """,
            (season['id'], season['id'], season['id']),
        )
        members = cur.fetchall()

    return render_template(
        'admin_members.html',
        season=season,
        members=members,
        error=error,
        added=added,
        info=info,
        wordmark_data_uri=_current_theme_wordmark_data_uri(),
    )


@app.route('/admin/members/<int:member_id>/edit', methods=['GET', 'POST'])
def admin_member_edit(member_id):
    if not require_password():
        return redirect(url_for('login'))

    error = None

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()

        if not first_name or not last_name or not email:
            error = "First name, last name, and email are required."
        else:
            try:
                with db.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE members
                        SET first_name = %s, last_name = %s, email = %s, phone = %s
                        WHERE id = %s
                        """,
                        (first_name, last_name, email, phone, member_id),
                    )
                return redirect(url_for('admin_members'))
            except Exception as e:
                error = f"Could not save changes: {e}"

    with db.cursor() as cur:
        cur.execute("SELECT * FROM members WHERE id = %s", (member_id,))
        member = cur.fetchone()

    if not member:
        return redirect(url_for('admin_members'))

    return render_template('admin_member_edit.html', member=member, error=error)


def _safe_pkpass_filename(member):
    name = f"{member['first_name']}-{member['last_name']}".strip("-").lower()
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in name).strip("-")
    return f"olsc-{safe or 'member'}.pkpass"


def _current_match_relevant_date():
    """Return current match kickoff as an Apple Wallet relevantDate string."""
    try:
        match = db.get_current_match()
        kickoff_at = match.get('kickoff_at') if match else None
        if not kickoff_at:
            return ""
        return kickoff_at.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return ""


@app.route('/wallet/assets/<filename>')
def wallet_asset(filename):
    """Public HTTPS assets for Google Wallet pass rendering."""
    allowed = {
        "olsc_wordmark_red.png": PASS_THEMES["away"]["wordmark_path"],
        "olsc_wordmark_white.png": PASS_THEMES["home"]["wordmark_path"],
        "olsc_crest_red.png": PASS_THEMES["home"]["crest_path"],
    }
    path = allowed.get(filename)
    if not path:
        return jsonify({"status": "error", "error": "asset not found"}), 404
    return send_file(path, mimetype="image/png", max_age=86400)


def _build_google_wallet_url(member, season, raw_token, serial_number, next_match_text, is_home):
    if not google_wallet_configured():
        return ""
    try:
        return build_google_wallet_save_url(
            member_id=member["id"],
            display_name=f"{member['first_name']} {member['last_name']}".strip(),
            season_name=season["name"],
            serial_number=serial_number,
            barcode_value=raw_token,
            next_match=next_match_text,
            base_url=_public_base_url(),
            is_home=is_home,
        )
    except GoogleWalletConfigError as e:
        print(f"Google Wallet not configured: {e}")
    except Exception as e:
        print(f"Google Wallet link generation failed: {e}")
    return ""


def _issue_member_pkpass(member, season):
    """Issue/rotate a wallet token and return signed pass bytes plus web URLs."""
    raw_token, serial_number = db.issue_wallet_token(member['id'], season['id'], platform='apple')

    next_match_text = ""
    is_home = True
    try:
        next_match = get_next_match()
        if next_match:
            next_match_text = next_match.get('pass_display') or ""
            is_home = bool(next_match.get('is_home', True))
    except Exception:
        next_match_text = ""

    pkpass_bytes = build_member_pkpass(MemberPassData(
        display_name=f"{member['first_name']} {member['last_name']}".strip(),
        season=season['name'],
        serial_number=serial_number,
        barcode_message=raw_token,
        next_match=next_match_text,
        description="OLSC Brooklyn Membership",
        is_home=is_home,
        relevant_date=_current_match_relevant_date(),
    ))
    mobile_pass_url = f"{_public_base_url()}{url_for('mobile_pass', token=raw_token)}"
    google_wallet_url = _build_google_wallet_url(member, season, raw_token, serial_number, next_match_text, is_home)
    return pkpass_bytes, mobile_pass_url, google_wallet_url


def _issue_and_email_pass(member, season):
    """Issue a wallet token, build a signed pass, and email it to a member."""
    try:
        pkpass_bytes, mobile_pass_url, google_wallet_url = _issue_member_pkpass(member, season)
    except AppleWalletConfigError as e:
        return False, f"Wallet not configured: {e}"
    except Exception as e:
        return False, f"Could not build pass: {e}"

    if _send_pkpass_email(member['email'], member['first_name'], pkpass_bytes, mobile_pass_url=mobile_pass_url, google_wallet_url=google_wallet_url):
        return True, None

    if os.getenv('EMAIL_SENDING_ENABLED', 'true').strip().lower() == 'false':
        return False, "Pass generated, but email sending is deliberately paused right now (EMAIL_SENDING_ENABLED=false) — not a bug."
    return False, "Pass generated but email failed to send (check SMTP/Resend env vars)."


@app.route('/admin/members/send-signup-link', methods=['POST'])
def admin_send_signup_link():
    """For when a lookup comes up empty: email the person a link to buy
    membership instead of just turning them away."""
    if not require_password():
        return redirect(url_for('login'))

    to_email = (request.form.get('email') or '').strip().lower()
    if not to_email:
        return redirect(url_for('admin_members', resend_error="Enter an email to send the signup link."))

    if _send_signup_nudge_email(to_email):
        return redirect(url_for('admin_members', signup_sent=to_email))
    return redirect(url_for('admin_members', resend_error="Could not send the signup link (check SMTP/Resend env vars)."))


@app.route('/admin/members/<int:member_id>/resend-pass', methods=['POST'])
def admin_member_resend_pass(member_id):
    if not require_password():
        return redirect(url_for('login'))

    season = db.get_current_season()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM members WHERE id = %s", (member_id,))
        member = cur.fetchone()

    if not member or not season:
        return redirect(url_for('admin_members'))

    ok, message = _issue_and_email_pass(member, season)
    if ok:
        return redirect(url_for('admin_members', resent=member['email']))
    return redirect(url_for('admin_members', resend_error=message))


@app.route('/admin/members/<int:member_id>/download-pass', methods=['POST'])
def admin_member_download_pass(member_id):
    if not require_password():
        return redirect(url_for('login'))

    season = db.get_current_season()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM members WHERE id = %s", (member_id,))
        member = cur.fetchone()

    if not member or not season:
        return redirect(url_for('admin_members'))

    try:
        pkpass_bytes, _mobile_pass_url, _google_wallet_url = _issue_member_pkpass(member, season)
    except AppleWalletConfigError as e:
        return redirect(url_for('admin_members', resend_error=f"Wallet not configured: {e}"))
    except Exception as e:
        return redirect(url_for('admin_members', resend_error=f"Could not build pass: {e}"))

    return send_file(
        io.BytesIO(pkpass_bytes),
        mimetype="application/vnd.apple.pkpass",
        as_attachment=True,
        download_name=_safe_pkpass_filename(member),
        max_age=0,
    )


@app.route('/admin/members/import', methods=['POST'])
def admin_members_import():
    if not require_password():
        return redirect(url_for('login'))

    season = db.get_current_season()
    file = request.files.get('file')
    if not file or not file.filename:
        return redirect(url_for('admin_members'))

    text = file.read().decode('utf-8-sig', errors='ignore')
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    skipped = 0

    with db.cursor() as cur:
        for row in reader:
            email = (row.get('email') or row.get('person.emailAddress') or '').strip().lower()
            if not email:
                skipped += 1
                continue

            if row.get('first_name') or row.get('last_name'):
                first_name = (row.get('first_name') or '').strip()
                last_name = (row.get('last_name') or '').strip()
            else:
                first_name, last_name = _split_name(row.get('person.displayName'))

            if not first_name and not last_name:
                skipped += 1
                continue

            phone = (row.get('phone') or row.get('person.mobileNumber') or '').strip()

            _upsert_member_in_season(cur, first_name, last_name, email, phone, season['id'])
            imported += 1

    return redirect(url_for('admin_members', imported=imported, skipped=skipped))


@app.route('/admin/matches', methods=['GET', 'POST'])
def admin_matches():
    if not require_password():
        return redirect(url_for('login'))

    season = db.get_current_season()
    error = None

    if request.method == 'POST':
        opponent = request.form.get('opponent', '').strip()
        is_home = request.form.get('is_home') == 'home'
        competition = request.form.get('competition', '').strip()
        kickoff_raw = request.form.get('kickoff_at', '').strip()
        venue = request.form.get('venue', '').strip()

        if not opponent or not kickoff_raw:
            error = "Opponent and kickoff time are required."
        else:
            try:
                kickoff_at = _localize_kickoff(kickoff_raw)
                with db.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO matches (season_id, opponent, is_home, competition, kickoff_at, venue)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (season['id'], opponent, is_home, competition, kickoff_at, venue),
                    )
            except Exception as e:
                error = f"Could not add match: {e}"

    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM matches WHERE season_id = %s ORDER BY kickoff_at",
            (season['id'],),
        )
        matches = cur.fetchall()

    tz = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))
    for m in matches:
        if m['kickoff_at']:
            m['kickoff_at'] = m['kickoff_at'].astimezone(tz)

    return render_template(
        'admin_matches.html',
        season=season,
        matches=matches,
        error=error,
        wordmark_data_uri=_current_theme_wordmark_data_uri(),
    )


@app.route('/admin/matches/<int:match_id>/export-checkins.csv')
def admin_export_match_checkins(match_id):
    """CSV of everyone checked in to a specific match."""
    if not require_password():
        return redirect(url_for('login'))

    with db.cursor() as cur:
        cur.execute("SELECT * FROM matches WHERE id = %s", (match_id,))
        match = cur.fetchone()
        if not match:
            return jsonify({"status": "error", "error": "Match not found"}), 404

        cur.execute(
            """
            SELECT m.first_name, m.last_name, m.email, m.phone,
                   c.checked_in_at, c.source
            FROM checkins c
            JOIN members m ON m.id = c.member_id
            WHERE c.match_id = %s
            ORDER BY c.checked_in_at
            """,
            (match_id,),
        )
        rows = cur.fetchall()

    tz = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["first_name", "last_name", "email", "phone", "checked_in_at", "source"])
    for r in rows:
        checked_in_local = r['checked_in_at'].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S %Z') if r['checked_in_at'] else ""
        writer.writerow([r['first_name'], r['last_name'], r['email'], r['phone'] or '', checked_in_local, r['source']])

    filename = f"checkins_{match['opponent'].replace(' ', '_')}_{match_id}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route('/admin/members/export.csv')
def admin_export_members():
    """CSV of the current season's roster, with each member's check-in count."""
    if not require_password():
        return redirect(url_for('login'))

    season = db.get_current_season()
    if not season:
        return jsonify({"status": "error", "error": "No current season set"}), 400

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT m.first_name, m.last_name, m.email, m.phone, m.created_at,
                   (SELECT COUNT(*) FROM checkins c
                    JOIN matches mt ON mt.id = c.match_id
                    WHERE c.member_id = m.id AND mt.season_id = %s) AS checkins_this_season
            FROM members m
            JOIN member_seasons ms ON ms.member_id = m.id
            WHERE ms.season_id = %s
            ORDER BY m.last_name, m.first_name
            """,
            (season['id'], season['id']),
        )
        rows = cur.fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["first_name", "last_name", "email", "phone", "checkins_this_season", "member_since"])
    for r in rows:
        writer.writerow([
            r['first_name'], r['last_name'], r['email'], r['phone'] or '',
            r['checkins_this_season'], r['created_at'].strftime('%Y-%m-%d') if r['created_at'] else '',
        ])

    filename = f"members_{season['name'].replace('/', '-')}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route('/admin/matches/<int:match_id>/set-current', methods=['POST'])
def admin_match_set_current(match_id):
    if not require_password():
        return redirect(url_for('login'))

    with db.cursor() as cur:
        cur.execute("UPDATE matches SET is_current = FALSE WHERE is_current")
        cur.execute("UPDATE matches SET is_current = TRUE WHERE id = %s", (match_id,))

    return redirect(url_for('admin_matches'))


def _qr_data_uri(payload):
    """Build a base64 PNG data URI for a QR code encoding `payload`."""
    img = qrcode.make(payload, error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _asset_data_uri(path):
    """Base64 PNG data URI for a file, for inlining wallet_pass_assets/
    images directly into a template with no separate static route."""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _current_theme():
    """(is_home, wordmark_data_uri) for whatever page is rendering right
    now, using the same is_home source (get_next_match) as the pass and
    mobile web page, so nothing can disagree about which kit's showing."""
    is_home = True
    try:
        next_match = get_next_match()
        if next_match:
            is_home = bool(next_match.get("is_home", True))
    except Exception:
        pass
    theme = PASS_THEMES["home"] if is_home else PASS_THEMES["away"]
    return is_home, _asset_data_uri(theme["wordmark_path"])


def _current_theme_wordmark_data_uri():
    """Convenience wrapper for callers that only need the image."""
    return _current_theme()[1]


@app.route('/recover-pass', methods=['GET', 'POST'])
def recover_pass():
    """Public self-service pass recovery.

    Deliberately reveals found-vs-not-found (see plan doc "Decision
    Aug 13-14 under Self-Service Pass Recovery") instead of a generic
    "if that email is active..." message. Membership is single-season, so
    "not found" usually just means "you haven't joined this season yet" —
    a real conversion moment, not just an error state.
    """
    message = None
    message_type = None  # 'success' | 'not_found' | 'error'

    if request.method == 'POST':
        ip = request.remote_addr or 'unknown'
        email = (request.form.get('email') or '').strip().lower()

        if not email:
            message = "Enter your email address."
            message_type = "error"
        elif _is_recovery_rate_limited(ip):
            message = "Too many attempts. Please try again in a bit."
            message_type = "error"
        else:
            _record_recovery_attempt(ip)
            season = db.get_current_season()
            member = None
            if season:
                with db.cursor() as cur:
                    cur.execute(
                        """
                        SELECT m.* FROM members m
                        JOIN member_seasons ms ON ms.member_id = m.id
                        WHERE ms.season_id = %s AND m.email = %s
                        """,
                        (season['id'], email),
                    )
                    member = cur.fetchone()

            if member and season:
                ok, error_detail = _issue_and_email_pass(member, season)
                if ok:
                    message_type = "success"
                    message = "Found it! A fresh pass is on its way to your email."
                else:
                    message_type = "error"
                    message = "We found your membership but couldn't send the email just now. Try again shortly, or reach out to the club."
            else:
                message_type = "not_found"

    return render_template(
        'recover_pass.html',
        message=message,
        message_type=message_type,
        shop_url=MEMBERSHIP_SHOP_URL,
    )


@app.route('/pass/<token>')
def mobile_pass(token):
    """Public mobile web pass page — the Android/non-Wallet path.

    Shows the same QR the Apple Wallet pass carries, so a member can show
    this page at the door from any phone browser. No admin auth: knowing
    the token *is* the access control, same as a password-reset link.
    """
    record = db.find_active_wallet_pass_by_token(token)
    if not record:
        return render_template('mobile_pass.html', found=False), 404

    barcode_url = f"{_public_base_url()}/checkin/t/{token}"

    next_match_text = ""
    is_home = True
    try:
        next_match = get_next_match()
        if next_match:
            next_match_text = next_match.get("pass_display") or ""
            is_home = bool(next_match.get("is_home", True))
    except Exception:
        next_match_text = ""

    theme = PASS_THEMES["home"] if is_home else PASS_THEMES["away"]
    google_wallet_url = _build_google_wallet_url(
        {
            "id": record["member_id"],
            "first_name": record["first_name"],
            "last_name": record["last_name"],
        },
        {
            "id": record["season_id"],
            "name": record["season_name"],
        },
        token,
        record.get("serial_number") or f"OLSC-{record['member_id']}-{record['season_id']}",
        next_match_text,
        is_home,
    )

    return render_template(
        'mobile_pass.html',
        found=True,
        display_name=f"{record['first_name']} {record['last_name']}".strip(),
        season_name=record['season_name'],
        next_match=next_match_text,
        qr_data_uri=_qr_data_uri(barcode_url),
        is_home=is_home,
        wordmark_data_uri=_asset_data_uri(theme["wordmark_path"]),
        google_wallet_url=google_wallet_url,
    )


@app.route('/scanner')
def scanner():
    if not require_password():
        return redirect(url_for('login'))

    season = db.get_current_season()
    match = db.get_current_match()
    is_home, wordmark_data_uri = _current_theme()

    return render_template(
        'scanner.html',
        season=season,
        match=_format_match_for_scan(match),
        is_home=is_home,
        wordmark_data_uri=wordmark_data_uri,
        shop_qr_data_uri=_qr_data_uri(MEMBERSHIP_SHOP_URL),
        shop_url=MEMBERSHIP_SHOP_URL,
    )


@app.route('/api/checkins/scan', methods=['POST'])
def api_checkins_scan():
    if not require_password():
        return jsonify({"status": "error", "code": "unauthorized", "message": "Login required."}), 401

    payload = request.get_json(silent=True) or {}
    token = _extract_scan_token(payload.get('token') or payload.get('barcode') or payload.get('value'))
    if not token:
        return jsonify({
            "status": "error",
            "code": "missing_token",
            "message": "No wallet token found in the scan.",
        }), 400

    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()

    try:
        with db.cursor() as cur:
            cur.execute("SELECT id, name FROM seasons WHERE is_current")
            season = cur.fetchone()
            if not season:
                return jsonify({
                    "status": "error",
                    "code": "no_current_season",
                    "message": "No current season is configured.",
                }), 400

            cur.execute("SELECT * FROM matches WHERE is_current")
            match = cur.fetchone()
            if not match:
                return jsonify({
                    "status": "error",
                    "code": "no_current_match",
                    "message": "No current match is configured. Set one in Matches before scanning.",
                }), 400

            cur.execute(
                """
                SELECT wp.id AS wallet_pass_id, wp.member_id, wp.season_id, wp.revoked_at,
                       m.first_name, m.last_name, m.email
                FROM wallet_passes wp
                JOIN members m ON m.id = wp.member_id
                WHERE wp.token_hash = %s
                """,
                (token_hash,),
            )
            wallet_pass = cur.fetchone()

            if not wallet_pass or wallet_pass['revoked_at'] or wallet_pass['season_id'] != season['id']:
                return jsonify({
                    "status": "error",
                    "code": "invalid_or_expired",
                    "message": "Invalid, expired, or revoked pass.",
                    "match": _format_match_for_scan(match),
                }), 404

            scanner_admin_id = session.get('username') or ADMIN_USERNAME or "admin"
            cur.execute(
                """
                INSERT INTO checkins (member_id, match_id, scanner_admin_id, source)
                VALUES (%s, %s, %s, 'scanner')
                ON CONFLICT (member_id, match_id) DO NOTHING
                RETURNING id, checked_in_at
                """,
                (wallet_pass['member_id'], match['id'], scanner_admin_id),
            )
            inserted = cur.fetchone()

            if inserted:
                result = "checked_in"
                checked_in_at = inserted['checked_in_at']
                message = "Checked in."
            else:
                cur.execute(
                    """
                    SELECT id, checked_in_at
                    FROM checkins
                    WHERE member_id = %s AND match_id = %s
                    """,
                    (wallet_pass['member_id'], match['id']),
                )
                existing = cur.fetchone()
                result = "already_checked_in"
                checked_in_at = existing['checked_in_at'] if existing else None
                message = "Already used for this match."

        checked_in_display = ""
        if checked_in_at:
            try:
                tz = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))
                checked_in_display = checked_in_at.astimezone(tz).strftime('%-I:%M:%S %p')
            except Exception:
                checked_in_display = str(checked_in_at)

        return jsonify({
            "status": "success",
            "result": result,
            "message": message,
            "checked_in_at": checked_in_display,
            "member": {
                "id": wallet_pass['member_id'],
                "name": f"{wallet_pass['first_name']} {wallet_pass['last_name']}".strip(),
                "email": wallet_pass['email'],
            },
            "match": _format_match_for_scan(match),
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "code": "server_error",
            "message": f"Scanner failed: {e}",
        }), 500


def _format_checkin_time(checked_in_at):
    if not checked_in_at:
        return ""
    try:
        tz = pytz.timezone(os.getenv('TIMEZONE', 'America/New_York'))
        return checked_in_at.astimezone(tz).strftime('%-I:%M:%S %p')
    except Exception:
        return str(checked_in_at)


@app.route('/api/checkins/manual', methods=['POST'])
def api_checkins_manual():
    """Check in a member found via the roster-search fallback, bypassing
    the wallet token entirely — the admin has already identified who this
    is by name, so there's no QR/token to look up. Same idempotency and
    response shape as /api/checkins/scan, but source='manual' so the two
    paths stay distinguishable in exports later."""
    if not require_password():
        return jsonify({"status": "error", "code": "unauthorized", "message": "Login required."}), 401

    payload = request.get_json(silent=True) or {}
    try:
        member_id = int(payload.get('member_id'))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "code": "missing_member_id", "message": "No member selected."}), 400

    try:
        with db.cursor() as cur:
            cur.execute("SELECT id, name FROM seasons WHERE is_current")
            season = cur.fetchone()
            if not season:
                return jsonify({"status": "error", "code": "no_current_season", "message": "No current season is configured."}), 400

            cur.execute("SELECT * FROM matches WHERE is_current")
            match = cur.fetchone()
            if not match:
                return jsonify({"status": "error", "code": "no_current_match", "message": "No current match is configured. Set one in Matches before scanning."}), 400

            cur.execute(
                """
                SELECT m.id, m.first_name, m.last_name, m.email
                FROM members m
                JOIN member_seasons ms ON ms.member_id = m.id
                WHERE m.id = %s AND ms.season_id = %s
                """,
                (member_id, season['id']),
            )
            member = cur.fetchone()
            if not member:
                return jsonify({
                    "status": "error",
                    "code": "not_in_current_season",
                    "message": "That member isn't in the current season.",
                    "match": _format_match_for_scan(match),
                }), 404

            scanner_admin_id = session.get('username') or ADMIN_USERNAME or "admin"
            cur.execute(
                """
                INSERT INTO checkins (member_id, match_id, scanner_admin_id, source)
                VALUES (%s, %s, %s, 'manual')
                ON CONFLICT (member_id, match_id) DO NOTHING
                RETURNING id, checked_in_at
                """,
                (member['id'], match['id'], scanner_admin_id),
            )
            inserted = cur.fetchone()

            if inserted:
                result = "checked_in"
                checked_in_at = inserted['checked_in_at']
                message = "Checked in."
            else:
                cur.execute(
                    "SELECT id, checked_in_at FROM checkins WHERE member_id = %s AND match_id = %s",
                    (member['id'], match['id']),
                )
                existing = cur.fetchone()
                result = "already_checked_in"
                checked_in_at = existing['checked_in_at'] if existing else None
                message = "Already used for this match."

        return jsonify({
            "status": "success",
            "result": result,
            "message": message,
            "checked_in_at": _format_checkin_time(checked_in_at),
            "member": {
                "id": member['id'],
                "name": f"{member['first_name']} {member['last_name']}".strip(),
                "email": member['email'],
            },
            "match": _format_match_for_scan(match),
        })
    except Exception as e:
        return jsonify({"status": "error", "code": "server_error", "message": f"Manual check-in failed: {e}"}), 500


@app.route('/api/members/roster.json')
def api_members_roster():
    """Name + ID only for the current season, for the scanner's client-side
    search fallback. Deliberately excludes email/phone — if this ends up on
    a lost/borrowed phone, it should only ever leak names, not contact info.
    """
    if not require_password():
        return jsonify({"status": "error", "code": "unauthorized", "message": "Login required."}), 401

    season = db.get_current_season()
    if not season:
        return jsonify([])

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT m.id, m.first_name, m.last_name
            FROM members m
            JOIN member_seasons ms ON ms.member_id = m.id
            WHERE ms.season_id = %s
            ORDER BY m.last_name, m.first_name
            """,
            (season['id'],),
        )
        rows = cur.fetchall()

    return jsonify([{"id": r['id'], "name": f"{r['first_name']} {r['last_name']}".strip()} for r in rows])


if __name__ == '__main__':
    # Check if API credentials are set
    if not config['API_KEY'] or not config['PROJECT_KEY']:
        print("⚠️  Warning: PASSKIT_API_KEY and PASSKIT_PROJECT_KEY not set")
        print("   Some features may not work until environment variables are configured")
        print("   Set these in Render dashboard → Environment tab")
    
    port = int(os.getenv('PORT', 5000))
    
    print("🏴󠁧󠁢󠁥󠁮󠁧󠁿  Liverpool OLSC - PassKit Manager")
    print(f"   Server starting at http://0.0.0.0:{port}")
    print(f"   Access from your phone using your computer's IP address")
    print()
    
    app.run(host='0.0.0.0', port=port, debug=False)
