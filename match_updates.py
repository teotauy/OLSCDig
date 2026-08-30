#!/usr/bin/env python3
"""
Liverpool FC Match Updates for PassKit passes.
Automatically updates pass fields with upcoming match information.
"""

import os
import json
import sys
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz
from team_abbreviations import format_match_display
import db

# Load environment variables
load_dotenv()

# PassKit configuration
PASSKIT_CONFIG = {
    "PROGRAM_ID": os.getenv("PROGRAM_ID", "3yyTsbqwmtXaiKZ5qWhqTP"),
    "API_BASE": os.getenv("API_BASE", "https://api.pub2.passkit.io"),
    "API_KEY": os.getenv("PASSKIT_API_KEY"),
    "PROJECT_KEY": os.getenv("PASSKIT_PROJECT_KEY"),
    "TIMEZONE": os.getenv("TIMEZONE", "America/New_York"),
}

def get_passkit_headers():
    """Get headers for PassKit API requests."""
    return {
        "Authorization": f"Bearer {PASSKIT_CONFIG['API_KEY']}",
        "Content-Type": "application/json",
        "X-Project-Key": PASSKIT_CONFIG["PROJECT_KEY"]
    }

_fixtures_cache = {"fetched_at": None, "matches": None}
FIXTURES_CACHE_TTL_SECONDS = 120


def get_liverpool_fixtures():
    """Cached wrapper around the real fetch, keyed on a short TTL.

    Every Apple Wallet device that refreshes calls this once -- a single
    push notification can wake dozens of devices within the same few
    seconds (confirmed for real on Aug 24: a 95-device push fanout each
    independently called this uncached, which tripped football-data.org's
    own rate limit and, combined with concurrent load our Flask dev
    server couldn't absorb, took the whole app down). The answer is
    identical for everyone within this window, so there's no reason for
    it to hit the real API more than once per TTL."""
    now = datetime.now(pytz.UTC)
    cached_at = _fixtures_cache["fetched_at"]
    if cached_at and (now - cached_at).total_seconds() < FIXTURES_CACHE_TTL_SECONDS:
        return _fixtures_cache["matches"]
    matches = _fetch_liverpool_fixtures_uncached()
    _fixtures_cache["fetched_at"] = now
    _fixtures_cache["matches"] = matches
    return matches


def _team_matches(headers, team_id, status, limit=50):
    """One football-data.org team-matches call. Returns [] on any error
    so a secondary LIVE fetch can't wipe the main SCHEDULED list."""
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
    params = {"status": status, "limit": limit}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return list(response.json().get("matches") or [])
    except Exception as e:
        print(f"Warning: football-data.org status={status} failed: {e}")
        return []


def _fetch_liverpool_fixtures_uncached():
    """
    Get Liverpool FC fixtures from football-data.org API (all competitions).
    Returns upcoming matches sorted by date; display time is in configured TIMEZONE.
    """
    # Set FOOTBALL_DATA_API_KEY in .env (get a key at https://www.football-data.org/)
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise ValueError("FOOTBALL_DATA_API_KEY is not set in environment")
    headers = {
        "X-Auth-Token": api_key
    }
    
    team_id = 64  # Liverpool FC
    
    try:
        # status=SCHEDULED is the query that actually returns upcoming
        # fixtures (they come back labeled TIMED). Confirmed Aug 30
        # against the live API: comma-separated statuses with limit 25
        # does NOT mean "next 25" — it returns the last 25 of the
        # season, so the "next match" jumped to Spurs on 12/19.
        # IN_PLAY/PAUSED (LIVE) is a separate call so match-day passes
        # still show today's game until the calendar day is over.
        scheduled = _team_matches(headers, team_id, "SCHEDULED", limit=50)
        live = _team_matches(headers, team_id, "LIVE", limit=10)
        by_id = {}
        for match in scheduled + live:
            by_id[match["id"]] = match
        fixtures = sorted(by_id.values(), key=lambda m: m["utcDate"])

        print(f"📡 Fetched {len(fixtures)} fixtures from football-data.org")
        for match in fixtures[:1]:
            print(f"   Raw UTC time: {match.get('utcDate')}")
        
        display_timezone = pytz.timezone(PASSKIT_CONFIG["TIMEZONE"])
        today_local = datetime.now(display_timezone).date()

        # Fetch every active override once, up front — not per fixture. Each
        # DB round-trip here costs ~1.3s (no connection pooling), so doing
        # this inside the loop below turned a fast local lookup into a
        # 25-fixture-long chain of network calls (~30s total) the moment
        # overrides moved off the JSON file and onto the DB.
        overrides_by_date = {
            o["match_date"].strftime("%Y-%m-%d"): o
            for o in db.get_active_upcoming_match_overrides(today_local)
        }

        # Process fixtures
        upcoming_matches = []
        for match in fixtures:
            home_team = match["homeTeam"]["name"]
            away_team = match["awayTeam"]["name"]
            match_date = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
            local_time = match_date.astimezone(display_timezone)
            if local_time.date() < today_local:
                continue

            # Check for manual override BEFORE processing
            date_key = local_time.strftime("%Y-%m-%d")
            override_row = overrides_by_date.get(date_key)
            override = None
            if override_row:
                override = {
                    "opponent": override_row["opponent"],
                    "date": override_row.get("display_date") or "",
                    "time": override_row.get("display_time") or "",
                    "pass_display": override_row.get("pass_display") or "",
                    "venue": override_row.get("venue") or "",
                    "is_home": bool(override_row.get("is_home", False)),
                }

            # Determine if Liverpool is home or away
            if home_team == "Liverpool FC":
                opponent = away_team
                venue = "Anfield"
                is_home = True
            else:
                opponent = home_team
                venue = match.get("venue", "Away")
                is_home = False
            
            # If override exists, use it (including its is_home — that's
            # what drives the pass color scheme).
            if override:
                full_date = local_time.strftime("%A, %B %d")
                if override.get("date"):
                    try:
                        override_date = datetime.strptime(
                            f"{override['date']} {match_date.year}", "%m/%d %Y"
                        )
                        full_date = override_date.strftime("%A, %B %d")
                    except ValueError:
                        pass
                sort_key = match_date.strftime("%Y-%m-%dT%H:%M:%S")
                upcoming_matches.append({
                    "opponent": override["opponent"],
                    "date": override["date"] or local_time.strftime("%-m/%-d"),
                    "time": override["time"],
                    "venue": override.get("venue") or venue,
                    "is_home": bool(override.get("is_home", is_home)),
                    "full_date": full_date,
                    "kickoff": override["time"],
                    "pass_display": override["pass_display"],
                    "sort_key": sort_key,
                })
                continue
            
            if match == fixtures[0]:
                print(f"   Display time ({PASSKIT_CONFIG['TIMEZONE']}): {local_time.strftime('%Y-%m-%d %H:%M %Z')}")
            
            date_str = local_time.strftime("%b %d")
            
            # Format time with AM/PM - drop :00 for exact hours
            hour = local_time.hour
            minute = local_time.minute
            
            # Determine AM/PM
            am_pm = "AM" if hour < 12 else "PM"
            
            # Convert to 12-hour format
            if hour == 0:
                display_hour = 12
            elif hour <= 12:
                display_hour = hour
            else:
                display_hour = hour - 12
            
            # Format time string
            if minute == 0:
                time_str = f"{display_hour} {am_pm}"
            else:
                time_str = f"{display_hour}:{minute:02d} {am_pm}"
            
            # Create optimized pass display format
            pass_display = format_match_display(opponent, date_str, time_str)
            
            sort_key = match_date.strftime("%Y-%m-%dT%H:%M:%S")
            upcoming_matches.append({
                "opponent": opponent,
                "date": date_str,
                "time": time_str,
                "venue": venue,
                "is_home": is_home,
                "full_date": local_time.strftime("%A, %B %d"),
                "kickoff": time_str,
                "pass_display": pass_display,
                "sort_key": sort_key,
            })
        
        # Add override-only matches (e.g. FA Cup not in API) and sort by date
        api_dates = {m["sort_key"][:10] for m in upcoming_matches}
        try:
            for override in db.get_active_upcoming_match_overrides(today_local):
                date_key = override["match_date"].strftime("%Y-%m-%d")
                if date_key in api_dates:
                    continue
                if override["match_date"] < today_local:
                    continue
                time_str = (override.get("display_time") or "12:00 PM").strip()
                try:
                    t = datetime.strptime(time_str, "%I:%M %p").time()
                except ValueError:
                    try:
                        t = datetime.strptime(time_str, "%I:%M%p").time()
                    except ValueError:
                        t = datetime.strptime("12:00", "%H:%M").time()
                dt_local = display_timezone.localize(datetime.combine(override["match_date"], t))
                sort_key_utc = dt_local.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%S")
                full_date = override["match_date"].strftime("%A, %B %d")
                display_date = override.get("display_date") or override["match_date"].strftime("%-m/%-d")
                pass_display = override.get("pass_display") or format_match_display(override["opponent"], display_date, time_str)
                upcoming_matches.append({
                    "opponent": override["opponent"],
                    "date": display_date,
                    "time": time_str,
                    "venue": override.get("venue") or "Away",
                    "is_home": bool(override.get("is_home", False)),
                    "full_date": full_date,
                    "kickoff": time_str,
                    "pass_display": pass_display,
                    "sort_key": sort_key_utc,
                })
        except Exception as e:
            print(f"Warning: Could not add override-only matches: {e}")
        upcoming_matches.sort(key=lambda m: m.get("sort_key", ""))
        for m in upcoming_matches:
            m.pop("sort_key", None)
        return upcoming_matches
        
    except Exception as e:
        print(f"Error fetching fixtures: {e}")
        return []


def get_finished_liverpool_matches(limit=15):
    """Recently finished Liverpool matches from football-data.org, for
    filling in results on our own `matches` rows (leaderboard scoring).

    Returns a list of dicts: {date (a date object, UTC), is_home,
    liverpool_goals, opponent_goals}. Computed from score.fullTime's raw
    home/away goal counts rather than the API's own `winner` field, so a
    result can't be wrong just because we misread the meaning of an enum
    value we're not fully certain of.
    """
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise ValueError("FOOTBALL_DATA_API_KEY is not set in environment")
    headers = {"X-Auth-Token": api_key}
    team_id = 64  # Liverpool FC

    url = f"https://api.football-data.org/v4/teams/{team_id}/matches"
    params = {"status": "FINISHED", "limit": limit}
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    results = []
    for match in data.get("matches", []):
        full_time = (match.get("score") or {}).get("fullTime") or {}
        home_goals, away_goals = full_time.get("home"), full_time.get("away")
        if home_goals is None or away_goals is None:
            continue  # e.g. abandoned/no score recorded
        is_home = match["homeTeam"]["name"] == "Liverpool FC"
        match_date = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00")).date()
        results.append({
            "date": match_date,
            "is_home": is_home,
            "liverpool_goals": home_goals if is_home else away_goals,
            "opponent_goals": away_goals if is_home else home_goals,
        })
    return results


def check_manual_override(match_date_str):
    """Check if there's a manual override for this match date (YYYY-MM-DD).
    Returns a dict shaped like the old JSON-file entries, for callers that
    still expect 'date'/'time' keys rather than the DB column names."""
    try:
        row = db.get_active_match_override_for_date(match_date_str)
        if not row:
            return None
        print(f"Using manual override for {match_date_str}: {row.get('note', '')}")
        return {
            "opponent": row["opponent"],
            "date": row.get("display_date") or "",
            "time": row.get("display_time") or "",
            "pass_display": row.get("pass_display") or "",
            "note": row.get("note") or "",
            "venue": row.get("venue") or "",
            "is_home": bool(row.get("is_home", False)),
        }
    except Exception as e:
        print(f"Warning: Could not load match overrides: {e}")
    return None

def _get_forced_next_match_from_overrides():
    """
    If any upcoming manual overrides exist, treat the earliest one as the
    authoritative "next match". This lets us strong-arm cases like FA Cup
    fixtures that the external API doesn't return correctly.
    """
    try:
        # Work in configured display timezone so "today" matches what admins see
        display_tz = pytz.timezone(PASSKIT_CONFIG.get("TIMEZONE", "America/New_York"))
        now_local = datetime.now(display_tz).date()

        candidates = db.get_active_upcoming_match_overrides(now_local)
        if not candidates:
            return None

        # Rows already come back ordered by match_date ascending.
        override = candidates[0]
        override_date = override["match_date"]

        opponent = (override.get("opponent") or "").strip()
        if not opponent:
            return None

        time_str = (override.get("display_time") or "").strip()
        display_date = (override.get("display_date") or "").strip()
        pass_display = (override.get("pass_display") or "").strip()
        full_date = override_date.strftime("%A, %B %d")

        return {
            "opponent": opponent,
            "date": display_date or override_date.strftime("%-m/%-d"),
            "time": time_str,
            "venue": override.get("venue") or "Away",
            "is_home": bool(override.get("is_home", False)),
            "full_date": full_date,
            "kickoff": time_str,
            "pass_display": pass_display or format_match_display(opponent, display_date, time_str),
        }
    except Exception as e:
        print(f"Warning: Could not determine forced next match from overrides: {e}")
        return None

def get_next_match():
    """Get the next upcoming match (or today's, until the calendar day
    in the display timezone is over). Merged API + override list is the
    source of truth; a forced override is only the fallback if the API
    returns nothing, so a far-future cup override can't skip this week's
    Premier League fixture.
    """
    fixtures = get_liverpool_fixtures()
    if fixtures:
        return fixtures[0]
    return _get_forced_next_match_from_overrides()

def update_pass_fields(match_data):
    """Update PassKit pass fields with match information."""
    if not match_data:
        print("No match data to update")
        return False
    
    # Get all passes for the program
    url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/list/{PASSKIT_CONFIG['PROGRAM_ID']}"
    
    payload = {
        "filters": {
            "limit": 1000,
            "offset": 0,
            "orderBy": "created",
            "orderAsc": True
        }
    }
    
    try:
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        response.raise_for_status()
        
        # Parse NDJSON response
        passes = []
        for line in response.text.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    if 'result' in data:
                        passes.append(data['result'])
                except json.JSONDecodeError:
                    pass
        
        print(f"Found {len(passes)} passes to update")
        
        print(f"📝 Updating passes with: '{match_data['pass_display']}' ({len(match_data['pass_display'])} chars)")
        
        # Update each pass using the correct PassKit endpoint
        update_url = f"{PASSKIT_CONFIG['API_BASE']}/members/member"
        
        success_count = 0
        failed_count = 0
        
        for pass_data in passes:
            member_id = pass_data.get("id")
            external_id = pass_data.get("externalId")
            
            if not member_id:
                failed_count += 1
                continue
            
            # Update ALL passes with the next match
            # (removed the filter to update everyone)
            
            # Update pass using PUT method with passOverrides
            # We need to include the person data to avoid validation errors
            person_data = pass_data.get("person", {})
            
            update_payload = {
                "programId": PASSKIT_CONFIG["PROGRAM_ID"],
                "id": member_id,
                "person": {
                    "displayName": person_data.get("displayName", "Unknown"),
                    "emailAddress": person_data.get("emailAddress", ""),
                    "surname": person_data.get("surname", ""),
                    "forename": person_data.get("forename", "")
                },
                "metaData": {
                    "nextMatch": match_data['pass_display']
                }
            }
            
            # Add externalId if available (some members might not have it)
            if external_id:
                update_payload["externalId"] = external_id
            
            try:
                response = requests.put(update_url, headers=get_passkit_headers(), json=update_payload, timeout=30)
                response.raise_for_status()
                success_count += 1
                
                # Show progress every 50 updates
                if success_count % 50 == 0:
                    print(f"  ✅ Updated {success_count} passes...")
                    
            except Exception as e:
                failed_count += 1
                if failed_count <= 5:  # Only show first 5 errors
                    print(f"  ❌ Failed to update pass {member_id}: {e}")
        
        print(f"\n📊 Update Results:")
        print(f"  ✅ Successfully updated: {success_count} passes")
        print(f"  ❌ Failed to update: {failed_count} passes")
        print(f"  📱 Pass display: '{match_data['pass_display']}'")
        
        return success_count > 0
        
    except Exception as e:
        print(f"Error fetching passes: {e}")
        return False

def send_match_reminder_notification(match_data):
    """Prepare match reminder notification (NOT SENDING - requires buy-in)."""
    if not match_data:
        return False
    
    # Prepare notification content but DO NOT SEND
    if match_data['is_home']:
        message = f"🏠 Liverpool vs {match_data['opponent']} at Anfield - {match_data['full_date']} at {match_data['kickoff']}"
    else:
        message = f"✈️ Liverpool vs {match_data['opponent']} - {match_data['full_date']} at {match_data['kickoff']}"
    
    print(f"📱 [NOT SENDING] Match reminder would be: {message}")
    print("⚠️  Push notifications require board buy-in before enabling")
    
    # TODO: Enable when approved by board
    # This would send to all members with passes in their wallets
    
    return True

def main():
    """Main function to update passes with next match info."""
    print("🏆 Liverpool FC - Match Updates")
    print("=" * 40)
    
    # Get next match
    print("📅 Fetching upcoming fixtures...")
    next_match = get_next_match()
    
    if not next_match:
        print("❌ No upcoming matches found")
        return
    
    print(f"⚽ Next match: Liverpool vs {next_match['opponent']}")
    print(f"📅 Date: {next_match['full_date']}")
    print(f"🕐 Time: {next_match['kickoff']}")
    print(f"🏟️ Venue: {next_match['venue']}")
    print(f"🏠 Home: {'Yes' if next_match['is_home'] else 'No'}")
    
    # Show what will be displayed on passes
    print("\n" + "=" * 50)
    print("📱 TEXT THAT WILL APPEAR ON PASSES:")
    print("=" * 50)
    print(f"   '{next_match['pass_display']}'")
    print("=" * 50)
    print(f"   Length: {len(next_match['pass_display'])} characters")
    print()
    
    # Ask for confirmation (auto-confirm in non-interactive mode)
    if not sys.stdin.isatty():
        confirm = "yes"
        print("✅ Auto-confirming update (non-interactive)")
    else:
        while True:
            confirm = input("✅ Confirm update? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                break
            elif confirm in ['no', 'n']:
                print("❌ Update cancelled by user")
                return
            else:
                print("⚠️  Please enter 'yes' or 'no'")
    
    # Update passes
    print("\n📱 Updating passes...")
    success = update_pass_fields(next_match)
    
    if success:
        print("✅ Passes updated successfully!")
        
        # Prepare reminder notification (NOT SENDING)
        print("\n📢 Preparing match reminder...")
        send_match_reminder_notification(next_match)
        
    else:
        print("❌ Failed to update passes")

if __name__ == "__main__":
    main()
