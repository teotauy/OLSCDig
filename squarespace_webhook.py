#!/usr/bin/env python3
"""
Squarespace Webhook Handler for PassKit Integration
Receives form submissions from Squarespace and automatically creates PassKit members.

This Flask app runs on your server and receives webhooks from Squarespace.
"""

import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from squarespace_to_passkit import process_squarespace_form_data

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Webhook security (optional but recommended)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

@app.route('/webhook/squarespace', methods=['POST'])
def handle_squarespace_webhook():
    """
    Handle order completions from Squarespace e-commerce.
    
    Expected payload format for Squarespace e-commerce:
    {
        "orderId": "order_123456",
        "customer": {
            "email": "customer@example.com",
            "firstName": "John",
            "lastName": "Smith"
        },
        "lineItems": [
            {
                "productName": "LFC Brooklyn 25/26 Membership",
                "quantity": 1,
                "variantName": "Standard Membership"
            }
        ],
        "createdOn": "2025-01-09T14:30:00Z"
    }
    """
    try:
        # Get the webhook payload
        payload = request.get_json()
        
        if not payload:
            return jsonify({"error": "No payload received"}), 400
        
        print(f"📨 Received webhook for order: {payload.get('orderId', 'Unknown Order')}")
        
        # Check if this order contains membership products
        if not is_membership_order(payload):
            print("ℹ️ Order does not contain membership products - skipping")
            return jsonify({
                "status": "ignored",
                "message": "No membership products in order"
            }), 200
        
        # Process the membership order
        return handle_membership_order(payload)
            
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

def is_membership_order(payload):
    """Check if the order contains membership products."""
    # Define membership product names/patterns
    MEMBERSHIP_PRODUCTS = [
        "membership",
        "lfc brooklyn",
        "brooklyn membership",
        "25/26",
        "26/27"
    ]
    
    line_items = payload.get('lineItems', [])
    
    for item in line_items:
        product_name = item.get('productName', '').lower()
        
        # Check if any membership keyword is in the product name
        if any(keyword in product_name for keyword in MEMBERSHIP_PRODUCTS):
            print(f"✅ Found membership product: {item.get('productName')}")
            return True
    
    return False

def handle_membership_order(payload):
    """Handle Squarespace e-commerce order with membership products."""
    customer = payload.get('customer', {})
    line_items = payload.get('lineItems', [])
    
    if not customer.get('email'):
        return jsonify({"error": "No customer email address provided"}), 400
    
    # Extract customer info
    customer_email = customer.get('email', '')
    customer_name = f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip()
    
    # Process each membership product in the order
    results = []
    
    for item in line_items:
        product_name = item.get('productName', '')
        quantity = item.get('quantity', 1)
        
        # Only process membership products (already filtered by is_membership_order)
        if any(keyword in product_name.lower() for keyword in ["membership", "lfc brooklyn", "brooklyn membership", "25/26", "26/27"]):
            
            # Create member data
            member_data = {
                "email": customer_email,
                "first_name": customer.get('firstName', ''),
                "last_name": customer.get('lastName', ''),
                "phone": customer.get('phone', ''),
                "membership_type": extract_membership_type(product_name),
                "external_id": f"sq_{customer_email}_{payload.get('orderId', '')}_{int(datetime.now().timestamp())}",
                "source": "Squarespace Order",
                "order_id": payload.get('orderId', ''),
                "product_name": product_name,
                "submission_time": payload.get('createdOn', datetime.now().isoformat())
            }
            
            # Process the member
            result = process_squarespace_form_data(member_data, use_passkit_email=True)
            results.append({
                "product": product_name,
                "result": result
            })
    
    # Return summary
    successful = sum(1 for r in results if r["result"]["success"])
    total = len(results)
    
    return jsonify({
        "success": True,
        "message": f"Processed {successful}/{total} membership products",
        "order_id": payload.get('orderId', ''),
        "customer_email": customer_email,
        "results": [
            {
                "product": r["product"],
                "success": r["result"]["success"],
                "member_id": r["result"].get("member_id"),
                "already_exists": r["result"].get("already_exists", False),
                "error": r["result"].get("error")
            }
            for r in results
        ]
    }), 200

def extract_membership_type(product_name):
    """Extract membership type from product name."""
    product_lower = product_name.lower()
    
    if "premium" in product_lower:
        return "Premium"
    elif "standard" in product_lower:
        return "Standard"
    elif "family" in product_lower:
        return "Family"
    else:
        return "Standard"

# Legacy function - kept for compatibility but not used for e-commerce orders
def handle_multiple_memberships(payload):
    """Handle multiple memberships in one transaction (legacy form-based)."""
    from squarespace_to_passkit import process_multiple_memberships
    
    # Extract transaction data
    transaction_data = {
        "transaction_id": payload.get('transactionId', f"txn_{int(datetime.now().timestamp())}"),
        "customer_email": payload.get('customerEmail', ''),
        "members": []
    }
    
    # Process each member
    for member_form in payload.get('data', {}).get('members', []):
        member_data = {
            "email": member_form.get('email', ''),
            "first_name": member_form.get('firstName', ''),
            "last_name": member_form.get('lastName', ''),
            "phone": member_form.get('phone', ''),
            "membership_type": member_form.get('membershipType', 'Standard')
        }
        
        if member_data["email"]:
            transaction_data["members"].append(member_data)
        else:
            print(f"⚠️ Skipping member with no email address")
    
    if not transaction_data["members"]:
        return jsonify({"error": "No valid members provided"}), 400
    
    # Process the transaction
    result = process_multiple_memberships(transaction_data)
    
    return jsonify({
        "success": True,
        "message": f"Processed {len(result['results'])} members",
        "transaction_id": result["transaction_id"],
        "summary": result["summary"],
        "results": [
            {
                "email": r["member_data"]["email"],
                "success": r["success"],
                "member_id": r.get("member_id"),
                "already_exists": r.get("already_exists", False)
            }
            for r in result["results"]
        ]
    }), 200

@app.route('/webhook/test', methods=['GET', 'POST'])
def test_webhook():
    """Test endpoint to verify webhook is working."""
    return jsonify({
        "status": "Webhook endpoint is working",
        "timestamp": datetime.now().isoformat(),
        "method": request.method
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Squarespace to PassKit Webhook",
        "timestamp": datetime.now().isoformat()
    })

def main():
    """Run the webhook server."""
    print("🚀 Starting Squarespace to PassKit Webhook Server")
    print("=" * 50)
    print(f"📡 Webhook endpoint: http://localhost:5003/webhook/squarespace")
    print(f"🧪 Test endpoint: http://localhost:5003/webhook/test")
    print(f"❤️ Health check: http://localhost:5003/health")
    print()
    print("📝 To set up Squarespace webhook:")
    print("1. Go to Squarespace Settings > Advanced > Webhooks")
    print("2. Create new webhook with URL: http://your-domain.com/webhook/squarespace")
    print("3. Select 'Form Submission' as trigger")
    print("4. Choose your membership form")
    print()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5003, debug=False)

if __name__ == "__main__":
    main()
