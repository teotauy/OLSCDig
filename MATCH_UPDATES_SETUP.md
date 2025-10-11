# 🏆 Liverpool FC Match Updates

## What This Does

Automatically updates all PassKit passes with:
- **Next match opponent** (e.g., "vs Manchester City")
- **Match date** (e.g., "Oct 15")
- **Match time** (e.g., "3:00 PM")
- **Venue** (e.g., "Anfield" or "Away")
- **Home/Away status** (e.g., "Yes" or "No")

## Setup Required

### 1. Get Football Data API Key
- Go to: https://www.football-data.org/
- Sign up for free account
- Get your API key
- Add to `.env` file:
  ```
  FOOTBALL_DATA_API_KEY=your_api_key_here
  ```

### 2. Update the Code
Replace `YOUR_FOOTBALL_DATA_API_KEY` in `match_updates.py` with your actual key.

### 3. Test It
```bash
python3 match_updates.py
```

## How It Works

1. **Fetches Liverpool fixtures** from football-data.org API
2. **Finds next match** (upcoming fixture)
3. **Updates all passes** with match information
4. **Sends push notification** to all members

## Automation Options

### Option 1: Daily Check (Recommended)
Add to crontab (`crontab -e`):
```bash
# Check for match updates daily at 9 AM
0 9 * * * cd /Users/colbyblack/DigID && python3 match_updates.py
```

### Option 2: Manual Updates
Run when you want to update:
```bash
python3 match_updates.py
```

### Option 3: Before Each Match
Run 24 hours before kickoff:
```bash
python3 match_updates.py
```

## Push Notifications

**⚠️ NOTIFICATION FEATURE IS DISABLED - REQUIRES BOARD BUY-IN**

The system can prepare push notifications but will NOT send them without approval:

- **Home matches:** "🏠 Liverpool vs City at Anfield - Sunday, Oct 15 at 3:00 PM"
- **Away matches:** "✈️ Liverpool vs City - Sunday, Oct 15 at 3:00 PM"

**Current status:** Only updates pass fields, no notifications sent.

## Pass Fields Updated

The following fields will be updated on all passes:
- `nextMatch` - "vs [Opponent]"
- `matchDate` - "Oct 15"
- `matchTime` - "3:00 PM"
- `venue` - "Anfield" or "Away"
- `isHomeMatch` - "Yes" or "No"

## Troubleshooting

### No matches found?
- Check your API key is correct
- Verify Liverpool FC team ID (64) is correct
- Check if there are upcoming fixtures

### Pass updates failing?
- Verify PassKit API credentials
- Check pass field names match your template
- Ensure you have permission to update passes

### API rate limits?
- Free tier allows 10 requests per minute
- Paid tier allows 100 requests per minute

## Next Steps

1. **Get API key** from football-data.org
2. **Test the system** with `python3 match_updates.py`
3. **Set up automation** with cron job
4. **Customize notification messages** as needed

---

**🔴⚽ Your passes will always show the next match!**
