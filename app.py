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
import smtplib
import time
import secrets
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from dotenv import load_dotenv
import pytz
import bcrypt
from team_abbreviations import format_match_display, abbreviate_team_name
from match_updates import get_next_match
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
LOGIN_RATE_LIMIT_WINDOW = 900   # 15 minutes
LOGIN_RATE_LIMIT_MAX = 5
_login_attempts = {}  # ip -> [timestamp, ...]

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
config = {
    "PROGRAM_ID": _env("PROGRAM_ID", "3yyTsbqwmtXaiKZ5qWhqTP"),
    "API_BASE": _env("API_BASE", "https://api.pub2.passkit.io"),
    "API_KEY": _env("PASSKIT_API_KEY"),
    "PROJECT_KEY": _env("PASSKIT_PROJECT_KEY"),
    "TIMEZONE": _env("TIMEZONE", "America/New_York"),
}

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
    return render_template('index.html')

@app.route('/add-member')
def add_member_page():
    """Page for adding new members (password protected)."""
    if not require_password():
        return redirect(url_for('login'))
    return render_template('add_member.html')

@app.route('/update-match')
def update_match_page():
    """Page for updating match info (password protected)."""
    if not require_password():
        return redirect(url_for('login'))
    return render_template('update_match.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for member addition. Rate-limited; supports password hash or plain env."""
    ip = request.remote_addr or 'unknown'
    if request.method == 'POST':
        if _is_login_rate_limited(ip):
            return render_template('login.html', error='Too many attempts. Try again in 15 minutes.')
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
        return render_template('forgot_password.html', recovery_enabled=True, error='Could not save new password (e.g. read-only filesystem). Use Render Environment to set ADMIN_PASSWORD.')
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

def _send_checkout_report_email(to_email, csv_content, filename):
    """Email the checkout CSV to to_email using SMTP from env. Returns True if sent."""
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    if not all([host, user, password]):
        return False
    port = int(os.getenv("SMTP_PORT", "587"))
    from_addr = os.getenv("EMAIL_FROM", user)
    msg = MIMEMultipart()
    msg["Subject"] = f"Checkout report: {filename}"
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

# Notification APIs removed

 

 

 

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
