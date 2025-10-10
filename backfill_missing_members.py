#!/usr/bin/env python3
"""
Backfill Missing Members from Squarespace Transactions
Processes all Squarespace membership purchases and creates missing PassKit members.

This script:
1. Gets all Squarespace transactions (membership products only)
2. Checks each email against existing PassKit members
3. Creates missing members in PassKit
4. Triggers PassKit welcome emails for new members
"""

import os
import json
import requests
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz

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

# Squarespace configuration (you'll need to add these to .env)
SQUARESPACE_CONFIG = {
    "API_KEY": os.getenv("SQUARESPACE_API_KEY"),
    "SITE_ID": os.getenv("SQUARESPACE_SITE_ID"),
    "API_BASE": "https://api.squarespace.com/1.0/commerce/orders"
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

def get_squarespace_headers():
    """Get headers for Squarespace API requests."""
    return {
        "Authorization": f"Bearer {SQUARESPACE_CONFIG['API_KEY']}",
        "Content-Type": "application/json"
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

def get_all_squarespace_orders():
    """
    Get all orders from Squarespace API.
    
    Returns:
        list: List of order data from Squarespace
    """
    if not SQUARESPACE_CONFIG["API_KEY"] or not SQUARESPACE_CONFIG["SITE_ID"]:
        print("❌ Squarespace API credentials not configured")
        print("Add SQUARESPACE_API_KEY and SQUARESPACE_SITE_ID to your .env file")
        return []
    
    url = f"{SQUARESPACE_CONFIG['API_BASE']}"
    headers = get_squarespace_headers()
    
    all_orders = []
    page_token = None
    
    try:
        while True:
            params = {
                "pageSize": 100,
                "pageToken": page_token
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            orders = data.get("orders", [])
            all_orders.extend(orders)
            
            # Check if there are more pages
            page_token = data.get("pagination", {}).get("nextPageToken")
            if not page_token:
                break
            
            print(f"📄 Fetched {len(orders)} orders (total: {len(all_orders)})")
        
        print(f"✅ Fetched {len(all_orders)} total orders from Squarespace")
        return all_orders
        
    except Exception as e:
        print(f"❌ Error fetching Squarespace orders: {e}")
        return []

def extract_membership_orders(orders):
    """
    Extract membership orders from all orders.
    
    Args:
        orders (list): All orders from Squarespace
        
    Returns:
        list: Orders containing membership products
    """
    membership_orders = []
    
    for order in orders:
        order_id = order.get("id", "")
        order_date = order.get("createdOn", "")
        customer_email = order.get("customerEmail", "")
        
        # Check each line item in the order
        line_items = order.get("lineItems", [])
        membership_items = []
        
        for item in line_items:
            product_name = item.get("productName", "")
            
            if is_membership_product(product_name):
                membership_items.append({
                    "productName": product_name,
                    "quantity": item.get("quantity", 1),
                    "price": item.get("unitPricePaid", {}).get("value", "0")
                })
        
        # If this order contains membership products, include it
        if membership_items:
            membership_orders.append({
                "orderId": order_id,
                "orderDate": order_date,
                "customerEmail": customer_email,
                "customerName": order.get("billingAddress", {}).get("firstName", "") + " " + order.get("billingAddress", {}).get("lastName", ""),
                "membershipItems": membership_items
            })
    
    print(f"🎯 Found {len(membership_orders)} orders containing membership products")
    return membership_orders

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
        customer_data (dict): Customer information from Squarespace order
        
    Returns:
        dict: Result of member creation
    """
    email = customer_data["customerEmail"]
    name_parts = customer_data.get("customerName", "").strip().split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    
    member_data = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "phone": "",  # Not available from Squarespace orders
        "membership_type": "Standard",  # Default, could be enhanced based on product
        "external_id": f"sq_backfill_{customer_data['orderId']}",
        "source": "Squarespace Backfill",
        "order_date": customer_data.get("orderDate", ""),
        "order_id": customer_data["orderId"]
    }
    
    # Create member in PassKit
    url = f"{PASSKIT_CONFIG['API_BASE']}/members/member"
    
    payload = {
        "programId": PASSKIT_CONFIG["PROGRAM_ID"],
        "externalId": member_data["external_id"],
        "person": {
            "forename": first_name,
            "surname": last_name,
            "displayName": customer_data.get("customerName", email),
            "emailAddress": email,
            "mobileNumber": ""
        },
        "metaData": {
            "nextMatch": "Some inferior side",  # Default placeholder
            "membershipType": "Standard",
            "joinDate": datetime.now().strftime("%Y-%m-%d"),
            "source": "Squarespace Backfill",
            "originalOrderId": customer_data["orderId"],
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
            "order_id": customer_data["orderId"]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "email": email,
            "order_id": customer_data["orderId"]
        }

def process_backfill():
    """
    Main backfill processing function.
    """
    print("🔄 Liverpool OLSC - Backfill Missing Members")
    print("=" * 50)
    
    # Step 1: Get all Squarespace orders
    print("📥 Fetching Squarespace orders...")
    all_orders = get_all_squarespace_orders()
    
    if not all_orders:
        print("❌ No orders found or API error")
        return
    
    # Step 2: Filter for membership orders
    print("🎯 Filtering for membership orders...")
    membership_orders = extract_membership_orders(all_orders)
    
    if not membership_orders:
        print("❌ No membership orders found")
        return
    
    # Step 3: Check each customer against PassKit
    print("🔍 Checking existing PassKit members...")
    
    missing_members = []
    existing_members = []
    
    for order in membership_orders:
        email = order["customerEmail"]
        
        if not email:
            print(f"⚠️ Skipping order {order['orderId']} - no email address")
            continue
        
        print(f"👤 Checking: {email}")
        
        existing_member = check_member_exists_in_passkit(email)
        
        if existing_member:
            print(f"  ✅ Already exists in PassKit")
            existing_members.append({
                "email": email,
                "order_id": order["orderId"],
                "member_id": existing_member.get("id")
            })
        else:
            print(f"  ❌ Missing from PassKit")
            missing_members.append(order)
    
    # Step 4: Create missing members
    print(f"\n📝 Creating {len(missing_members)} missing members...")
    
    created_members = []
    failed_creations = []
    
    for customer_data in missing_members:
        print(f"\n👤 Creating member: {customer_data['customerEmail']}")
        
        result = create_missing_member(customer_data)
        
        if result["success"]:
            print(f"  ✅ Created successfully - Member ID: {result['member_id']}")
            print(f"  📧 PassKit welcome email triggered")
            created_members.append(result)
        else:
            print(f"  ❌ Failed: {result['error']}")
            failed_creations.append(result)
    
    # Step 5: Summary
    print(f"\n📊 Backfill Summary:")
    print(f"  📥 Total Squarespace orders: {len(all_orders)}")
    print(f"  🎯 Membership orders found: {len(membership_orders)}")
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
        "total_orders": len(all_orders),
        "membership_orders": len(membership_orders),
        "existing_members": len(existing_members),
        "created_members": len(created_members),
        "failed_creations": len(failed_creations),
        "created_members_list": created_members,
        "failed_creations_list": failed_creations
    }
    
    with open(f"backfill_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to backfill_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

def main():
    """Main function."""
    print("🚀 Starting backfill process...")
    print("\n⚠️  This will:")
    print("  1. Fetch ALL Squarespace orders")
    print("  2. Filter for membership products only")
    print("  3. Check each customer against PassKit")
    print("  4. Create missing members")
    print("  5. Trigger PassKit welcome emails")
    
    confirm = input("\n🤔 Continue? (yes/no): ")
    
    if confirm.lower() in ['yes', 'y']:
        process_backfill()
    else:
        print("❌ Backfill cancelled")

if __name__ == "__main__":
    main()
