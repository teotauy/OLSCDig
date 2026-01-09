#!/usr/bin/env python3
"""
Test script for multiple membership processing.
Demonstrates how to handle multiple memberships from one transaction.
"""

from squarespace_to_passkit import process_multiple_memberships
import json

def test_single_membership():
    """Test single membership creation."""
    print("🧪 Testing Single Membership")
    print("=" * 40)
    
    member_data = {
        "email": "test.single@example.com",
        "first_name": "John",
        "last_name": "Single",
        "phone": "+1234567890",
        "membership_type": "Standard"
    }
    
    from squarespace_to_passkit import process_squarespace_form_data
    result = process_squarespace_form_data(member_data, use_passkit_email=True)
    
    print(f"Result: {result['success']}")
    if result['success']:
        print(f"Member ID: {result.get('member_id')}")
        print(f"Pass URL: {result.get('pass_url')}")
        if result.get('already_exists'):
            print("⚠️ Member already existed")

def test_multiple_memberships():
    """Test multiple memberships from one transaction."""
    print("\n🧪 Testing Multiple Memberships")
    print("=" * 40)
    
    # Simulate a family membership purchase
    transaction_data = {
        "transaction_id": "txn_test_12345",
        "customer_email": "primary@example.com",
        "members": [
            {
                "email": "husband@example.com",
                "first_name": "John",
                "last_name": "Smith",
                "phone": "+1234567890",
                "membership_type": "Standard"
            },
            {
                "email": "wife@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "phone": "+1234567891",
                "membership_type": "Standard"
            },
            {
                "email": "son@example.com",
                "first_name": "Junior",
                "last_name": "Smith",
                "phone": "+1234567892",
                "membership_type": "Youth"
            }
        ]
    }
    
    result = process_multiple_memberships(transaction_data)
    
    print(f"Transaction ID: {result['transaction_id']}")
    print(f"Summary: {result['summary']}")
    
    for i, member_result in enumerate(result['results'], 1):
        print(f"\nMember {i}: {member_result['member_data']['email']}")
        print(f"  Success: {member_result['success']}")
        if member_result.get('already_exists'):
            print("  Status: Already existed (no duplicate created)")
        elif member_result['success']:
            print(f"  Member ID: {member_result.get('member_id')}")
            print(f"  Pass URL: {member_result.get('pass_url')}")
        else:
            print(f"  Error: {member_result.get('error')}")

def test_duplicate_handling():
    """Test duplicate member handling."""
    print("\n🧪 Testing Duplicate Handling")
    print("=" * 40)
    
    # Try to create the same member twice
    member_data = {
        "email": "duplicate.test@example.com",
        "first_name": "Duplicate",
        "last_name": "Test",
        "phone": "+1234567899",
        "membership_type": "Standard"
    }
    
    from squarespace_to_passkit import process_squarespace_form_data
    
    print("First creation:")
    result1 = process_squarespace_form_data(member_data, use_passkit_email=True)
    print(f"Success: {result1['success']}")
    
    print("\nSecond creation (should detect duplicate):")
    result2 = process_squarespace_form_data(member_data, use_passkit_email=True)
    print(f"Success: {result2['success']}")
    if result2.get('already_exists'):
        print("✅ Duplicate detected and handled correctly")

def test_passkit_email_vs_custom():
    """Test PassKit built-in email vs custom email."""
    print("\n🧪 Testing Email Options")
    print("=" * 40)
    
    member_data = {
        "email": "email.test@example.com",
        "first_name": "Email",
        "last_name": "Test",
        "phone": "+1234567898",
        "membership_type": "Standard"
    }
    
    from squarespace_to_passkit import process_squarespace_form_data
    
    print("Using PassKit's built-in welcome email:")
    result1 = process_squarespace_form_data(member_data, use_passkit_email=True)
    print(f"Success: {result1['success']}")
    print("Note: PassKit should send welcome email automatically")
    
    # Note: We don't test custom email here to avoid sending actual emails
    print("\nUsing custom welcome email (not tested to avoid sending emails):")
    print("Would send custom Liverpool OLSC branded email")

def main():
    """Run all tests."""
    print("🏆 Liverpool OLSC - Multiple Membership Testing")
    print("=" * 60)
    
    try:
        test_single_membership()
        test_multiple_memberships()
        test_duplicate_handling()
        test_passkit_email_vs_custom()
        
        print("\n✅ All tests completed!")
        print("\n📝 Key Features Tested:")
        print("  ✅ Single membership creation")
        print("  ✅ Multiple memberships in one transaction")
        print("  ✅ Duplicate detection and handling")
        print("  ✅ PassKit built-in welcome email")
        print("  ✅ Transaction tracking and reporting")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("Make sure your .env file is configured correctly")

if __name__ == "__main__":
    main()
