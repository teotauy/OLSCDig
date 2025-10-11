# 📱 Pushover Setup Guide

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
- **Every 10 minutes:** Current headcount (only if count changed)
- **Smart sounds:** Different sounds based on crowd size
- **Priority alerts:** High priority when pub is packed (20+ people)

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
@reboot cd /Users/colbyblack/DigID && python3 notifications.py &
```

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
- Script only sends updates when headcount changes
- Adjust the 10-minute interval in the code if needed

## Integration with Phase 1

This runs **alongside** your existing Flask app:
- **Flask app:** Web interface + bulk checkout (Phase 1)
- **Notifications:** Automatic updates + text commands (Phase 2)

Both work independently - if notifications break, your web app still works!

---

**🔴⚽ Get your API token and you're ready to go!**
