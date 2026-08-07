#!/usr/bin/env python3
"""
Apple Wallet .pkpass signing spike.

Goal: prove that cert setup + signing + install works on a real iPhone,
before building any DB/admin/scanner code. If this fails, the self-hosted
wallet plan is a no-go for this season and PassKit stays.

Usage:
    python3 wallet_spike/generate_pkpass.py

Requires (see wallet_spike/SETUP.md):
    certs/passTypeCert.p12   - exported from Keychain Access
    certs/wwdr.pem           - Apple WWDR G4 intermediate cert
    env vars: APPLE_TEAM_ID, APPLE_PASS_TYPE_ID, APPLE_CERT_PASSWORD
"""

import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).parent
REPO_ROOT = BASE.parent
CERTS = REPO_ROOT / "certs"
WORKDIR = BASE / "_build"
OUT_PKPASS = BASE / "olsc_test.pkpass"

TEAM_ID = os.environ.get("APPLE_TEAM_ID")
PASS_TYPE_ID = os.environ.get("APPLE_PASS_TYPE_ID")
CERT_PASSWORD = os.environ.get("APPLE_CERT_PASSWORD", "")

PASS_CERT_P12 = CERTS / "passTypeCert.p12"
WWDR_PEM = CERTS / "wwdr.pem"


def require_env():
    missing = [n for n in ("APPLE_TEAM_ID", "APPLE_PASS_TYPE_ID") if not os.environ.get(n)]
    if missing:
        raise SystemExit(
            f"Missing env vars: {', '.join(missing)}. "
            f"Export them (see wallet_spike/SETUP.md) before running."
        )
    if not PASS_CERT_P12.exists():
        raise SystemExit(f"Missing {PASS_CERT_P12} — export it from Keychain Access first.")
    if not WWDR_PEM.exists():
        raise SystemExit(f"Missing {WWDR_PEM} — download Apple's WWDR G4 cert first.")


def make_placeholder_images(pass_dir: Path):
    specs = {
        "icon.png": (29, 29),
        "icon@2x.png": (58, 58),
        "icon@3x.png": (87, 87),
        "logo.png": (160, 50),
        "logo@2x.png": (320, 100),
    }
    for name, size in specs.items():
        img = Image.new("RGBA", size, (200, 16, 46, 255))
        d = ImageDraw.Draw(img)
        d.text((4, size[1] // 2 - 6), "OLSC", fill="white")
        img.save(pass_dir / name)


def build_pass_json() -> dict:
    return {
        "formatVersion": 1,
        "passTypeIdentifier": PASS_TYPE_ID,
        "teamIdentifier": TEAM_ID,
        "organizationName": "OLSC Brooklyn",
        "serialNumber": "SPIKE-TEST-0001",
        "description": "OLSC Brooklyn Membership (spike test)",
        "generic": {
            "primaryFields": [
                {"key": "name", "label": "MEMBER", "value": "Test Member"}
            ],
            "secondaryFields": [
                {"key": "season", "label": "SEASON", "value": "2025/26"}
            ],
        },
        "barcodes": [
            {
                "message": "https://example.invalid/checkin/t/spike-test-token",
                "format": "PKBarcodeFormatQR",
                "messageEncoding": "iso-8859-1",
            }
        ],
        "backgroundColor": "rgb(200,16,46)",
        "foregroundColor": "rgb(255,255,255)",
        "labelColor": "rgb(255,255,255)",
    }


def write_manifest(pass_dir: Path):
    manifest = {}
    for f in sorted(pass_dir.iterdir()):
        if f.name in ("manifest.json", "signature"):
            continue
        manifest[f.name] = hashlib.sha1(f.read_bytes()).hexdigest()
    (pass_dir / "manifest.json").write_text(json.dumps(manifest))


def run_openssl(args, *, stdin_data=None, retry_without_legacy=False):
    """Run openssl, feeding secrets via stdin so they never appear in argv,
    process listings (ps), or error output."""
    result = subprocess.run(
        args, input=stdin_data, capture_output=True, text=True
    )
    if result.returncode != 0:
        if retry_without_legacy and "-legacy" in args:
            fallback = [a for a in args if a != "-legacy"]
            result = subprocess.run(
                fallback, input=stdin_data, capture_output=True, text=True
            )
            if result.returncode == 0:
                return
        # stderr from openssl (e.g. "Mac verify error: invalid password?")
        # never contains the password itself, so this is safe to show.
        raise SystemExit(f"openssl failed: {result.stderr.strip()}")


def sign_manifest(pass_dir: Path):
    signer_pem = WORKDIR / "signer.pem"
    signer_key = WORKDIR / "signer.key"

    try:
        run_openssl(
            [
                "openssl", "pkcs12", "-in", str(PASS_CERT_P12),
                "-clcerts", "-nokeys", "-out", str(signer_pem),
                "-passin", "stdin", "-legacy",
            ],
            stdin_data=CERT_PASSWORD,
            retry_without_legacy=True,
        )
        run_openssl(
            [
                "openssl", "pkcs12", "-in", str(PASS_CERT_P12),
                "-nocerts", "-nodes", "-out", str(signer_key),
                "-passin", "stdin", "-legacy",
            ],
            stdin_data=CERT_PASSWORD,
            retry_without_legacy=True,
        )
        run_openssl(
            [
                "openssl", "smime", "-binary", "-sign",
                "-certfile", str(WWDR_PEM),
                "-signer", str(signer_pem),
                "-inkey", str(signer_key),
                "-in", str(pass_dir / "manifest.json"),
                "-out", str(pass_dir / "signature"),
                "-outform", "DER",
            ],
        )
    finally:
        signer_key.unlink(missing_ok=True)
        signer_pem.unlink(missing_ok=True)


def zip_pass(pass_dir: Path, out_path: Path):
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in pass_dir.iterdir():
            z.write(f, f.name)


def main():
    require_env()

    if WORKDIR.exists():
        shutil.rmtree(WORKDIR)
    pass_dir = WORKDIR / "pass"
    pass_dir.mkdir(parents=True)

    (pass_dir / "pass.json").write_text(json.dumps(build_pass_json()))
    make_placeholder_images(pass_dir)
    write_manifest(pass_dir)
    sign_manifest(pass_dir)
    zip_pass(pass_dir, OUT_PKPASS)

    print(f"Built {OUT_PKPASS}")
    print("AirDrop or email this file to an iPhone and tap it — it should offer 'Add to Apple Wallet'.")


if __name__ == "__main__":
    main()
