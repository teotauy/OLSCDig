# PassKit Headcount System (Liverpool OLSC)

This repo provides:
- A live headcount generator (runs every minute via GitHub Actions; writes `public/headcount.json` for a Pages site)
- A nightly bulk checkout at midnight Eastern (turns all CHECKED_IN members into CHECKED_OUT)
- Optional local scripts for real-time console monitoring and manual bulk checkout

## Components
- `capacity_monitor.py`: Local console monitor. Prints checked-in count every few seconds.
- `bulk_checkout.py`: Checks out all currently checked-in members for the program.
- `.github/workflows/headcount.yml`: Runs every minute, updates `public/headcount.json` and commits it for GitHub Pages to serve.
- `.github/workflows/checkout.yml`: Runs nightly at 00:00 Eastern, performs bulk checkout.
- `public/index.html`: Minimal page that displays the current headcount and a countdown until the next refresh.

## Setup
1) Install dependencies locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Configure environment
- Copy `.env.example` to `.env` and fill values
- Required:
  - `PROGRAM_ID` (e.g., 3yyTsbqwmtXaiKZ5qWhqTP)
  - `API_BASE` (e.g., https://api.pub1.passkit.io)
  - `TIMEZONE` (e.g., America/New_York)
  - `PASSKIT_API_KEY` – your PassKit API key
  - `PASSKIT_PROJECT_KEY` – your PassKit project key

3) GitHub Actions secrets (for free hosting)
Store these as repository Secrets (Settings → Secrets and variables → Actions):
- `PROGRAM_ID` – your program id (3yyTsbqwmtXaiKZ5qWhqTP)
- `API_BASE` – your PassKit REST API base URL
- `PASSKIT_API_KEY` – your PassKit API key
- `PASSKIT_PROJECT_KEY` – your PassKit project key

4) Enable GitHub Pages
- Settings → Pages → Build from `main` branch, `/public` folder

## Running locally
- Live console headcount:
```bash
python capacity_monitor.py
```
- Manual bulk checkout:
```bash
python bulk_checkout.py
```

## Notes
- Headcount definition: members with `members.member.status == CHECKED_IN`
- Bulk checkout: sets all `CHECKED_IN` to `CHECKED_OUT`
- Nightly time: Midnight Eastern (America/New_York)

Reference: [passkit-python-grpc-sdk](https://github.com/PassKit/passkit-python-grpc-sdk)

