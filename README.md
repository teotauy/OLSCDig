# OLSC Brooklyn — Digital ID (Wallet & Check-In System)

> **Status:** Live in production for the 2026/27 season.
> **Last updated:** Aug 31, 2026.

Self-hosted membership system for OLSC Brooklyn (Liverpool FC supporters
club, Brooklyn NY). Members live in our own Supabase Postgres DB, not a
third-party vendor. We generate and sign real Apple Wallet and Google
Wallet passes ourselves, push live match-day updates to them, and scan
members in at the door with our own QR check-in flow.

This replaced a PassKit.io vendor subscription. If you find a doc in this
repo describing PassKit member creation, PassKit pass fields, or a
PassKit subscription — it's archived history from before the migration.
The full story of that migration and the current status of every piece is
in **[SELF_HOSTED_WALLET_PLAN.md](SELF_HOSTED_WALLET_PLAN.md)**.

## What this is

- **Members & seasons** — Postgres (Supabase), not a spreadsheet or a
  vendor's dashboard.
- **Apple Wallet passes** — signed `.pkpass` files, built and emailed by
  this app. Installed passes get live match-day updates pushed via
  Apple's PassKit web-service protocol (APNs).
- **Google Wallet passes** — Generic Objects via Google's Wallet API,
  same live match-day updates via a direct PATCH to the saved object.
- **Check-in** — a QR scanner page for door staff; check-ins write to our
  own `checkins` table, tied to whichever match is marked "current."
- **Admin tools** — member roster/import/export, match schedule +
  overrides, leaderboard, bulk pass-sending tools (see below), all
  password-protected.
- **Squarespace signup** — new memberships create a member and email a
  pass automatically via a webhook (Make.com bridges Squarespace, which
  has no native webhooks on our plan).

## Admin pages

All under `/admin/*`, password-protected (`require_password()`):

| Page | What it's for |
| --- | --- |
| `/admin` | Action hub (scan, people, door night, wallets). |
| `/admin/members` | Roster: search, edit, CSV import/export, download/resend an individual pass. |
| `/admin/matches` | Viewing-night schedule for the scanner ("Set current"). **Push Pass Updates Now** refreshes Apple + Google to football-data.org's next match — not this table. |
| `/admin/match-overrides` | Fix a match football-data.org gets wrong or misses (cup ties, corrected kickoff times) — DB-backed, no code deploy needed. |
| `/admin/leaderboard` | Attendance leaderboard for the season. |
| `/admin/issue-passes` | Bulk-send a first pass to every member who's never gotten one — checkbox review, CSV export, nothing sends until you click. |
| `/admin/pass-remediation` | Bulk-resend to members whose existing pass predates a fix and needs replacing — same review-before-send pattern. |
| `/scanner` | QR check-in at the door. |

Public / rare:

| Page | What it's for |
| --- | --- |
| `/` | How full — live check-in count for early-entry capacity (tablet on the wall). Scanner already shows the count at the door. |

Member-facing:

| Page | What it's for |
| --- | --- |
| `/pass/<token>` | Mobile web fallback for anyone without Apple/Google Wallet — same QR, live next-match info. |
| `/recover-pass` | Self-service "resend my pass" by email. |

## Local dev

```bash
python3 app.py
```

Needs a `.env` with (at minimum) `DATABASE_URL`, `ADMIN_PASSWORD`,
`FLASK_SECRET_KEY`. Apple Wallet, Google Wallet, Resend email, and
football-data.org each need their own env vars to actually work — see
[WEB_APP_DEPLOYMENT.md](WEB_APP_DEPLOYMENT.md) for the current checklist.

## Deployed

Render (`olsc-web-app`, see `render.yaml`), auto-deploys on push to
`main`. A daily scheduled GitHub Action
(`.github/workflows/check-next-match.yml`) checks for match changes and
pushes Wallet updates automatically.

## Current known gaps

Tracked honestly — full list in
[QA_VERIFICATION_PLAN.md](QA_VERIFICATION_PLAN.md). Headlines as of
Aug 31:

- **Manual Wallet push works** for post-Aug-20 Apple passes (real
  phones, Ipswich). **85** registered / **100** devices, all fetched.
- **~38 pre-fix passes** still cannot auto-update; barcode still scans.
  Resend is a when, not a how (in-person / Discord, not a blast).
- **Daily cron unattended** after the next fixture hasn't been watched
  yet; Forest→Ipswich was detected then not retried until fetch tracking
  shipped.
- We **cannot** see Expired-in-Wallet, a full uninstall list, or
  Android vs iPhone (`platform` is always `apple`).

## Docs map

- **[SELF_HOSTED_WALLET_PLAN.md](SELF_HOSTED_WALLET_PLAN.md)** — the real
  status doc: what shipped, when, and why. Start here for history.
- **[QA_VERIFICATION_PLAN.md](QA_VERIFICATION_PLAN.md)** — what's been
  verified against real external systems vs. still assumed.
- **[WEB_APP_DEPLOYMENT.md](WEB_APP_DEPLOYMENT.md)** — Render deploy +
  env var checklist.
- **[MATCH_OVERRIDES.md](MATCH_OVERRIDES.md)** — how to fix a wrong/missing match.
- **[MATCH_UPDATES_SETUP.md](MATCH_UPDATES_SETUP.md)** — how the automatic
  match-day pass updates work.
- **[ISSUE_PASS_VERIFICATION_MUTATES_REAL_DATA.md](ISSUE_PASS_VERIFICATION_MUTATES_REAL_DATA.md)**
  — don't inspect `pass.json` by reissuing a real member (rotates their
  serial). Still true after the Aug 30–31 work.
- **[ROADMAP.md](ROADMAP.md)** — shipped vs. planned.
- Everything else at the repo root describing PassKit is archived
  history — each has a banner at the top saying so.

---

**You'll Never Walk Alone.**
