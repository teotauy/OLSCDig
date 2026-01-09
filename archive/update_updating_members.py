#!/usr/bin/env python3
"""
Update only members whose next match field shows "updating".
This handles new members who get the default "updating" value.
"""

import os
import json
import requests
from datetime import datetime
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

def get_liverpool_fixtures():
    """Get Liverpool FC fixtures from football-data.org API."""
    API_KEY = "7e9f8206e9db47fa8a4b15b783a7543b"
    
    headers = {
        "X-Auth-Token": API_KEY
    }
    
    team_id = 64  # Liverpool FC
    
    try:
        url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
        params = {
            "status": "SCHEDULED",
            "limit": 5
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        fixtures = data.get("matches", [])
        
        if fixtures:
            match = fixtures[0]
            home_team = match["homeTeam"]["name"]
            away_team = match["awayTeam"]["name"]
            match_date = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
            
            if home_team == "Liverpool FC":
                opponent = away_team
                venue = "Anfield"
                is_home = True
            else:
                opponent = home_team
                venue = match.get("venue", "Away")
                is_home = False
            
            local_time = match_date.astimezone(pytz.timezone(PASSKIT_CONFIG["TIMEZONE"]))
            date_str = local_time.strftime("%b %d")
            time_str = local_time.strftime("%I:%M %p")
            
            pass_display = format_match_display(opponent, date_str, time_str)
            
            return {
                "opponent": opponent,
                "date": date_str,
                "time": time_str,
                "venue": venue,
                "is_home": is_home,
                "pass_display": pass_display
            }
        
        return None
        
    except Exception as e:
        print(f"Error fetching fixtures: {e}")
        return None

def find_updating_members():
    """Find all members whose next match field shows 'updating'."""
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
                    "filterField": "metaData.nextMatch",
                    "filterValue": "Some inferior side",
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
        print(f"Error fetching updating members: {e}")
        return []

def update_member_match(member, match_data):
    """Update a single member's next match field."""
    member_id = member.get("id")
    if not member_id:
        return False
    
    url = f"{PASSKIT_CONFIG['API_BASE']}/members/member"
    
    person_data = member.get("person", {})
    external_id = member.get("externalId")
    
    payload = {
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
    
    if external_id:
        payload["externalId"] = external_id
    
    try:
        response = requests.put(url, headers=get_passkit_headers(), json=payload, timeout=30)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error updating member {member_id}: {e}")
        return False

def main():
    """Main function to update members with 'updating' status."""
    print("🔄 Liverpool FC - Update 'Updating' Members")
    print("=" * 50)
    
    # Get next match
    print("📅 Fetching next match...")
    match_data = get_liverpool_fixtures()
    
    if not match_data:
        print("❌ No upcoming matches found")
        return
    
    print(f"⚽ Next match: Liverpool vs {match_data['opponent']}")
    print(f"📅 Date: {match_data['date']}")
    print(f"🕐 Time: {match_data['time']}")
    print(f"📱 Will update to: {match_data['pass_display']}")
    
    # Find members with "updating" status
    print("\n🔍 Finding members with 'updating' status...")
    updating_members = find_updating_members()
    
    if not updating_members:
        print("✅ No members found with 'updating' status")
        return
    
    print(f"📋 Found {len(updating_members)} members with 'updating' status")
    
    # Update each member
    print(f"\n🔄 Updating members...")
    success_count = 0
    failed_count = 0
    
    for i, member in enumerate(updating_members, 1):
        name = member.get("person", {}).get("displayName", "Unknown")
        print(f"  {i}/{len(updating_members)}: {name}")
        
        if update_member_match(member, match_data):
            success_count += 1
        else:
            failed_count += 1
    
    print(f"\n📊 Update Results:")
    print(f"  ✅ Successfully updated: {success_count} members")
    print(f"  ❌ Failed to update: {failed_count} members")
    print(f"  📱 Updated to: '{match_data['pass_display']}'")

if __name__ == "__main__":
    main()
