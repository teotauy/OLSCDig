# Apple Wallet spike — manual setup

These steps need your Apple ID login and macOS Keychain Access, so they're
yours to run — I can't do them for you. Once done, `generate_pkpass.py` will
work.

## 1. Pass Type ID

1. developer.apple.com → Certificates, Identifiers & Profiles → Identifiers → **+**
2. Choose **Pass Type IDs** → Continue.
3. Description: `OLSC Brooklyn Membership`. Identifier: `pass.com.redcrowlabs.olsc`
   (or whatever reverse-domain you want — must be unique, keep it, it goes in `pass.json`).
4. Register.

## 2. Signing certificate

1. Click the new Pass Type ID → **Create Certificate**.
2. It asks for a CSR. On your Mac: Keychain Access → Certificate Assistant →
   Request a Certificate From a Certificate Authority. Save to disk (don't
   need a CA email response).
3. Upload the CSR, download the resulting `pass.cer`.
4. Double-click `pass.cer` to install it into Keychain Access (login keychain).
5. In Keychain Access, find the cert under "My Certificates" (it'll show the
   private key nested under it since the CSR was generated on this Mac).
   Right-click → Export → save as `passTypeCert.p12`. Set an export password —
   you'll need it as `APPLE_CERT_PASSWORD` below.
6. Move the file to `certs/passTypeCert.p12` (repo root, already gitignored).

## 3. Apple WWDR intermediate certificate

Download **Worldwide Developer Relations – G4** from
https://www.apple.com/certificateauthority/ — save as `certs/wwdr.cer`, then convert:

```bash
openssl x509 -in certs/wwdr.cer -inform DER -out certs/wwdr.pem -outform PEM
```

## 4. Team ID

developer.apple.com → Membership → Team ID (10-character string).

## 5. Environment variables

```bash
export APPLE_TEAM_ID="<your team id>"
export APPLE_PASS_TYPE_ID="pass.com.redcrowlabs.olsc"
export APPLE_CERT_PASSWORD="<the export password from step 2.5>"
```

## 6. Run it

```bash
pip install pillow   # if not already installed
python3 wallet_spike/generate_pkpass.py
```

This writes `wallet_spike/olsc_test.pkpass`. AirDrop or email it to an iPhone
and tap it — iOS should offer "Add to Apple Wallet" directly, no web server
needed for this test. That's the actual go/no-go signal for the whole plan.

If it fails, capture the exact error (Wallet usually shows something like
"Safari cannot download this file" or silently does nothing) before
troubleshooting — it narrows down cert vs. pass.json vs. signature issues.

## 7. Production HTTPS download test

After the AirDrop/email spike succeeds, test the app-integrated route:

1. Add the Apple env vars and cert files to the running environment.
2. Start or deploy the Flask app.
3. Log in as admin first.
4. Open:

```text
/wallet/test-pass.pkpass
```

On Render, use the full HTTPS URL for the live app. iOS should download the
pass from the hosted Flask route and offer "Add to Apple Wallet." This proves
the production delivery path, not just local signing.
