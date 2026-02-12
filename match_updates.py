#!/usr/bin/env python3
"""
Liverpool FC Match Updates for PassKit passes.
Automatically updates pass fields with upcoming match information.
"""

import os
import json
import sys
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz
from team_abbreviations import format_match_display

# Load environment variables
load_dotenv()

# PassKit configuration
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

def get_liverpool_fixtures():
    """
    Get Liverpool FC fixtures from football-data.org API (all competitions).
    Returns upcoming matches sorted by date; display time is in configured TIMEZONE.
    """
    # Free tier API key (you can get your own at football-data.org)
    API_KEY = "7e9f8206e9db47fa8a4b15b783a7543b"
    
    headers = {
        "X-Auth-Token": API_KEY
    }
    
    team_id = 64  # Liverpool FC
    
    try:
        # All scheduled matches (no competition filter) - get enough to include FA Cup, PL, etc.
        url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
        params = {
            "status": "SCHEDULED",
            "limit": 25
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        # Sort by kickoff so the chronologically next match is first (e.g. FA Cup before later PL)
        fixtures = sorted(data.get("matches", []), key=lambda m: m["utcDate"])
        
        # Debug: Print raw UTC times
        print(f"📡 Fetched {len(fixtures)} fixtures from football-data.org")
        for match in fixtures[:1]:  # Print first match for debugging
            print(f"   Raw UTC time: {match.get('utcDate')}")
        
        # Process fixtures
        upcoming_matches = []
        for match in fixtures:
            home_team = match["homeTeam"]["name"]
            away_team = match["awayTeam"]["name"]
            match_date = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
            
            # Check for manual override BEFORE processing
            date_key = match_date.strftime("%Y-%m-%d")
            override = check_manual_override(date_key)
            
            # Determine if Liverpool is home or away
            if home_team == "Liverpool FC":
                opponent = away_team
                venue = "Anfield"
                is_home = True
            else:
                opponent = home_team
                venue = match.get("venue", "Away")
                is_home = False
            
            # If override exists, use it
            if override:
                # Parse override date to get full date string
                current_year = match_date.year
                override_date = datetime.strptime(f"{override['date']} {current_year}", "%m/%d %Y")
                full_date = override_date.strftime("%A, %B %d")
                
                upcoming_matches.append({
                    "opponent": override["opponent"],
                    "date": override["date"],
                    "time": override["time"],
                    "venue": venue,
                    "is_home": is_home,
                    "full_date": full_date,
                    "kickoff": override["time"],
                    "pass_display": override["pass_display"]
                })
                continue
            
            # All displayed times in configured timezone (e.g. America/New_York)
            display_timezone = pytz.timezone(PASSKIT_CONFIG["TIMEZONE"])
            local_time = match_date.astimezone(display_timezone)
            
            if match == fixtures[0]:
                print(f"   Display time ({PASSKIT_CONFIG['TIMEZONE']}): {local_time.strftime('%Y-%m-%d %H:%M %Z')}")
            
            date_str = local_time.strftime("%b %d")
            
            # Format time with AM/PM - drop :00 for exact hours
            hour = local_time.hour
            minute = local_time.minute
            
            # Determine AM/PM
            am_pm = "AM" if hour < 12 else "PM"
            
            # Convert to 12-hour format
            if hour == 0:
                display_hour = 12
            elif hour <= 12:
                display_hour = hour
            else:
                display_hour = hour - 12
            
            # Format time string
            if minute == 0:
                time_str = f"{display_hour} {am_pm}"
            else:
                time_str = f"{display_hour}:{minute:02d} {am_pm}"
            
            # Create optimized pass display format
            pass_display = format_match_display(opponent, date_str, time_str)
            
            upcoming_matches.append({
                "opponent": opponent,
                "date": date_str,
                "time": time_str,
                "venue": venue,
                "is_home": is_home,
                "full_date": local_time.strftime("%A, %B %d"),
                "kickoff": time_str,
                "pass_display": pass_display
            })
        
        return upcoming_matches
        
    except Exception as e:
        print(f"Error fetching fixtures: {e}")
        return []

def check_manual_override(match_date_str):
    """Check if there's a manual override for this match date."""
    try:
        override_file = os.path.join(os.path.dirname(__file__), "match_overrides.json")
        if os.path.exists(override_file):
            with open(override_file, 'r') as f:
                overrides = json.load(f)
                if overrides.get("enabled") and "overrides" in overrides:
                    # Check for override by date (format: YYYY-MM-DD)
                    if match_date_str in overrides["overrides"]:
                        override = overrides["overrides"][match_date_str]
                        print(f"⚠️  Using manual override for {match_date_str}: {override.get('note', '')}")
                        return override
    except Exception as e:
        print(f"Warning: Could not load match overrides: {e}")
    return None

def get_next_match():
    """Get the next upcoming match."""
    fixtures = get_liverpool_fixtures()
    if fixtures:
        return fixtures[0]  # Next match (already processed with override check)
    return None

def update_pass_fields(match_data):
    """Update PassKit pass fields with match information."""
    if not match_data:
        print("No match data to update")
        return False
    
    # Get all passes for the program
    url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/list/{PASSKIT_CONFIG['PROGRAM_ID']}"
    
    payload = {
        "filters": {
            "limit": 1000,
            "offset": 0,
            "orderBy": "created",
            "orderAsc": True
        }
    }
    
    try:
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        response.raise_for_status()
        
        # Parse NDJSON response
        passes = []
        for line in response.text.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    if 'result' in data:
                        passes.append(data['result'])
                except json.JSONDecodeError:
                    pass
        
        print(f"Found {len(passes)} passes to update")
        
        print(f"📝 Updating passes with: '{match_data['pass_display']}' ({len(match_data['pass_display'])} chars)")
        
        # Update each pass using the correct PassKit endpoint
        update_url = f"{PASSKIT_CONFIG['API_BASE']}/members/member"
        
        success_count = 0
        failed_count = 0
        
        for pass_data in passes:
            member_id = pass_data.get("id")
            external_id = pass_data.get("externalId")
            
            if not member_id:
                failed_count += 1
                continue
            
            # Update ALL passes with the next match
            # (removed the filter to update everyone)
            
            # Update pass using PUT method with passOverrides
            # We need to include the person data to avoid validation errors
            person_data = pass_data.get("person", {})
            
            update_payload = {
                "programId": PASSKIT_CONFIG["PROGRAM_ID"],
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
            
            # Add externalId if available (some members might not have it)
            if external_id:
                update_payload["externalId"] = external_id
            
            try:
                response = requests.put(update_url, headers=get_passkit_headers(), json=update_payload, timeout=30)
                response.raise_for_status()
                success_count += 1
                
                # Show progress every 50 updates
                if success_count % 50 == 0:
                    print(f"  ✅ Updated {success_count} passes...")
                    
            except Exception as e:
                failed_count += 1
                if failed_count <= 5:  # Only show first 5 errors
                    print(f"  ❌ Failed to update pass {member_id}: {e}")
        
        print(f"\n📊 Update Results:")
        print(f"  ✅ Successfully updated: {success_count} passes")
        print(f"  ❌ Failed to update: {failed_count} passes")
        print(f"  📱 Pass display: '{match_data['pass_display']}'")
        
        return success_count > 0
        
    except Exception as e:
        print(f"Error fetching passes: {e}")
        return False

def send_match_reminder_notification(match_data):
    """Prepare match reminder notification (NOT SENDING - requires buy-in)."""
    if not match_data:
        return False
    
    # Prepare notification content but DO NOT SEND
    if match_data['is_home']:
        message = f"🏠 Liverpool vs {match_data['opponent']} at Anfield - {match_data['full_date']} at {match_data['kickoff']}"
    else:
        message = f"✈️ Liverpool vs {match_data['opponent']} - {match_data['full_date']} at {match_data['kickoff']}"
    
    print(f"📱 [NOT SENDING] Match reminder would be: {message}")
    print("⚠️  Push notifications require board buy-in before enabling")
    
    # TODO: Enable when approved by board
    # This would send to all members with passes in their wallets
    
    return True

def main():
    """Main function to update passes with next match info."""
    print("🏆 Liverpool FC - Match Updates")
    print("=" * 40)
    
    # Get next match
    print("📅 Fetching upcoming fixtures...")
    next_match = get_next_match()
    
    if not next_match:
        print("❌ No upcoming matches found")
        return
    
    print(f"⚽ Next match: Liverpool vs {next_match['opponent']}")
    print(f"📅 Date: {next_match['full_date']}")
    print(f"🕐 Time: {next_match['kickoff']}")
    print(f"🏟️ Venue: {next_match['venue']}")
    print(f"🏠 Home: {'Yes' if next_match['is_home'] else 'No'}")
    
    # Show what will be displayed on passes
    print("\n" + "=" * 50)
    print("📱 TEXT THAT WILL APPEAR ON PASSES:")
    print("=" * 50)
    print(f"   '{next_match['pass_display']}'")
    print("=" * 50)
    print(f"   Length: {len(next_match['pass_display'])} characters")
    print()
    
    # Ask for confirmation (auto-confirm in non-interactive mode)
    if not sys.stdin.isatty():
        confirm = "yes"
        print("✅ Auto-confirming update (non-interactive)")
    else:
        while True:
            confirm = input("✅ Confirm update? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                break
            elif confirm in ['no', 'n']:
                print("❌ Update cancelled by user")
                return
            else:
                print("⚠️  Please enter 'yes' or 'no'")
    
    # Update passes
    print("\n📱 Updating passes...")
    success = update_pass_fields(next_match)
    
    if success:
        print("✅ Passes updated successfully!")
        
        # Prepare reminder notification (NOT SENDING)
        print("\n📢 Preparing match reminder...")
        send_match_reminder_notification(next_match)
        
    else:
        print("❌ Failed to update passes")

if __name__ == "__main__":
    main()
