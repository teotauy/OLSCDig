#!/usr/bin/env python3
"""
Test different filter field names to find the correct one.
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

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "X-Project-Key": PROJECT_KEY
}

url = f"{API_BASE}/members/member/list/{PROGRAM_ID}"

def parse_ndjson(response_text):
    """Parse newline-delimited JSON response."""
    members = []
    for line in response_text.strip().split('\n'):
        if line:
            data = json.loads(line)
            if 'result' in data:
                members.append(data['result'])
    return members

# Try different filter field names
filter_fields = [
    "status",
    "passStatus",
    "memberStatus",
    "member.status"
]

print("Testing different filter field names...")
print("=" * 60)

for field_name in filter_fields:
    print(f"\n🔍 Trying filterField: '{field_name}'")
    
    payload = {
        "filters": {
            "limit": 10,
            "offset": 0,
            "orderBy": "created",
            "orderAsc": True,
            "filterGroups": [{
                "condition": "AND",
                "fieldFilters": [{
                    "filterField": field_name,
                    "filterValue": "CHECKED_IN",
                    "filterOperator": "eq"
                }]
            }]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            members = parse_ndjson(response.text)
            print(f"   ✅ SUCCESS! Found {len(members)} CHECKED_IN members")
            print(f"   👉 Use filterField: '{field_name}'")
            
            if members:
                print(f"\n   First member:")
                person = members[0].get('person', {})
                name = person.get('displayName', 'Unknown')
                status = members[0].get('status', 'Unknown')
                print(f"   - Name: {name}")
                print(f"   - Status: {status}")
            break
        else:
            error = response.json().get('error', {})
            print(f"   ❌ {response.status_code}: {error.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")

print("\n" + "=" * 60)

