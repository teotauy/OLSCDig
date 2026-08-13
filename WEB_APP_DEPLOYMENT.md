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
- `ADMIN_PASSWORD` - Password for admin login (or use `ADMIN_PASSWORD_HASH` for a hashed password; see [Login & security](#login--security) below)
- `FLASK_SECRET_KEY` - Random secret key for sessions: `python3 -c "import secrets; print(secrets.token_hex(32))"`

**Optional:**
- `ADMIN_USERNAME` - Username required on the login form (e.g. `admin`). If set, both username and password must match.
- `API_BASE` - Defaults to `https://api.pub2.passkit.io`
- `TIMEZONE` - Defaults to `America/New_York`
- `SESSION_COOKIE_SECURE` - Set to `true` when using HTTPS (e.g. on Render) so the session cookie is only sent over HTTPS.
- `PUBLIC_BASE_URL` - Public app URL, e.g. `https://olsc-web-app.onrender.com`. Used in emailed pass links and Google Wallet asset URLs.
- `HEADCOUNT_REFRESH_SECONDS` - How often the headcount updates (default `60`). Set to `30` for twice as fast, or `45` for a middle ground. Minimum 10, maximum 300.
- **Checkout report email:** After "Check Out Everyone", the CSV can be emailed. Set:
  - `CHECKOUT_REPORT_EMAIL` - Address to receive the report (e.g. `colby@colbyangusblack.com`).
  - `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USER`, `SMTP_PASSWORD` - Your SMTP server (e.g. Gmail, SendGrid). Optional: `EMAIL_FROM` (defaults to `SMTP_USER`).
  - Or use Resend: `RESEND_API_KEY`, optional `RESEND_FROM_EMAIL` (defaults to `OLSC Brooklyn <DIGITALIDS@OLSCBROOKLYN.COM>`), optional `RESEND_REPLY_TO` (defaults to `OLSC_BK@olscbrooklyn.com`).
  If these are set, the report is sent as an attachment after each bulk checkout.
- **Google Wallet demo-mode issuing:** Set:
  - `GOOGLE_WALLET_ISSUER_ID` - `3388000000023170524`.
  - `GOOGLE_WALLET_SERVICE_ACCOUNT_JSON_BASE64` - Base64 of the Google Cloud service account JSON key whose service account email is invited as **Developer** on that Wallet issuer.
  - `GOOGLE_WALLET_CLASS_SUFFIX` - Optional. Defaults to a season-based OLSC Brooklyn Digital ID class suffix.
  While the issuer is in demo mode, only Wallet Console test accounts can add passes.

### Login & security

- **Password:** You can set `ADMIN_PASSWORD` (plain) or `ADMIN_PASSWORD_HASH` (bcrypt hash). If both are set, the hash is used. To generate a hash:  
  `python3 -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"`  
  then set `ADMIN_PASSWORD_HASH` to that value and leave `ADMIN_PASSWORD` unset for better security.
- **Rate limiting:** Login is limited to 5 attempts per 15 minutes per IP. After that, the user must wait before trying again.
- **Forgot password (Render):** There is no recovery code on Render (filesystem is ephemeral). Use **Forgot password?** on the login page for instructions: set a new `ADMIN_PASSWORD` (and optionally `ADMIN_PASSWORD_HASH`) in the Render Environment and save so the service redeploys.
- **Forgot password (local):** Set `ADMIN_RECOVERY_CODE` in `.env` to a secret string you keep safe. Then use **Forgot password?** → enter that recovery code and a new password. The new password is stored hashed in `.admin_hash` (gitignored).
- **Google sign-in (optional):** To show “Sign in with Google”, set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (from Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client). Authorized redirect URI must be `https://your-render-url.onrender.com/login/callback`. To restrict who can log in, set `ALLOWED_GOOGLE_EMAILS` to a comma-separated list of allowed email addresses (e.g. `you@example.com,other@example.com`).

**If you run match updates on Render (cron or script):**
- `FOOTBALL_DATA_API_KEY` – API key from [football-data.org](https://www.football-data.org/). Use the same value as in your local `.env`. Required for `match_updates.py` to fetch fixtures.

**If you run Pushover notifications on Render:**
- `PUSHOVER_USER_KEY` – Your Pushover user key (same as in local `.env`).
- `PUSHOVER_API_TOKEN` – Your Pushover app API token (same as in local `.env`).

#### Render ENV checklist (copy into Dashboard → Environment)

| Variable | Where | Notes |
|----------|--------|--------|
| `PROGRAM_ID` | Required | PassKit program ID |
| `PASSKIT_API_KEY` | Required | PassKit API key |
| `PASSKIT_PROJECT_KEY` | Required | PassKit project key |
| `ADMIN_PASSWORD` | Required | Or use `ADMIN_PASSWORD_HASH` |
| `FLASK_SECRET_KEY` | Required | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `API_BASE` | Optional | Default `https://api.pub2.passkit.io` |
| `TIMEZONE` | Optional | Default `America/New_York` |
| `SESSION_COOKIE_SECURE` | Optional | Set `true` for HTTPS (Render) |
| `PUBLIC_BASE_URL` | Recommended | Public HTTPS app URL used in emailed pass links and Google Wallet assets |
| `HEADCOUNT_REFRESH_SECONDS` | Optional | Headcount refresh interval in seconds (default 60; e.g. 30 for faster) |
| `CHECKOUT_REPORT_EMAIL` | Optional | Email for checkout CSV |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Optional | For checkout report email |
| `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_REPLY_TO` | Optional | Preferred pass/report email path through Resend; sender defaults to `OLSC Brooklyn <DIGITALIDS@OLSCBROOKLYN.COM>`, reply-to defaults to `OLSC_BK@olscbrooklyn.com` |
| `GOOGLE_WALLET_ISSUER_ID` | Google Wallet | OLSC Brooklyn issuer ID: `3388000000023170524` |
| `GOOGLE_WALLET_SERVICE_ACCOUNT_JSON_BASE64` | Google Wallet | Base64-encoded JSON key for the Wallet issuer service account |
| `GOOGLE_WALLET_CLASS_SUFFIX` | Optional | Override the Generic Pass class suffix |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth; set redirect URI |
| `ALLOWED_GOOGLE_EMAILS` | Optional | Comma-separated allowed emails |
| `FOOTBALL_DATA_API_KEY` | If match updates run on Render | From football-data.org |
| `PUSHOVER_USER_KEY` | If notifications run on Render | Pushover user key |
| `PUSHOVER_API_TOKEN` | If notifications run on Render | Pushover app token |

**Local `.env`:** Use the same names. Set `FOOTBALL_DATA_API_KEY`, `PUSHOVER_USER_KEY`, and `PUSHOVER_API_TOKEN` in `.env` for `match_updates.py` and `notifications.py`; add them to Render only if you run those scripts there.

**Custom background image:** The app uses `static/background.png` (Brooklyn OLSC stadium image) as the background on landing, login, and all main pages; if the file is missing, the gradient is shown.

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

#### Deploy to Vercel (alternative to Render)

You can run the same Flask app on Vercel. Vercel is serverless (no persistent disk), so a few behaviors differ:

1. **Connect repo:** [Vercel](https://vercel.com) → Add New Project → Import your Git repo. Vercel will detect Flask from `app.py` and `vercel.json` (which sets `"framework": "flask"`).
2. **Environment variables:** In the project’s Settings → Environment Variables, add the same variables as for Render (see Step 1 above). Use **Vercel’s** dashboard, not Render’s. Set `SESSION_COOKIE_SECURE` to `true` for HTTPS.
3. **Password:** Because the filesystem is read-only, the app cannot write `.admin_hash`. Use **`ADMIN_PASSWORD`** or **`ADMIN_PASSWORD_HASH`** in Vercel’s env; “Forgot password” cannot save a new hash to disk, so change the password by updating those env vars and redeploying.
4. **Match overrides:** `match_overrides.json` in the repo is **read** as usual. Saving an override from the web form **does not persist** on Vercel (the app will report that). To add or change an override, edit `match_overrides.json` in the repo and push; the next deploy will pick it up.
5. **Checkout reports:** The CSV is still generated and can be emailed if SMTP is set; saving the file to disk is skipped on read-only hosts.

After deploy, your app URL will be like `https://your-project.vercel.app`. Use it the same way as the Render URL (headcount, add member, update match, etc.).

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

### 401 Unauthorized (Update Match or Headcount fails)

**Symptoms:** "401 Client Error: Unauthorized for url: https://api.pub2.passkit.io/..." or headcount shows "Error loading" / "?".

**Cause:** PassKit is rejecting requests because the app’s credentials are missing or wrong on Render.

**Fix:**

1. In **Render Dashboard** → your **olsc-web-app** service → **Environment**.
2. Set (or correct) these variables. Use the **exact same values** as in your local `.env` that work for `python3 match_updates.py` or `python3 quick_add_members.py`:
   - **`PASSKIT_API_KEY`** – PassKit API key (long string). No extra spaces before/after.
   - **`PASSKIT_PROJECT_KEY`** – PassKit project key (hex string). No extra spaces.
3. **Save**. Render will redeploy. Wait for the deploy to finish, then try again.

**Verify:** If it still fails, copy the two values from your working `.env` again and re-paste into Render (sometimes a hidden character or truncation causes 401).

### Headcount shows "Error loading"

Same root cause as above: the headcount endpoint calls PassKit to list checked-in members. If PassKit returns 401, the app returns an error and the UI shows "Error loading". Fix the 401 using the steps above; headcount will work once PassKit auth is correct. When it works, "0 people" is shown as a number, not an error.

### Can't Login
- Check that `ADMIN_PASSWORD` is set correctly in Render dashboard
- Clear browser cookies and try again

### Match Update Fails (other than 401)
- Check that `PASSKIT_API_KEY` and `PASSKIT_PROJECT_KEY` are set (see 401 section above)
- Verify API credentials work by testing locally first (`python3 match_updates.py`)

### Service Won't Start
- Check Render logs: Dashboard → Your Service → Logs
- Verify all required environment variables are set
- Check that `requirements.txt` has all dependencies

### Google Wallet link fails on Android

**Symptoms:** The Add to Google Wallet link opens but fails with an authorization, issuer, or demo-mode error.

**Fix:**

1. Confirm `GOOGLE_WALLET_ISSUER_ID` in Render is exactly `3388000000023170524`.
2. Decode `GOOGLE_WALLET_SERVICE_ACCOUNT_JSON_BASE64` locally and note `client_email`.
3. In Google Pay & Wallet Console → **Users**, confirm that exact service account email is invited as **Developer** on the same issuer.
4. In Google Pay & Wallet Console → **Test accounts**, confirm the Android Google account is listed.
5. Save Render env changes and let the service redeploy, then resend a member pass email.

The service account JSON is tied to the Cloud project/service account, not directly to the issuer ID. A key from the correct Cloud project can still work after an issuer ID correction, as long as that service account email has Developer access on the corrected issuer.

### Slow Loading
- Render free tier spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds to wake up
- Consider upgrading to paid tier for always-on service

## Cost

### Current Strategy

Keep the app on Render free tier while we are building and stabilizing the self-hosted Wallet/check-in system. Free tier is fine for setup, deploy testing, Wallet download tests, DB smoke tests, and scanner development.

Upgrade `olsc-web-app` to paid/always-on only before real match-day use. The reason to upgrade is cold starts at the door, not normal traffic volume or rate limits.

**Free Tier:**
- ✅ 750 hours/month free
- ✅ Automatic SSL
- ✅ Custom domain support
- ⚠️ Spins down after 15 min inactivity (wakes up automatically)
- ✅ OK during build/stabilization

**Paid Tier ($7/month):**
- ✅ Always on (no spin-down)
- ✅ Faster response times
- ✅ Better for production use
- ✅ Recommended before first real match-day scanner use

**Build pipeline minutes:**
- Pushes/deploys consume Render build pipeline minutes.
- This app has a small Python build, so normal development deploys should be low impact.
- Avoid enabling Performance Build Pipeline unless needed.
- Use Render Billing/Usage and spend limits if you want a hard cap.

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


