#!/usr/bin/env python3
"""
Team name abbreviations for pass display optimization.
Converts long team names to short, recognizable abbreviations.
"""

TEAM_ABBREVIATIONS = {
    # Premier League teams
    "Arsenal FC": "Arsenal",
    "Aston Villa FC": "Aston Villa", 
    "AFC Bournemouth": "Bournemouth",
    "Bournemouth": "Bournemouth",
    "Brentford FC": "Brentford",
    "Brighton & Hove Albion FC": "Brighton",
    "Burnley FC": "Burnley",
    "Chelsea FC": "Chelsea",
    "Crystal Palace FC": "Crystal Palace",
    "Everton FC": "Everton",
    "Fulham FC": "Fulham",
    "Ipswich Town FC": "Ipswich",
    "Leeds United FC": "Leeds",
    "Leicester City FC": "Leicester",
    "Liverpool FC": "Liverpool",
    "Manchester City FC": "Man City",
    "Manchester United FC": "Man U",
    "Newcastle United FC": "Newcastle",
    "Norwich City FC": "Norwich",
    "Nottingham Forest FC": "Forest",
    "Sheffield United FC": "Sheffield",
    "Southampton FC": "Southampton",
    "Sunderland AFC": "Sunderland",
    "Tottenham Hotspur FC": "Spurs",
    "Watford FC": "Watford",
    "West Ham United FC": "West Ham",
    "Wolverhampton Wanderers FC": "Wolves",
    
    # European teams (common opponents)
    "FC Barcelona": "Barcelona",
    "Real Madrid CF": "Real Madrid",
    "Bayern Munich": "Bayern",
    "Paris Saint-Germain": "PSG",
    "Atletico Madrid": "Atletico",
    "Juventus FC": "Juventus",
    "AC Milan": "AC Milan",
    "Inter Milan": "Inter",
    "FC Internazionale Milano": "Inter",
    "AS Roma": "Roma",
    "Napoli": "Napoli",
    "Borussia Dortmund": "Dortmund",
    "RB Leipzig": "Leipzig",
    "Ajax Amsterdam": "Ajax",
    "PSV Eindhoven": "PSV",
    "FC Porto": "Porto",
    "Benfica": "Benfica",
    "Celtic FC": "Celtic",
    "Rangers FC": "Rangers",
    "Olympique de Marseille": "Marseille",
    "Qarabağ Ağdam FK": "Qarabag",
    "Galatasaray SK": "Galatasaray",
    "Galatasaray": "Galatasaray",

    # Add more as needed
}

# Common alternate spellings someone might actually type into a manual
# match override -- the dict above only matches football-data.org's exact
# API name ("Tottenham Hotspur FC"). A cup tie override entered as just
# "Tottenham Hotspur" or "Spurs" used to fall through to a bad 14-char
# truncation ("Tottenham Hots") instead of resolving correctly.
_EXTRA_ALIASES = {
    "tottenham": "Spurs",
    "tottenham hotspur": "Spurs",
    "spurs": "Spurs",
    "man united": "Man U",
    "man utd": "Man U",
    "manchester united": "Man U",
    "man u": "Man U",
    "man city": "Man City",
    "manchester city": "Man City",
    "wolves": "Wolves",
    "wolverhampton": "Wolves",
    "wolverhampton wanderers": "Wolves",
    "brighton": "Brighton",
    "brighton and hove albion": "Brighton",
    "brighton & hove albion": "Brighton",
    "brighton hove albion": "Brighton",
    "west ham": "West Ham",
    "west ham united": "West Ham",
    "newcastle": "Newcastle",
    "newcastle united": "Newcastle",
    "nottingham forest": "Forest",
    "forest": "Forest",
    "leeds": "Leeds",
    "leeds united": "Leeds",
    "leicester": "Leicester",
    "leicester city": "Leicester",
    "crystal palace": "Crystal Palace",
    "aston villa": "Aston Villa",
    "bournemouth": "Bournemouth",
    "afc bournemouth": "Bournemouth",
    "sheffield united": "Sheffield",
    "sheffield": "Sheffield",
    "ipswich": "Ipswich",
    "ipswich town": "Ipswich",
    "norwich": "Norwich",
    "norwich city": "Norwich",
    "sunderland": "Sunderland",
}


def _normalize_for_lookup(name):
    """Lowercase and strip a trailing 'FC'/'AFC'/'CF' so 'Tottenham Hotspur
    FC' and a manually-typed 'Tottenham Hotspur' hit the same entry."""
    n = (name or "").strip().lower()
    for suffix in (" fc", " afc", " cf"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
            break
    return n.strip()


# Every existing exact-name key, plus the aliases above, keyed by their
# normalized form -- built once at import time.
_ABBREVIATION_LOOKUP = {_normalize_for_lookup(k): v for k, v in TEAM_ABBREVIATIONS.items()}
for _alias, _short in _EXTRA_ALIASES.items():
    _ABBREVIATION_LOOKUP.setdefault(_alias, _short)


def abbreviate_team_name(full_name):
    """Convert full team name to short abbreviation. Matches the exact
    football-data.org API name ("Tottenham Hotspur FC"), a plain common
    name someone might type into a manual override ("Tottenham Hotspur"),
    or the short form itself ("Spurs") -- case/whitespace-insensitive."""
    if not full_name:
        return ""
    abbr = _ABBREVIATION_LOOKUP.get(_normalize_for_lookup(full_name))
    if abbr is not None:
        return abbr
    stripped = full_name.strip()
    return stripped if len(stripped) <= 14 else stripped[:14]

def format_match_display(opponent, date_str, time_str):
    """Format match info for pass display with optimal character usage."""
    # Abbreviate opponent
    short_opponent = abbreviate_team_name(opponent)
    
    # Use M/D format (no leading zeros for single digits)
    formatted_date = date_str.replace("Oct ", "10/").replace("Nov ", "11/").replace("Dec ", "12/")
    formatted_date = formatted_date.replace("Jan ", "1/").replace("Feb ", "2/").replace("Mar ", "3/")
    formatted_date = formatted_date.replace("Apr ", "4/").replace("May ", "5/").replace("Jun ", "6/")
    formatted_date = formatted_date.replace("Jul ", "7/").replace("Aug ", "8/").replace("Sep ", "9/")
    
    # Remove leading zero from day (e.g., "12/06" -> "12/6", "1/05" -> "1/5")
    if "/0" in formatted_date:
        formatted_date = formatted_date.replace("/0", "/")
    
    # Format: "Man U | 10/19 11:30 AM"
    return f"{short_opponent} | {formatted_date} {time_str}"

# Test the formatting
if __name__ == "__main__":
    test_cases = [
        ("Manchester United FC", "Oct 19", "11:30 AM"),
        ("Arsenal FC", "Nov 5", "3:00 PM"),
        ("Manchester City FC", "Dec 25", "12:00 PM"),
    ]
    
    print("🧪 Testing pass formatting:")
    for opponent, date, time in test_cases:
        formatted = format_match_display(opponent, date, time)
        print(f"  {opponent} → {formatted} ({len(formatted)} chars)")
