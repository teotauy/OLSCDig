# Liverpool FC Match Updates

> Rewritten Aug 20, 2026; rewritten again Aug 30–31 after a real
> Forest → Ipswich cycle: APNs 200s that never retried, a football-data.org
> query that briefly painted every new pass with Spurs on 12/19, and a
> manual push that then *did* land on real phones.

## What this does

Keeps "next match" (opponent, date, kickoff time, home/away theme)
current on every issued pass — both the freshly-built ones and the ones
already sitting in someone's Apple or Google Wallet.

## How it actually works

1. **`get_next_match()`** (in `match_updates.py`) is the single source of
   truth. It takes the earliest fixture whose **local calendar date is
   today or later**. football-data.org is queried with `status=SCHEDULED`
   (that filter is what actually returns upcoming games, even though they
   come back labeled `TIMED`) plus a separate `LIVE` call so match-day
   still shows today's opponent. **Do not comma-combine statuses with a
   small `limit`.** Confirmed against the live API Aug 30: that returns
   the *last* 25 of the season, which is how passes briefly showed Spurs
   on 12/19 instead of Ipswich on 9/4. DB-backed
   [match overrides](MATCH_OVERRIDES.md) overlay the same list by date;
   a far-future cup override cannot skip an earlier Premier League game.
2. **Every pass build already reflects this live** — `_member_pass_data()`
   in `app.py` calls `get_next_match()` fresh each time a pass is issued,
   resent, or refetched, so a brand-new pass is never stale. Home/away
   theme (red vs white) comes from the same `is_home` flag as the text.
3. **Already-installed passes need to be told to update:**
   - **Apple Wallet:** `_notify_apple_pass_updates()` bumps a shared
     "content changed" tag and sends an APNs push to every registered
     device (see `/passkit/v1/*` in `app.py`). Payload is an empty JSON
     object; headers are `apns-topic` = Pass Type ID, `apns-push-type:
     background`, `apns-priority: 5` (Apple's current APNs docs: a
     missing push-type can be dropped even on HTTP 200; omitting
     priority defaults to 10, wrong for a silent Wallet wake-up). The
     phone then fetches the rebuilt pass. Invalid APNs tokens are
     deleted from `pass_devices` — that is **not** deleting the pass
     from Wallet.
   - **Google Wallet:** `_notify_google_pass_updates()` PATCHes every
     issued Generic Object (`textModulesData`, `hexBackgroundColor`,
     **and** `logo`). Color without logo leaves the previous match's
     wordmark on the new background.
   - Both run together via `_notify_wallet_pass_updates()`.

The `/admin/matches` table is **not** this feed. That page is viewing
nights for the scanner (`matches.is_current`). Ipswich can be next on
the pass without a row on that table. **Push Pass Updates Now** uses
`get_next_match()`, not "Set current."

## What triggers a push

- **Automatically, daily:** `.github/workflows/check-next-match.yml` at
  9am UTC POSTs `/internal/check-next-match`. If the next-match
  fingerprint **changed**, it pushes Apple + Google. If it didn't, but
  some registered Apple devices never GETed a pass since the last
  content tag (`pass_devices.last_fetched_at`), it retries those
  (and re-PATCHes Google). APNs 200 is not treated as "the phone has
  the new pass."
- **Manually:** `/admin/matches` → **Push Pass Updates Now**. That
  request returns immediately and runs the fan-out in a background
  thread — waiting in the HTTP request was 502ing at gunicorn's old
  30s timeout. Confirm text says Apple **and** Google (the button
  always did both). Setting a match as "current" does **not** push.

## What we can (and cannot) see

Counts as of Aug 31, from production:

| Signal | Meaning |
| --- | --- |
| Row in `pass_devices` | Phone registered for Apple Wallet updates (85 passes / 100 devices). |
| `last_fetched_at` set | That phone actually downloaded a refresh. All 100 registered devices have. |
| Issued before Aug 20 08:24 UTC | Pre-`webServiceURL` fix — **38** cannot register; push will never reach them. Barcode still scans. |
| Issued Aug 20–24 | Can register, but those files still had `relevantDate` — may sit in Wallet's Expired pile even if content updates. |
| Issued after Aug 24 | No `relevantDate`; should stay in the active stack. |
| `google_object_id` set | We generated a Google save link (~135). **Not** "they saved it." |
| Google PATCH 200 vs 404 | Only real "saved to Google Wallet" signal, and we don't persist it. Last counted ~15 saves. |
| `platform` column | Always `apple`. We cannot tell Android from iPhone. |

Apple does **not** tell us "this pass shows Expired" or give a complete
uninstall list. Unregister only fires if a *working* pass was added and
then deleted. The 38 never registered, so deleting that pass is invisible.

## Verification status (Aug 31)

See [QA_VERIFICATION_PLAN.md](QA_VERIFICATION_PLAN.md). Short version:

- **Manual push works** on post-fix Apple passes: Will Foote (issued
  Saturday) and a freshly issued pass showed Ipswich after **Push Pass
  Updates Now**. 100/100 registered devices had `last_fetched_at`.
- **Daily cron unattended** after the next fixture change is still the
  remaining watch — Forest→Ipswich was detected Aug 29, then no-op'd
  Aug 30 because the fingerprint was already saved (the retry gap).
- **Already-Expired / pre-fix** passes still need a resend, not another
  push. Delete-and-reinstall is the only reliable way off Expired.

## Troubleshooting

- **Pass shows Spurs 12/19 (or some other late-season game):** that was
  the comma-status + `limit: 25` bug. Fixed Aug 30. If you still see it
  on a pass issued during that window, push again (or resend).
- **No matches found / next match looks wrong:** `FOOTBALL_DATA_API_KEY`,
  then [MATCH_OVERRIDES.md](MATCH_OVERRIDES.md).
- **Added an override but a pass doesn't show it:** click **Push Pass
  Updates Now** (or wait for the daily job). The override alone doesn't
  push.
- **Cron JSON `changed: false` / `reason: unchanged`:** fingerprint
  already matches. Look for `reason: retry_unfetched`, or push manually.
- **Clicked push, got 502:** usually a Render deploy, or the old 30s
  worker timeout (fixed). Wait until Matches loads, click again — you
  should get "Update started…" without waiting for every phone.
- **A specific pass never updates:** if it's one of the 38 pre-fix,
  resend (in person or `/admin/pass-remediation`). Push cannot fix those.

---

**New passes reflect the current next match when built. Installed
post-fix Apple passes update on manual push (confirmed). The daily job
retries phones that never came back. Pre-fix / already-Expired passes
need a new file, not another cron.**
