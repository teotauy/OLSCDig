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
| PassKit "get latest pass" — `If-Modified-Since` / `304` support | ❌ | **Real gap found tonight during this audit**, not a guess: the endpoint always rebuilds and returns 200 with fresh content; it never reads the incoming `If-Modified-Since` header to return a cheap 304 when nothing changed. Confirmed via independent source that Apple's spec expects this. | Not broken (degrades to "always send full data," not "always fail"), but should be built properly — add `If-Modified-Since` handling, return 304 when the pass's content hasn't changed since that timestamp. |
| APNs push delivery | ⚠️ | Got a real, structurally-valid rejection (`400 BadDeviceToken`) from Apple's live production push servers using the real cert — strong evidence the mTLS handshake, topic, and cert chain are correct. | Never confirmed a real push actually reaches a real device and the device visibly updates. Needs one real device with a real installed pass. |
| Resend quota header names/values (`x-resend-daily-quota` etc.) | ❌ | Verified only against Resend's documentation text and mocked HTTP responses in tests. **Never seen a real API response's actual headers.** Docs can be wrong or stale — same risk class as the Apple bug. | Next real send (once you approve one) — log and inspect the actual raw headers Resend returns, confirm they match what the code parses. |
| Google Wallet — real completed save on a real device | ❌ | Confirmed via your own screenshot that the pre-save screen renders clean (no demo-mode banner). **Never confirmed a real "Add" tap actually completes** and produces a working pass. | Needs one real device (yours or a volunteer's) to actually tap Add and confirm the pass lands correctly in Google Wallet. |

## Tier 2 — will get exercised naturally soon, but unverified until then

| Item | Status | What's actually been confirmed | What's still needed |
| --- | --- | --- | --- |
| `get_finished_liverpool_matches()` (leaderboard results sync) | ❌ | Built against football-data.org's documented score schema (`score.fullTime.home/away`), confirmed the schema exists via their docs. **Zero verification against a real finished match** — none has been played yet this season. | After the Aug 23 match: manually check the leaderboard picked up the correct real result before trusting it silently going forward. |
| Squarespace → Make.com → `/api/squarespace/order` | ❌ | Our endpoint tested with hand-built payloads matching Squarespace's *documented* field names. The Make.com scenario itself doesn't exist yet — never received a real payload from a real order. | Once the Make scenario is built: run one real test order through it before trusting it unattended. |
| CSV import | ✅ | Real production run: 126 real members imported successfully (confirmed via your own screenshot). Synthetic edge cases (bad rows, duplicate emails, Squarespace-style headers, crash-mid-import) also tested. | Lower risk — reasonably well covered already. |

## Tier 3 — worth checking, lower urgency

| Item | Status | What's actually been confirmed | What's still needed |
| --- | --- | --- | --- |
| Legacy PassKit-tied fallback routes (`/legacy/passkit/add-member`, `/update-match`, `/resend-welcome`) | ❌ | Untouched and untested this entire project. The headcount endpoint that *was* tied to the same legacy PassKit API was found silently 500ing in production — real reason to suspect these siblings might be broken too. | Quick pass: hit each one and see if it actually works, or just confirm they're truly unreachable/unlinked and retire them outright instead of leaving broken code as a fallback that doesn't work. |
| Email dark mode CSS | ⚠️ | Confirmed via generated-HTML string checks that the `prefers-color-scheme` block and `color-scheme` meta tags are present. **Never visually confirmed in a real mail client.** | Check on the next real send you approve — look at it in both light and dark mode on a real phone. |
| Email subject line / preheader text | ⚠️ | Confirmed via generated-HTML string checks only. | Same — confirm in a real inbox on the next approved send. |
| Render free-tier behavior (750hr cap, spin-down) | ⚠️ | Based on Render's own docs; partially corroborated by real production logs (confirms the app *is* running as expected on Render). | No action needed unless behavior diverges from what's documented. |

---

## Immediate next actions, in order

1. **Fix the `If-Modified-Since`/304 gap** in the PassKit "get latest pass" endpoint — real, identified, no dependency on you approving anything, safe to do now.
2. **Audit the three legacy PassKit fallback routes** — confirm broken-and-should-be-retired vs. actually fine. No real member impact either way since they're unlinked, but "unlinked and untested" shouldn't also mean "silently broken and left in place."
3. **When you're ready to approve exactly one real send**: use it to close two gaps at once — confirm the real Resend quota headers match what the code expects, and visually confirm the dark-mode email in a real inbox.
4. **When someone's near a real Android phone**: close the Google Wallet real-save gap.
5. **Aug 23, after the first match**: manually verify the leaderboard's auto-synced result against the real score before trusting that pipeline unattended going forward.
