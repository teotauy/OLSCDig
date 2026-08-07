#!/usr/bin/env python3
"""Apple Wallet pass generation utilities for OLSC Brooklyn."""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
DEFAULT_CERT_DIR = ROOT / "certs"


class AppleWalletConfigError(RuntimeError):
    """Raised when Apple Wallet signing configuration is missing or invalid."""


@dataclass(frozen=True)
class AppleWalletConfig:
    team_id: str
    pass_type_id: str
    cert_password: str
    pass_cert_p12: Path
    wwdr_pem: Path


@dataclass(frozen=True)
class MemberPassData:
    display_name: str
    season: str
    serial_number: str
    barcode_message: str
    next_match: str = ""
    description: str = "OLSC Brooklyn Membership"


def _env(key, default=""):
    value = os.getenv(key, default)
    return value.strip() if isinstance(value, str) else value


def load_apple_wallet_config():
    config = AppleWalletConfig(
        team_id=_env("APPLE_TEAM_ID"),
        pass_type_id=_env("APPLE_PASS_TYPE_ID"),
        cert_password=os.getenv("APPLE_CERT_PASSWORD", ""),
        pass_cert_p12=Path(_env("APPLE_PASS_CERT_PATH", str(DEFAULT_CERT_DIR / "passTypeCert.p12"))),
        wwdr_pem=Path(_env("APPLE_WWDR_CERT_PATH", str(DEFAULT_CERT_DIR / "wwdr.pem"))),
    )

    missing = []
    if not config.team_id:
        missing.append("APPLE_TEAM_ID")
    if not config.pass_type_id:
        missing.append("APPLE_PASS_TYPE_ID")
    if missing:
        raise AppleWalletConfigError(f"Missing env vars: {', '.join(missing)}")
    if not config.pass_cert_p12.exists():
        raise AppleWalletConfigError(f"Missing pass certificate: {config.pass_cert_p12}")
    if not config.wwdr_pem.exists():
        raise AppleWalletConfigError(f"Missing Apple WWDR certificate: {config.wwdr_pem}")
    return config


def _run_openssl(args, *, stdin_data=None, retry_without_legacy=False):
    result = subprocess.run(args, input=stdin_data, capture_output=True, text=True)
    if result.returncode == 0:
        return
    if retry_without_legacy and "-legacy" in args:
        fallback = [arg for arg in args if arg != "-legacy"]
        result = subprocess.run(fallback, input=stdin_data, capture_output=True, text=True)
        if result.returncode == 0:
            return
    raise AppleWalletConfigError(f"openssl failed: {result.stderr.strip()}")


def _make_placeholder_images(pass_dir):
    specs = {
        "icon.png": (29, 29),
        "icon@2x.png": (58, 58),
        "icon@3x.png": (87, 87),
        "logo.png": (160, 50),
        "logo@2x.png": (320, 100),
    }
    for name, size in specs.items():
        img = Image.new("RGBA", size, (200, 16, 46, 255))
        draw = ImageDraw.Draw(img)
        draw.text((4, size[1] // 2 - 6), "OLSC", fill="white")
        img.save(pass_dir / name)


def _build_pass_json(config, pass_data):
    secondary_fields = [
        {"key": "season", "label": "SEASON", "value": pass_data.season},
    ]
    if pass_data.next_match:
        secondary_fields.append({"key": "nextMatch", "label": "NEXT MATCH", "value": pass_data.next_match})

    return {
        "formatVersion": 1,
        "passTypeIdentifier": config.pass_type_id,
        "teamIdentifier": config.team_id,
        "organizationName": "OLSC Brooklyn",
        "serialNumber": pass_data.serial_number,
        "description": pass_data.description,
        "generic": {
            "primaryFields": [
                {"key": "name", "label": "MEMBER", "value": pass_data.display_name}
            ],
            "secondaryFields": secondary_fields,
        },
        "barcodes": [
            {
                "message": pass_data.barcode_message,
                "format": "PKBarcodeFormatQR",
                "messageEncoding": "iso-8859-1",
            }
        ],
        "backgroundColor": "rgb(200,16,46)",
        "foregroundColor": "rgb(255,255,255)",
        "labelColor": "rgb(255,255,255)",
    }


def _write_manifest(pass_dir):
    manifest = {}
    for file_path in sorted(pass_dir.iterdir()):
        if file_path.name in ("manifest.json", "signature"):
            continue
        manifest[file_path.name] = hashlib.sha1(file_path.read_bytes()).hexdigest()
    (pass_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _sign_manifest(pass_dir, config):
    signer_pem = pass_dir.parent / "signer.pem"
    signer_key = pass_dir.parent / "signer.key"
    try:
        _run_openssl(
            [
                "openssl", "pkcs12", "-in", str(config.pass_cert_p12),
                "-clcerts", "-nokeys", "-out", str(signer_pem),
                "-passin", "stdin", "-legacy",
            ],
            stdin_data=config.cert_password,
            retry_without_legacy=True,
        )
        _run_openssl(
            [
                "openssl", "pkcs12", "-in", str(config.pass_cert_p12),
                "-nocerts", "-nodes", "-out", str(signer_key),
                "-passin", "stdin", "-legacy",
            ],
            stdin_data=config.cert_password,
            retry_without_legacy=True,
        )
        _run_openssl(
            [
                "openssl", "smime", "-binary", "-sign",
                "-certfile", str(config.wwdr_pem),
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


def _zip_pass(pass_dir):
    out_path = pass_dir.parent / "member.pkpass"
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in pass_dir.iterdir():
            archive.write(file_path, file_path.name)
    return out_path.read_bytes()


def build_member_pkpass(pass_data, config=None):
    """Build and sign a .pkpass package, returning bytes."""
    config = config or load_apple_wallet_config()
    temp_dir = Path(tempfile.mkdtemp(prefix="olsc-wallet-pass-"))
    try:
        pass_dir = temp_dir / "pass"
        pass_dir.mkdir(parents=True)
        (pass_dir / "pass.json").write_text(
            json.dumps(_build_pass_json(config, pass_data)),
            encoding="utf-8",
        )
        _make_placeholder_images(pass_dir)
        _write_manifest(pass_dir)
        _sign_manifest(pass_dir, config)
        return _zip_pass(pass_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
