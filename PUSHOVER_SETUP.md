# 📱 Pushover Setup Guide

## 🚀 Quick Start Options

**Option A: Run on Your Laptop** (see below)  
**Option B: Deploy to Cloud** (recommended - runs 24/7) → See [Cloud Deployment Guide](CLOUD_NOTIFICATIONS_DEPLOYMENT.md)

## What You Have

✅ **User Key:** `uxsqmcnqrjzzsy82uaogdjctczyvix` (already configured)  
❌ **API Token:** Need to create this

## Step 1: Create Pushover Application

1. Go to: https://pushover.net/apps/build
2. Fill out the form:
   - **Application Name:** `Liverpool OLSC`
   - **Description:** `Headcount notifications for Liverpool supporters club`
   - **Icon:** (optional - can upload Liverpool logo)
3. Click **Create Application**
4. Copy the **API Token** (looks like: `a1b2c3d4e5f6g7h8i9j0`)

## Step 2: Add to .env File

Add this line to your `.env` file:
```
PUSHOVER_API_TOKEN=your_api_token_here
```

## Step 3: Install Dependencies

```bash
pip install requests
```

## Step 4: Test It

```bash
python3 notifications.py
```

You should receive a test notification on your phone!

## Features

### Automatic Notifications
- **Every 1 minute:** Checks headcount (sends notification **only** if count changed)
- **Smart sounds:** Different sounds based on crowd size
- **Priority alerts:** High priority when pub is packed (20+ people)
- **Timestamps:** All notifications include the time

### Text Commands (Send via Pushover app)
- **`count`** → Current headcount
- **`list`** → List of checked-in members
- **`status`** → Detailed system status
- **`help`** → Show available commands

### Smart Notifications
- **0 people:** "No one checked in" (no sound)
- **1-9 people:** "X people at the pub" (default sound)
- **10-19 people:** "X people - getting busy!" (cosmic sound)
- **20+ people:** "X people - PACKED!" (siren + high priority)

## Running the System

### Option 1: Manual (for testing)
```bash
python3 notifications.py
```

### Option 2: Background (always running)
```bash
nohup python3 notifications.py &
```

### Option 3: Cron Job (automatic start)
Add to crontab (`crontab -e`):
```
@reboot cd /Users/colbyblack/DigID && python3 notifications.py > notifications.log 2>&1 &
```

### Option 4: Check if Running
Check if notifications are currently running:
```bash
# Check process status
ps aux | grep notifications.py

# Or use the status API
python3 status_api.py
```

**Important:** The script must be running continuously to catch check-ins. If it stops, you won't get notifications until you restart it.

### Preventing Laptop Sleep During Matches

**If your laptop goes to sleep, the script stops and won't catch check-ins!**

**On Mac (recommended):**
```bash
# Prevent sleep while running notifications (keeps Mac awake)
caffeinate -d python3 notifications.py
```

Or run both in background:
```bash
caffeinate -d nohup python3 notifications.py > notifications.log 2>&1 &
```

**Alternative: System Settings**
1. **System Settings** → **Battery** (or **Energy Saver** on older Macs)
2. When plugged in: Set "Prevent automatic sleeping" or increase sleep timer
3. Or use **Amphetamine** app (free on Mac App Store) to keep Mac awake

**On Windows:**
- **Settings** → **System** → **Power & Sleep**
- Set "When plugged in, PC goes to sleep after: Never"
- Or use `powercfg /change standby-timeout-ac 0` in Command Prompt (as admin)

**Quick Match Day Solution:**
Just before the match, run:
```bash
caffeinate -d python3 notifications.py
```
This keeps your Mac awake while the script runs. Press Ctrl+C when done.

## Troubleshooting

### No notifications received?
1. Check Pushover app is installed and logged in
2. Verify API token in `.env` file
3. Test with: `python3 notifications.py`

### API token issues?
1. Double-check token from https://pushover.net/apps
2. Make sure it's added to `.env` file
3. Restart the script

### Too many notifications?
- Script only sends notifications when headcount changes
- Adjust intervals in the code if needed

### Notifications not catching all check-ins?
**Common issues:**
1. **Script not running** - The script must be running continuously to catch check-ins
   - Check if running: `ps aux | grep notifications.py`
   - Or use: `python3 status_api.py` and check the status
2. **Script crashed** - Check for error messages in the console
3. **Rapid check-ins** - If multiple people check in within 1 minute, you'll get one notification with the final count
4. **Network issues** - Script logs errors if it can't connect to PassKit API

**To ensure it's always running:**
- Use `nohup` or a process manager (see Option 2 above)
- Set up a cron job to auto-start on reboot (see Option 3 above)
- Check periodically that it's still running

**Recent improvements (January 2025):**
- ✅ Better logging with timestamps (console only)
- ✅ Timestamps added to notification messages
- ✅ More reliable error handling

## ☁️ Cloud Deployment (Recommended)

**Want it to run 24/7 without your laptop?** Deploy to the cloud!

See **[Cloud Notifications Deployment Guide](CLOUD_NOTIFICATIONS_DEPLOYMENT.md)** for:
- Render deployment (free tier available)
- Railway deployment
- Other cloud options
- Cost comparison

**Benefits:**
- ✅ Always running (no laptop needed)
- ✅ No sleep issues
- ✅ More reliable
- ✅ Free tier options available

## Integration with Phase 1

This runs **alongside** your existing Flask app:
- **Flask app:** Web interface + bulk checkout (Phase 1)
- **Notifications:** Automatic updates + text commands (Phase 2)

Both work independently - if notifications break, your web app still works!

---

**🔴⚽ Get your API token and you're ready to go!**
