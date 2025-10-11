#!/usr/bin/env python3
"""
Team name abbreviations for pass display optimization.
Converts long team names to short, recognizable abbreviations.
"""

TEAM_ABBREVIATIONS = {
    # Premier League teams
    "Arsenal FC": "Arsenal",
    "Aston Villa FC": "Aston Villa", 
    "Bournemouth": "Bournemouth",
    "Brentford FC": "Brentford",
    "Brighton & Hove Albion FC": "Brighton",
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
    
    # Add more as needed
}

def abbreviate_team_name(full_name):
    """Convert full team name to short abbreviation."""
    return TEAM_ABBREVIATIONS.get(full_name, full_name[:8])  # Fallback to first 8 chars

def format_match_display(opponent, date_str, time_str):
    """Format match info for pass display with optimal character usage."""
    # Abbreviate opponent
    short_opponent = abbreviate_team_name(opponent)
    
    # Use MM/DD format
    formatted_date = date_str.replace("Oct ", "10/").replace("Nov ", "11/").replace("Dec ", "12/")
    formatted_date = formatted_date.replace("Jan ", "01/").replace("Feb ", "02/").replace("Mar ", "03/")
    formatted_date = formatted_date.replace("Apr ", "04/").replace("May ", "05/").replace("Jun ", "06/")
    formatted_date = formatted_date.replace("Jul ", "07/").replace("Aug ", "08/").replace("Sep ", "09/")
    
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
