# OLSC Brooklyn Offseason Shutdown & Restart Manual

Use this when the PassKit subscription is about to be turned off, and again when the next season starts.

## Before Turning Off PassKit

### Mothball Checklist

- [ ] Run `python3 export_passkit_season.py` one final time.
- [ ] Open `season_exports/latest/dashboard.html` and confirm it loads.
- [ ] Confirm `season_exports/latest/member_events.csv` has the latest match check-ins.
- [ ] Confirm `season_exports/latest/members.csv` has the full member list.
- [ ] Copy the entire latest `season_exports/YYYYMMDD_HHMMSS/` folder to cloud storage.
- [ ] Export the latest Squarespace orders/members CSV.
- [ ] Save current service URLs and environment variable names in a password manager.
- [ ] Do not commit `season_exports/`; it contains member PII and is intentionally gitignored.

1. **Run the full export.**
   ```bash
   cd /Users/colbyblack/DigID
   python3 export_passkit_season.py
   ```

2. **Verify the export folder.**
   The export lives in `season_exports/YYYYMMDD_HHMMSS/`, with `season_exports/latest` pointing at the newest run.

   Key files to confirm:
   - `dashboard.html` - season dashboard you can open in a browser.
   - `members.csv` and `members_raw.json` - member/pass backup.
   - `member_events.csv` and `member_events_raw.json` - check-in event backup.
   - `season_stats.json` - machine-readable stats summary.
   - `top_attendees.csv` and `busiest_matches.csv` - quick answers for awards/recaps.

3. **Copy the export somewhere outside this repo.**
   Save a copy to iCloud/Google Drive/Dropbox or an external drive before cancelling PassKit. PassKit data may be deleted within days after the subscription stops.

4. **Save service details separately.**
   Keep these in a password manager, not in git:
   - PassKit login email.
   - PassKit project key and API key.
   - Current `PROGRAM_ID`.
   - Hosted app provider, login, project/service name, and service URL.
   - SMTP credentials, if checkout reports or fallback welcome emails are enabled.
   - Football-data.org API key.
   - Squarespace webhook details, if enabled.
   - Google OAuth client ID, client secret, and authorized redirect URI, if enabled.
   - Pushover keys, if notifications are used.

5. **Export Squarespace orders/members too.**
   Download the latest orders/member CSV from Squarespace so you can rebuild PassKit even if old passes are gone.

6. **Optional: pull a last-match check-in file.**
   After the full export, filter `season_exports/latest/member_events.csv` by the last match date, or use the existing generated file if present:
   `season_exports/latest/last_match_checkins_2026-05-24_liverpool_vs_brentford.csv`.

## What Can Be Paused

- PassKit subscription can be cancelled only after the export is verified and copied off-machine.
- Render/Vercel can stay deployed or be suspended. If you suspend it, keep the environment variable list documented.
- Football-data.org, SMTP, Google OAuth, and Pushover can stay as-is unless you want to rotate or pause them.
- The local app can sit untouched as long as `.env` and exported data are backed up separately.

## Starting Back Up Next Season

1. **Reactivate PassKit.**
   Log in to PassKit, restart the subscription, and confirm whether the old project/program survived. If it did not, create a new Members/Loyalty program for the new season.

2. **Confirm the pass template.**
   In PassKit, verify:
   - The program is published/active.
   - The welcome email is enabled.
   - The pass has the right OLSC Brooklyn branding.
   - The dynamic match field still exists and is wired to `metaData.nextMatch`.
   - Check-in/check-out is enabled for the program.
   - Expiry date matches the new season.
   - The pass type identifier and wallet distribution settings are active.
   - A test pass can be issued, installed, checked in, and checked out.

3. **Update local `.env`.**
   Set or refresh:
   - `PROGRAM_ID`
   - `PASSKIT_API_KEY`
   - `PASSKIT_PROJECT_KEY`
   - `API_BASE=https://api.pub2.passkit.io`
   - `TIMEZONE=America/New_York`
   - `FOOTBALL_DATA_API_KEY`
   - `ADMIN_PASSWORD` or `ADMIN_PASSWORD_HASH`
   - `FLASK_SECRET_KEY`
   - Optional SMTP, Google OAuth, Pushover, and checkout report variables.

4. **Update Render/Vercel environment variables.**
   In the hosted app dashboard, paste the same current PassKit values and save so the service redeploys.
   Required hosted variables:
   - `PROGRAM_ID`
   - `PASSKIT_API_KEY`
   - `PASSKIT_PROJECT_KEY`
   - `ADMIN_PASSWORD` or `ADMIN_PASSWORD_HASH`
   - `FLASK_SECRET_KEY`
   Recommended hosted variables:
   - `API_BASE=https://api.pub2.passkit.io`
   - `TIMEZONE=America/New_York`
   - `SESSION_COOKIE_SECURE=true`
   - `FOOTBALL_DATA_API_KEY`
   - `CHECKOUT_REPORT_EMAIL` and `SMTP_*`, if checkout CSVs should email automatically.

5. **Run a smoke test locally.**
   ```bash
   python3 export_passkit_season.py
   python3 match_updates.py
   ```
   The export should list members/events without a 401. `match_updates.py` should fetch Liverpool fixtures and update passes.

6. **Test the web app.**
   - Open the hosted app.
   - Log in.
   - Check that headcount loads.
   - Use `Update Match` to push the next match.
   - Add one test member or resend a welcome email to yourself.
   - Confirm the pass opens and saves to Apple/Google Wallet.
   - Check in the test pass, confirm headcount increments, then run `Check Out Everyone` and confirm it returns to zero.

7. **Load new-season members.**
   Use the current Squarespace orders/member export and the existing import tools:
   - `quick_add_members.py` for a small manual batch.
   - `backfill_missing_members.py` / Squarespace tools for larger imports.
   - Check duplicates before sending welcome emails.

8. **Refresh match overrides.**
   Update `match_overrides.json` for FA Cup, friendlies, or matches not returned by football-data.org. Then use the web `Update Match` page or `python3 match_updates.py`.

9. **Reconnect automations if used.**
   - Squarespace webhook URL and secret.
   - Checkout report email via `CHECKOUT_REPORT_EMAIL` and SMTP vars.
   - Google OAuth redirect URI for the current hosted domain.
   - Pushover notifications, if you bring them back.
   - Any scheduled match update job or local reminder you used previously.

10. **First match checklist.**
    - Headcount page works on your phone.
    - Add member page works.
    - Update match shows the correct opponent/time.
    - At least one pass can check in.
    - `Check Out Everyone` works after the test and downloads/emails a CSV.

## Troubleshooting

- **401 from PassKit:** API key, project key, or program ID is wrong in local `.env` or hosted environment variables.
- **Headcount shows error:** Same root cause as 401, because headcount lists checked-in PassKit members.
- **Passes update but text does not change:** Confirm the pass field is dynamic and reads `metaData.nextMatch`.
- **No fixtures:** Check `FOOTBALL_DATA_API_KEY`, then add a manual override if football-data.org does not include the match.
- **Welcome email missing:** Confirm PassKit welcome email settings first; then confirm SMTP fallback variables if using the app fallback.
- **Filesystem changes vanish on Vercel:** Edit repo files such as `match_overrides.json` and redeploy. Serverless disk is not persistent.
- **Export script works but no check-ins appear:** Confirm check-in/check-out is enabled on the new PassKit program and that the scanner/app is using the current `PROGRAM_ID`.
- **Old pass links fail next season:** PassKit may have deleted the old program. Issue new passes from the new program and send fresh welcome links.

## Annual Archive Habit

At the end of every season, run `python3 export_passkit_season.py`, open `season_exports/latest/dashboard.html`, and copy the whole timestamped folder to cloud storage before touching the PassKit subscription.

## Useful Commands

```bash
# Full member/event export plus dashboard
python3 export_passkit_season.py

# Open the latest dashboard on macOS
open season_exports/latest/dashboard.html

# Update all passes with the next Liverpool match
python3 match_updates.py

# Run the web app locally
python3 app.py
```

The generated export folder is intentionally not committed. Keep the repo for code/docs and keep `season_exports/` in backed-up private storage.

## 2026-05-29 Mothball Run Status

Completed locally:
- Final PassKit export created at `season_exports/20260529_133136/`.
- Latest dashboard verified at `season_exports/latest/dashboard.html`.
- Member backup verified at `season_exports/latest/members.csv`.
- Check-in event backup verified at `season_exports/latest/member_events.csv`.
- Last-match check-in file created at `season_exports/latest/last_match_checkins_2026-05-24_liverpool_vs_brentford.csv`.
- Off-repo backup folder created at `/Users/colbyblack/Desktop/OLSC_Brooklyn_2025-26_Mothball_Backup`.
- Off-repo zip archive created at `/Users/colbyblack/Desktop/OLSC_Brooklyn_2025-26_Mothball_Backup.zip`.
- Restart docs copied into the Desktop backup.
- Local `orders.csv` snapshot copied into the Desktop backup as `orders_repo_snapshot.csv`.

Still needs account-owner action:
- Copy `/Users/colbyblack/Desktop/OLSC_Brooklyn_2025-26_Mothball_Backup.zip` to private cloud storage or an external drive.
- Export the latest orders/members CSV directly from Squarespace, if the local `orders.csv` is not the final source of truth.
- Save PassKit, hosted app, SMTP, football-data.org, Squarespace, Google OAuth, and Pushover credentials/service details in a password manager.
