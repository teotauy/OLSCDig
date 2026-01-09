#!/usr/bin/env python3
"""
Check the actual response from pub2 server.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("PASSKIT_API_KEY")
PROJECT_KEY = os.getenv("PASSKIT_PROJECT_KEY")
PROGRAM_ID = os.getenv("PROGRAM_ID", "3yyTsbqwmtXaiKZ5qWhqTP")

url = f"https://api.pub2.passkit.io/members/member/list/{PROGRAM_ID}"

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

response = requests.post(url, headers=headers, json=payload, timeout=10)

print(f"Status Code: {response.status_code}")
print(f"Response Text Length: {len(response.text)}")
print(f"\nFirst 500 chars of response:")
print(response.text[:500])
print(f"\n\nLast 100 chars of response:")
print(response.text[-100:])

# Try to parse line by line
print(f"\n\nTrying to parse as NDJSON (newline-delimited JSON)...")
lines = response.text.strip().split('\n')
print(f"Found {len(lines)} lines")

if len(lines) > 0:
    import json
    for i, line in enumerate(lines[:3], 1):
        try:
            data = json.loads(line)
            print(f"\nLine {i} parsed successfully:")
            print(f"  Keys: {list(data.keys())}")
        except Exception as e:
            print(f"\nLine {i} error: {e}")
            print(f"  Content: {line[:100]}")

