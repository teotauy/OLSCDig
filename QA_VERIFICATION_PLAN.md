# QA & Verification Plan

Started Aug 20, 2026, after a real production bug: the Apple Wallet push
webhook URL had a doubled `/v1` segment, silently 404ing on every real
device's registration attempt since the feature shipped. It was verified
against my own code's internal consistency, never against Apple's actual
documented behavior — the two are not the same thing, and treating them as
equivalent is what caused the miss.

**The standard from here on:** anything that talks to a real external
system (Apple, Google, Resend, Squarespace/Make, football-data.org, Render)
gets checked against that system's actual documented behavior, or actual
observed behavior in production, before it's called done. Testing that my
own code agrees with my own assumptions is not verification — it's the
exact failure mode that caused this.

This doc tracks every external integration point, its real verification
status, and what's still needed to close each gap. Updated as items get
closed, not left to rot.

Status key: ✅ verified against real external behavior · ⚠️ built correctly
per spec but never exercised against the real system · ❌ known gap or
unconfirmed assumption.

---

## Tier 1 — same failure class as the bug that just happened

Real member impact if wrong, and built the same way (spec-read + self-tested)
as the thing that broke.

| Item | Status | What's actually been confirmed | What's still needed |
| --- | --- | --- | --- |
| PassKit webServiceURL / device registration path | ✅ | Fixed and replayed against a real serial number from production logs (404→201). Route path and query param name (`passesUpdatedSince`) independently cross-checked against external documentation, not just my own spec-reading. | None — this specific bug is closed. |
| PassKit "list updatable passes" response shape (200 body / 204 empty) | ⚠️ | Built to spec, tested only via Flask test client against my own requests. | Confirm against a real Apple Wallet client's actual request/response cycle once a real device has a pass with the fixed webServiceURL installed. |
| PassKit "get latest pass" — `If-Modified-Since` / `304` support | ✅ | **Built and closed same day.** Real gap found during this audit (the endpoint always rebuilt and returned 200, never honoring `If-Modified-Since`), not a guess. Fixed and verified through the real route with 4 cases: fresh/200, matching-timestamp/304, stale-timestamp/200, 200-again after a real content change. | None — closed. |
| APNs push delivery | ⚠️ | Got a real, structurally-valid rejection (`400 BadDeviceToken`) from Apple's live production push servers using the real cert — strong evidence the mTLS handshake, topic, and cert chain are correct. | Never confirmed a real push actually reaches a real device and the device visibly updates. Needs one real device with a real installed pass. |
| Resend quota header names/values (`x-resend-daily-quota` etc.) | ✅ | **Confirmed against a real response, Aug 20** — the first real bulk send (5 members) returned real headers: `daily_quota_raw`, `monthly_quota_raw`, and `ratelimit_remaining` all parsed correctly. Real headers exposed a *different* real bug in the process — see next row. | None — the headers themselves parse correctly. |
| Resend `reset_at` — was conflating the rate-limit window with the daily/monthly quota | ✅ (found + fixed Aug 20) | The first real response showed `reset_at` landing 0.57 seconds after `checked_at`. Checked Resend's actual docs: `ratelimit-reset` is the ~1-second burst-rate window, not the daily/monthly quota — and Resend documents **no** reset-time header for those quotas at all. Before this fix, a real daily-quota 429 would have shown "resets in a few seconds" (false reassurance; the real wait can be up to 24h). Fixed: captures Resend's real error `name` (`rate_limit_exceeded` / `daily_quota_exceeded` / `monthly_quota_exceeded`) and gives each an honest message; dropped the misleading countdown from the usage badge entirely. | None — closed. Exactly the kind of gap this doc exists to catch, found on the first real send after adopting the standard. |
| Google Wallet — real completed save on a real device | ❌ | Confirmed via your own screenshot that the pre-save screen renders clean (no demo-mode banner). **Never confirmed a real "Add" tap actually completes** and produces a working pass. | Needs one real device (yours or a volunteer's) to actually tap Add and confirm the pass lands correctly in Google Wallet. |
| Google Wallet — match-week auto-update (new, Aug 20) | ⚠️ | Built the same way Apple's push-update works: `google_object_id`/`google_class_id` are now persisted at issuance ([db.py](db.py) `set_google_wallet_object`), and `_notify_google_pass_updates()` PATCHes every issued object when next-match changes, wired into the same three trigger points as Apple's push. **Verified against Google's real live API**: manually inserted a real test object under our real issuer class, called the actual `patch_google_wallet_object` function against it, and confirmed via an independent GET (not just the PATCH response echo) that `textModulesData` and `hexBackgroundColor` genuinely changed server-side. Also confirmed the real production `_issue_member_pkpass` path persists the ids correctly, and that `_notify_google_pass_updates()` correctly no-ops (logs, doesn't crash) for an object nobody's saved yet — got a real 404 from Google for exactly that case. | Same gap as the row above: never watched a PATCH actually reach a pass sitting in a real person's Google Wallet and visibly update on-screen. Existing pre-Aug-20 Google Wallet saves (if any) have no `google_object_id` on file and won't auto-update until that member is resent a pass. |

## Tier 2 — will get exercised naturally soon, but unverified until then

| Item | Status | What's actually been confirmed | What's still needed |
| --- | --- | --- | --- |
| `get_finished_liverpool_matches()` (leaderboard results sync) | ❌ | Built against football-data.org's documented score schema (`score.fullTime.home/away`), confirmed the schema exists via their docs. **Zero verification against a real finished match** — none has been played yet this season. | After the Aug 23 match: manually check the leaderboard picked up the correct real result before trusting it silently going forward. |
| Squarespace → Make.com → `/api/squarespace/order` | ❌ | Our endpoint tested with hand-built payloads matching Squarespace's *documented* field names. The Make.com scenario itself doesn't exist yet — never received a real payload from a real order. | Once the Make scenario is built: run one real test order through it before trusting it unattended. |
| CSV import | ✅ | Real production run: 126 real members imported successfully (confirmed via your own screenshot). Synthetic edge cases (bad rows, duplicate emails, Squarespace-style headers, crash-mid-import) also tested. | Lower risk — reasonably well covered already. |

## Tier 3 — worth checking, lower urgency

| Item | Status | What's actually been confirmed | What's still needed |
| --- | --- | --- | --- |
| Legacy PassKit-tied fallback routes (`/legacy/passkit/add-member`, `/update-match`, `/resend-welcome`) | ⚠️ | All three pages load fine (200). Deliberately stopped there — confirming their *forms* actually work means submitting to the live PassKit API, a real external system I'm not touching without explicit sign-off after tonight. | Needs your call: worth actually testing the PassKit API path, or just retire these three since they're unlinked and the DB-backed system replaced them anyway? |
| Email dark mode CSS | ⚠️ | Confirmed via generated-HTML string checks that the `prefers-color-scheme` block and `color-scheme` meta tags are present. **Never visually confirmed in a real mail client.** | Check on the next real send you approve — look at it in both light and dark mode on a real phone. |
| Email subject line / preheader text | ⚠️ | Confirmed via generated-HTML string checks only. | Same — confirm in a real inbox on the next approved send. |
| Render free-tier behavior (750hr cap, spin-down) | ⚠️ | Based on Render's own docs; partially corroborated by real production logs (confirms the app *is* running as expected on Render). | No action needed unless behavior diverges from what's documented. |

---

## Real sends completed, Aug 20

125 real passes sent and confirmed via the two new bulk-send admin pages
— 40 via `/admin/pass-remediation` (members whose pass predated the
webServiceURL fix) and 85 via `/admin/issue-passes` (members who'd never
had a pass at all), plus 5 sent individually earlier the same day. All
125 confirmed against real `wallet_passes` rows, not just on-screen
success messages. This is what surfaced the real Resend headers above,
and closes most of the practical risk in "does a big batch actually work"
— see `_bulk_issue_and_email`'s pacing in `app.py` for how a future
larger batch stays safe.

## Immediate next actions, in order

1. **Real-device confirmation** — watch a real Apple push and a real
   Google Wallet PATCH actually land on an installed pass and update
   on-screen. The one open item shared by both Tier 1 wallet rows above;
   needs physical phones, not code.
2. **Audit the three legacy PassKit fallback routes** — confirm
   broken-and-should-be-retired vs. actually fine. No real member impact
   either way since they're unlinked, but "unlinked and untested"
   shouldn't also mean "silently broken and left in place."
3. **Squarespace → Make.com, one real order** — endpoint's tested against
   hand-built payloads; the Make scenario and a real purchase through it
   are still unconfirmed.
4. **Aug 23, after the first match**: manually verify the leaderboard's
   auto-synced result against the real score before trusting that
   pipeline unattended going forward.
