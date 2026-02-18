# ⚽ Match Overrides (match_overrides.json)

## What This Is

`match_overrides.json` lets you **override or add** the next-match info that appears on passes. The football-data.org API only returns **Premier League** fixtures for the team; it does **not** include FA Cup, League Cup, or other competitions. Overrides fix that and also let you correct wrong times from the API.

## When to Add an Override

1. **Match not in the API** – FA Cup, League Cup, Europa League, friendlies, etc. Add an **override-only** entry (date that isn’t in the API). The app merges these with API fixtures and sorts by date so the real “next match” can be an override.
2. **API time wrong** – Kickoff is correct in the API but displayed wrong (timezone/format). Add an override for that **exact date** (YYYY-MM-DD). The app will use your time/text instead of the API for that fixture.
3. **Custom display** – You want a specific opponent name or time format on the pass (e.g. “3 PM” instead of “10:00 AM” in another timezone).

## File Location and Format

- **File:** `match_overrides.json` in the project root.
- **Enabled:** Set `"enabled": true` at the top level. If `false`, overrides are ignored.

Each override is keyed by **date in YYYY-MM-DD** (e.g. `"2026-02-14"`). Example:

```json
{
  "overrides": {
    "2026-02-14": {
      "opponent": "Brighton",
      "time": "3 PM",
      "date": "2/14",
      "pass_display": "Brighton | 2/14 3 PM",
      "note": "FA Cup - not in API"
    }
  },
  "enabled": true
}
```

### Fields per override

| Field          | Required | Description |
|----------------|----------|-------------|
| `opponent`     | Yes      | Name shown in UI and used for display (e.g. "Brighton", "Man City"). |
| `time`         | Yes      | Kickoff time as you want it on the pass (e.g. "3 PM", "11:30 AM", "2:45PM"). |
| `date`         | Yes      | Short date for pass: `M/D` (e.g. "2/14", "10/19"). |
| `pass_display` | Yes      | Exact string that goes on the pass (e.g. "Brighton \| 2/14 3 PM"). Keep it short. |
| `note`         | No       | For you (e.g. "FA Cup - not in API", "Manual override - ET"). |

- **Override-only (match not in API):** Use the same fields. The date key (e.g. `2026-02-14`) is used for sorting; the app will show this match as “next” when it’s the earliest upcoming override or API fixture.
- **Override for API fixture (wrong time/display):** Use the **same date key** as the API fixture (YYYY-MM-DD). Your override replaces the API data for that date.

## How the App Uses Overrides

- **match_updates.py** (CLI and web app “Update Match”):
  - Fetches scheduled fixtures from the API (PL only).
  - For each API fixture date, if that date exists in `overrides`, it uses the override instead of the API.
  - Then it adds any **override-only** dates (dates in `overrides` that did **not** appear in the API).
  - Sorts all matches (API + override-only) by kickoff and takes the **first** as the next match.
- So the next match can be:
  - The next API fixture (with or without an override for that date), or
  - A future match that exists **only** in overrides (e.g. FA Cup).

## Current Overrides (reference)

As of last update, the file contains:

| Date       | Opponent     | Time      | Note / use case          |
|-----------|--------------|-----------|---------------------------|
| 2026-02-14 | Brighton     | 3 PM      | FA Cup – not in API      |
| 2026-02-08 | Manchester City | 11:30 AM | Manual override (ET)      |
| 2026-01-21 | Marseille    | 3 PM      | Manual time format       |
| 2026-01-17 | Burnley      | 2:45PM    | API time wrong           |

Past dates in the file are harmless; they’re ignored once that date is in the past when computing “next” match.

## Quick Add Checklist

1. Open `match_overrides.json`.
2. Add a new key under `overrides` with date **YYYY-MM-DD** (e.g. `"2026-03-01"`).
3. Set `opponent`, `time`, `date` (M/D), `pass_display`, and optionally `note`.
4. Save. No code change needed.
5. Run **Update Match** (web or `python3 match_updates.py`) so passes refresh.

## Team names on the pass

Short names (e.g. “Brighton”, “Man City”) are defined in `team_abbreviations.py`. If you use a new opponent name in an override, add it there if you want a shortened label; otherwise the override’s `pass_display` is used as-is.

---

**See also:** [MATCH_UPDATES_SETUP.md](MATCH_UPDATES_SETUP.md) for how to run updates locally or from the web app.
