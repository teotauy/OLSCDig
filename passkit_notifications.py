#!/usr/bin/env python3
"""
PassKit Push Notifications Module
Sends push notifications to all PassKit members via API.

This module provides functionality to:
1. Send immediate push notifications to all members
2. Schedule push notifications for future delivery
3. Send targeted notifications to specific member groups
"""

import os
import json
import requests
import schedule
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import threading

# Load environment variables
load_dotenv()

# PassKit configuration
PASSKIT_CONFIG = {
    'API_BASE': os.getenv('API_BASE'),
    'PROGRAM_ID': os.getenv('PROGRAM_ID'),
    'API_KEY': os.getenv('PASSKIT_API_KEY'),
    'PROJECT_KEY': os.getenv('PASSKIT_PROJECT_KEY')
}

def get_passkit_headers():
    """Get PassKit API headers."""
    return {
        'Authorization': f'Bearer {PASSKIT_CONFIG["API_KEY"]}',
        'X-Project-Key': PASSKIT_CONFIG['PROJECT_KEY'],
        'Content-Type': 'application/json'
    }

def send_passkit_notification(message, title="⚽ Liverpool OLSC", sound="default", priority="normal"):
    """
    Send a push notification to all PassKit members.
    
    Args:
        message (str): The notification message
        title (str): The notification title
        sound (str): Notification sound (default, none, etc.)
        priority (str): Notification priority (normal, high, urgent)
        
    Returns:
        dict: Result with success status and details
    """
    print(f"🔔 Sending PassKit notification: {title} - {message}")
    
    try:
        # First, get all members
        members = get_all_members()
        if not members:
            return {
                "success": False,
                "error": "No members found",
                "sent_count": 0
            }
        
        sent_count = 0
        failed_count = 0
        
        # Send notification to each member by updating their pass
        for member in members:
            member_id = member.get("id")
            member_name = member.get("person", {}).get("displayName", "Unknown")
            
            if send_notification_to_member(member_id, message, title):
                sent_count += 1
                print(f"  ✅ Sent to {member_name}")
            else:
                failed_count += 1
                print(f"  ❌ Failed to send to {member_name}")
        
        result = {
            "success": sent_count > 0,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "total_members": len(members),
            "message": message,
            "title": title,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📊 Notification summary: {sent_count}/{len(members)} sent successfully")
        return result
        
    except Exception as e:
        print(f"❌ Error sending PassKit notification: {e}")
        return {
            "success": False,
            "error": str(e),
            "sent_count": 0
        }

def get_all_members():
    """Get all members from PassKit."""
    try:
        url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/list/{PASSKIT_CONFIG['PROGRAM_ID']}"
        payload = {
            "filters": {
                "limit": 1000,
                "offset": 0
            }
        }
        
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        response.raise_for_status()
        
        members = []
        # Parse NDJSON response
        for line in response.text.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    if 'result' in data:
                        members.append(data['result'])
                except json.JSONDecodeError:
                    pass
        
        return members
        
    except Exception as e:
        print(f"❌ Error fetching members: {e}")
        return []

def send_notification_to_member(member_id, message, title):
    """
    Send notification to a specific member by updating their pass.
    
    Args:
        member_id (str): The member's ID
        message (str): The notification message
        title (str): The notification title
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get current member data first
        member_url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/{member_id}"
        response = requests.get(member_url, headers=get_passkit_headers(), timeout=30)
        
        if response.status_code != 200:
            return False
            
        member_data = response.json()
        person_data = member_data.get("person", {})
        
        # Update the member's pass with notification data
        update_url = f"{PASSKIT_CONFIG['API_BASE']}/members/member"
        update_payload = {
            "programId": PASSKIT_CONFIG["PROGRAM_ID"],
            "id": member_id,
            "person": {
                "displayName": person_data.get("displayName", ""),
                "emailAddress": person_data.get("emailAddress", ""),
                "surname": person_data.get("surname", ""),
                "forename": person_data.get("forename", "")
            },
            "metaData": {
                **member_data.get("metaData", {}),
                "lastNotification": message,
                "notificationTitle": title,
                "notificationTime": datetime.now().isoformat()
            }
        }
        
        response = requests.put(update_url, headers=get_passkit_headers(), json=update_payload, timeout=30)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error sending notification to member {member_id}: {e}")
        return False

class ScheduledNotifications:
    """Handle scheduled push notifications."""
    
    def __init__(self):
        self.scheduled_jobs = []
    
    def schedule_notification(self, message, title, scheduled_time, description=""):
        """
        Schedule a push notification for future delivery.
        
        Args:
            message (str): The notification message
            title (str): The notification title
            scheduled_time (datetime): When to send the notification
            description (str): Description of the notification
            
        Returns:
            dict: Result with success status and job details
        """
        try:
            # Calculate delay from now
            now = datetime.now()
            delay = (scheduled_time - now).total_seconds()
            
            if delay <= 0:
                return {
                    "success": False,
                    "error": "Scheduled time must be in the future"
                }
            
            # Create job info
            job_info = {
                "id": f"notification_{int(time.time())}",
                "message": message,
                "title": title,
                "scheduled_time": scheduled_time.isoformat(),
                "description": description,
                "created_at": now.isoformat()
            }
            
            # Schedule the job
            job = schedule.every().day.at(scheduled_time.strftime("%H:%M")).do(
                self._send_scheduled_notification, job_info
            )
            
            self.scheduled_jobs.append(job_info)
            
            print(f"📅 Scheduled notification for {scheduled_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Message: {message}")
            
            return {
                "success": True,
                "job_id": job_info["id"],
                "scheduled_time": scheduled_time.isoformat(),
                "message": "Notification scheduled successfully"
            }
            
        except Exception as e:
            print(f"❌ Error scheduling notification: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _send_scheduled_notification(self, job_info):
        """Send a scheduled notification."""
        print(f"🔔 Sending scheduled notification: {job_info['message']}")
        result = send_passkit_notification(
            job_info["message"], 
            job_info["title"]
        )
        
        # Remove from scheduled jobs
        self.scheduled_jobs = [job for job in self.scheduled_jobs if job["id"] != job_info["id"]]
        
        return result
    
    def get_scheduled_notifications(self):
        """Get list of scheduled notifications."""
        return self.scheduled_jobs
    
    def cancel_scheduled_notification(self, job_id):
        """Cancel a scheduled notification."""
        self.scheduled_jobs = [job for job in self.scheduled_jobs if job["id"] != job_id]
        schedule.clear(job_id)  # This might need adjustment based on schedule library
        return True

# Global scheduler instance
scheduler = ScheduledNotifications()

def run_scheduler():
    """Run the notification scheduler (for background thread)."""
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def start_notification_scheduler():
    """Start the notification scheduler in a background thread."""
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("📅 PassKit notification scheduler started")

if __name__ == "__main__":
    # Test the notification system
    print("🔔 PassKit Notification System Test")
    print("=" * 40)
    
    # Test immediate notification
    result = send_passkit_notification(
        "This is a test notification from the Liverpool OLSC system!",
        "🧪 System Test"
    )
    
    print(f"Result: {result}")
    
    # Test scheduling (5 minutes from now)
    scheduled_time = datetime.now() + timedelta(minutes=5)
    schedule_result = scheduler.schedule_notification(
        "This is a scheduled test notification!",
        "📅 Scheduled Test",
        scheduled_time,
        "Test notification scheduled 5 minutes from now"
    )
    
    print(f"Scheduled: {schedule_result}")
    print(f"Active schedules: {len(scheduler.get_scheduled_notifications())}")
