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

`get_next_match()` (in `match_updates.py`) checks for a forced override
first (`_get_forced_next_match_from_overrides()` in the same file), and
uses the earliest one if it's actually upcoming. Otherwise it falls back
to the earliest `SCHEDULED` fixture from football-data.org. This is the
same function driving passes, the mobile pass page, and the daily
auto-update job — one source of truth, so there's no way for the site and
the passes to disagree about what "next match" is.

- **Match not in the API at all** (FA Cup, friendly, etc.): add an
  override for that date. It becomes "next match" once it's the earliest
  upcoming date, override or API fixture.
- **API has the date but the time/display is wrong**: add an override for
  that *same* date — yours takes priority over the API's for that date.

## After adding or fixing an override

If it changes what "next match" currently is, click **Push Pass Updates
Now** on `/admin/matches` (or just wait for the next daily auto-check) so
already-installed passes actually pick it up — adding the override alone
doesn't push anything to devices by itself.

## Team names on the pass

Short display names (e.g. "Brighton", "Man City") for API-sourced
fixtures come from `team_abbreviations.py`. An override's `pass_display`
is used exactly as typed, so there's nothing extra to configure there.

---

**See also:** [MATCH_UPDATES_SETUP.md](MATCH_UPDATES_SETUP.md) for how the
automatic push-to-Wallet side of this works.
