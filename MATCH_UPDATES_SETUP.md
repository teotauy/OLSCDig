# Liverpool FC Match Updates

> Rewritten Aug 20, 2026; updated Aug 30, 2026 after a real cron cycle
> that APNs-accepted 99 pushes and then never retried, leaving phones on
> last week's match and last week's colors.

## What this does

Keeps "next match" (opponent, date, kickoff time, home/away theme)
current on every issued pass — both the freshly-built ones and the ones
already sitting in someone's Apple or Google Wallet.

## How it actually works

1. **`get_next_match()`** (in `match_updates.py`) is the single source of
   truth. It takes the earliest fixture whose **local calendar date is
   today or later**, from football-data.org statuses `SCHEDULED`,
   `TIMED`, `IN_PLAY`, and `PAUSED` (not `SCHEDULED` alone — that drops
   the fixture at kickoff, so a 9am-UTC job would push next week's
   opponent and next week's colors mid-match-day). DB-backed
   [match overrides](MATCH_OVERRIDES.md) overlay the same list by date;
   a far-future cup override cannot skip an earlier Premier League game.
2. **Every pass build already reflects this live** — `_member_pass_data()`
   in `app.py` calls `get_next_match()` fresh each time a pass is issued,
   resent, or refetched, so a brand-new pass is never stale. Home/away
   theme (red vs white) comes from the same `is_home` flag as the text.
3. **Already-installed passes need to be told to update.** That's the
   part that used to require a script:
   - **Apple Wallet:** `_notify_apple_pass_updates()` bumps a shared
     "content changed" tag and sends an APNs push to every device that's
     registered for updates (via Apple's PassKit web-service protocol —
     see the `/passkit/v1/*` routes in `app.py`). The push is an empty
     JSON body with `apns-topic` = Pass Type ID, `apns-push-type:
     background`, and `apns-priority: 5` — Apple's current APNs docs say
     a missing push-type can be delayed or dropped even when the POST
     returns 200, and omitting priority defaults to 10, which is a
     mismatch for a silent Wallet wake-up. The device then fetches the
     freshly-built pass itself; no full pass content is pushed directly.
   - **Google Wallet:** `_notify_google_pass_updates()` PATCHes every
     already-saved Generic Object (`textModulesData`, `hexBackgroundColor`,
     **and** `logo`) via Google's Wallet Objects API. Color without logo
     leaves the previous match's wordmark on the new background.
   - Both run together via `_notify_wallet_pass_updates()`.

## What triggers a push

- **Automatically, daily:** `.github/workflows/check-next-match.yml` runs
  at 9am UTC (10am UK time in BST) and POSTs to
  `/internal/check-next-match` (shared-secret auth, not the admin
  session). It computes the same "next match" fingerprint the site uses.
  If that fingerprint **changed**, it pushes Apple + Google. If it
  **didn't** change but some registered Apple devices never actually
  GETed a pass since the last content tag, it retries those devices
  (and re-PATCHes Google). APNs 200 is not treated as "the phone has
  the new pass." Most days both gates are quiet, so the job is a no-op.
- **Manually:** `/admin/matches` → **Push Pass Updates Now**. Setting a
  match as "current" on that page does **not** push — that's scanner/
  headcount only.

## Verification status

See [QA_VERIFICATION_PLAN.md](QA_VERIFICATION_PLAN.md). The API calls
themselves are verified against the real Apple/Google servers. The
Aug 29 cron did detect Forest → Ipswich and reported 99/99 Apple
pushes; today's (Aug 30) run then no-op'd because the fingerprint was
already saved. That "push once, never retry" loop is what the fetch
tracking above is for.

## Troubleshooting

- **No matches found / next match looks wrong:** Check
  `FOOTBALL_DATA_API_KEY` is set, then check
  [MATCH_OVERRIDES.md](MATCH_OVERRIDES.md) — most "wrong match" issues
  are a missing/incorrect override, not an API problem.
- **Added an override but a pass doesn't show it:** The override itself
  doesn't push anything — click **Push Pass Updates Now** on
  `/admin/matches` (or wait for the daily job) after adding it.
- **Cron JSON says `changed: false` / `reason: unchanged`:** the
  fingerprint already matches; if phones are still stale, look for
  `reason: retry_unfetched` on the next run, or click **Push Pass Updates
  Now**.
- **A specific installed pass never updates:** 38 members still have
  pre-`webServiceURL` passes that cannot register for push at all — they
  need a resend from `/admin/pass-remediation`, not another cron.

---

**Passes always reflect the current next match when built or refetched;
already-installed ones get told to refetch on the schedule above, and
the job retries devices that never came back.**
