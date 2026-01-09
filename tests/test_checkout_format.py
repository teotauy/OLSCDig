import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("PASSKIT_API_KEY")
PROJECT_KEY = os.getenv("PASSKIT_PROJECT_KEY")
PROGRAM_ID = os.getenv("PROGRAM_ID")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "X-Project-Key": PROJECT_KEY
}

# Test member ID
member_id = "48bsHU4rJATlmw4xg1HZpk"  # Lars Sunnell

# Try different payload formats
payloads = [
    {"id": member_id},
    {"memberId": member_id},
    {"externalId": member_id},
    {"programId": PROGRAM_ID, "id": member_id},
    {"programId": PROGRAM_ID, "memberId": member_id},
]

url = "https://api.pub2.passkit.io/members/member/checkOut"

print("Testing different checkout payload formats...")
print(f"URL: {url}")
print()

for i, payload in enumerate(payloads, 1):
    print(f"Test {i}: {payload}")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ SUCCESS!")
            print(f"   Response: {response.text[:100]}")
            break
        else:
            print(f"   Error: {response.text[:150]}")
    except Exception as e:
        print(f"   Exception: {e}")
    print()
