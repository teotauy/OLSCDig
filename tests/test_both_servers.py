#!/usr/bin/env python3
"""
Test both pub1 (EU) and pub2 (USA) servers to find which one your account is on.
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("PASSKIT_API_KEY")
PROJECT_KEY = os.getenv("PASSKIT_PROJECT_KEY")
PROGRAM_ID = os.getenv("PROGRAM_ID", "3yyTsbqwmtXaiKZ5qWhqTP")

servers = [
    ("EU (pub1)", "https://api.pub1.passkit.io"),
    ("USA (pub2)", "https://api.pub2.passkit.io")
]

print("Testing both PassKit servers...")
print("=" * 60)

for name, base_url in servers:
    print(f"\n🔍 Testing {name}: {base_url}")
    
    url = f"{base_url}/members/member/list/{PROGRAM_ID}"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "X-Project-Key": PROJECT_KEY
    }
    
    payload = {
        "filters": {
            "limit": 10,
            "offset": 0,
            "orderBy": "created",
            "orderAsc": True
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ SUCCESS! This is your server!")
            data = response.json()
            members = data.get('members') or data.get('data') or []
            print(f"   Found {len(members)} members")
            print(f"\n   👉 UPDATE YOUR .env FILE:")
            print(f"   API_BASE={base_url}")
            break
        elif response.status_code == 401:
            print(f"   ❌ 401 Unauthorized")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', {}).get('message', 'Unknown error')}")
            except:
                print(f"   Error: {response.text[:100]}")
        else:
            print(f"   ❌ Error {response.status_code}")
            print(f"   {response.text[:150]}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")

print("\n" + "=" * 60)
print("\n⚠️  If both servers return 401 errors:")
print("1. Your API key may need to be regenerated")
print("2. Check PassKit dashboard for a fresh API key")
print("3. Make sure you're using a 'Long Lived Token' not a session token")
print("\n📧 Contact PassKit support if the issue persists")

