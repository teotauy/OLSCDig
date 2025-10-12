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
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import pytz
from passkit_notifications import send_passkit_notification, scheduler, start_notification_scheduler

load_dotenv()

app = Flask(__name__)

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

@app.route('/')
def index():
    """Main page with headcount display and checkout button."""
    return render_template('index.html')

@app.route('/notifications')
def notifications():
    """Notifications management page."""
    return render_template('notifications.html')

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

@app.route('/api/send_notification', methods=['POST'])
def api_send_notification():
    """API endpoint to send PassKit push notification."""
    try:
        data = request.get_json()
        message = data.get('message', '')
        title = data.get('title', '⚽ Liverpool OLSC')
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        result = send_passkit_notification(message, title)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/schedule_notification', methods=['POST'])
def api_schedule_notification():
    """API endpoint to schedule PassKit push notification."""
    try:
        data = request.get_json()
        message = data.get('message', '')
        title = data.get('title', '⚽ Liverpool OLSC')
        scheduled_time_str = data.get('scheduled_time', '')
        description = data.get('description', '')
        
        if not message or not scheduled_time_str:
            return jsonify({
                'success': False,
                'error': 'Message and scheduled_time are required'
            }), 400
        
        # Parse scheduled time
        scheduled_time = datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))
        
        result = scheduler.schedule_notification(message, title, scheduled_time, description)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduled_notifications')
def api_scheduled_notifications():
    """API endpoint to get list of scheduled notifications."""
    try:
        scheduled = scheduler.get_scheduled_notifications()
        return jsonify({
            'success': True,
            'scheduled_notifications': scheduled
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cancel_notification/<job_id>', methods=['POST'])
def api_cancel_notification(job_id):
    """API endpoint to cancel a scheduled notification."""
    try:
        success = scheduler.cancel_scheduled_notification(job_id)
        return jsonify({
            'success': success,
            'message': 'Notification cancelled' if success else 'Notification not found'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Check if API credentials are set
    if not config['API_KEY'] or not config['PROJECT_KEY']:
        print("❌ Error: PASSKIT_API_KEY and PASSKIT_PROJECT_KEY must be set in .env file")
        exit(1)
    
    print("🏴󠁧󠁢󠁥󠁮󠁧󠁿  Liverpool OLSC - PassKit Manager")
    print(f"   Server starting at http://0.0.0.0:5000")
    print(f"   Access from your phone using your computer's IP address")
    print()
    
    # Start the notification scheduler
    start_notification_scheduler()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
