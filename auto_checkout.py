#!/usr/bin/env python3
"""
Auto checkout all members without confirmation.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

PASSKIT_CONFIG = {
    "PROGRAM_ID": os.getenv("PROGRAM_ID", "3yyTsbqwmtXaiKZ5qWhqTP"),
    "API_BASE": os.getenv("API_BASE", "https://api.pub2.passkit.io"),
    "API_KEY": os.getenv("PASSKIT_API_KEY"),
    "PROJECT_KEY": os.getenv("PASSKIT_PROJECT_KEY"),
}

def get_passkit_headers():
    return {
        "Authorization": f"Bearer {PASSKIT_CONFIG['API_KEY']}",
        "Content-Type": "application/json",
        "X-Project-Key": PASSKIT_CONFIG["PROJECT_KEY"]
    }

def get_checked_in_members():
    """Get all checked-in members."""
    url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/list/{PASSKIT_CONFIG['PROGRAM_ID']}"
    
    payload = {
        "filters": {
            "limit": 1000,
            "offset": 0,
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
    
    response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
    response.raise_for_status()
    
    members = []
    for line in response.text.strip().split('\n'):
        if line:
            try:
                data = json.loads(line)
                if 'result' in data:
                    members.append(data['result'])
            except json.JSONDecodeError:
                pass
    
    return members

def checkout_member(member_id):
    """Check out a single member."""
    url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/checkOut"
    
    payload = {
        "memberId": member_id
    }
    
    response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
    return response.status_code == 200

def main():
    print("🏴󠁧󠁢󠁥󠁮󠁧󠁿  Liverpool OLSC - Auto Checkout")
    print("=" * 50)
    
    print("📡 Fetching checked-in members...")
    members = get_checked_in_members()
    
    if not members:
        print("✅ No members checked in")
        return
    
    print(f"📋 Found {len(members)} checked-in members")
    
    print(f"\n🔄 Checking out all {len(members)} members...")
    
    success_count = 0
    failed_count = 0
    
    for i, member in enumerate(members, 1):
        name = member.get("person", {}).get("displayName", "Unknown")
        member_id = member.get("id")
        
        if checkout_member(member_id):
            success_count += 1
            print(f"  ✅ {i}/{len(members)}: {name}")
        else:
            failed_count += 1
            print(f"  ❌ {i}/{len(members)}: {name}")
    
    print(f"\n📊 Checkout Results:")
    print(f"  ✅ Successfully checked out: {success_count}")
    print(f"  ❌ Failed: {failed_count}")
    print(f"  📧 Total processed: {len(members)}")

if __name__ == "__main__":
    main()

