#!/usr/bin/env python3
"""
Process orders.csv directly using our working member creation system.
"""

import csv
from squarespace_to_passkit import process_squarespace_form_data

def process_orders_csv():
    """Process the orders.csv file."""
    print("🔄 Processing orders.csv")
    print("=" * 40)
    
    results = []
    current_year_count = 0
    filtered_out_count = 0
    
    with open('orders.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            # Check if this is a membership product
            product_name = row.get("Lineitem name", "")
            
            if "LFC Brooklyn" in product_name and "Membership" in product_name:
                # Filter for current year (25/26) memberships only
                if "25/26" in product_name:
                    current_year_count += 1
                    
                    email = row.get("Email", "")
                    form_name = row.get("Product Form: Name", "")
                    created_date = row.get("Created at", "")
                    
                    if email and form_name:
                        # Split the form name into first/last
                        name_parts = form_name.split()
                        first_name = name_parts[0] if name_parts else ""
                        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                        
                        member_data = {
                            "email": email,
                            "first_name": first_name,
                            "last_name": last_name,
                            "phone": row.get("Billing Phone", ""),
                            "membership_type": "Standard",
                            "external_id": f"sq_2526_{row.get('Order ID', '')}",
                            "source": "Orders CSV Backfill 25/26",
                            "order_date": created_date,
                            "order_id": row.get("Order ID", "")
                        }
                        
                        print(f"👤 Processing: {email} ({first_name} {last_name})")
                        print(f"  📅 Order: {created_date}")
                        
                        # Use our working member creation system
                        result = process_squarespace_form_data(member_data, use_passkit_email=True)
                        results.append(result)
                        
                        if result["success"]:
                            print(f"  ✅ Created successfully")
                        else:
                            print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
                else:
                    filtered_out_count += 1
                    print(f"⏭️  Skipping non-current year membership: {product_name}")
    
    print(f"\n📊 Filtering Summary:")
    print(f"  🎯 Current year (25/26) memberships: {current_year_count}")
    print(f"  ⏭️  Filtered out (other years): {filtered_out_count}")
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    
    print(f"\n📊 Processing Summary:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📧 Total: {len(results)}")

if __name__ == "__main__":
    process_orders_csv()
