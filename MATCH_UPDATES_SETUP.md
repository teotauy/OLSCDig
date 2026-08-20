# Liverpool FC Match Updates

> Rewritten Aug 20, 2026 — this used to describe a script that pushed
> "next match" text to PassKit passes via their API, run from a local
> crontab. That's gone. This describes how it actually works now: passes
> are built with live data on demand, and already-installed passes get
> pushed a real update via Apple/Google's own APIs, on a schedule that
> runs in GitHub Actions, not on anyone's laptop.

## What this does

Keeps "next match" (opponent, date, kickoff time, home/away theme)
current on every issued pass — both the freshly-built ones and the ones
already sitting in someone's Apple or Google Wallet.

## How it actually works

1. **`get_next_match()`** (in `match_updates.py`) is the single source of
   truth: checks DB-backed [match overrides](MATCH_OVERRIDES.md) first,
   then falls back to the earliest `SCHEDULED` fixture from
   football-data.org (Premier League only — see MATCH_OVERRIDES.md for
   cup ties etc.).
2. **Every pass build already reflects this live** — `_member_pass_data()`
   in `app.py` calls `get_next_match()` fresh each time a pass is issued,
   resent, or refetched, so a brand-new pass is never stale.
3. **Already-installed passes need to be told to update.** That's the
   part that used to require a script:
   - **Apple Wallet:** `_notify_apple_pass_updates()` bumps a shared
     "content changed" tag and sends an APNs push to every device that's
     registered for updates (via Apple's PassKit web-service protocol —
     see the `/passkit/v1/*` routes in `app.py`). The device then fetches
     the freshly-built pass itself; no full pass content is pushed
     directly.
   - **Google Wallet:** `_notify_google_pass_updates()` PATCHes every
     already-saved Generic Object directly via Google's Wallet Objects
     API — Google delivers that to the member's device on its own, no
     separate "registered device" step the way Apple has one.
   - Both run together via `_notify_wallet_pass_updates()`.

## What triggers a push

- **Automatically, daily:** `.github/workflows/check-next-match.yml` runs
  at 9am UTC (10am UK time in BST) and POSTs to
  `/internal/check-next-match` (shared-secret auth, not the admin
  session). It computes the same "next match" fingerprint the site uses;
  if it's different from the last time it checked, it pushes to both
  platforms. Most days nothing has changed, so nothing gets pushed — the
  job is a no-op far more often than not.
- **Manually:** `/admin/matches` → **Push Pass Updates Now**, or
  automatically whenever an admin sets a different match as "current" via
  that same page.

## Verification status

This has real, tracked gaps — see the "Google Wallet — match-week
auto-update" and "Apple Wallet — APNs push delivery" rows in
[QA_VERIFICATION_PLAN.md](QA_VERIFICATION_PLAN.md). Short version: the
API calls themselves are verified against the real Apple/Google servers,
but nobody's yet watched a real installed pass on a real phone visibly
update from an automatic push — that needs a real device and hasn't
happened yet.

## Troubleshooting

- **No matches found / next match looks wrong:** Check
  `FOOTBALL_DATA_API_KEY` is set, then check
  [MATCH_OVERRIDES.md](MATCH_OVERRIDES.md) — most "wrong match" issues
  are a missing/incorrect override, not an API problem.
- **Added an override but a pass doesn't show it:** The override itself
  doesn't push anything — click **Push Pass Updates Now** on
  `/admin/matches` (or wait for the daily job) after adding it.
- **A specific installed pass never updates:** Confirms the open gap
  above — needs the real-device verification, not a code fix we know is
  missing today.

---

**Passes always reflect the current next match when built or refetched;
already-installed ones get told to refetch on the schedule above.**
