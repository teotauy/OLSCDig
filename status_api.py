#!/usr/bin/env python3
"""
Simple status API for the Liverpool OLSC control panel.
Provides real-time status of running processes and last run times.
"""

import os
import json
import subprocess
import psutil
import requests
from datetime import datetime
from flask import Flask, jsonify
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables
load_dotenv()

def get_process_status(script_name):
    """Check if a Python script is currently running."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and any(script_name in ' '.join(proc.info['cmdline']) for arg in proc.info['cmdline']):
                return {
                    'running': True,
                    'pid': proc.info['pid'],
                    'started': datetime.fromtimestamp(proc.create_time()).strftime('%Y-%m-%d %H:%M:%S')
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return {'running': False}

def get_last_run_time(script_name):
    """Get the last run time of a script from log files."""
    log_file = f"last_run_{script_name.replace('.py', '')}.log"
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                last_run = f.read().strip()
                return last_run
        except:
            pass
    
    return "Never run"

def get_checked_in_members():
    """Get current checked-in members count and list."""
    try:
        # Import the checkout script's functions
        import sys
        sys.path.append('.')
        from checkout import load_config, get_passkit_headers, parse_ndjson
        
        config = load_config()
        url = f"{config['API_BASE']}/members/member/list/{config['PROGRAM_ID']}"
        
        payload = {
            "filters": {
                "limit": 1000,
                "offset": 0,
                "orderBy": "created",
                "orderAsc": True,
                "filterGroups": [{
                    "condition": "AND",
                    "fieldFilters": [{
                        "filterField": "status",
                        "filterValue": "CHECKED_IN",
                        "filterOperator": "eq"
                    }]
                }]
            }
        }
        
        response = requests.post(url, headers=get_passkit_headers(config), json=payload, timeout=10)
        response.raise_for_status()
        members = parse_ndjson(response.text)
        
        member_list = []
        for member in members:
            person = member.get('person', {})
            name = person.get('displayName', 'Unknown')
            member_list.append(name)
        
        return {
            'count': len(members),
            'members': member_list
        }
        
    except Exception as e:
        return {
            'count': 0,
            'members': [],
            'error': str(e)
        }

@app.route('/api/status')
def get_status():
    """Get overall system status."""
    status = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'processes': {
            'notifications.py': get_process_status('notifications.py'),
            'app.py': get_process_status('app.py')
        },
        'last_runs': {
            'checkout.py': get_last_run_time('checkout.py'),
            'match_updates.py': get_last_run_time('match_updates.py'),
            'update_updating_members.py': get_last_run_time('update_updating_members.py'),
            'test_connection.py': get_last_run_time('test_connection.py')
        },
        'checked_in': get_checked_in_members()
    }
    
    return jsonify(status)

@app.route('/api/checked-in')
def get_checked_in():
    """Get current checked-in members."""
    return jsonify(get_checked_in_members())

if __name__ == '__main__':
    print("🚀 Starting Liverpool OLSC Status API...")
    print("📡 Status API: http://localhost:5002/api/status")
    print("👥 Checked-in API: http://localhost:5002/api/checked-in")
    app.run(host='0.0.0.0', port=5002, debug=False)
