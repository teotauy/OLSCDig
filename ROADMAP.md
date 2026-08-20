# OLSC Brooklyn / DigID — Feature Roadmap

> Rewritten Aug 20, 2026. The previous version of this doc described the
> PassKit-vendor system (bulk checkout, PassKit as source of truth) — all
> replaced. This reflects what's actually shipped today.

## Done (shipped)

### Core system
- **Members, seasons, check-ins** — Supabase Postgres, owned by us, not a vendor.
- **Apple Wallet passes** — signed `.pkpass`, live next-match data, home/away theming.
- **Google Wallet passes** — Generic Object save links, same live data.
- **QR check-in scanner** (`/scanner`) — writes to our own `checkins` table.
- **Live headcount** — `/admin`, `/api/headcount`.
- **Attendance leaderboard** — `/admin/leaderboard`.

### Match-day updates
- **Automatic push to installed passes** when "next match" changes — Apple via APNs + PassKit web-service protocol (with `If-Modified-Since`/304 support), Google via a direct PATCH to the saved object. Daily scheduled check (GitHub Actions, 9am UTC) plus manual trigger from `/admin/matches`.
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

## Known gaps (tracked, not hidden)

Full detail and status in [QA_VERIFICATION_PLAN.md](QA_VERIFICATION_PLAN.md). Headline items:

- **Real-device confirmation** that an automatic Apple push, and an automatic Google Wallet PATCH, actually land on a phone and visibly update — the API calls themselves are verified against the real Apple/Google servers, but nobody's watched it happen on a real installed pass yet.
- **Squarespace → Make.com → our webhook**, end to end with a real order — built and unit-tested against hand-built payloads, not yet run against an actual Squarespace purchase.
- **Leaderboard result sync** (`get_finished_liverpool_matches()`) — built against football-data.org's documented schema, unverified against a real finished match until one's actually been played (first one: Aug 23).
- **The 3 mothballed legacy PassKit pages** (`/legacy/passkit/add-member`, `/update-match`, `/resend-welcome`) — pages load, their form submissions against the real PassKit API were never tested. Decision pending: worth testing, or just retire since they're unlinked and superseded.

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
