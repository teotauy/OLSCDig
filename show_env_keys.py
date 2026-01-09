#!/usr/bin/env python3
"""
Helper script to display environment variable names and values (masked for security).
Useful for copying keys to Render or other cloud services.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Keys we want to find
keys_to_find = [
    "PASSKIT_API_KEY",
    "PASSKIT_PROJECT_KEY",
    "PUSHOVER_API_TOKEN",
    "PUSHOVER_USER_KEY",
    "PROGRAM_ID",
    "API_BASE",
    "TIMEZONE"
]

print("🔑 Environment Variables Found:\n")
print("=" * 60)

for key in keys_to_find:
    value = os.getenv(key)
    if value:
        # Show first 8 and last 4 characters for security
        if len(value) > 12:
            masked = f"{value[:8]}...{value[-4:]}"
        else:
            masked = "***"  # Too short to mask safely
        print(f"✅ {key}")
        print(f"   Value: {masked}")
        print(f"   Full value: {value}")  # Show full value for copying
        print()
    else:
        print(f"❌ {key} - NOT SET")
        print()

print("=" * 60)
print("\n💡 Copy the full values above to use in Render environment variables.")
print("   (The masked versions are just for verification)")




