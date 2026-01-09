#!/usr/bin/env python3
"""
Quick script to add new members to the PassKit system.
Just edit the MEMBERS list below with your new members and run the script.
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

# ADD YOUR NEW MEMBERS HERE:
MEMBERS = [
    {
        "first_name": "Jamie",
        "last_name": "Laughlin",
        "email": "jamielaughlin@live.co.uk",
        "phone": ""
    }
]

def get_passkit_headers():
    """Get headers for PassKit API requests."""
    return {
        "Authorization": f"Bearer {PASSKIT_CONFIG['API_KEY']}",
        "Content-Type": "application/json",
        "X-Project-Key": PASSKIT_CONFIG["PROJECT_KEY"]
    }

def check_member_exists(email):
    """
    Check if a member already exists in PassKit by email.
    
    Note: PassKit API doesn't support filtering by email directly, so we fetch
    members and search through them. This searches the most recent 500 members.
    """
    try:
        url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/list/{PASSKIT_CONFIG['PROGRAM_ID']}"
        
        # Fetch recent members (PassKit API doesn't support email filtering)
        # We'll search through up to 500 recent members
        payload = {
            "filters": {
                "limit": 500,  # Check recent 500 members
                "offset": 0,
                "orderBy": "created",
                "orderAsc": False  # Most recent first
            }
        }
        
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        
        # Check for errors before raising
        if response.status_code != 200:
            print(f"⚠️ Warning: Member check returned {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            # Don't fail completely - just return None and continue
            return None
        
        response.raise_for_status()
        
        # Parse NDJSON response and search for matching email
        response_text = response.text.strip()
        if not response_text:
            return None
        
        email_lower = email.lower()
            
        for line in response_text.split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    # Check if data is wrapped in 'result' key
                    member = None
                    if 'result' in data:
                        member = data['result']
                    elif 'person' in data:
                        member = data
                    
                    if member:
                        # Check if email matches (case-insensitive)
                        member_email = member.get('person', {}).get('emailAddress', '')
                        if member_email.lower() == email_lower:
                            return member
                except json.JSONDecodeError as e:
                    # Log but continue parsing other lines
                    print(f"⚠️ Warning: Failed to parse line in member search response: {e}")
                    continue
        
        # Not found in recent members
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Warning: Network error checking member existence for {email}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response status: {e.response.status_code}")
            print(f"   Response body: {e.response.text[:200]}")
        # Return None on error - caller should handle this appropriately
        return None
    except Exception as e:
        print(f"⚠️ Warning: Unexpected error checking member existence for {email}: {e}")
        import traceback
        traceback.print_exc()
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
    """Main function to add members from the MEMBERS list."""
    print("🏆 Liverpool OLSC - Quick Add New Members")
    print("=" * 45)
    
    if not MEMBERS:
        print("❌ No members in the MEMBERS list!")
        print("Edit the script and add members to the MEMBERS list at the top.")
        return
    
    print(f"📝 Ready to add {len(MEMBERS)} members:")
    for i, member in enumerate(MEMBERS, 1):
        print(f"  {i}. {member['first_name']} {member['last_name']} ({member['email']})")
    
    print(f"\n🚀 Adding members...")
    
    successful = 0
    failed = 0
    already_existed = 0
    
    for member in MEMBERS:
        result = create_member(
            member["first_name"],
            member["last_name"], 
            member["email"],
            member.get("phone", "")
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
    print(f"  📧 Total processed: {len(MEMBERS)}")

if __name__ == "__main__":
    main()
