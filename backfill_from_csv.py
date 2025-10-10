#!/usr/bin/env python3
"""
Backfill Missing Members from Squarespace CSV Export
Alternative to API-based backfill - processes CSV export from Squarespace.

Usage: python3 backfill_from_csv.py squarespace_export.csv
"""

import os
import json
import requests
import csv
import sys
from datetime import datetime
from dotenv import load_dotenv

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

# Product filtering - only process these product types
MEMBERSHIP_PRODUCTS = [
    "membership",
    "olsc membership", 
    "liverpool olsc membership",
    "supporters club membership",
    "annual membership",
    "yearly membership"
]

# Exclude these products (scarves, etc.)
EXCLUDED_PRODUCTS = [
    "scarf",
    "merchandise",
    "shirt",
    "jersey",
    "hat",
    "mug",
    "pin",
    "badge"
]

def get_passkit_headers():
    """Get headers for PassKit API requests."""
    return {
        "Authorization": f"Bearer {PASSKIT_CONFIG['API_KEY']}",
        "Content-Type": "application/json",
        "X-Project-Key": PASSKIT_CONFIG["PROJECT_KEY"]
    }

def is_membership_product(product_name):
    """
    Check if a product is a membership product.
    
    Args:
        product_name (str): Product name from Squarespace
        
    Returns:
        bool: True if this is a membership product
    """
    if not product_name:
        return False
    
    product_lower = product_name.lower()
    
    # Check if it's an excluded product
    for excluded in EXCLUDED_PRODUCTS:
        if excluded in product_lower:
            return False
    
    # Check if it's a membership product
    for membership in MEMBERSHIP_PRODUCTS:
        if membership in product_lower:
            return True
    
    return False

def check_member_exists_in_passkit(email):
    """
    Check if a member exists in PassKit by email.
    
    Args:
        email (str): Member's email address
        
    Returns:
        dict: Member data if found, None if not found
    """
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

def create_missing_member(customer_data):
    """
    Create a missing member in PassKit.
    
    Args:
        customer_data (dict): Customer information from CSV
        
    Returns:
        dict: Result of member creation
    """
    email = customer_data["email"]
    first_name = customer_data.get("first_name", "")
    last_name = customer_data.get("last_name", "")
    order_id = customer_data.get("order_id", "")
    
    member_data = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "phone": customer_data.get("phone", ""),
        "membership_type": "Standard",
        "external_id": f"sq_backfill_{order_id}" if order_id else f"sq_backfill_{int(datetime.now().timestamp())}",
        "source": "Squarespace CSV Backfill",
        "order_date": customer_data.get("order_date", ""),
        "order_id": order_id
    }
    
    # Create member in PassKit
    url = f"{PASSKIT_CONFIG['API_BASE']}/members/member"
    
    payload = {
        "programId": PASSKIT_CONFIG["PROGRAM_ID"],
        "externalId": member_data["external_id"],
        "person": {
            "forename": first_name,
            "surname": last_name,
            "displayName": f"{first_name} {last_name}".strip() or email,
            "emailAddress": email,
            "mobileNumber": customer_data.get("phone", "")
        },
        "metaData": {
            "nextMatch": "Some inferior side",
            "membershipType": "Standard",
            "joinDate": datetime.now().strftime("%Y-%m-%d"),
            "source": "Squarespace CSV Backfill",
            "originalOrderId": order_id,
            "backfillDate": datetime.now().isoformat()
        },
        "sendWelcomeEmail": True  # Trigger PassKit's welcome email
    }
    
    try:
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return {
            "success": True,
            "member_id": result.get("id"),
            "email": email,
            "order_id": order_id
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "email": email,
            "order_id": order_id
        }

def process_csv_backfill(csv_file_path):
    """
    Process CSV file for backfill.
    
    Args:
        csv_file_path (str): Path to Squarespace CSV export
    """
    print(f"📄 Processing CSV file: {csv_file_path}")
    
    membership_customers = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Check if this row contains a membership product
                product_name = row.get("Product Name", "")
                
                if is_membership_product(product_name):
                    customer_data = {
                        "email": row.get("Customer Email", ""),
                        "first_name": row.get("Customer First Name", ""),
                        "last_name": row.get("Customer Last Name", ""),
                        "phone": row.get("Customer Phone", ""),
                        "order_id": row.get("Order Number", ""),
                        "order_date": row.get("Order Date", ""),
                        "product_name": product_name
                    }
                    
                    if customer_data["email"]:
                        membership_customers.append(customer_data)
        
        print(f"🎯 Found {len(membership_customers)} membership purchases in CSV")
        
        if not membership_customers:
            print("❌ No membership purchases found in CSV")
            return
        
        # Remove duplicates (same email, multiple orders)
        unique_customers = {}
        for customer in membership_customers:
            email = customer["email"]
            if email not in unique_customers:
                unique_customers[email] = customer
            else:
                # Keep the most recent order
                existing_date = unique_customers[email].get("order_date", "")
                new_date = customer.get("order_date", "")
                if new_date > existing_date:
                    unique_customers[email] = customer
        
        unique_customers_list = list(unique_customers.values())
        print(f"👥 {len(unique_customers_list)} unique customers after deduplication")
        
        # Check each customer against PassKit
        print("🔍 Checking existing PassKit members...")
        
        missing_members = []
        existing_members = []
        
        for customer_data in unique_customers_list:
            email = customer_data["email"]
            
            print(f"👤 Checking: {email}")
            
            existing_member = check_member_exists_in_passkit(email)
            
            if existing_member:
                print(f"  ✅ Already exists in PassKit")
                existing_members.append({
                    "email": email,
                    "order_id": customer_data.get("order_id"),
                    "member_id": existing_member.get("id")
                })
            else:
                print(f"  ❌ Missing from PassKit")
                missing_members.append(customer_data)
        
        # Create missing members
        print(f"\n📝 Creating {len(missing_members)} missing members...")
        
        created_members = []
        failed_creations = []
        
        for customer_data in missing_members:
            print(f"\n👤 Creating member: {customer_data['email']}")
            
            result = create_missing_member(customer_data)
            
            if result["success"]:
                print(f"  ✅ Created successfully - Member ID: {result['member_id']}")
                print(f"  📧 PassKit welcome email triggered")
                created_members.append(result)
            else:
                print(f"  ❌ Failed: {result['error']}")
                failed_creations.append(result)
        
        # Summary
        print(f"\n📊 Backfill Summary:")
        print(f"  📄 Total membership purchases in CSV: {len(membership_customers)}")
        print(f"  👥 Unique customers: {len(unique_customers_list)}")
        print(f"  ✅ Already in PassKit: {len(existing_members)}")
        print(f"  🆕 New members created: {len(created_members)}")
        print(f"  ❌ Failed creations: {len(failed_creations)}")
        
        if created_members:
            print(f"\n🆕 New Members Created:")
            for member in created_members:
                print(f"  • {member['email']} (Order: {member['order_id']})")
        
        if failed_creations:
            print(f"\n❌ Failed Creations:")
            for member in failed_creations:
                print(f"  • {member['email']} - {member['error']}")
        
        # Save results to file
        results = {
            "backfill_date": datetime.now().isoformat(),
            "csv_file": csv_file_path,
            "total_membership_purchases": len(membership_customers),
            "unique_customers": len(unique_customers_list),
            "existing_members": len(existing_members),
            "created_members": len(created_members),
            "failed_creations": len(failed_creations),
            "created_members_list": created_members,
            "failed_creations_list": failed_creations
        }
        
        with open(f"csv_backfill_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to csv_backfill_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
    except Exception as e:
        print(f"❌ Error processing CSV: {e}")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python3 backfill_from_csv.py <squarespace_export.csv>")
        print("\nExample: python3 backfill_from_csv.py squarespace_orders_export.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        sys.exit(1)
    
    print("🔄 Liverpool OLSC - CSV Backfill Missing Members")
    print("=" * 50)
    print(f"📄 CSV file: {csv_file}")
    print("\n⚠️  This will:")
    print("  1. Parse CSV for membership purchases only")
    print("  2. Remove duplicates (same email)")
    print("  3. Check each customer against PassKit")
    print("  4. Create missing members")
    print("  5. Trigger PassKit welcome emails")
    
    confirm = input("\n🤔 Continue? (yes/no): ")
    
    if confirm.lower() in ['yes', 'y']:
        process_csv_backfill(csv_file)
    else:
        print("❌ Backfill cancelled")

if __name__ == "__main__":
    main()
