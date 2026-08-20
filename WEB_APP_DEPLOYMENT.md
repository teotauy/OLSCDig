# Deploy the Web App to Render

> Rewritten Aug 20, 2026. The env var list, troubleshooting, and feature
> list below previously described the PassKit-vendor version of this app
> (PassKit as required config, "Add Member"/"Update Match"/"Checkout
> Everyone" as the core loop). That system is retired. This describes the
> current DB-backed app.

## What this deploys

The single Flask app (`app.py`) that is the whole system: member roster,
Apple/Google Wallet pass issuance, match-day updates, QR check-in, and
all admin pages. See [README.md](README.md) for the full feature list.

Deployed as the `olsc-web-app` service in `render.yaml`, auto-deploying
on push to `main`.

## Environment variables

### Required — the app won't run correctly without these

| Variable | Notes |
| --- | --- |
| `DATABASE_URL` | Supabase Postgres connection string. |
| `ADMIN_PASSWORD` or `ADMIN_PASSWORD_HASH` | Admin login. If both are set, the hash wins. Generate a hash: `python3 -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"` |
| `FLASK_SECRET_KEY` | Session signing key: `python3 -c "import secrets; print(secrets.token_hex(32))"` |

### Apple Wallet — required for Apple passes to work at all

| Variable | Notes |
| --- | --- |
| `APPLE_TEAM_ID` | Apple Developer team ID. |
| `APPLE_PASS_TYPE_ID` | Registered Pass Type ID. |
| `APPLE_CERT_PASSWORD` | Password on the `.p12` signing cert. |
| `APPLE_PASS_CERT_P12_BASE64` | Base64 of the signing cert `.p12`. On Render, use this — not a file path. |
| `APPLE_WWDR_PEM_BASE64` | Base64 of Apple's WWDR intermediate cert. Same reasoning. |

Locally you can use `APPLE_PASS_CERT_PATH` / `APPLE_WWDR_CERT_PATH`
(defaults point at `certs/`) instead of the base64 vars — Render has no
persistent disk to point a path at, so it needs the base64 form.

### Google Wallet — required for Google passes to work at all

| Variable | Notes |
| --- | --- |
| `GOOGLE_WALLET_ISSUER_ID` | OLSC Brooklyn's Wallet issuer ID. |
| `GOOGLE_WALLET_SERVICE_ACCOUNT_JSON_BASE64` | Base64 of the service account JSON key. That service account's email must be invited as **Developer** on the issuer in the Google Pay & Wallet Console. |
| `GOOGLE_WALLET_CLASS_SUFFIX` | Optional — defaults to a season-based class suffix. |

### Email — required for any pass to actually get emailed

| Variable | Notes |
| --- | --- |
| `RESEND_API_KEY` | Primary path. |
| `RESEND_FROM_EMAIL` | Optional, defaults to `OLSC Brooklyn <DIGITALIDS@OLSCBROOKLYN.COM>`. |
| `RESEND_REPLY_TO` | Optional, defaults to `OLSC_BK@olscbrooklyn.com`. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` | Fallback path if not using Resend. |
| `EMAIL_SENDING_ENABLED` | Optional kill switch — set `false` to generate passes without emailing (returns a clear "deliberately paused" message rather than a generic failure). |

### Other integrations

| Variable | Notes |
| --- | --- |
| `FOOTBALL_DATA_API_KEY` | Required for real fixture data — without it, "next match" is always blank. |
| `SQUARESPACE_WEBHOOK_SECRET` | Shared secret the Make.com scenario sends for `/api/squarespace/order`. Auto member+pass creation silently 503s without this set. |
| `INTERNAL_TASK_SECRET` | Shared secret for the scheduled GitHub Action hitting `/internal/check-next-match` and `/internal/sync-match-results`. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Optional — enables "Sign in with Google" on the login page. Redirect URI must be `https://<your-render-url>/login/callback`. |
| `ALLOWED_GOOGLE_EMAILS` | Optional, comma-separated allowlist restricting Google sign-in. |

### Cosmetic / operational, all optional

| Variable | Notes |
| --- | --- |
| `ADMIN_USERNAME` | Require a username too, not just a password. |
| `ADMIN_RECOVERY_CODE` | Local-only forgot-password flow (Render has no persistent disk for this — see Troubleshooting). |
| `SESSION_COOKIE_SECURE` | Set `true` on Render (HTTPS). |
| `PUBLIC_BASE_URL` | Public app URL, used in emailed pass links and Wallet asset URLs. Set this or links in emails may be wrong. |
| `HEADCOUNT_REFRESH_SECONDS` | Default `60`. Min 10, max 300. |
| `TIMEZONE` | Default `America/New_York`. |
| `OLSC_SEASON` | Only affects the `/wallet/test-pass` demo route. |

### Mothballed — only matters if you flip the legacy switch back on

| Variable | Notes |
| --- | --- |
| `PASSKIT_LEGACY_ENABLED` | Default `false`/unset — 3 old PassKit-vendor-API admin routes 404 by default. See `_passkit_legacy_gate()` in `app.py`. |
| `PROGRAM_ID`, `PASSKIT_API_KEY`, `PASSKIT_PROJECT_KEY`, `API_BASE` | Only needed if `PASSKIT_LEGACY_ENABLED=true`. |

## Deploying

**Render Blueprint (what's actually set up):** push to GitHub with
`render.yaml` committed → Render Dashboard → **New +** → **Blueprint** →
connect the repo → Render creates the `olsc-web-app` service from
`render.yaml` → set the environment variables above in the dashboard.

Pushing to `main` auto-deploys from then on.

## Login & password recovery

- Rate-limited: 5 attempts per 15 minutes per IP.
- **On Render:** no recovery flow writes to disk (ephemeral filesystem) —
  to reset a forgotten password, just set a new `ADMIN_PASSWORD` (or
  `ADMIN_PASSWORD_HASH`) in the Render dashboard and save; it redeploys.
- **Locally:** set `ADMIN_RECOVERY_CODE` in `.env`, then use **Forgot
  password?** on the login page with that code to set a new password
  (stored hashed in `.admin_hash`, gitignored).

## Troubleshooting

**Headcount / a page errors out:** Check Render logs (Dashboard → your
service → Logs) for the actual exception — almost always a missing env
var for whichever integration that page touches (Apple cert vars for
pass pages, `RESEND_API_KEY` for anything that emails, `DATABASE_URL`
for anything at all).

**Google Wallet link fails on Android:** Confirm
`GOOGLE_WALLET_ISSUER_ID` is correct, decode
`GOOGLE_WALLET_SERVICE_ACCOUNT_JSON_BASE64` and confirm that exact
`client_email` is invited as **Developer** on that issuer in the Google
Pay & Wallet Console, and that the Android account testing it is added
under **Test accounts** if the issuer isn't fully published yet.

**Apple Wallet pass won't build:** Usually a bad/missing
`APPLE_PASS_CERT_P12_BASE64`, `APPLE_WWDR_PEM_BASE64`, or wrong
`APPLE_CERT_PASSWORD` — `AppleWalletConfigError` messages are specific
about which one.

**Slow first request:** Render free tier spins down after ~15 min
idle; first request after that takes ~30s to wake up. Not worth
upgrading to paid/always-on until real match-day scanner reliance
matters more than the free tier's 750 hrs/month.

**A bulk pass send seems slow:** Expected — see `_bulk_issue_and_email`
in `app.py`; sends are deliberately paced to stay under Resend's rate
limit, and per-member pass-building work adds up on top of that for a
big batch. Not a hang.

## Local dev

```bash
export DATABASE_URL="..."
export ADMIN_PASSWORD="your-password-here"
export FLASK_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
python3 app.py
```

Then open http://localhost:5000. Add whichever of the integration vars
above you need for the specific thing you're testing — the app degrades
per-feature (e.g. missing Google Wallet vars just means that button
doesn't render) rather than failing to start.
