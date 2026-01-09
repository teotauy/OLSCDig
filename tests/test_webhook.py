#!/usr/bin/env python3
"""
Test script for the Squarespace webhook.
Tests both single and multiple membership scenarios.
"""

import requests
import json
from datetime import datetime

# Test webhook URL (update this to your Render URL)
# WEBHOOK_URL = "http://localhost:5003/webhook/squarespace"  # Local testing
WEBHOOK_URL = "https://olsc-webhook.onrender.com/webhook/squarespace"  # Render URL

def test_membership_order():
    """Test membership order webhook."""
    print("🧪 Testing membership order webhook...")
    
    timestamp = int(datetime.now().timestamp())
    payload = {
        "orderId": f"order_{timestamp}",
        "customer": {
            "email": f"testuser{timestamp}@example.com",
            "firstName": "Test",
            "lastName": "User",
            "phone": "+1234567890"
        },
        "lineItems": [
            {
                "productName": "LFC Brooklyn 25/26 Membership",
                "quantity": 1,
                "variantName": "Standard Membership"
            }
        ],
        "createdOn": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_scarf_order():
    """Test non-membership order (should be ignored)."""
    print("🧪 Testing scarf order (should be ignored)...")
    
    timestamp = int(datetime.now().timestamp())
    payload = {
        "orderId": f"order_{timestamp}",
        "customer": {
            "email": f"testuser{timestamp}@example.com",
            "firstName": "Test",
            "lastName": "User"
        },
        "lineItems": [
            {
                "productName": "LFC Brooklyn Scarf",
                "quantity": 1,
                "variantName": "Red Scarf"
            }
        ],
        "createdOn": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        # Should return 200 but with "ignored" status
        return response.status_code == 200 and response.json().get("status") == "ignored"
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_multiple_memberships():
    """Test multiple memberships webhook."""
    print("\n🧪 Testing multiple memberships webhook...")
    
    timestamp = int(datetime.now().timestamp())
    payload = {
        "formName": "Family Membership",
        "transactionId": f"txn_{timestamp}",
        "customerEmail": "primary@example.com",
        "data": {
            "members": [
                {
                    "firstName": "John",
                    "lastName": "Smith",
                    "email": f"john{timestamp}@example.com",
                    "phone": "+1234567890",
                    "membershipType": "Standard"
                },
                {
                    "firstName": "Jane",
                    "lastName": "Smith",
                    "email": f"jane{timestamp}@example.com",
                    "phone": "+1234567891",
                    "membershipType": "Standard"
                }
            ]
        },
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_health_check():
    """Test health check endpoint."""
    print("\n❤️ Testing health check...")
    
    health_url = WEBHOOK_URL.replace('/webhook/squarespace', '/health')
    
    try:
        response = requests.get(health_url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Squarespace Webhook")
    print("=" * 40)
    
    # Test health check first
    health_ok = test_health_check()
    
    if not health_ok:
        print("\n❌ Health check failed. Is the webhook server running?")
        print("Run: python3 squarespace_webhook.py")
        return
    
    # Test webhook endpoints
    membership_ok = test_membership_order()
    scarf_ok = test_scarf_order()
    multiple_ok = test_multiple_memberships()
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    print(f"Health Check: {'✅' if health_ok else '❌'}")
    print(f"Membership Order: {'✅' if membership_ok else '❌'}")
    print(f"Scarf Order (ignored): {'✅' if scarf_ok else '❌'}")
    print(f"Multiple Memberships: {'✅' if multiple_ok else '❌'}")
    
    if all([health_ok, membership_ok, scarf_ok, multiple_ok]):
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed. Check the logs above.")

if __name__ == "__main__":
    main()
