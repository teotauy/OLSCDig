#!/usr/bin/env python3
"""
PassKit Pass Theme Management
Handles home vs away shirt colorways for Liverpool OLSC passes.

This module provides functionality to:
1. Update pass themes based on match location (home/away)
2. Apply Liverpool FC home and away colors to passes
3. Automatically detect match location from fixture data
"""

import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from team_abbreviations import get_liverpool_fixtures

# Load environment variables
load_dotenv()

# PassKit configuration
PASSKIT_CONFIG = {
    'API_BASE': os.getenv('API_BASE'),
    'PROGRAM_ID': os.getenv('PROGRAM_ID'),
    'API_KEY': os.getenv('PASSKIT_API_KEY'),
    'PROJECT_KEY': os.getenv('PASSKIT_PROJECT_KEY')
}

# Liverpool FC Theme Colors
LIVERPOOL_THEMES = {
    'home': {
        'primary_color': '#C8102E',      # Liverpool Red
        'secondary_color': '#FFFFFF',    # White
        'accent_color': '#F0F0F0',       # Light Gray
        'text_color': '#FFFFFF',         # White text
        'background_color': '#C8102E',   # Red background
        'name': 'Liverpool Red',
        'description': 'Home shirt theme - Liverpool Red with white accents'
    },
    'away': {
        'primary_color': '#00A65A',      # Liverpool Green (away kit)
        'secondary_color': '#FFFFFF',    # White
        'accent_color': '#F0F0F0',       # Light Gray
        'text_color': '#FFFFFF',         # White text
        'background_color': '#00A65A',   # Green background
        'name': 'Liverpool Green',
        'description': 'Away shirt theme - Liverpool Green with white accents'
    },
    'third': {
        'primary_color': '#000000',      # Black (third kit)
        'secondary_color': '#FFFFFF',    # White
        'accent_color': '#C8102E',       # Liverpool Red accent
        'text_color': '#FFFFFF',         # White text
        'background_color': '#000000',   # Black background
        'name': 'Liverpool Black',
        'description': 'Third shirt theme - Black with red accents'
    }
}

def get_passkit_headers():
    """Get PassKit API headers."""
    return {
        'Authorization': f'Bearer {PASSKIT_CONFIG["API_KEY"]}',
        'X-Project-Key': PASSKIT_CONFIG['PROJECT_KEY'],
        'Content-Type': 'application/json'
    }

def detect_match_location(fixture_data):
    """
    Detect if a match is home or away based on fixture data.
    
    Args:
        fixture_data (dict): Fixture data from football-data.org API
        
    Returns:
        str: 'home', 'away', or 'unknown'
    """
    try:
        # Check if Liverpool is the home team
        if 'homeTeam' in fixture_data and 'awayTeam' in fixture_data:
            home_team = fixture_data['homeTeam'].get('name', '').lower()
            away_team = fixture_data['awayTeam'].get('name', '').lower()
            
            # Check for Liverpool variations
            liverpool_variations = ['liverpool', 'liverpool fc', 'lfc']
            
            for variation in liverpool_variations:
                if variation in home_team:
                    return 'home'
                elif variation in away_team:
                    return 'away'
        
        # Fallback: check competition or venue
        if 'competition' in fixture_data:
            competition = fixture_data['competition'].get('name', '').lower()
            if 'champions league' in competition or 'europa' in competition:
                # European matches might be at neutral venues
                return 'unknown'
        
        return 'unknown'
        
    except Exception as e:
        print(f"❌ Error detecting match location: {e}")
        return 'unknown'

def get_theme_for_match(fixture_data=None):
    """
    Get the appropriate theme for the next match.
    
    Args:
        fixture_data (dict): Optional fixture data. If not provided, fetches next match.
        
    Returns:
        dict: Theme configuration for the match
    """
    try:
        if not fixture_data:
            # Fetch next match
            fixtures = get_liverpool_fixtures()
            if not fixtures:
                print("⚠️ No upcoming matches found, using default home theme")
                return LIVERPOOL_THEMES['home']
            
            fixture_data = fixtures[0]
        
        # Detect match location
        location = detect_match_location(fixture_data)
        
        # Return appropriate theme
        if location == 'home':
            print("🏠 Home match detected - using Liverpool Red theme")
            return LIVERPOOL_THEMES['home']
        elif location == 'away':
            print("✈️ Away match detected - using Liverpool Green theme")
            return LIVERPOOL_THEMES['away']
        else:
            print("❓ Match location unknown - using default home theme")
            return LIVERPOOL_THEMES['home']
            
    except Exception as e:
        print(f"❌ Error getting theme for match: {e}")
        return LIVERPOOL_THEMES['home']

def update_pass_theme(member_id, theme_type):
    """
    Update a single pass with the specified theme.
    
    Args:
        member_id (str): The member's ID
        theme_type (str): Theme type ('home', 'away', 'third')
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if theme_type not in LIVERPOOL_THEMES:
            print(f"❌ Invalid theme type: {theme_type}")
            return False
        
        theme = LIVERPOOL_THEMES[theme_type]
        
        # Get current member data first
        member_url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/{member_id}"
        response = requests.get(member_url, headers=get_passkit_headers(), timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Error fetching member {member_id}: {response.status_code}")
            return False
            
        member_data = response.json()
        person_data = member_data.get("person", {})
        
        # Update the member's pass with theme data
        update_url = f"{PASSKIT_CONFIG['API_BASE']}/members/member"
        update_payload = {
            "programId": PASSKIT_CONFIG["PROGRAM_ID"],
            "id": member_id,
            "person": {
                "displayName": person_data.get("displayName", ""),
                "emailAddress": person_data.get("emailAddress", ""),
                "surname": person_data.get("surname", ""),
                "forename": person_data.get("forename", "")
            },
            "metaData": {
                **member_data.get("metaData", {}),
                "theme": theme_type,
                "themeName": theme['name'],
                "themeColors": {
                    "primary": theme['primary_color'],
                    "secondary": theme['secondary_color'],
                    "accent": theme['accent_color'],
                    "background": theme['background_color']
                },
                "themeUpdated": datetime.now().isoformat()
            }
        }
        
        response = requests.put(update_url, headers=get_passkit_headers(), json=update_payload, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Updated theme for member {member_id} to {theme['name']}")
            return True
        else:
            print(f"❌ Error updating theme for member {member_id}: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating pass theme: {e}")
        return False

def update_all_passes_theme(theme_type='auto'):
    """
    Update all passes with the specified theme or auto-detect from next match.
    
    Args:
        theme_type (str): Theme type ('home', 'away', 'third', 'auto')
        
    Returns:
        dict: Result with success status and counts
    """
    try:
        print(f"🎨 Updating pass themes...")
        
        # Get theme
        if theme_type == 'auto':
            theme_config = get_theme_for_match()
            theme_type = 'home' if theme_config == LIVERPOOL_THEMES['home'] else 'away'
        else:
            theme_config = LIVERPOOL_THEMES.get(theme_type, LIVERPOOL_THEMES['home'])
        
        # Get all members
        url = f"{PASSKIT_CONFIG['API_BASE']}/members/member/list/{PASSKIT_CONFIG['PROGRAM_ID']}"
        payload = {
            "filters": {
                "limit": 1000,
                "offset": 0
            }
        }
        
        response = requests.post(url, headers=get_passkit_headers(), json=payload, timeout=30)
        response.raise_for_status()
        
        members = []
        # Parse NDJSON response
        for line in response.text.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    if 'result' in data:
                        members.append(data['result'])
                except json.JSONDecodeError:
                    pass
        
        print(f"📋 Found {len(members)} members to update")
        
        # Update each member
        successful = 0
        failed = 0
        
        for member in members:
            member_id = member.get("id")
            member_name = member.get("person", {}).get("displayName", "Unknown")
            
            if update_pass_theme(member_id, theme_type):
                successful += 1
                print(f"  ✅ {member_name}")
            else:
                failed += 1
                print(f"  ❌ {member_name}")
        
        result = {
            "success": successful > 0,
            "theme_type": theme_type,
            "theme_name": theme_config['name'],
            "successful_updates": successful,
            "failed_updates": failed,
            "total_members": len(members),
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📊 Theme update summary: {successful}/{len(members)} updated successfully")
        print(f"🎨 Applied theme: {theme_config['name']} ({theme_config['description']})")
        
        return result
        
    except Exception as e:
        print(f"❌ Error updating pass themes: {e}")
        return {
            "success": False,
            "error": str(e),
            "successful_updates": 0,
            "failed_updates": 0
        }

def get_available_themes():
    """Get list of available themes."""
    return LIVERPOOL_THEMES

def get_current_theme_info():
    """Get information about the current theme for the next match."""
    try:
        theme_config = get_theme_for_match()
        theme_type = None
        
        # Find which theme this is
        for theme_key, theme_data in LIVERPOOL_THEMES.items():
            if theme_data == theme_config:
                theme_type = theme_key
                break
        
        return {
            "theme_type": theme_type,
            "theme_config": theme_config,
            "next_match_theme": theme_config['name']
        }
        
    except Exception as e:
        print(f"❌ Error getting current theme info: {e}")
        return None

if __name__ == "__main__":
    # Test the theme system
    print("🎨 PassKit Theme Management Test")
    print("=" * 40)
    
    # Get current theme for next match
    theme_info = get_current_theme_info()
    if theme_info:
        print(f"🎯 Next match theme: {theme_info['theme_config']['name']}")
        print(f"   Type: {theme_info['theme_type']}")
        print(f"   Primary color: {theme_info['theme_config']['primary_color']}")
    
    # List available themes
    print("\n📋 Available themes:")
    for theme_key, theme_data in LIVERPOOL_THEMES.items():
        print(f"  {theme_key}: {theme_data['name']} - {theme_data['description']}")
    
    # Test updating all passes (commented out to avoid spam)
    # print("\n🔄 Testing theme update...")
    # result = update_all_passes_theme('auto')
    # print(f"Result: {result}")
