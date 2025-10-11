#!/usr/bin/env python3
"""
Liverpool FC Match Updates for PassKit passes.
Automatically updates pass fields with upcoming match information.
"""

import os
import json
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
    Get Liverpool FC fixtures from football-data.org API.
    Returns upcoming matches with opponent, date, time, venue.
    """
    # Free tier API key (you can get your own at football-data.org)
    API_KEY = "7e9f8206e9db47fa8a4b15b783a7543b"
    
    headers = {
        "X-Auth-Token": API_KEY
    }
    
    # Liverpool FC team ID in Premier League
    team_id = 64  # Liverpool FC
    
    try:
        # Get upcoming fixtures
        url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
        params = {
            "status": "SCHEDULED",
            "limit": 5  # Next 5 matches
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        fixtures = data.get("matches", [])
        
        # Process fixtures
        upcoming_matches = []
        for match in fixtures:
            home_team = match["homeTeam"]["name"]
            away_team = match["awayTeam"]["name"]
            match_date = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
            
            # Determine if Liverpool is home or away
            if home_team == "Liverpool FC":
                opponent = away_team
                venue = "Anfield"
                is_home = True
            else:
                opponent = home_team
                venue = match.get("venue", "Away")
                is_home = False
            
            # Format date and time for pass display
            local_time = match_date.astimezone(pytz.timezone(PASSKIT_CONFIG["TIMEZONE"]))
            date_str = local_time.strftime("%b %d")
            time_str = local_time.strftime("%I:%M %p")
            
            # Create optimized pass display format
            pass_display = format_match_display(opponent, date_str, time_str)
            
            upcoming_matches.append({
                "opponent": opponent,
                "date": date_str,
                "time": time_str,
                "venue": venue,
                "is_home": is_home,
                "full_date": local_time.strftime("%A, %B %d"),
                "kickoff": local_time.strftime("%I:%M %p"),
                "pass_display": pass_display
            })
        
        return upcoming_matches
        
    except Exception as e:
        print(f"Error fetching fixtures: {e}")
        return []

def get_next_match():
    """Get the next upcoming match."""
    fixtures = get_liverpool_fixtures()
    if fixtures:
        return fixtures[0]  # Next match
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
