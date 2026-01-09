# 🌐 Deploy Web App to Render (Free & Secure)

## What This Does

Deploys a **fully web-based** member management system that you can access from anywhere on your phone:

- ✅ **Add Members** - Password-protected form to add new members
- ✅ **Update Match Info** - One-click update to refresh all passes with next match
- ✅ **View Headcount** - Live count of checked-in members
- ✅ **Bulk Checkout** - Check everyone out after matches
- ✅ **Mobile-Friendly** - Works perfectly on your phone at the bar
- ✅ **Free** - Uses Render's free tier
- ✅ **Secure** - Password-protected, API keys stay on server

## Quick Deploy (10 minutes)

### 1. Set Up Environment Variables

In your Render dashboard, you'll need to set these environment variables for the `olsc-web-app` service:

**Required:**
- `PROGRAM_ID` - Your PassKit Program ID (e.g., `3yyTsbqwmtXaiKZ5qWhqTP`)
- `PASSKIT_API_KEY` - Your PassKit API key
- `PASSKIT_PROJECT_KEY` - Your PassKit Project Key
- `ADMIN_PASSWORD` - Password for accessing admin features (choose a strong password!)
- `FLASK_SECRET_KEY` - Random secret key for sessions (generate one: `python3 -c "import secrets; print(secrets.token_hex(32))"`)

**Optional:**
- `API_BASE` - Defaults to `https://api.pub2.passkit.io`
- `TIMEZONE` - Defaults to `America/New_York`

### 2. Deploy to Render

#### Option A: Using Render Dashboard

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select the repository: `teotauy/DigID` (or your repo)
5. Configure:
   - **Name:** `olsc-web-app`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 app.py`
6. Add all environment variables from Step 1
7. Click **"Create Web Service"**

#### Option B: Using render.yaml (Recommended)

1. Push your code to GitHub (make sure `render.yaml` is committed)
2. Go to https://dashboard.render.com
3. Click **"New +"** → **"Blueprint"**
4. Connect your GitHub repository
5. Render will automatically detect `render.yaml` and create both services
6. Set environment variables in the dashboard for `olsc-web-app`

### 3. Access Your Web App

Once deployed, Render will give you a URL like:
```
https://olsc-web-app.onrender.com
```

**Bookmark this URL on your phone!**

### 4. First Login

1. Open the URL on your phone
2. Click **"+ Add Member"** or **"⚽ Update Match"**
3. Enter your `ADMIN_PASSWORD`
4. You're in! 🎉

## Using the Web App

### Add a Member (At the Bar)

1. Open the web app on your phone
2. Click **"+ Add Member"**
3. Login with your password
4. Fill in:
   - First Name
   - Last Name
   - Email (required)
   - Phone (optional)
5. Click **"Add Member"**
6. Member is added and welcome email is sent automatically!

### Update Match Info

1. Open the web app
2. Click **"⚽ Update Match"**
3. Login with your password
4. See the next match info
5. Click **"Update All Passes"**
6. All passes are updated instantly!

### View Headcount

- Just open the main page - headcount updates every 60 seconds automatically

### Checkout Everyone

- Click **"Check Out Everyone"** button on main page
- Confirms before checking out
- Works great after matches end

## Security Features

✅ **Password Protection** - All admin features require login
✅ **Session-Based Auth** - Secure session management
✅ **API Keys Protected** - Never exposed to browser
✅ **HTTPS** - Render provides SSL automatically

## Troubleshooting

### Can't Login
- Check that `ADMIN_PASSWORD` is set correctly in Render dashboard
- Clear browser cookies and try again

### Match Update Fails
- Check that `PASSKIT_API_KEY` and `PASSKIT_PROJECT_KEY` are set
- Verify API credentials work by testing locally first

### Service Won't Start
- Check Render logs: Dashboard → Your Service → Logs
- Verify all required environment variables are set
- Check that `requirements.txt` has all dependencies

### Slow Loading
- Render free tier spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds to wake up
- Consider upgrading to paid tier for always-on service

## Cost

**Free Tier:**
- ✅ 750 hours/month free
- ✅ Automatic SSL
- ✅ Custom domain support
- ⚠️ Spins down after 15 min inactivity (wakes up automatically)

**Paid Tier ($7/month):**
- ✅ Always on (no spin-down)
- ✅ Faster response times
- ✅ Better for production use

## Local Testing

Test before deploying:

```bash
# Set environment variables
export ADMIN_PASSWORD="your-password-here"
export FLASK_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export PASSKIT_API_KEY="your-api-key"
export PASSKIT_PROJECT_KEY="your-project-key"
export PROGRAM_ID="your-program-id"

# Run the app
python3 app.py
```

Then open http://localhost:5000

## Next Steps

1. Deploy to Render
2. Bookmark the URL on your phone
3. Test adding a member
4. Test updating match info
5. You're ready to use it at the bar! 🍺⚽


