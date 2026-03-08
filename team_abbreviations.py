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

def abbreviate_team_name(full_name):
    """Convert full team name to short abbreviation."""
    if not full_name:
        return ""
    # Use mapping if present; otherwise keep full name if short, else first 14 chars (was 8, caused "Galatasa")
    abbr = TEAM_ABBREVIATIONS.get(full_name.strip())
    if abbr is not None:
        return abbr
    return full_name if len(full_name) <= 14 else full_name[:14]

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
