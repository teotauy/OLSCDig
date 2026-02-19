# Liverpool OLSC - PassKit Integration System

> **Status**: ✅ **FULLY WORKING!**  
> **Last Updated**: January 2025  
> Complete automation from Squarespace to PassKit with real-time management

## What This Does

Complete Liverpool OLSC member management system:

1. **🛒 Squarespace → PassKit Automation** - New memberships automatically create PassKit members and send welcome emails
2. **👤 Web-Based Member Addition** - Add members through a secure web interface (password protected)
3. **📱 Scan members in** - Use PassKit Pass Reader app (changes status to `CHECKED_IN`)
4. **👀 View headcount** - See how many people are checked in (updates every 60 seconds)
5. **✅ Bulk checkout** - One button to check everyone out after a match
6. **⚽ Match Updates** - Automatic Liverpool FC fixture updates on all passes
7. **🔔 Push Notifications** - Real-time headcount updates via Pushover

## Quick Start

### Option 1: GitHub Pages Control Panel (Easiest)

Access the control panel from anywhere:
- **Control Panel**: https://teotauy.github.io/OLSCDig/control-panel.html
- **Read-only Headcount**: https://teotauy.github.io/OLSCDig/public/index.html

### Option 2: Web App (Render or local)

**Deployed (Render):** If you've deployed with the blueprint, use your Render URL (e.g. `https://olsc-web-app.onrender.com`). If you get 401 or "Error loading" on headcount, see [WEB_APP_DEPLOYMENT.md](WEB_APP_DEPLOYMENT.md#troubleshooting).

**Local:**
```bash
python3 app.py
```

Then open:
- **On your computer**: http://localhost:5000
- **On your phone**: http://[your-ip]:5000 (make sure you're on the same Wi-Fi)

**Features:**
- **Headcount Display** - Live count of checked-in members
- **Bulk Checkout** - Check everyone out with one click
- **Add Members** - Password-protected interface at `/add-member`

### Option 3: Command-Line

```bash
python3 checkout.py
```

Lists all checked-in members and checks them out after confirmation.

### Test Connection

```bash
python3 status_api.py
```

Verifies API is working and shows current member counts.

### Quick Add Members

**Option A: Web Interface (Recommended)**
1. Start the web app: `python3 app.py`
2. Go to http://localhost:5000/add-member
3. Log in with your password (set `ADMIN_PASSWORD` in `.env`), or use **Forgot password?** / **Sign in with Google** if configured (see [WEB_APP_DEPLOYMENT.md](WEB_APP_DEPLOYMENT.md#login--security))
4. Fill in the form and submit

**Option B: Command Line Script (edit list, then run)**

This is the standard way to add one or more members from your machine:

1. **Edit** `quick_add_members.py` and add people to the `MEMBERS` list (first name, last name, email, optional phone).
2. **Run** the script so it creates them in PassKit and triggers welcome emails:
   ```bash
   python3 quick_add_members.py
   ```
   The script skips anyone who already exists (by email) and reports how many were created vs already existed.

**Duplicate Prevention:**
- Automatically checks for existing members before creating
- Searches through the most recent 500 members by email (case-insensitive)
- Prevents duplicate member creation
- Skips welcome emails for existing members
- Perfect for clubs with a few hundred members

## How to Find Your Computer's IP

**On Mac:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}'
```

**On Windows:**
```bash
ipconfig
```

Look for your local IP (usually starts with 192.168.x.x or 10.x.x.x)

## Features

✅ **Squarespace → PassKit Automation** - New memberships auto-create PassKit members  
✅ **Real-Time Headcount** - Auto-refreshes every 60 seconds  
✅ **One-Click Checkout** - Bulk check out all members after a match  
✅ **Match Updates** - Automatic Liverpool FC fixture updates on passes  
✅ **Push Notifications** - Real-time headcount updates via Pushover  
✅ **Mobile-Optimized** - Beautiful Liverpool red & green design  
✅ **Fast & Reliable** - Direct PassKit API integration  
✅ **No Manual Work** - Fully automated from purchase to pass  

## Documentation

- **[🗺️ Feature Roadmap](ROADMAP.md)** - What’s done, optional, and planned
- **[📚 Complete Documentation](COMPREHENSIVE_README.md)** - Everything you need to know
- **[🌐 Web App on Render](WEB_APP_DEPLOYMENT.md)** - Deploy so you can use the app from your phone (and fix 401 / headcount "Error loading")
- **[⚽ Match Updates Setup](MATCH_UPDATES_SETUP.md)** - Update all passes with next match (CLI and web)
- **[⚽ Match Overrides](MATCH_OVERRIDES.md)** - FA Cup, League Cup, wrong times: when and how to edit `match_overrides.json`
- **[🛒 Squarespace Integration Setup](SQUARESPACE_INTEGRATION_SETUP.md)** - Automated member onboarding
- **[🔄 Backfill Missing Members Guide](BACKFILL_MISSING_MEMBERS_GUIDE.md)** - Process historical orders
- **[🎛️ Control Panel Deployment](CONTROL_PANEL_DEPLOYMENT.md)** - GitHub Pages setup
- **[🔔 Pushover Setup](PUSHOVER_SETUP.md)** - Notification system setup

## File Structure

```
.
├── app.py                    # Flask web app (START HERE)
├── checkout.py               # Command-line bulk checkout
├── quick_add_members.py      # Quick manual member addition tool
├── status_api.py             # Test API connection & system status
├── control-panel.html        # GitHub Pages control panel
├── COMPREHENSIVE_README.md   # Complete documentation
├── templates/
│   └── index.html           # Mobile-friendly web interface
├── .env                     # Your API credentials
└── README.md               # This file
```

## Configuration

Your `.env` file is already configured with:
- ✅ PassKit API Key
- ✅ PassKit Project Key
- ✅ Program ID: 3yyTsbqwmtXaiKZ5qWhqTP
- ✅ API Base: https://api.pub2.passkit.io (USA server)
- ✅ Timezone: America/New_York

## Usage Instructions

### After a Match

1. Open the web page on your phone
2. You'll see how many people are checked in
3. Tap the "Check Out Everyone" button
4. Confirm
5. Done! ✅

### Daily Headcount Monitoring

Just leave the page open on your phone or computer. It auto-refreshes every 60 seconds so you always know how many people are at the pub.

## Troubleshooting

### Can't access from phone

Make sure:
- Phone and computer are on same Wi-Fi
- Firewall isn't blocking port 5000
- Using your computer's IP, not "localhost"

### API errors (401, headcount "Error loading")

- **Local:** Run `python3 status_api.py` to diagnose. Should show total members and CHECKED_IN count.
- **Render (web app):** If you see "401 Unauthorized" or headcount "Error loading", set `PASSKIT_API_KEY` and `PASSKIT_PROJECT_KEY` in Render → olsc-web-app → Environment (same as your `.env`). See [WEB_APP_DEPLOYMENT.md](WEB_APP_DEPLOYMENT.md#troubleshooting).

### Need to restart

Just Ctrl+C to stop, then `python3 app.py` to restart.

## Future Enhancements

Want to make this even better? Here are some ideas:

1. **Auto Midnight Checkout** - Schedule automatic checkout at midnight
2. **Cloud Hosting** - Deploy to Heroku/Railway for 24/7 access
3. **Individual Checkout** - Check out specific members, not just everyone
4. **Analytics** - Track attendance over time
5. **Notifications** - Get alerts when capacity is reached

## Technical Details

- **Language**: Python 3
- **Web Framework**: Flask
- **API**: PassKit REST API (pub2 - USA server)
- **Response Format**: NDJSON (newline-delimited JSON)
- **Authentication**: Bearer token + Project Key header

## Support

Everything is working! If you need help:
1. Run `python3 status_api.py` to check API status
2. Check this README for troubleshooting
3. Contact PassKit support if API issues arise

---

**🏴󠁧󠁢󠁥󠁮󠁧󠁿 You'll Never Walk Alone! ⚽**
