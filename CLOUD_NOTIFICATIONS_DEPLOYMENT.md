# ☁️ Cloud Deployment Guide for Pushover Notifications

Deploy the notifications script to the cloud so it runs 24/7 without needing your laptop!

## 🎯 Why Deploy to Cloud?

- ✅ **Always running** - No need to keep laptop on
- ✅ **No sleep issues** - Cloud servers never sleep
- ✅ **Reliable** - Runs continuously in the background
- ✅ **Free tier available** - Most services offer free options

## 🚀 Option 1: Render (Recommended)

**✅ You already have a $7/month Render plan - perfect!** You can add this as a new service on your existing account.

### Step 1: Create Background Worker

1. Go to [render.com](https://render.com) and sign in
2. Click **"New +"** → **"Background Worker"**
3. Connect your GitHub repository (same repo as your webhook)
4. Configure:
   - **Name**: `olsc-notifications`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 notifications.py`
   - **Plan**: Starter ($7/month) - **You already have this!** (or use Free tier if you want, but it sleeps after 15 min)
   
**Note:** You can run multiple services on the same Render account. This will be a separate service from your webhook.

### Step 2: Set Environment Variables

In Render dashboard → Environment tab, add:

```
PASSKIT_PROGRAM_ID=3yyTsbqwmtXaiKZ5qWhqTP
PASSKIT_API_BASE=https://api.pub2.passkit.io
PASSKIT_API_KEY=your_api_key_here
PASSKIT_PROJECT_KEY=your_project_key_here
PUSHOVER_USER_KEY=uxsqmcnqrjzzsy82uaogdjctczyvix
PUSHOVER_API_TOKEN=your_pushover_token_here
TIMEZONE=America/New_York
```

### Step 3: Deploy

1. Click **"Create Background Worker"**
2. Wait for deployment (2-3 minutes)
3. Check logs to verify it's running

### Step 4: Verify It's Working

1. Check Render logs - you should see:
   ```
   ⚽ Liverpool OLSC - Pushover Notifications
   📱 Sending test notification...
   ✅ Setup complete! You should receive a test notification.
   ```

2. You should receive a test notification on your phone!

## 🚂 Option 2: Railway (Simple & Fast)

### Step 1: Create Service

1. Go to [railway.app](https://railway.app) and sign in
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repository

### Step 2: Configure Service

1. Railway will auto-detect Python
2. Set **Start Command**: `python3 notifications.py`
3. Add environment variables (same as Render above)

### Step 3: Deploy

Railway will auto-deploy. Check logs to verify it's running.

## 🐳 Option 3: Docker + Any Cloud Service

If you want more control, you can containerize it:

### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY notifications.py .

CMD ["python3", "notifications.py"]
```

Then deploy to:
- **Fly.io** (free tier)
- **DigitalOcean App Platform**
- **AWS ECS/Fargate**
- **Google Cloud Run**

## 📊 Monitoring & Logs

### Render
- Dashboard → Service → Logs
- Real-time log streaming
- Log retention: 7 days (free), 30 days (paid)

### Railway
- Dashboard → Service → Logs
- Real-time log streaming
- Log retention: 7 days

## 🔧 Troubleshooting

### Script Keeps Restarting
- Check environment variables are set correctly
- Verify Pushover API token is valid
- Check logs for error messages

### No Notifications Received
1. Check logs for errors
2. Verify `PUSHOVER_API_TOKEN` is set
3. Test Pushover token manually
4. Check that script is actually running (not crashed)

### Service Goes to Sleep (Free Tier)
- **Render Free**: Services sleep after 15 minutes of inactivity
  - **Solution**: Upgrade to Starter ($7/month) or use Railway
- **Railway Free**: No sleep, but limited hours
  - **Solution**: Upgrade to Pro ($5/month) for 24/7

## 💰 Cost Comparison

| Service | Free Tier | Paid Tier | Best For |
|---------|-----------|-----------|----------|
| **Render** | ✅ (sleeps after 15min) | $7/month (always on) | Easy setup |
| **Railway** | ✅ (limited hours) | $5/month (always on) | Simple & fast |
| **Fly.io** | ✅ (always on) | $0-5/month | Always-on free option |
| **Heroku** | ❌ (no free tier) | $7/month | Legacy option |

## ✅ Recommended Setup

**For reliability (always on):**
- **Render Starter** ($7/month) - ✅ **You already have this!** Perfect for always-on notifications
- **Railway Pro** ($5/month) - Cheapest paid option
- **Fly.io** (Free) - Best free always-on option

**For testing:**
- **Render Free** - Good for testing (wakes up when needed)
- **Railway Free** - Good for testing

## 🎯 Quick Start (Render - You're Already Set Up!)

Since you already have a Render account with a $7/month plan:

1. **Go to your Render dashboard**
2. **Click "New +"** → **"Background Worker"**
3. **Connect your GitHub repo** (same one as your webhook)
4. **Set environment variables** (copy from Step 2 above)
5. **Deploy** → Done!

**Important:** This will run alongside your existing webhook service. Both services can run on the same Render account - you're not limited to one service!

Your notifications will now run 24/7 in the cloud! 🎉

---

**Need help?** Check the logs in your cloud service dashboard - they'll show exactly what's happening.

