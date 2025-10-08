#!/usr/bin/env python3
import csv
import json
import os
from datetime import datetime
import pytz

def count_checked_in_from_csv(csv_file):
    """Count CHECKED_IN members from the CSV file."""
    checked_in_count = 0
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('members.member.status') == 'CHECKED_IN':
                    checked_in_count += 1
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return 0
    
    return checked_in_count

def main():
    # Find the CSV file
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and '3yyTsbqwmtXaiKZ5qWhqTP' in f]
    
    if not csv_files:
        print("No CSV file found")
        return
    
    csv_file = csv_files[0]
    print(f"Using CSV file: {csv_file}")
    
    # Count checked-in members
    count = count_checked_in_from_csv(csv_file)
    print(f"CHECKED_IN count: {count}")
    
    # Create headcount.json
    now = datetime.now(pytz.timezone('America/New_York'))
    payload = {
        "count": int(count),
        "updated_at": now.isoformat(timespec="seconds"),
    }
    
    os.makedirs("public", exist_ok=True)
    with open("public/headcount.json", "w") as f:
        json.dump(payload, f)
    print("Wrote public/headcount.json")

if __name__ == "__main__":
    main()
