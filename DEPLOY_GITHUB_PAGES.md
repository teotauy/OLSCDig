# 🌐 Deploy to GitHub Pages

## What This Does

Creates a **public, read-only** headcount display at:
`https://[your-username].github.io/DigID/`

- ✅ Shows live headcount
- ✅ Auto-refreshes every 60 seconds
- ✅ Football pitch countdown
- ✅ Works on any device from anywhere
- ✅ No server needed
- ❌ **NO CHECKOUT BUTTON** (checkout stays local and secure)

## Quick Deploy (5 minutes)

### 1. Test Locally First

```bash
cd /Users/colbyblack/DigID
python3 -m http.server 8000 --directory public
```

Open http://localhost:8000 - you should see the headcount!

### 2. Commit the Public Version

```bash
git add public/index.html
git commit -m "Add read-only GitHub Pages headcount display"
git push origin main
```

### 3. Enable GitHub Pages

1. Go to your GitHub repo: https://github.com/[your-username]/DigID
2. Click **Settings** (top right)
3. Click **Pages** (left sidebar)
4. Under "Build and deployment":
   - **Source**: Deploy from a branch
   - **Branch**: `main`
   - **Folder**: `/public`
5. Click **Save**

### 4. Wait 1-2 Minutes

GitHub will build and deploy your site automatically.

### 5. Access Your Public Headcount

Your live headcount will be at:
```
https://[your-username].github.io/DigID/
```

Share this URL with anyone! They can see the headcount but can't check people out.

## Security Notes

### What's Public (Safe)
- ✅ Headcount number
- ✅ Live updates
- ✅ Read-only access

### What's Exposed (Acceptable Risk)
- ⚠️ API credentials are in the JavaScript
- ⚠️ Anyone can see them in browser dev tools
- ⚠️ BUT: They can only READ data, not checkout
- ⚠️ Only affects your one membership program

### What Stays Private (Secure)
- ✅ Checkout button (not in public version)
- ✅ Checkout stays on your local Flask app
- ✅ Only you can bulk checkout after matches

## For Checkout (Still Local)

Use your Flask app when you need to checkout:

```bash
cd /Users/colbyblack/DigID
python3 -m flask --app app run --host 0.0.0.0 --port 5001
```

Then open http://localhost:5001 and click "Check Out Everyone"

## Two Versions Summary

| Feature | GitHub Pages (Public) | Flask App (Local) |
|---------|----------------------|-------------------|
| Show headcount | ✅ | ✅ |
| Auto-refresh | ✅ | ✅ |
| Football pitch | ✅ | ✅ |
| Access from anywhere | ✅ | ❌ (same Wi-Fi only) |
| Checkout button | ❌ | ✅ |
| Secure API key | ❌ | ✅ |
| Always on | ✅ | ❌ (need to run it) |

## Updating the Display

If you want to change the design or text:

1. Edit `public/index.html`
2. Test locally: `python3 -m http.server 8000 --directory public`
3. Commit and push:
   ```bash
   git add public/index.html
   git commit -m "Update public display"
   git push origin main
   ```
4. GitHub Pages auto-updates in 1-2 minutes

## Custom Domain (Optional)

Want to use `headcount.liverpoolnyc.com` instead of GitHub's URL?

1. Buy domain from Namecheap/GoDaddy
2. In GitHub Pages settings, add custom domain
3. Update your DNS records
4. Done!

---

**🔴⚽ Public headcount display + Secure local checkout = Perfect!**

