#!/usr/bin/env python3
"""
Pushover notifications for Liverpool OLSC headcount system.
Sends periodic headcount updates and responds to text commands.
"""

import os
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Pushover configuration (set in .env / Render)
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")

# PassKit configuration (same as main app)
PASSKIT_CONFIG = {
    "PROGRAM_ID": os.getenv("PROGRAM_ID", "3yyTsbqwmtXaiKZ5qWhqTP"),
    "API_BASE": os.getenv("API_BASE", "https://api.pub2.passkit.io"),
    "API_KEY": os.getenv("PASSKIT_API_KEY"),
    "PROJECT_KEY": os.getenv("PASSKIT_PROJECT_KEY"),
    "TIMEZONE": os.getenv("TIMEZONE", "America/New_York"),
}

def get_passkit_headers():
    """Get headers for PassKit API requests."""
    return {
        "Authorization": f"Bearer {PASSKIT_CONFIG['API_KEY']}",
        "Content-Type": "application/json",
        "X-Project-Key": PASSKIT_CONFIG["PROJECT_KEY"]
    }

def parse_ndjson(response_text):
    """Parse newline-delimited JSON response from PassKit API."""
    members = []
    for line in response_text.strip().split('\n'):
        if line:
            try:
                data = json.loads(line)
                if 'result' in data:
                    members.append(data['result'])
            except json.JSONDecodeError:
                pass
    return members

def get_checked_in_members():
    """Fetch all CHECKED_IN members from PassKit API."""
    url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/list/{PASSKIT_CONFIG['PROGRAM_ID']}"
    
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
    
    try:
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        response.raise_for_status()
        return parse_ndjson(response.text)
    except Exception as e:
        print(f"Error fetching members: {e}")
        return None

def send_pushover_notification(message, title="⚽ Liverpool OLSC", sound="default", priority=0):
    """Send a notification via Pushover."""
    if not PUSHOVER_API_TOKEN or not PUSHOVER_USER_KEY:
        print(f"Pushover notification: {title} - {message}")
        return False

    url = "https://api.pushover.net/1/messages.json"
    payload = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "title": title,
        "message": message,
        "sound": sound,
        "priority": priority
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending Pushover notification: {e}")
        return False

def send_headcount_update(include_timestamp=True):
    """Send current headcount update."""
    members = get_checked_in_members()
    
    if members is None:
        send_pushover_notification(
            "❌ Error checking headcount",
            "⚠️ System Alert",
            sound="siren",
            priority=1
        )
        return
    
    count = len(members)
    priority = 0  # Default priority
    now = datetime.now(pytz.timezone(PASSKIT_CONFIG["TIMEZONE"]))
    time_str = now.strftime("%I:%M %p")
    
    # Determine message and sound based on count
    if count == 0:
        message = "🏴󠁧󠁢󠁥󠁮󠁧󠁿 No one checked in"
        sound = "none"
    elif count < 10:
        message = f"⚽ {count} people at the pub"
        sound = "default"
    elif count < 20:
        message = f"🔥 {count} people - getting busy!"
        sound = "cosmic"
    else:
        message = f"🚨 {count} people - PACKED!"
        sound = "siren"
        priority = 1  # High priority for busy times
    
    # Add timestamp to message
    if include_timestamp:
        message += f" ({time_str})"
    
    send_pushover_notification(message, sound=sound, priority=priority)

def send_member_list():
    """Send list of checked-in members."""
    members = get_checked_in_members()
    
    if members is None:
        send_pushover_notification("❌ Error fetching member list")
        return
    
    if not members:
        send_pushover_notification("📋 No one is currently checked in")
        return
    
    # Create member list (max 10 to avoid message length limits)
    member_names = []
    for member in members[:10]:
        person = member.get('person', {})
        name = person.get('displayName', 'Unknown')
        member_names.append(f"• {name}")
    
    message = f"📋 {len(members)} people checked in:\n" + "\n".join(member_names)
    
    if len(members) > 10:
        message += f"\n... and {len(members) - 10} more"
    
    send_pushover_notification(message, "📋 Member List")

def send_help():
    """Send help message with available commands."""
    help_text = """📱 Available commands:
• count - Current headcount
• list - List checked-in members  
• status - Detailed status
• help - Show this message

Automatic updates every 1 minute."""
    
    send_pushover_notification(help_text, "📱 Commands")

def send_detailed_status():
    """Send detailed system status."""
    members = get_checked_in_members()
    
    if members is None:
        send_pushover_notification("❌ System error - cannot connect to PassKit")
        return
    
    count = len(members)
    now = datetime.now(pytz.timezone(PASSKIT_CONFIG["TIMEZONE"]))
    time_str = now.strftime("%I:%M %p")
    
    message = f"""📊 System Status
Time: {time_str}
Checked in: {count} people
System: ✅ Online
Last check: Just now"""
    
    send_pushover_notification(message, "📊 Status")

def main():
    """Main notification loop."""
    print("⚽ Liverpool OLSC - Pushover Notifications")
    if PUSHOVER_USER_KEY:
        print(f"User Key: {PUSHOVER_USER_KEY[:10]}...")
    if not PUSHOVER_USER_KEY or not PUSHOVER_API_TOKEN:
        print("⚠️  Set PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN in .env")
        print("   Create a Pushover app at: https://pushover.net/apps/build")
        print("   Add PUSHOVER_USER_KEY=your_user_key and PUSHOVER_API_TOKEN=your_token to .env")
        print()
        print("Running in test mode (notifications will print to console)")
    
    print("\n📱 Sending test notification...")
    send_pushover_notification(
        "🚀 Liverpool OLSC notifications are now active!",
        "⚽ System Online",
        sound="cosmic"
    )
    
    print("✅ Setup complete! You should receive a test notification.")
    print("\nAvailable commands (send via Pushover):")
    print("• count - Get current headcount")
    print("• list - List checked-in members")
    print("• status - Get detailed status")
    print("• help - Show help")
    
    print("\nAutomatic updates every 1 minute...")
    print("Press Ctrl+C to stop")
    
    last_count = None
    last_log_time = None
    check_interval = 60  # Check every 60 seconds (1 minute)
    log_interval = 600  # Log status every 10 minutes even if no change (console only, no notification)
    
    try:
        while True:
            members = get_checked_in_members()
            if members is not None:
                current_count = len(members)
                now = datetime.now()
                
                # Send update if count changed
                if last_count != current_count:
                    print(f"[{now.strftime('%H:%M:%S')}] Count changed: {last_count} → {current_count}")
                    send_headcount_update()
                    last_count = current_count
                    last_log_time = now
                # Just log that we checked (every 10 minutes to avoid spam) - console only, no notification
                elif last_log_time is None or (now - last_log_time).total_seconds() >= log_interval:
                    print(f"[{now.strftime('%H:%M:%S')}] Monitoring... {current_count} people checked in (no change)")
                    last_log_time = now
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Error fetching members - will retry")
            
            # Sleep for 1 minute
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\n👋 Stopping notifications...")
        send_pushover_notification("🔴 Liverpool OLSC notifications stopped", sound="none")

if __name__ == "__main__":
    main()
