# OLSC Brooklyn / DigID – Feature Roadmap

Single reference for what’s done, what’s next, and what’s on the horizon.

---

## Done (shipped)

### Core product
- **PassKit integration** – Members, check-in/out, passes
- **Real-time headcount** – Live count, 60s refresh (web + `/api/headcount`)
- **Bulk checkout** – “Check out everyone” with CSV report + optional email
- **Match updates** – Liverpool fixtures on passes (CLI + web “Update Match”)
- **Match overrides** – FA Cup / one-off games via `match_overrides.json`
- **Add member (web)** – Password-protected form; welcome email
- **Quick add (CLI)** – `quick_add_members.py` for manual adds

### Web app (Flask on Render)
- **Deployed on Render** – HTTPS, env-based config
- **Auth** – Password + optional Google OAuth; forgot password; rate limiting
- **Landing / headcount / login / add member / update match / forgot password** – All wired and styled
- **Background** – Stadium image (`static/background.png`) with gradient fallback
- **Branding** – “OLSC Brooklyn” + soccer ball in UI

### Security & ops
- **No client-side PassKit keys** – Static headcount pages use `/api/headcount`
- **Env-only secrets** – `FOOTBALL_DATA_API_KEY`, `PUSHOVER_USER_KEY`, `PUSHOVER_API_TOKEN` (see `ENV_UPDATE_INSTRUCTIONS.md`)
- **Render ENV checklist** – In `WEB_APP_DEPLOYMENT.md`

### Notifications & automation (optional, can run local or on Render)
- **Pushover** – Headcount/status via `notifications.py` (env: `PUSHOVER_USER_KEY`, `PUSHOVER_API_TOKEN`)
- **Match update automation** – Cron/scheduled `match_updates.py` (env: `FOOTBALL_DATA_API_KEY`)

### Docs
- **Deployment** – `WEB_APP_DEPLOYMENT.md`, `ENV_UPDATE_INSTRUCTIONS.md`
- **Match overrides** – `MATCH_OVERRIDES.md`
- **Match updates** – `MATCH_UPDATES_SETUP.md`
- **Squarespace** – `SQUARESPACE_INTEGRATION_SETUP.md`, backfill guide, etc.

---

## Optional / config-dependent (ready when you enable)

- **Squarespace → PassKit** – Webhook + automation when you deploy the webhook and set it in Squarespace
- **Checkout report email** – When `CHECKOUT_REPORT_EMAIL` + SMTP are set in Render
- **Google sign-in** – When `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (and optionally `ALLOWED_GOOGLE_EMAILS`) are set
- **Pushover on Render** – When `notifications.py` runs on Render and `PUSHOVER_*` are in Render env
- **Match updates on Render** – When `match_updates.py` runs on Render and `FOOTBALL_DATA_API_KEY` is in Render env

---

## Planned / future (backlog)

### High value
- **Auto midnight checkout** – Scheduled daily checkout (e.g. cron)
- **Individual checkout** – Check out specific members from the web UI
- **Squarespace webhook in production** – Deploy and point Squarespace so new purchases auto-create members
- **Analytics** – Attendance over time, peak times, match-type breakdown

### Nice to have
- **Season reports** – Wrapped-style summaries (e.g. “Your season”, “Liverpool’s record when you attended”)
- **Automated welcome emails** – Delayed welcome + pass download instructions (e.g. SquareSpace integration)
- **Member self-service** – Update info, re-download pass, view check-in history
- **Error handling & logging** – Structured logs, retries, optional alerting (email/Slack)
- **Monitoring** – Uptime, error tracking (e.g. Sentry), rate-limit awareness

### Longer term / advanced
- **Apple Wallet** – Live Activities, Dynamic Island, Siri
- **Android** – Live tiles, Google Assistant
- **Multi-venue / geofencing** – Multiple locations, location-based check-in
- **Multi-club / white-label** – Template for other supporter clubs
- **SMS (e.g. Twilio)** – Match reminders, event announcements
- **Database layer** – Optional DB for history, analytics, backup (PassKit remains source of truth)

---

## Where things live

| Topic              | Doc / place |
|--------------------|-------------|
| Deploy web app     | `WEB_APP_DEPLOYMENT.md` |
| ENV (local + Render) | `ENV_UPDATE_INSTRUCTIONS.md`, `WEB_APP_DEPLOYMENT.md` |
| Match overrides    | `MATCH_OVERRIDES.md` |
| Match updates      | `MATCH_UPDATES_SETUP.md` |
| Full system overview | `COMPREHENSIVE_README.md` |
| Upgrade/cleanup ideas | `UPGRADE_WORKPLAN.md` |

---

*Last updated to reflect OLSC Brooklyn rebrand, Render deployment, security/env changes, background image, and consolidated roadmap.*
