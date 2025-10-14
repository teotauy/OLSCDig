# 🚀 Render Deployment Guide for Squarespace Webhook

This guide will help you deploy the Squarespace webhook to Render so new memberships automatically create PassKit members.

## 📋 Prerequisites

- GitHub repository with your code
- Render account (free tier available)
- Squarespace admin access
- PassKit credentials

## 🔧 Step 1: Deploy to Render

### 1.1 Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with your GitHub account
3. Connect your repository

### 1.2 Create Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Use these settings:
   - **Name**: `olsc-webhook`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 squarespace_webhook.py`
   - **Plan**: Free

### 1.3 Set Environment Variables
In Render dashboard, go to Environment tab and add:

```
PASSKIT_PROGRAM_ID=3yyTsbqwmtXaiKZ5qWhqTP
PASSKIT_API_BASE=https://api.pub2.passkit.io
PASSKIT_API_KEY=your_api_key_here
PASSKIT_PROJECT_KEY=your_project_key_here
WEBHOOK_SECRET=your_random_secret_here
TIMEZONE=America/New_York
```

**⚠️ Important**: Generate a random `WEBHOOK_SECRET` (like `abc123xyz789`) for security.

### 1.4 Deploy
1. Click "Create Web Service"
2. Wait for deployment (2-3 minutes)
3. Note your webhook URL: `https://olsc-webhook.onrender.com`

## 🔗 Step 2: Configure Squarespace Webhook

### 2.1 Add Webhook in Squarespace
1. Go to Squarespace Settings → Advanced → Webhooks
2. Click "Add Webhook"
3. Configure:
   - **Event**: "Order Completed"
   - **URL**: `https://olsc-webhook.onrender.com/webhook/squarespace`
   - **Method**: POST
   - **Format**: JSON

### 2.2 Test the Connection
1. Make a test purchase (or use existing order)
2. Check Render logs for webhook activity
3. Verify new member appears in PassKit

## 🔍 Step 3: Monitor & Troubleshoot

### 3.1 Check Logs
- Render dashboard → Service → Logs
- Look for webhook POST requests
- Watch for any errors

### 3.2 Common Issues
- **404 Error**: Check webhook URL in Squarespace
- **500 Error**: Check environment variables
- **No member created**: Check PassKit API credentials

### 3.3 Test Manually
```bash
curl -X POST https://olsc-webhook.onrender.com/health
# Should return: {"status": "ok", "service": "olsc-webhook"}
```

## ✅ What Happens Now

1. **Customer buys membership** → Squarespace sends webhook
2. **Webhook creates PassKit member** → Sends welcome email
3. **Member gets pass** → Shows "Some inferior side" initially
4. **Daily match update** → Updates pass with real match info

## 🔒 Security Notes

- Webhook secret prevents unauthorized access
- Only processes "Order Completed" events
- Validates Squarespace webhook signature
- Filters for membership products only

## 📞 Support

If something goes wrong:
1. Check Render logs first
2. Test PassKit API with `test_connection.py`
3. Verify Squarespace webhook configuration
4. Check that new members get welcome emails

---

**🎉 You're done!** New memberships will now automatically create PassKit members and send welcome emails.
