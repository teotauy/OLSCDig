# OLSC Brooklyn / DigID — Feature Roadmap

> Rewritten Aug 20, 2026. The previous version of this doc described the
> PassKit-vendor system (bulk checkout, PassKit as source of truth) — all
> replaced. This reflects what's actually shipped today. Match-update
> mechanics last verified Aug 31 — see [MATCH_UPDATES_SETUP.md](MATCH_UPDATES_SETUP.md).

## Done (shipped)

### Core system
- **Members, seasons, check-ins** — Supabase Postgres, owned by us, not a vendor.
- **Apple Wallet passes** — signed `.pkpass`, live next-match data, home/away theming.
- **Google Wallet passes** — Generic Object save links, same live data.
- **QR check-in scanner** (`/scanner`) — writes to our own `checkins` table.
- **Live headcount** — public `/` (how full / early-entry capacity). Scanner shows the count at the door. `/api/headcount`.
- **Attendance leaderboard** — `/admin/leaderboard`.

### Match-day updates
- **Automatic push to installed passes** when "next match" changes — Apple via APNs + PassKit web-service protocol (`apns-push-type: background`, `apns-priority: 5`, fetch tracking, 304 only on an exact Last-Modified match), Google via PATCH of text + color + logo. Daily GitHub Actions job (9am UTC) plus **Push Pass Updates Now** (runs in the background so the admin page doesn't 502). `/admin/matches` "Set current" is scanner-only and does **not** push. football-data.org is queried as `SCHEDULED` + separate `LIVE` — comma-combined statuses with `limit: 25` returns the *end* of the season (that bug painted passes with Spurs 12/19 on Aug 30; fixed the same day).
- **DB-backed match overrides** (`/admin/match-overrides`) for cup ties / wrong API times — no code deploy needed, replaced the old `match_overrides.json` file.

### Member management
- **CSV import** (`/admin/members`) — batched, idempotent, typo-domain detection.
- **Squarespace → auto member + pass** — webhook via Make.com (Squarespace's plan has no native webhooks).
- **Bulk first-time pass issuance** (`/admin/issue-passes`) — checkbox review, CSV export, nothing sends until explicitly clicked.
- **Bulk pass remediation** (`/admin/pass-remediation`) — same pattern, for resending to members whose pass predates a fix.
- **Self-service pass recovery** (`/recover-pass`) — resend by email, no admin needed.
- **Mobile web pass fallback** (`/pass/<token>`) — for anyone without Apple/Google Wallet.

### Auth & ops
- **Password + optional Google OAuth login**, forgot-password flow, rate limiting.
- **Resend email sending** — with real usage tracking (daily/monthly quota, rate-limit vs. quota-exceeded correctly distinguished as of Aug 20) and a visible usage badge on every page that can send in bulk.
- **PassKit vendor routes mothballed**, not deleted — gated behind `PASSKIT_LEGACY_ENABLED` (default off), kept only as an emergency fallback. See `_passkit_legacy_gate()` in `app.py`.
- **Volunteer door access** (`/admin/door-access`) — scoped, revocable, expiring links that grant scanner-only access, no admin password needed or exposed.
- **Protocol tests** (`tests/test_pass_update_protocol.py`) — 304 equality, fetch tracking, APNs headers.
- **Security hardening** (Aug 25) — fixed an open redirect, a Google OAuth flow that failed open on error, timing-unsafe secret comparisons, and a hardcoded `FLASK_SECRET_KEY` fallback that was actually in use in production.

## Known gaps (tracked, not hidden)

Full detail and status in [QA_VERIFICATION_PLAN.md](QA_VERIFICATION_PLAN.md). Headline items:

- **~38 members still on a pre-Aug-20 pass** — they cannot register for Apple push (broken `webServiceURL`). Barcode still scans. Pass Remediation is built; sending is a deliberate hold (in-person / Discord opt-in, not a blast). As of Aug 31: **85** post-fix Apple passes have a registered device, **100/100** of those devices have fetched a refresh after a real push. We cannot see Expired-in-Wallet or a complete uninstall list; `platform` is always `apple`, so Android is not a stored flag.
- **Daily cron unattended after the next fixture** — manual **Push Pass Updates Now** is confirmed on real phones (Will Foote, Ipswich). The Aug 29 cron detected Forest→Ipswich then never retried; fetch tracking is in place so the next unattended change is the remaining watch.
- **Venue location for lock-screen alerts** — coordinates were found wrong (~220m off) via a real matchday test and corrected, but the fix itself hasn't been re-tested in person yet, and the phone's own Location Services settings are a separate unverified variable.
- **Squarespace → Make.com → our webhook**, end to end with a real order — built and unit-tested against hand-built payloads, not yet run against an actual Squarespace purchase.
- **The 3 mothballed legacy PassKit pages** (`/legacy/passkit/add-member`, `/update-match`, `/resend-welcome`) — pages load, their form submissions against the real PassKit API were never tested. Decision pending: worth testing, or just retire since they're unlinked and superseded.
- **`matches.is_current` has no automation** — someone has to manually create next week's *viewing-night* row and flip which one's current for the scanner. That table is not the pass "next match" feed.

## Planned / backlog

### Next up
- **Mobile admin hub** — a dead-simple, large-button mobile page: Scan People In / Look Someone Up / Add a Member / View Leaderboard. Button set agreed, not yet built.

### Nice to have
- **Season reports** — attendance summaries, "your season," Liverpool's record when you attended.
- **Member self-service** — update own info, view own check-in history.
- **Structured logging / error alerting** — beyond the current print-to-Render-logs approach.
- **Monitoring** — uptime/error tracking (e.g. Sentry).

### Longer term
- **Multi-venue / geofencing.**
- **Multi-club / white-label** template for other supporter clubs.
- **SMS reminders** (e.g. Twilio).

## Where things live

| Topic | Doc |
| --- | --- |
| System overview | [README.md](README.md) |
| Full history / current status | [SELF_HOSTED_WALLET_PLAN.md](SELF_HOSTED_WALLET_PLAN.md) |
| Verification status per integration | [QA_VERIFICATION_PLAN.md](QA_VERIFICATION_PLAN.md) |
| Deploy + env vars | [WEB_APP_DEPLOYMENT.md](WEB_APP_DEPLOYMENT.md) |
| Match overrides | [MATCH_OVERRIDES.md](MATCH_OVERRIDES.md) |
| Match-day update mechanics | [MATCH_UPDATES_SETUP.md](MATCH_UPDATES_SETUP.md) |
