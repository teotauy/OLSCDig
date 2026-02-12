#!/usr/bin/env python3
"""
Simple web interface for Liverpool OLSC PassKit management.
Provides mobile-friendly buttons for bulk checkout and live headcount.

✅ WORKING VERSION with correct pub2 endpoints and NDJSON parsing.
"""

import os
import requests
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from dotenv import load_dotenv
import pytz
from team_abbreviations import format_match_display, abbreviate_team_name
from match_updates import get_next_match
# Notifications feature removed

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-secret-key-in-production')

# Configuration
config = {
    "PROGRAM_ID": os.getenv("PROGRAM_ID", "3yyTsbqwmtXaiKZ5qWhqTP"),
    "API_BASE": os.getenv("API_BASE", "https://api.pub2.passkit.io"),
    "API_KEY": os.getenv("PASSKIT_API_KEY"),
    "PROJECT_KEY": os.getenv("PASSKIT_PROJECT_KEY"),
    "TIMEZONE": os.getenv("TIMEZONE", "America/New_York"),
}

def get_passkit_headers():
    """Get headers for PassKit API requests."""
    return {
        "Authorization": f"Bearer {config['API_KEY']}",
        "Content-Type": "application/json",
        "X-Project-Key": config["PROJECT_KEY"]
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
    """Check if user is authenticated."""
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')  # Change this!
    if not session.get('authenticated'):
        return False
    return True

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
    """Login page for member addition."""
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')  # Change this!
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == admin_password:
            session['authenticated'] = True
            next_page = request.args.get('next', url_for('add_member_page'))
            return redirect(next_page)
        else:
            return render_template('login.html', error='Incorrect password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session."""
    session.pop('authenticated', None)
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

@app.route('/api/checkout', methods=['POST'])
def api_checkout():
    """API endpoint to checkout all CHECKED_IN members."""
    try:
        # Get all checked-in members
        members = get_checked_in_members()
        
        if not members:
            return jsonify({
                "status": "success",
                "message": "No members to checkout",
                "checked_out": 0
            })
        
        # Checkout each member using the checkOut endpoint
        checkout_url = f"{config['API_BASE']}/members/member/checkOut"
        
        success_count = 0
        failed = []
        
        for member in members:
            member_id = member.get("id")
            
            # Payload for checkout (use memberId, not id!)
            checkout_payload = {
                "memberId": member_id
            }
            
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
            "failed": failed
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
