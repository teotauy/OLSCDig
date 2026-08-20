# 🚀 Complete Deployment Walkthrough

> **⚠️ ARCHIVED — historical, describes the old PassKit-vendor system.** The live system has since replaced PassKit entirely with a Supabase-backed member/pass/check-in system (Flask app on Render, Apple/Google Wallet passes signed and pushed by us, no PassKit dependency). See [SELF_HOSTED_WALLET_PLAN.md](SELF_HOSTED_WALLET_PLAN.md) for the current system, [README.md](README.md) for an overview, and [QA_VERIFICATION_PLAN.md](QA_VERIFICATION_PLAN.md) for current verification status. Kept here for historical reference only — do not follow these steps against the live system.

---


This guide will walk you through deploying your Liverpool OLSC PassKit system to the web.

## 📋 What You're Deploying

You have **two services** to deploy:

1. **Web App** (`app.py`) - Member management interface
   - Add members
   - Update match info
   - View headcount
   - Bulk checkout

2. **Webhook** (`squarespace_webhook.py`) - Automated member creation
   - Receives Squarespace order webhooks
   - Creates PassKit members automatically
   - Sends welcome emails

## 🎯 Option 1: Deploy to Render (Recommended)

Render is free and perfect for this use case. Your `render.yaml` is already configured!

### Step 1: Push Your Code to GitHub

First, commit and push your changes:

```bash
cd /Users/colbyblack/DigID

# Add all your changes
git add .

# Commit
git commit -m "Ready for deployment"

# Push to GitHub
git push origin main
```

### Step 2: Create Render Account

1. Go to [render.com](https://render.com)
2. Click **"Get Started"** or **"Sign Up"**
3. Sign up with your **GitHub account** (easiest way)
4. Authorize Render to access your repositories

### Step 3: Deploy Using Blueprint (Easiest)

1. In Render dashboard, click **"New +"** → **"Blueprint"**
2. Connect your GitHub repository: `teotauy/DigID` (or your repo name)
3. Render will detect your `render.yaml` file automatically
4. Click **"Apply"**

This will create **both services** at once!

### Step 4: Set Environment Variables

You need to configure environment variables for each service. Render will prompt you, or you can set them in the dashboard.

#### For `olsc-web-app` (Web App):

Go to the `olsc-web-app` service → **Environment** tab → Add these:

```
PROGRAM_ID=3yyTsbqwmtXaiKZ5qWhqTP
API_BASE=https://api.pub2.passkit.io
PASSKIT_API_KEY=your_api_key_here
PASSKIT_PROJECT_KEY=your_project_key_here
TIMEZONE=America/New_York
ADMIN_PASSWORD=your_secure_password_here
FLASK_SECRET_KEY=generate_random_key_here
```

**To generate FLASK_SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

#### For `olsc-webhook` (Webhook):

Go to the `olsc-webhook` service → **Environment** tab → Add these:

```
PASSKIT_PROGRAM_ID=3yyTsbqwmtXaiKZ5qWhqTP
PASSKIT_API_BASE=https://api.pub2.passkit.io
PASSKIT_API_KEY=your_api_key_here
PASSKIT_PROJECT_KEY=your_project_key_here
WEBHOOK_SECRET=your_random_secret_here
TIMEZONE=America/New_York
```

**To generate WEBHOOK_SECRET:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 5: Wait for Deployment

- Render will build and deploy both services
- This takes about 2-3 minutes
- Watch the logs to see progress
- You'll see URLs like:
  - `https://olsc-web-app.onrender.com`
  - `https://olsc-webhook.onrender.com`

### Step 6: Test Your Deployment

#### Test Web App:
1. Open `https://olsc-web-app.onrender.com` in your browser
2. You should see the landing page with headcount
3. Click **"+ Add Member"** or **"⚽ Update Match"**
4. Enter your `ADMIN_PASSWORD`
5. Test adding a member or updating match info

#### Test Webhook:
1. Open `https://olsc-webhook.onrender.com/health` in your browser
2. Should return: `{"status": "ok", "service": "olsc-webhook"}`

### Step 7: Configure Squarespace Webhook

1. Go to Squarespace → Settings → Advanced → Webhooks
2. Click **"Add Webhook"**
3. Configure:
   - **Event**: "Order Completed"
   - **URL**: `https://olsc-webhook.onrender.com/webhook/squarespace`
   - **Method**: POST
   - **Format**: JSON
4. Save

### Step 8: Bookmark Your URLs

- **Web App**: `https://olsc-web-app.onrender.com` (bookmark on your phone!)
- **Webhook**: `https://olsc-webhook.onrender.com` (for Squarespace)

## 🎯 Option 2: Deploy Webhook Only (If You Don't Need Web App)

If you only want automated member creation from Squarespace:

1. Follow Steps 1-2 above
2. In Render, click **"New +"** → **"Web Service"** (not Blueprint)
3. Connect your GitHub repo
4. Configure:
   - **Name**: `olsc-webhook`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 squarespace_webhook.py`
5. Set environment variables (see Step 4 above, webhook section)
6. Deploy!

## 🎯 Option 3: Run Locally (For Testing)

If you want to test before deploying:

```bash
cd /Users/colbyblack/DigID

# Set environment variables
export PROGRAM_ID="3yyTsbqwmtXaiKZ5qWhqTP"
export API_BASE="https://api.pub2.passkit.io"
export PASSKIT_API_KEY="your_key_here"
export PASSKIT_PROJECT_KEY="your_key_here"
export ADMIN_PASSWORD="test123"
export FLASK_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# Run the app
python3 app.py
```

Then open http://localhost:5000

## 🔒 Security Checklist

- ✅ Never commit `.env` file to Git
- ✅ Use strong `ADMIN_PASSWORD` (not "admin123")
- ✅ Generate random `FLASK_SECRET_KEY` and `WEBHOOK_SECRET`
- ✅ Keep your PassKit API keys secret
- ✅ Use HTTPS (Render provides this automatically)

## 💰 Cost

**Render Free Tier:**
- ✅ 750 hours/month free (enough for both services)
- ✅ Automatic SSL certificates
- ✅ Custom domain support
- ⚠️ Services spin down after 15 min inactivity (wake up automatically)

**Render Paid Tier ($7/month per service):**
- ✅ Always on (no spin-down)
- ✅ Faster response times
- ✅ Better for production use

For a club management system, the free tier is usually fine!

## 🐛 Troubleshooting

### Service Won't Start
- Check Render logs: Dashboard → Service → Logs
- Verify all environment variables are set correctly
- Make sure `requirements.txt` has all dependencies

### Can't Login to Web App
- Verify `ADMIN_PASSWORD` is set correctly
- Check that `FLASK_SECRET_KEY` is set
- Clear browser cookies and try again

### Webhook Not Receiving Orders
- Check Squarespace webhook URL is correct
- Verify `WEBHOOK_SECRET` matches (if you're validating it)
- Check Render logs for incoming requests
- Test webhook health endpoint

### Slow Loading
- First request after 15 min inactivity takes ~30 seconds (free tier)
- Consider upgrading to paid tier for always-on

## 📱 Mobile Access

Once deployed, you can:
- Bookmark the web app URL on your phone
- Add members at the bar
- Update match info from anywhere
- View headcount from anywhere

## ✅ You're Done!

Once deployed:
1. ✅ Web app accessible from anywhere
2. ✅ Squarespace orders create members automatically
3. ✅ Welcome emails sent automatically
4. ✅ Mobile-friendly interface
5. ✅ Secure password protection

## 🔄 Updating Your Deployment

When you make changes:

```bash
# Make your changes locally
# Test them
python3 app.py

# Commit and push
git add .
git commit -m "Update feature X"
git push origin main

# Render automatically redeploys!
```

Render watches your GitHub repo and redeploys automatically when you push changes.

---

**Need help?** Check the logs in Render dashboard or test locally first!
