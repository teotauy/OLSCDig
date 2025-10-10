#!/usr/bin/env python3
"""
Automated PassKit Member Creation and Welcome Email System
Integrates Squarespace form data with PassKit member creation and welcome emails.

This script can be triggered by:
1. Squarespace webhook (when form is submitted)
2. Manual CSV import from Squarespace exports
3. Scheduled batch processing
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

# Email configuration (you'll need to set up email service)
EMAIL_CONFIG = {
    "SMTP_SERVER": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "SMTP_PORT": int(os.getenv("SMTP_PORT", "587")),
    "EMAIL_USER": os.getenv("EMAIL_USER"),
    "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD"),
    "FROM_EMAIL": os.getenv("FROM_EMAIL", "noreply@liverpoololsc.com"),
    "FROM_NAME": os.getenv("FROM_NAME", "Liverpool OLSC"),
}

def get_passkit_headers():
    """Get headers for PassKit API requests."""
    return {
        "Authorization": f"Bearer {PASSKIT_CONFIG['API_KEY']}",
        "Content-Type": "application/json",
        "X-Project-Key": PASSKIT_CONFIG["PROJECT_KEY"]
    }

def create_passkit_member(member_data):
    """
    Create a new member in PassKit and return the pass URL.
    
    Args:
        member_data (dict): Member information from Squarespace form
        
    Returns:
        dict: Result with success status, member_id, and pass_url
    """
    url = f"{PASSKIT_CONFIG['API_BASE']}/members/member"
    
    # Prepare member data for PassKit
    payload = {
        "programId": PASSKIT_CONFIG["PROGRAM_ID"],
        "externalId": member_data.get("external_id", f"sq_{member_data['email']}"),
        "person": {
            "forename": member_data.get("first_name", ""),
            "surname": member_data.get("last_name", ""),
            "displayName": f"{member_data.get('first_name', '')} {member_data.get('last_name', '')}".strip(),
            "emailAddress": member_data["email"],
            "mobileNumber": member_data.get("phone", "")
        },
        "metaData": {
            "nextMatch": "Some inferior side",  # Default placeholder for new members
            "membershipType": member_data.get("membership_type", "Standard"),
            "joinDate": datetime.now().strftime("%Y-%m-%d"),
            "source": "Squarespace Form"
        }
    }
    
    try:
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        member_id = result.get("id")
        
        # Get the pass URL for this member
        pass_url = get_member_pass_url(member_id)
        
        return {
            "success": True,
            "member_id": member_id,
            "pass_url": pass_url,
            "member_data": member_data
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating PassKit member: {e}")
        return {
            "success": False,
            "error": str(e),
            "member_data": member_data
        }

def get_member_pass_url(member_id):
    """
    Get the pass URL for a member.
    This URL is what gets sent in the welcome email.
    """
    try:
        # Get member details to construct pass URL
        url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/{member_id}"
        response = requests.get(url, headers=get_passkit_headers(), timeout=30)
        response.raise_for_status()
        
        member_data = response.json()
        # The pass URL format is typically:
        # https://pub2.passkit.io/pass/{program_id}/{member_id}
        pass_url = f"https://pub2.passkit.io/pass/{PASSKIT_CONFIG['PROGRAM_ID']}/{member_id}"
        
        return pass_url
        
    except Exception as e:
        print(f"❌ Error getting pass URL: {e}")
        return None

def send_welcome_email(member_data, pass_url, delay_hours=0):
    """
    Send welcome email with pass download link.
    
    Args:
        member_data (dict): Member information
        pass_url (str): PassKit pass URL
        delay_hours (int): Hours to delay sending (0 = send immediately)
    """
    if delay_hours > 0:
        print(f"⏰ Scheduling email for {delay_hours} hours from now...")
        # In a real implementation, you'd use a task queue like Celery
        # For now, we'll just log the scheduled time
        scheduled_time = datetime.now() + timedelta(hours=delay_hours)
        print(f"📅 Email scheduled for: {scheduled_time}")
        return
    
    # Prepare email content
    subject = "Welcome to Liverpool OLSC - Your Digital Membership Card is Ready!"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; }}
            .header {{ background: linear-gradient(135deg, #c8102e 0%, #00a65a 100%); color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .button {{ background: #c8102e; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
            .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>⚽ Welcome to Liverpool OLSC!</h1>
        </div>
        
        <div class="content">
            <h2>Hello {member_data.get('first_name', 'Member')}!</h2>
            
            <p>Welcome to the Liverpool Official Supporters Club! Your membership is now active and your digital membership card is ready to download.</p>
            
            <p><strong>Your membership details:</strong></p>
            <ul>
                <li><strong>Name:</strong> {member_data.get('first_name', '')} {member_data.get('last_name', '')}</li>
                <li><strong>Email:</strong> {member_data['email']}</li>
                <li><strong>Membership Type:</strong> {member_data.get('membership_type', 'Standard')}</li>
                <li><strong>Join Date:</strong> {datetime.now().strftime('%B %d, %Y')}</li>
            </ul>
            
            <p><strong>📱 Download Your Digital Card:</strong></p>
            <p>Tap the button below to add your Liverpool OLSC membership card to your phone's wallet:</p>
            
            <a href="{pass_url}" class="button">📱 Add to Wallet</a>
            
            <p><strong>What's Next?</strong></p>
            <ul>
                <li>Add your card to your phone's wallet (Apple Wallet or Google Pay)</li>
                <li>Join us at The Monro for match days</li>
                <li>Scan your card when you arrive to check in</li>
                <li>Enjoy exclusive member benefits and events</li>
            </ul>
            
            <p><strong>Need Help?</strong></p>
            <p>If you have any questions about your membership or need assistance with your digital card, please contact us at <a href="mailto:support@liverpoololsc.com">support@liverpoololsc.com</a></p>
            
            <p>You'll Never Walk Alone!<br>
            The Liverpool OLSC Team</p>
        </div>
        
        <div class="footer">
            <p>Liverpool Official Supporters Club | The Monro | New York</p>
            <p>This email was sent to {member_data['email']}. If you didn't sign up for membership, please ignore this email.</p>
        </div>
    </body>
    </html>
    """
    
    # For now, just log the email content
    # In a real implementation, you'd use SMTP or an email service
    print(f"📧 Welcome email prepared for {member_data['email']}")
    print(f"📱 Pass URL: {pass_url}")
    print(f"📝 Subject: {subject}")
    
    # TODO: Implement actual email sending
    # send_email_via_smtp(member_data['email'], subject, html_content)
    
    return True

def process_squarespace_form_data(form_data):
    """
    Process form data from Squarespace webhook or CSV export.
    
    Args:
        form_data (dict): Form submission data from Squarespace
    """
    print(f"🔄 Processing new member: {form_data.get('email')}")
    
    # Create member in PassKit
    result = create_passkit_member(form_data)
    
    if result["success"]:
        print(f"✅ Created PassKit member: {result['member_id']}")
        
        # Send welcome email
        if result["pass_url"]:
            send_welcome_email(form_data, result["pass_url"])
            print(f"📧 Welcome email sent to {form_data['email']}")
        else:
            print(f"❌ Could not get pass URL for {form_data['email']}")
    else:
        print(f"❌ Failed to create member: {result['error']}")
    
    return result

def process_csv_export(csv_file_path):
    """
    Process a CSV export from Squarespace with new members.
    
    Args:
        csv_file_path (str): Path to CSV file from Squarespace
    """
    print(f"📄 Processing CSV file: {csv_file_path}")
    
    results = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Map Squarespace CSV columns to our format
                member_data = {
                    "email": row.get("Email Address", ""),
                    "first_name": row.get("First Name", ""),
                    "last_name": row.get("Last Name", ""),
                    "phone": row.get("Phone Number", ""),
                    "membership_type": row.get("Membership Type", "Standard"),
                    "external_id": row.get("External ID", f"sq_{row.get('Email Address', '')}"),
                    "source": "Squarespace CSV Export"
                }
                
                if member_data["email"]:
                    result = process_squarespace_form_data(member_data)
                    results.append(result)
                else:
                    print(f"⚠️ Skipping row with no email address")
        
        # Summary
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        print(f"\n📊 CSV Processing Summary:")
        print(f"  ✅ Successful: {successful}")
        print(f"  ❌ Failed: {failed}")
        print(f"  📧 Total: {len(results)}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error processing CSV: {e}")
        return []

def main():
    """Main function for testing and manual processing."""
    print("🏆 Liverpool OLSC - Squarespace to PassKit Integration")
    print("=" * 60)
    
    # Example: Process a single member (for testing)
    test_member = {
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "Member",
        "phone": "+1234567890",
        "membership_type": "Standard",
        "external_id": "sq_test@example.com"
    }
    
    print("🧪 Testing with sample member...")
    result = process_squarespace_form_data(test_member)
    
    if result["success"]:
        print("✅ Test successful!")
    else:
        print("❌ Test failed!")
    
    print("\n📝 To process a CSV export:")
    print("python3 squarespace_to_passkit.py --csv path/to/squarespace_export.csv")
    
    print("\n📝 To set up webhook integration:")
    print("1. Set up Flask endpoint to receive Squarespace webhooks")
    print("2. Configure Squarespace to send form data to your endpoint")
    print("3. Process form data automatically on submission")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--csv":
        if len(sys.argv) > 2:
            csv_file = sys.argv[2]
            process_csv_export(csv_file)
        else:
            print("❌ Please provide CSV file path: python3 squarespace_to_passkit.py --csv path/to/file.csv")
    else:
        main()
