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
| APNs push delivery | ✅ (confirmed Aug 25-29) | **Closed for real.** A real installed pass (owner's own phone) was confirmed showing the correct live next-match text, home theme, and no phantom "Expired" after a real push cycle. Getting there also surfaced and fixed two real bugs in the process (see relevantDate and crash rows below) — this is exactly the kind of thing that only shows up on a real device. | None for the mechanism itself. Still only confirmed on one device/iOS version — broader confirmation happens naturally as more of the ~40 remediation members get resent. |
| Resend quota header names/values (`x-resend-daily-quota` etc.) | ✅ | **Confirmed against a real response, Aug 20** — the first real bulk send (5 members) returned real headers: `daily_quota_raw`, `monthly_quota_raw`, and `ratelimit_remaining` all parsed correctly. Real headers exposed a *different* real bug in the process — see next row. | None — the headers themselves parse correctly. |
| Resend `reset_at` — was conflating the rate-limit window with the daily/monthly quota | ✅ (found + fixed Aug 20) | The first real response showed `reset_at` landing 0.57 seconds after `checked_at`. Checked Resend's actual docs: `ratelimit-reset` is the ~1-second burst-rate window, not the daily/monthly quota — and Resend documents **no** reset-time header for those quotas at all. Before this fix, a real daily-quota 429 would have shown "resets in a few seconds" (false reassurance; the real wait can be up to 24h). Fixed: captures Resend's real error `name` (`rate_limit_exceeded` / `daily_quota_exceeded` / `monthly_quota_exceeded`) and gives each an honest message; dropped the misleading countdown from the usage badge entirely. | None — closed. Exactly the kind of gap this doc exists to catch, found on the first real send after adopting the standard. |
| Google Wallet — real completed save on a real device | ⚠️ (stronger evidence, not fully closed) | Confirmed via your own screenshot that the pre-save screen renders clean (no demo-mode banner). **New evidence Aug 25**: a real match-week push PATCHed 12/133 issued objects successfully (the other 121 correctly 404 — nobody's saved those yet), meaning 12 real people really did complete an "Add to Google Wallet" tap. | Still nobody's personally, visually confirmed the *content* updates correctly on a real Google Wallet screen (only that the server-side PATCH succeeded). Lower priority than it was — real usage is happening either way. |
| Google Wallet — match-week auto-update (new, Aug 20) | ✅ (confirmed at real scale, Aug 25) | Built the same way Apple's push-update works: `google_object_id`/`google_class_id` persisted at issuance, `_notify_google_pass_updates()` PATCHes every issued object on next-match change. Verified twice against Google's real live API in isolation (insert-then-patch-then-independent-GET), then verified **at real production scale**: a real match-week push hit all 133 issued objects, 12 succeeded (real saves), 121 correctly no-op'd (unsaved, expected 404s), zero crashes. | None — closed. Existing pre-Aug-20 Google saves (if any) still have no `google_object_id` on file and won't auto-update until that member is resent a pass — same known gap as the Apple side. |

| `relevantDate` causing installed passes to show as "Expired" | ✅ (found + fixed Aug 24) | **Real, member-visible bug found via a real installed pass**, not a guess: Apple Wallet shows a pass as Expired the instant `relevantDate` is in the past (confirmed against Apple's own developer forums), and ours was tied to a manually-managed field nobody updates as time passes. Removed entirely; verified a fresh pass no longer includes the field, and confirmed on a real device after reinstall that the phantom-Expired state clears. | None — closed. One caveat surfaced along the way, not a code bug: an *already-flagged* Expired pass may not clear via push alone (undocumented anywhere, checked multiple sources) — delete-and-reinstall is the guaranteed path, which is already the plan for the remediation batch anyway. |
| Season-long `expirationDate` | ✅ | Added per your call, separate from the relevantDate fix — one fixed far-future date (`seasons.ends_on`, currently 2027-06-10) can't trigger the same bug since it's never in the past for an active pass. Verified on a real freshly-built pass. | None — closed. |
| Production crash under real push-notification load | ✅ (found + fixed Aug 24, re-verified Aug 25) | **Real incident, not a hypothetical**: triggering a real push woke ~95 devices at once; each independently hit football-data.org with zero caching (tripping their rate limit) while the app was still running Flask's dev server (explicitly not meant for concurrent traffic) — it crashed (502/503), confirmed via Render logs. Fixed both causes (fixtures now cached 120s; switched to gunicorn, 1 process/8 threads). **Re-verified for real**: the exact same push scenario (marking a new match current) ran again on Aug 25 — 96/96 Apple pushed, app stayed up throughout. | None — closed, and re-tested against a real repeat of the failure scenario, not just a smoke test. |
| Redundant second push on every `admin_match_set_current` | ✅ (found + fixed Aug 25) | Found via the above: marking a match "current" (a scanner/headcount-only action since relevantDate no longer depends on it) was *also* firing a full wallet push — a leftover coupling from before the relevantDate fix. Removed; verified the DB update still works and the push genuinely no longer fires (via a fake notifier that raises if called). | None — closed. The daily cron is now the only automatic trigger, roughly once a week as intended. |
| Venue location (`locations` field) for lock-screen alerts | ⚠️ (bug found + fixed Aug 25, new value untested) | **Real matchday test, Aug 25**: zero lock-screen pop-ups at the actual venue. Checked the hardcoded coordinates against the real address (481 5th Ave, Brooklyn) — off by ~220m, with no documented source for the original value. Corrected via real geocoding; verified a fresh pass now carries the right coordinates. | Never tested at the venue with the corrected coordinates — that requires being physically there. Also needs the phone's own settings checked (Location Services "While Using"/"Always" for Wallet, "Allow Access When Locked") — untested independent variable, could still block the alert even with correct coordinates. |
| `matches.is_current` / scanner default target | ✅ | Was stuck on a finished match (Newcastle) with no automatic mechanism to advance it — fixed manually for Forest (Aug 29), confirmed headcount and scanner default correctly read against it, and confirmed 3 real check-ins recorded correctly against the right match on the day. | Still a **manual** step every match week (no automation creates the next match row or flips `is_current` on its own) — not a bug, just a real recurring task worth remembering. |
| Volunteer door access, scoped and revocable | ✅ | Built in response to a real gap (volunteers previously needed the full admin password to scan). Verified end-to-end against the real DB: create → redeem in a separate session → confirmed scanner-only access (blocked from real admin pages) → revoked from a different session → confirmed the original session lost access on its very next request, without needing to log out. | None — closed. |
| Auth security review (open redirect, OAuth fail-open, timing-unsafe comparisons) | ✅ | Found via a full code-level security review, not reported by anyone: `next=` redirect on login/OAuth callback had no validation (open redirect); a failed Google userinfo call granted admin access anyway, skipping the email allowlist entirely; two internal-secret checks used non-constant-time comparison. All three fixed and verified with real request tests (malicious `next=` rejected, simulated failed userinfo call now rejects the login). | None for these three. `FLASK_SECRET_KEY` was also found unset in Render (hardcoded fallback in use) during this review — fixed by the user setting a real value; the 138 existing encrypted tokens were migrated to the new key first so nothing broke. No CSRF tokens on admin forms — lower priority, meaningfully mitigated already by `SESSION_COOKIE_SAMESITE=Lax`. |

## Tier 2 — will get exercised naturally soon, but unverified until then

| Item | Status | What's actually been confirmed | What's still needed |
| --- | --- | --- | --- |
| `get_finished_liverpool_matches()` (leaderboard results sync) | ✅ (confirmed Aug 25) | **Real match, real result**: Newcastle (Aug 23) was automatically synced with the correct real score (a draw) by the very next day's cron run — confirmed directly against the `matches` table, not just assumed. | None — closed. |
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

## Real sends completed, Aug 20-23 — and one still deliberately not

109 real first-time passes sent via `/admin/issue-passes` (85 on Aug 20,
19 more on Aug 23 as new members got added), plus 5 sent individually —
all confirmed against real `wallet_passes` rows, not just on-screen
success messages. This is what surfaced the real Resend headers above,
and closes most of the practical risk in "does a big batch actually
work" — see `_bulk_issue_and_email`'s pacing in `app.py`.

**Correction to an earlier version of this doc**: it previously said 40
members were also resent via `/admin/pass-remediation` on Aug 20. That
never actually happened — checked directly against the DB (Aug 25): 38
pre-fix stale passes still exist. The tool was built and verified with
a fake sender, but sending was deliberately held back to see whether the
automatic push alone would fix things first (it can't, for this specific
cohort — their devices can never successfully register at all, so no
push can ever reach them). Two of the original 40 members personally
checked in fine at the real Forest match on Aug 29 (confirming a stale
pass still scans correctly at the door) while still carrying frozen,
pre-fix pass content. Remediation for the remaining 38 is still an open,
deliberate decision — see Outstanding below.

## Immediate next actions, in order

1. **Re-run the "does the automatic cycle work unattended" test — reset
   again as of Aug 30.** This test has now been accidentally invalidated
   twice by the same root cause: see
   [ISSUE_PASS_VERIFICATION_MUTATES_REAL_DATA.md](ISSUE_PASS_VERIFICATION_MUTATES_REAL_DATA.md).
   Fix that first (or at minimum, don't touch member id 8's pass again
   for any reason), then check whether it picks up the next fixture
   change on its own with zero manual intervention.
2. **Run Pass Remediation for the remaining 38** — deliberately not done
   yet. Tool's built and verified; this is a "when," not a "how," decision
   at this point.
3. **Re-test the venue location fix at the venue itself** — the
   coordinates are corrected and verified server-side, but never
   confirmed against a real lock-screen alert in person. Also check the
   phone's own Location Services / lock-screen settings for Wallet, since
   either one alone could still block the alert regardless of the other.
4. **Audit the three legacy PassKit fallback routes** — confirm
   broken-and-should-be-retired vs. actually fine. No real member impact
   either way since they're unlinked, but "unlinked and untested"
   shouldn't also mean "silently broken and left in place."
5. **Squarespace → Make.com, one real order** — endpoint's tested against
   hand-built payloads; the Make scenario and a real purchase through it
   are still unconfirmed.
6. **The mobile admin hub page** (huge-button scan/lookup/add-member
   page) — proposed, approved in concept, never built. Lowest urgency of
   the open items; purely a convenience feature.
