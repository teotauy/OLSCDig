# 🔧 Environment Variable Update Instructions

This guide walks you through updating your environment variables after the security fixes.

---

## 📋 What Changed

We removed hardcoded API keys from the code. You now need to set these in your environment:

1. **`FOOTBALL_DATA_API_KEY`** - For `match_updates.py` (was hardcoded)
2. **`PUSHOVER_USER_KEY`** - For `notifications.py` (was hardcoded)
3. **`PUSHOVER_API_TOKEN`** - Already in your `.env` ✅

---

## 🖥️ Part 1: Update Local `.env` File

### Step 1: Open your `.env` file

```bash
cd /Users/colbyblack/DigID
nano .env
# or use your preferred editor (VS Code, vim, etc.)
```

### Step 2: Add the missing variable

Your `.env` already has:
- ✅ `FOOTBALL_DATA_API_KEY=7e9f8206e9db47fa8a4b15b783a7543b`
- ✅ `PUSHOVER_API_TOKEN=atxyjoykhphqyng39p98qgivyccm8j`

**Add this line** (the Pushover user key that was previously hardcoded):

```
PUSHOVER_USER_KEY=uxsqmcnqrjzzsy82uaogdjctczyvix
```

### Step 3: Your complete `.env` should look like this:

```
PASSKIT_API_KEY=QHxrhw8Wi2T6W5lvN1ZxK35BYqvX6ynYnPvSbDaV36dYkczgwWCkKckDPtlRoq4VlC5f-M9vn4wVJejSqVOKEqFkrYJ2P6M2W7UtxH-mOnD5RBBjwCjmNuPGUGYQDwMFKogg08Su2eE-1PzKGipfslEkxRH078J4e0XFWRzfZc7jmLXBHYr47UNy0JLM4kmQPbktsK-nQdGvunwStmxyAIie6lKcjnVHw8L61tyL6nAsO1VsclmHe5UG5ImB3XD2Xl5naggXBjEz1p74k5lO85VovN1y9IEI6s5m-Rh_WZXVB3-BEV6Ft5xEKTHpHlqB
PASSKIT_PROJECT_KEY=f94c829556448ba780034221a0aa0a9c9a208792cfa20fa1c4e3ad71612a3a33
PROGRAM_ID=3yyTsbqwmtXaiKZ5qWhqTP
API_BASE=https://api.pub2.passkit.io
TIMEZONE=America/New_York
PUSHOVER_API_TOKEN=atxyjoykhphqyng39p98qgivyccm8j
FOOTBALL_DATA_API_KEY=7e9f8206e9db47fa8a4b15b783a7543b
PUSHOVER_USER_KEY=uxsqmcnqrjzzsy82uaogdjctczyvix
```

### Step 4: Test locally

```bash
# Test match updates
python3 match_updates.py

# Test notifications (if you run it)
python3 notifications.py
```

Both should work without errors now.

---

## ☁️ Part 2: Update Render Dashboard

### Step 1: Go to Render Dashboard

1. Open https://dashboard.render.com
2. Log in if needed
3. Click on your **`olsc-web-app`** service (or whatever you named it)

### Step 2: Navigate to Environment

1. In the left sidebar, click **"Environment"**
2. You'll see a list of your current environment variables

### Step 3: Add the new variables

**Only add these if you run the scripts on Render:**

#### If you run `match_updates.py` on Render (cron job or scheduled task):

1. Click **"Add Environment Variable"** (or **"Add"** button)
2. **Key:** `FOOTBALL_DATA_API_KEY`
3. **Value:** `7e9f8206e9db47fa8a4b15b783a7543b`
4. Click **"Save Changes"**

#### If you run `notifications.py` on Render:

1. Click **"Add Environment Variable"**
2. **Key:** `PUSHOVER_USER_KEY`
3. **Value:** `uxsqmcnqrjzzsy82uaogdjctczyvix`
4. Click **"Save Changes"**

3. Click **"Add Environment Variable"** again
4. **Key:** `PUSHOVER_API_TOKEN`
5. **Value:** `atxyjoykhphqyng39p98qgivyccm8j`
6. Click **"Save Changes"**

### Step 4: Verify your Render environment variables

After adding, your Render Environment tab should show:

**Required (always needed):**
- ✅ `PROGRAM_ID` = `3yyTsbqwmtXaiKZ5qWhqTP`
- ✅ `PASSKIT_API_KEY` = (your long key)
- ✅ `PASSKIT_PROJECT_KEY` = `f94c829556448ba780034221a0aa0a9c9a208792cfa20fa1c4e3ad71612a3a33`
- ✅ `ADMIN_PASSWORD` = (your password)
- ✅ `FLASK_SECRET_KEY` = (your secret key)

**Optional (if you use them):**
- ✅ `API_BASE` = `https://api.pub2.passkit.io` (if set)
- ✅ `TIMEZONE` = `America/New_York` (if set)
- ✅ `SESSION_COOKIE_SECURE` = `true` (if set)
- ✅ `CHECKOUT_REPORT_EMAIL` = (if set)
- ✅ `SMTP_*` variables (if set)

**New (only if you run scripts on Render):**
- ✅ `FOOTBALL_DATA_API_KEY` = `7e9f8206e9db47fa8a4b15b783a7543b` (if match updates run on Render)
- ✅ `PUSHOVER_USER_KEY` = `uxsqmcnqrjzzsy82uaogdjctczyvix` (if notifications run on Render)
- ✅ `PUSHOVER_API_TOKEN` = `atxyjoykhphqyng39p98qgivyccm8j` (if notifications run on Render)

### Step 5: Render will auto-redeploy

After you save environment variables, Render automatically redeploys your service. Wait for the deploy to finish (usually 1-2 minutes).

---

## ✅ Verification Checklist

### Local (.env)
- [ ] `FOOTBALL_DATA_API_KEY` is set
- [ ] `PUSHOVER_USER_KEY` is set
- [ ] `PUSHOVER_API_TOKEN` is set
- [ ] `match_updates.py` runs without errors
- [ ] `notifications.py` runs without errors (if you use it)

### Render Dashboard
- [ ] Logged into Render dashboard
- [ ] Found your `olsc-web-app` service
- [ ] Opened Environment tab
- [ ] Added `FOOTBALL_DATA_API_KEY` (if match updates run on Render)
- [ ] Added `PUSHOVER_USER_KEY` (if notifications run on Render)
- [ ] Added `PUSHOVER_API_TOKEN` (if notifications run on Render)
- [ ] Saved changes
- [ ] Waited for redeploy to complete

---

## 🚨 Important Notes

### Do I need to add these to Render?

**Only if you run these scripts on Render:**

- **`FOOTBALL_DATA_API_KEY`** → Only needed if `match_updates.py` runs on Render (e.g., via cron job)
- **`PUSHOVER_USER_KEY`** → Only needed if `notifications.py` runs on Render
- **`PUSHOVER_API_TOKEN`** → Only needed if `notifications.py` runs on Render

**If you run these scripts locally only**, you don't need to add them to Render.

### What if I don't run these scripts on Render?

If you only run `match_updates.py` and `notifications.py` locally (on your computer), you **don't need to add** `FOOTBALL_DATA_API_KEY` or `PUSHOVER_*` to Render. The web app (`app.py`) doesn't use these variables.

---

## 🆘 Troubleshooting

### "FOOTBALL_DATA_API_KEY is not set in environment"

**Local:** Make sure `.env` has `FOOTBALL_DATA_API_KEY=...` and you're running the script from the project directory.

**Render:** Make sure you added it to the Environment tab and the service redeployed.

### Pushover notifications not working

**Local:** Check that both `PUSHOVER_USER_KEY` and `PUSHOVER_API_TOKEN` are in `.env`.

**Render:** Check that both are in the Environment tab.

### Render service won't start

- Check Render logs: Dashboard → Your Service → Logs
- Verify all required variables are set (see checklist above)
- Make sure there are no typos in variable names or values

---

## 📝 Quick Reference

### Local `.env` (always needed for local scripts)

```bash
FOOTBALL_DATA_API_KEY=7e9f8206e9db47fa8a4b15b783a7543b
PUSHOVER_USER_KEY=uxsqmcnqrjzzsy82uaogdjctczyvix
PUSHOVER_API_TOKEN=atxyjoykhphqyng39p98qgivyccm8j
```

### Render Environment (only if scripts run on Render)

| Variable | Value | When to Add |
|----------|-------|-------------|
| `FOOTBALL_DATA_API_KEY` | `7e9f8206e9db47fa8a4b15b783a7543b` | If `match_updates.py` runs on Render |
| `PUSHOVER_USER_KEY` | `uxsqmcnqrjzzsy82uaogdjctczyvix` | If `notifications.py` runs on Render |
| `PUSHOVER_API_TOKEN` | `atxyjoykhphqyng39p98qgivyccm8j` | If `notifications.py` runs on Render |

---

## ✨ Done!

Once you've updated both local `.env` and Render (if needed), you're all set. The security fixes are complete, and your API keys are now properly stored in environment variables instead of hardcoded in the source code.
