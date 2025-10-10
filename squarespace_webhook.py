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
WEBHOOK_SECRET = os.getenv("SQUARESPACE_WEBHOOK_SECRET")

@app.route('/webhook/squarespace', methods=['POST'])
def handle_squarespace_webhook():
    """
    Handle form submissions from Squarespace.
    
    Expected payload format from Squarespace:
    {
        "formName": "Membership Application",
        "data": {
            "firstName": "John",
            "lastName": "Smith",
            "email": "john@example.com",
            "phone": "+1234567890",
            "membershipType": "Premium"
        },
        "timestamp": "2025-01-09T14:30:00Z"
    }
    """
    try:
        # Get the webhook payload
        payload = request.get_json()
        
        if not payload:
            return jsonify({"error": "No payload received"}), 400
        
        print(f"📨 Received webhook: {payload.get('formName', 'Unknown Form')}")
        
        # Extract form data
        form_data = payload.get('data', {})
        
        if not form_data.get('email'):
            return jsonify({"error": "No email address provided"}), 400
        
        # Map Squarespace form fields to our format
        member_data = {
            "email": form_data.get('email', ''),
            "first_name": form_data.get('firstName', ''),
            "last_name": form_data.get('lastName', ''),
            "phone": form_data.get('phone', ''),
            "membership_type": form_data.get('membershipType', 'Standard'),
            "external_id": f"sq_{form_data.get('email', '')}",
            "source": "Squarespace Webhook",
            "submission_time": payload.get('timestamp', datetime.now().isoformat())
        }
        
        # Process the member
        result = process_squarespace_form_data(member_data)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": "Member created successfully",
                "member_id": result["member_id"],
                "pass_url": result["pass_url"]
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Failed to create member",
                "error": result["error"]
            }), 500
            
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

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
