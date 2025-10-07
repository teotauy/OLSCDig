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

2) Place PassKit credentials for local runs
- Put `certificate.pem`, `ca-chain.pem`, `key.pem` in `certs/`
- Decrypt `key.pem` locally once:

```bash
cd certs
openssl ec -in key.pem -out key.pem
```

3) Configure environment
- Copy `.env.example` to `.env` and fill values
- Required:
  - `PROGRAM_ID` (e.g., MEM-XXXXXXX)
  - `API_HOST` (e.g., grpc.pub1.passkit.io)
  - `TIMEZONE` (e.g., America/New_York)
  - `CERTIFICATE_PEM`, `CA_CHAIN_PEM`, `KEY_PEM` paths (defaults point to `certs/`)
  - `KEY_PASSWORD` (blank if key already decrypted)

4) GitHub Actions secrets (for free hosting)
Store these as repository Secrets (Settings → Secrets and variables → Actions):
- `PASSKIT_CERTIFICATE_PEM_B64` – base64 of certificate.pem
- `PASSKIT_CA_CHAIN_PEM_B64` – base64 of ca-chain.pem
- `PASSKIT_KEY_PEM_B64` – base64 of encrypted key.pem
- `PASSKIT_KEY_PASSWORD` – password to decrypt key.pem
- `PROGRAM_ID` – your program id
- `API_HOST` – e.g., grpc.pub1.passkit.io

5) Enable GitHub Pages
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

