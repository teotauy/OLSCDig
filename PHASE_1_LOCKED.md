# 🔒 PHASE 1 - LOCKED AND WORKING

**Status:** ✅ TESTED AND VERIFIED  
**Date:** October 9, 2025  
**Git Tag:** `phase-1-working`  
**Git Commit:** `e35a064`

---

## What Works

### ✅ Web Interface
- **URL:** http://localhost:5001 (or http://192.168.1.174:5001 on phone)
- **Features:**
  - Real-time headcount display
  - Auto-refresh every 60 seconds
  - Football pitch countdown animation (⚽ → 🥅)
  - One-click bulk checkout button
  - Mobile-friendly Liverpool-themed design

### ✅ Bulk Checkout
- **Tested:** Successfully checked out all 28 members
- **Verified:** CSV export from PassKit confirmed all members CHECKED_OUT
- **Speed:** Takes a few seconds (processes each member via API)
- **Confirmation:** Browser popup prevents accidental clicks

### ✅ API Integration
- **Server:** https://api.pub2.passkit.io (USA server, not EU)
- **Authentication:** Bearer token + X-Project-Key header
- **Response Format:** NDJSON (newline-delimited JSON)
- **Key Fix:** Uses `memberId` not `id` in checkout payload

---

## Files (Phase 1)

### Production
- `app.py` - Flask web application
- `checkout.py` - Command-line bulk checkout
- `templates/index.html` - Mobile web interface
- `.env` - API credentials (configured for pub2)
- `requirements.txt` - Python dependencies

### Testing
- `test_connection.py` - API health check
- `test_both_servers.py` - Test pub1 vs pub2
- `test_checkout_format.py` - Test payload formats
- `test_filter.py` - Test filter fields
- `test_pub2_response.py` - Response debugging

### Documentation
- `README.md` - Main documentation
- `SUCCESS.md` - Setup story and technical details
- `PHASE_1_LOCKED.md` - This file

---

## How to Start

```bash
cd /Users/colbyblack/DigID
python3 -m flask --app app run --host 0.0.0.0 --port 5001
```

Then open: http://localhost:5001

## How to Stop

```bash
pkill -f flask
```

---

## Emergency Rollback

If Phase 2 breaks things, run:

```bash
./ROLLBACK_TO_PHASE1.sh
```

Or manually:

```bash
git reset --hard phase-1-working
```

---

## What Phase 1 Does

1. **During Events:**
   - Members check in using PassKit Pass Reader app
   - Status changes to CHECKED_IN
   - Headcount page shows live count
   - Updates every 60 seconds

2. **After Events:**
   - Open web page
   - Click "Check Out Everyone" button
   - Wait a few seconds
   - All members changed to CHECKED_OUT
   - Verified in PassKit dashboard

---

## Key Learnings

### What Didn't Work
- ❌ `api.pub1.passkit.io` (EU server - wrong region)
- ❌ GET requests (API uses POST)
- ❌ Regular JSON parsing (API returns NDJSON)
- ❌ `{"id": memberId}` payload (needs `memberId` key)
- ❌ `filterField: "passStatus"` (field is just "status")

### What Works
- ✅ `api.pub2.passkit.io` (USA server)
- ✅ POST requests with filter payloads
- ✅ NDJSON parsing (one JSON object per line)
- ✅ `{"memberId": memberId}` payload
- ✅ `filterField: "status"` with value "CHECKED_IN"

---

## Phase 2 Ideas (Future)

- [ ] Automatic midnight checkout (cron job or GitHub Actions)
- [ ] Individual member checkout (not just bulk)
- [ ] Attendance analytics and reports
- [ ] Email/SMS notifications
- [ ] Cloud deployment (Heroku/Railway/Fly.io)
- [ ] Authentication/login
- [ ] GitHub Pages static version

**DO NOT START PHASE 2 UNTIL THIS IS CONFIRMED LOCKED!**

---

🔴⚽ **Phase 1 is rock solid. You'll Never Walk Alone!**

