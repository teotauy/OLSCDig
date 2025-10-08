#!/usr/bin/env python3
import requests
import json

# Test the PassKit API to see the actual structure
API_KEY = "QHxrhw8Wi2T6W5lvN1ZxK35BYqvX6ynYnPvSbDaV36dYkczgwWCkKckDPtlRoq4VlC5f-M9vn4wVJejSqVOKEqFkrYJ2P6M2W7UtxH-mOnD5RBBjwCjmNuPGUGYQDwMFKogg08Su2eE-1PzKGipfslEkxRH078J4e0XFWRzfZc7jmLXBHYr47UNy0JLM4kmQPbktsK-nQdGvunwStmxyAIie6lKcjnVHw8L61tyL6nAsO1VsclmHe5UG5ImB3XD2Xl5naggXBjEz1p74k5lO85VovN1y9IEI6s5m-Rh_WZXVB3-BEV6Ft5xEKTHpHlqB"
PROJECT_KEY = "f94c829556448ba780034221a0aa0a9c9a208792cfa20fa1c4e3ad71612a3a33"
PROGRAM_ID = "3yyTsbqwmtXaiKZ5qWhqTP"
# Try different possible API base URLs
api_bases = [
    "https://api.pub1.passkit.io",
    "https://api.passkit.io", 
    "https://pub1.passkit.io",
    "https://api.passkit.com",
    "https://pub1.passkit.com"
]

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "X-Project-Key": PROJECT_KEY
}

# Test different API base URLs and endpoints
for api_base in api_bases:
    print(f"\n=== Testing API Base: {api_base} ===")
    
    endpoints_to_try = [
        f"{api_base}/membership/members",
        f"{api_base}/members",
        f"{api_base}/membership/programs/{PROGRAM_ID}/members",
        f"{api_base}/membership/memberships",
        f"{api_base}/membership/memberships?programId={PROGRAM_ID}"
    ]
    
    for url in endpoints_to_try:
        print(f"\nTrying endpoint: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print(f"SUCCESS! Status 200 - Response text: {response.text[:500]}...")
                try:
                    data = response.json()
                    print(f"JSON Response: {json.dumps(data, indent=2)}")
                except:
                    print("Response is not JSON")
                break
            elif response.status_code != 404:
                print(f"Non-404 Error: {response.text[:200]}...")
        except Exception as e:
            print(f"Exception: {e}")
    
    # If we found a working endpoint, break
    if response.status_code == 200:
        break

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"API Response: {json.dumps(data, indent=2)}")
    else:
        print(f"Error Response: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
