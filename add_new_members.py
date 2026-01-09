#!/usr/bin/env python3
"""
Quick script to add new members to the PassKit system.
Usage: python3 add_new_members.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import requests
import json

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

def check_member_exists(email):
    """Check if a member already exists in PassKit by email."""
    try:
        url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/list/{PASSKIT_CONFIG['PROGRAM_ID']}"
        
        payload = {
            "filters": {
                "limit": 100,
                "offset": 0,
                "filterGroups": [{
                    "condition": "AND",
                    "fieldFilters": [{
                        "filterField": "person.emailAddress",
                        "filterValue": email,
                        "filterOperator": "eq"
                    }]
                }]
            }
        }
        
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        response.raise_for_status()
        
        # Parse NDJSON response
        for line in response.text.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    if 'result' in data:
                        return data['result']
                except json.JSONDecodeError:
                    pass
        
        return None
        
    except Exception as e:
        print(f"❌ Error checking member existence: {e}")
        return None

def create_member(first_name, last_name, email, phone=""):
    """Create a new member in PassKit."""
    print(f"\n👤 Adding member: {first_name} {last_name} ({email})")
    
    # Check if member already exists
    existing_member = check_member_exists(email)
    
    if existing_member:
        print(f"⚠️ Member already exists with ID: {existing_member.get('id')}")
        return {
            "success": True,
            "member_id": existing_member.get("id"),
            "already_exists": True,
            "message": "Member already exists"
        }
    
    # Create new member
    url = f"{PASSKIT_CONFIG['API_BASE']}/members/member"
    
    # Generate external ID
    external_id = f"manual_{email}_{int(datetime.now().timestamp())}"
    
    payload = {
        "programId": PASSKIT_CONFIG["PROGRAM_ID"],
        "externalId": external_id,
        "tierId": "base",  # Base tier as requested
        "person": {
            "forename": first_name,
            "surname": last_name,
            "displayName": f"{first_name} {last_name}".strip(),
            "emailAddress": email,
            "mobileNumber": phone
        },
        "metaData": {
            "nextMatch": "Some inferior side",  # Default placeholder
            "membershipType": "Standard",
            "joinDate": datetime.now().strftime("%Y-%m-%d"),
            "source": "Manual Addition"
        },
        "sendWelcomeEmail": True  # Trigger PassKit's welcome email
    }
    
    try:
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ PassKit API Error {response.status_code}: {response.text}")
            return {
                "success": False,
                "error": f"API Error {response.status_code}: {response.text}"
            }
        
        response.raise_for_status()
        result = response.json()
        member_id = result.get("id")
        
        # Get pass URL
        pass_url = f"https://pub2.passkit.io/pass/{PASSKIT_CONFIG['PROGRAM_ID']}/{member_id}"
        
        print(f"✅ Member created successfully!")
        print(f"   Member ID: {member_id}")
        print(f"   Pass URL: {pass_url}")
        print(f"   📧 Welcome email triggered")
        
        return {
            "success": True,
            "member_id": member_id,
            "pass_url": pass_url,
            "email": email,
            "name": f"{first_name} {last_name}"
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating member: {e}")
        return {
            "success": False,
            "error": str(e),
            "email": email
        }

def main():
    """Main function to add members interactively."""
    print("🏆 Liverpool OLSC - Add New Members")
    print("=" * 40)
    
    members = []
    
    print("Enter member details (press Enter with empty name to finish):")
    
    while True:
        print(f"\n--- Member {len(members) + 1} ---")
        first_name = input("First Name: ").strip()
        
        if not first_name:
            break
            
        last_name = input("Last Name: ").strip()
        email = input("Email: ").strip()
        phone = input("Phone (optional): ").strip()
        
        if not last_name or not email:
            print("❌ Last name and email are required!")
            continue
            
        members.append({
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone
        })
    
    if not members:
        print("❌ No members to add.")
        return
    
    print(f"\n📝 Ready to add {len(members)} members:")
    for i, member in enumerate(members, 1):
        print(f"  {i}. {member['first_name']} {member['last_name']} ({member['email']})")
    
    confirm = input(f"\n🤔 Add these {len(members)} members? (yes/no): ")
    
    if confirm.lower() not in ['yes', 'y']:
        print("❌ Cancelled.")
        return
    
    print(f"\n🚀 Adding members...")
    
    successful = 0
    failed = 0
    already_existed = 0
    
    for member in members:
        result = create_member(
            member["first_name"],
            member["last_name"], 
            member["email"],
            member["phone"]
        )
        
        if result["success"]:
            if result.get("already_exists"):
                already_existed += 1
            else:
                successful += 1
        else:
            failed += 1
    
    print(f"\n📊 Summary:")
    print(f"  ✅ New members created: {successful}")
    print(f"  ⚠️ Already existed: {already_existed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📧 Total processed: {len(members)}")

if __name__ == "__main__":
    main()

