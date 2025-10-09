#!/usr/bin/env python3
"""
Test PassKit API connection with CORRECT endpoints and NDJSON parsing.
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("PASSKIT_API_KEY")
PROJECT_KEY = os.getenv("PASSKIT_PROJECT_KEY")
PROGRAM_ID = os.getenv("PROGRAM_ID", "3yyTsbqwmtXaiKZ5qWhqTP")
API_BASE = os.getenv("API_BASE", "https://api.pub2.passkit.io")

if not API_KEY or not PROJECT_KEY:
    print("❌ Please set PASSKIT_API_KEY and PASSKIT_PROJECT_KEY in .env file")
    exit(1)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "X-Project-Key": PROJECT_KEY
}

def parse_ndjson(response_text):
    """Parse newline-delimited JSON response."""
    members = []
    for line in response_text.strip().split('\n'):
        if line:
            try:
                data = json.loads(line)
                # Each line has a "result" key with the member data
                if 'result' in data:
                    members.append(data['result'])
            except json.JSONDecodeError as e:
                print(f"⚠️  Skipping line due to JSON error: {e}")
    return members

print("Testing PassKit API Connection (USA Server - pub2)")
print(f"API Base: {API_BASE}")
print(f"Program ID: {PROGRAM_ID}")
print()

# Test 1: List all members (no filter)
print("Test 1: Listing all members...")
url = f"{API_BASE}/members/member/list/{PROGRAM_ID}"

payload = {
    "filters": {
        "limit": 100,
        "offset": 0,
        "orderBy": "created",
        "orderAsc": True
    }
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        members = parse_ndjson(response.text)
        print(f"✅ SUCCESS! Found {len(members)} total members")
        
        # Count by status
        checked_in = sum(1 for m in members if m.get("status") == "CHECKED_IN")
        checked_out = sum(1 for m in members if m.get("status") == "CHECKED_OUT")
        enrolled = sum(1 for m in members if m.get("status") == "ENROLLED")
        
        print(f"   - {checked_in} CHECKED_IN")
        print(f"   - {checked_out} CHECKED_OUT")
        print(f"   - {enrolled} ENROLLED")
    else:
        print(f"❌ Error: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

print()

# Test 2: List only CHECKED_IN members (with filter)
print("Test 2: Filtering for CHECKED_IN members only...")

payload = {
    "filters": {
        "limit": 100,
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
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        members = parse_ndjson(response.text)
        print(f"✅ SUCCESS! Found {len(members)} checked-in members")
        
        if members:
            print("\nFirst 5 checked-in members:")
            for i, member in enumerate(members[:5], 1):
                person = member.get('person', {})
                name = person.get('displayName', 'Unknown')
                member_id = member.get('id', 'Unknown')
                status = member.get('status', 'Unknown')
                print(f"   {i}. {name} (ID: {member_id}, Status: {status})")
    else:
        print(f"❌ Error: {response.text[:200]}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

print()
print("=" * 60)
print("Connection test complete!")
print("\n✅ If both tests succeeded, your API is working!")
print("You can now run: python3 app.py")
