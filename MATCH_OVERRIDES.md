# Match Overrides

> Rewritten Aug 20, 2026 — this used to describe editing `match_overrides.json`
> directly and redeploying. That file is gone; overrides are now a DB table
> with an admin page, so fixing a wrong match takes 30 seconds and no deploy.

## What This Is

football-data.org only returns **Premier League** fixtures. It does **not**
include FA Cup, League Cup, Europa League, or friendlies, and it's
occasionally wrong about a kickoff time. Overrides fix both: add a match
the API doesn't know about, or correct one it has wrong.

## Where

**`/admin/match-overrides`** (password-protected). Add, edit (re-submitting
the same date replaces it), or delete an override — no code change, no
deploy, takes effect immediately.

## Fields

| Field | Required | Notes |
| --- | --- | --- |
| Match date | Yes | The real calendar date of the match. Used for sorting against API fixtures. |
| Opponent | Yes | e.g. "Brighton", "Man City". |
| Kickoff time | Yes | However you want it shown, e.g. "3 PM". |
| Home/Away | Yes | Drives which pass theme (color/wordmark) is used. |
| Venue | No | |
| Pass display text | No | Auto-generated from opponent/date/time if left blank. Fill in only if you want custom wording. |
| Note | No | For your own reference (e.g. "FA Cup — not in API"). |

Each override row also has an `enabled` flag in the DB (defaults on) —
there's no UI toggle for it today; disabling one currently means deleting
it and re-adding if needed later.

## How the app uses overrides

`get_next_match()` (in `match_updates.py`) merges DB overrides into the
football-data.org fixture list by date, then takes the earliest match
whose local calendar date is today or later. This is the same function
driving passes, the mobile pass page, and the daily auto-update job —
one source of truth, so there's no way for the site and the passes to
disagree about what "next match" is.

A far-future cup override cannot skip an earlier Premier League game.
`is_home` on the override is what the pass uses for red vs white.

- **Match not in the API at all** (FA Cup, friendly, etc.): add an
  override for that date. It becomes "next match" once it's the earliest
  upcoming date, override or API fixture.
- **API has the date but the time/display is wrong**: add an override for
  that *same* date — yours takes priority over the API's for that date,
  including `is_home` (which drives the pass color scheme).

**If the pass shows a late-season opponent (e.g. Spurs 12/19) and you
did not add an override:** check `match_overrides` first, then read
[MATCH_UPDATES_SETUP.md](MATCH_UPDATES_SETUP.md). On Aug 30 that happened
with an **empty** overrides table — football-data.org pagination, not
this page.

## After adding or fixing an override

If it changes what "next match" currently is, click **Push Pass Updates
Now** on `/admin/matches` (or just wait for the next daily auto-check) so
already-installed passes actually pick it up — adding the override alone
doesn't push anything to devices by itself. The button returns immediately
("Update started…") and fans out Apple + Google in the background.

## Team names on the pass

Short display names (e.g. "Brighton", "Man City") for API-sourced
fixtures come from `team_abbreviations.py`. An override's `pass_display`
is used exactly as typed, so there's nothing extra to configure there.

---

**See also:** [MATCH_UPDATES_SETUP.md](MATCH_UPDATES_SETUP.md) for how the
automatic push-to-Wallet side of this works.
