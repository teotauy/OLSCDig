#!/usr/bin/env python3
"""
Simple bulk checkout script for PassKit members.
Changes all CHECKED_IN members to CHECKED_OUT.

✅ WORKING VERSION with correct pub2 endpoints and NDJSON parsing.

Usage: python checkout.py
"""

import os
import requests
import json
from dotenv import load_dotenv

def load_config():
    """Load configuration from environment variables."""
    load_dotenv()
    config = {
        "PROGRAM_ID": os.getenv("PROGRAM_ID"),
        "API_BASE": os.getenv("API_BASE", "https://api.pub2.passkit.io"),
        "API_KEY": os.getenv("PASSKIT_API_KEY"),
        "PROJECT_KEY": os.getenv("PASSKIT_PROJECT_KEY"),
    }
    
    # Validate required fields
    missing = [k for k, v in config.items() if k in ("PROGRAM_ID", "API_KEY", "PROJECT_KEY") and not v]
    if missing:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing)}")
        print(f"\nPlease check your .env file")
        exit(1)
    
    return config

def get_passkit_headers(config):
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
                if 'result' in data:
                    members.append(data['result'])
            except json.JSONDecodeError:
                pass
    return members

def get_checked_in_members(config):
    """Fetch all CHECKED_IN members from PassKit API."""
    url = f"{config['API_BASE']}/members/member/list/{config['PROGRAM_ID']}"
    
    # POST body with filter for CHECKED_IN status
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
        response = requests.post(url, headers=get_passkit_headers(config), json=payload, timeout=30)
        response.raise_for_status()
        return parse_ndjson(response.text)
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching members: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text[:200]}")
        return None

def checkout_member(config, member_id):
    """Change a single member's status to CHECKED_OUT."""
    url = f"{config['API_BASE']}/members/member/checkOut"
    
    payload = {
        "memberId": member_id
    }
    
    try:
        response = requests.post(url, headers=get_passkit_headers(config), json=payload, timeout=30)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Failed: {str(e)[:50]}")
        return False

def main():
    """Main execution function."""
    print("=" * 50)
    print("🏴󠁧󠁢󠁥󠁮󠁧󠁿  Liverpool OLSC - Bulk Checkout")
    print("=" * 50)
    print()
    
    config = load_config()
    
    print("📡 Fetching checked-in members...")
    members = get_checked_in_members(config)
    
    if members is None:
        print("\n⚠️  Could not fetch members from PassKit API.")
        print("Please check your API credentials and network connection.")
        exit(1)
    
    if not members:
        print("✅ No members are currently checked in!")
        exit(0)
    
    print(f"\n📋 Found {len(members)} checked-in members:\n")
    
    for i, member in enumerate(members, 1):
        person = member.get('person', {})
        name = person.get('displayName', 'Unknown')
        print(f"   {i}. {name}")
    
    print("\n" + "=" * 50)
    response = input(f"Check out all {len(members)} members? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("❌ Cancelled.")
        exit(0)
    
    print("\n🔄 Checking out members...\n")
    
    success_count = 0
    for member in members:
        member_id = member.get("id")
        person = member.get('person', {})
        name = person.get('displayName', 'Unknown')
        
        print(f"   Checking out {name}...", end=" ")
        if checkout_member(config, member_id):
            success_count += 1
            print("✅")
    
    print(f"\n" + "=" * 50)
    print(f"✅ Successfully checked out {success_count}/{len(members)} members")
    print("=" * 50)

if __name__ == "__main__":
    main()
