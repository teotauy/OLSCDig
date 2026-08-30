#!/usr/bin/env python3
"""Apple Wallet pass generation utilities for OLSC Brooklyn."""

import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
DEFAULT_CERT_DIR = ROOT / "certs"
BASE64_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")


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
    barcode_alt_text: str = ""
    auth_token: str = ""
    web_service_url: str = ""
    next_match: str = ""
    description: str = "OLSC Brooklyn Membership"
    is_home: bool = True  # drives home (red) vs away (white/red, 2026/27 road kit) pass theme
    relevant_date: str = ""
    expiration_date: str = ""  # season end -- unlike relevant_date, safe to set: it's a
    # single fixed far-future date, never in the past for an active pass, so it can't
    # trigger the relevantDate "shows as Expired" bug
    locations: tuple = (
        {
            # 481 5th Ave, Brooklyn, NY 11215 (the actual venue) -- the
            # previous value here was ~220m off with no documented source,
            # confirmed too far for the lock-screen alert to ever fire on
            # a real device (Aug 25 matchday test, zero pop-ups).
            "latitude": 40.6676747,
            "longitude": -73.9872480,
            "relevantText": "Up the Reds.",
        },
    )


def _env(key, default=""):
    value = os.getenv(key, default)
    return value.strip() if isinstance(value, str) else value


def _materialize_base64_cert(value, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_value = "".join(str(value).split())
    if "=" in clean_value:
        padding_start = clean_value.find("=")
        padding_end = padding_start
        while padding_end < len(clean_value) and clean_value[padding_end] == "=":
            padding_end += 1
        clean_value = clean_value[:padding_end]
    invalid_chars = sorted({char for char in clean_value if char not in BASE64_CHARS})
    if invalid_chars:
        shown = ", ".join(repr(char) for char in invalid_chars[:8])
        raise AppleWalletConfigError(
            f"Could not decode base64 certificate for {path.name}: invalid non-base64 character(s): {shown}. "
            "The value should usually start with `MII`, include only letters/numbers/+//, may end with `=`, "
            "and should not include quotes, `%`, env var names, or shell prompts."
        )
    try:
        path.write_bytes(base64.b64decode(clean_value, validate=True))
    except Exception as exc:
        raise AppleWalletConfigError(
            f"Could not decode base64 certificate for {path.name}: {exc}. "
            "Regenerate the value with `base64 -i <file> | tr -d '\\n' | pbcopy` "
            "and paste only that value into Render."
        ) from exc
    return path


def load_apple_wallet_config(materialize_dir=None):
    materialize_dir = Path(materialize_dir) if materialize_dir else None
    pass_cert_b64 = _env("APPLE_PASS_CERT_P12_BASE64")
    wwdr_b64 = _env("APPLE_WWDR_PEM_BASE64")

    if pass_cert_b64:
        if not materialize_dir:
            raise AppleWalletConfigError("APPLE_PASS_CERT_P12_BASE64 requires a materialize directory")
        pass_cert_p12 = _materialize_base64_cert(pass_cert_b64, materialize_dir / "passTypeCert.p12")
    else:
        pass_cert_p12 = Path(_env("APPLE_PASS_CERT_PATH", str(DEFAULT_CERT_DIR / "passTypeCert.p12")))

    if wwdr_b64:
        if not materialize_dir:
            raise AppleWalletConfigError("APPLE_WWDR_PEM_BASE64 requires a materialize directory")
        wwdr_pem = _materialize_base64_cert(wwdr_b64, materialize_dir / "wwdr.pem")
    else:
        wwdr_pem = Path(_env("APPLE_WWDR_CERT_PATH", str(DEFAULT_CERT_DIR / "wwdr.pem")))

    config = AppleWalletConfig(
        team_id=_env("APPLE_TEAM_ID"),
        pass_type_id=_env("APPLE_PASS_TYPE_ID"),
        cert_password=os.getenv("APPLE_CERT_PASSWORD", ""),
        pass_cert_p12=pass_cert_p12,
        wwdr_pem=wwdr_pem,
    )

    missing = []
    if not config.team_id:
        missing.append("APPLE_TEAM_ID")
    if not config.pass_type_id:
        missing.append("APPLE_PASS_TYPE_ID")
    if "APPLE_CERT_PASSWORD" not in os.environ:
        missing.append("APPLE_CERT_PASSWORD")
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


ASSETS_DIR = ROOT / "wallet_pass_assets"

# 2026/27 kit-based pass themes, chosen automatically from the fixture's
# is_home flag (the same data source as the "next match" text — if the pass
# says "vs Newcastle" it's red, "@ Everton" it's the away/white scheme, and
# the two can never disagree). Away = the actual 2026/27 road kit: white
# with red lettering, not PassKit-era green.
PASS_THEMES = {
    "home": {
        "background": "rgb(227,27,35)",
        "foreground": "rgb(255,255,255)",
        "label": "rgb(255,255,255)",
        "icon_bg": (227, 27, 35, 255),
        "icon_border": None,
        "crest_path": ASSETS_DIR / "olsc_crest_white.png",
        "wordmark_path": ASSETS_DIR / "olsc_wordmark_white.png",
    },
    "away": {
        "background": "rgb(255,255,255)",
        "foreground": "rgb(227,27,35)",
        "label": "rgb(227,27,35)",
        "icon_bg": (255, 255, 255, 255),
        # A plain white icon can disappear against Wallet's own light-mode
        # chrome (notifications, lock screen) — a thin red frame keeps it
        # defined without changing the away color story.
        "icon_border": (227, 27, 35, 255),
        "crest_path": ASSETS_DIR / "olsc_crest_red.png",
        "wordmark_path": ASSETS_DIR / "olsc_wordmark_red.png",
    },
}


def _load_art(path):
    """Load one of the bundled crest/wordmark assets and trim to its actual
    content bounding box. The wordmark source files in particular are
    centered inside a canvas several times wider than the artwork itself
    (Desktop/logos export) — without trimming, "left-align the logo" is
    impossible, since the untrimmed image still has its own huge built-in
    side margins baked in before we ever get to position it."""
    img = Image.open(path).convert("RGBA")
    alpha = img.split()[3]
    bbox = alpha.getbbox()
    return img.crop(bbox) if bbox else img


def _paste_centered(canvas, art, margin_frac=0.14):
    """Resize `art` (preserving aspect ratio) to fit `canvas` minus a margin,
    and paste it centered."""
    cw, ch = canvas.size
    max_w = int(cw * (1 - margin_frac * 2))
    max_h = int(ch * (1 - margin_frac * 2))
    scale = min(max_w / art.width, max_h / art.height)
    resized = art.resize((max(1, int(art.width * scale)), max(1, int(art.height * scale))), Image.LANCZOS)
    offset = ((cw - resized.width) // 2, (ch - resized.height) // 2)
    canvas.alpha_composite(resized, offset)


def _paste_left_aligned(canvas, art, margin_frac=0.06, vertical_margin_frac=0.22):
    """Like _paste_centered, but flush against the left edge (a small
    margin in from it) with the remaining space on the right — for the
    Wallet pass header logo, which Apple renders left-anchored, so any
    slack space belongs on the right, not split evenly on both sides.

    Vertical margin is deliberately much larger than the horizontal one:
    confirmed on a real device that Apple's own rendering of the
    collapsed-stack header row clips into the logo when it's sized too
    close to the full canvas height, trimming the top/bottom of the
    crest and wordmark. The canvas has more vertical headroom than
    Apple actually gives the logo, so this leaves real breathing room
    rather than trusting the nominal canvas size.
    """
    cw, ch = canvas.size
    left_margin = int(cw * margin_frac)
    max_w = cw - left_margin
    max_h = int(ch * (1 - vertical_margin_frac * 2))
    scale = min(max_w / art.width, max_h / art.height)
    resized = art.resize((max(1, int(art.width * scale)), max(1, int(art.height * scale))), Image.LANCZOS)
    offset = (left_margin, (ch - resized.height) // 2)
    canvas.alpha_composite(resized, offset)


def _make_pass_images(pass_dir, theme):
    """Generate icon + logo art using the real OLSC/LFC crest and wordmark,
    colored for `theme` (PASS_THEMES["home"] or ["away"])."""
    crest = _load_art(theme["crest_path"])
    wordmark = _load_art(theme["wordmark_path"])

    # icon.png / @2x / @3x — opaque badge, shown outside the pass card
    # (notifications, lock screen). Crest only: too small for legible text,
    # and this is a recognition mark, not the place identity gets clarified.
    icon_sizes = {"icon.png": 29, "icon@2x.png": 58, "icon@3x.png": 87}
    for name, size in icon_sizes.items():
        if theme["icon_border"]:
            border_w = max(1, round(size * 0.06))
            img = Image.new("RGBA", (size, size), theme["icon_border"])
            inner = Image.new("RGBA", (size - border_w * 2, size - border_w * 2), theme["icon_bg"])
            img.paste(inner, (border_w, border_w))
        else:
            img = Image.new("RGBA", (size, size), theme["icon_bg"])
        _paste_centered(img, crest, margin_frac=0.1)
        img.save(pass_dir / name)

    # logo.png / @2x — transparent background so it sits naturally on the
    # pass's own background color instead of showing as a hard rectangle.
    # Crest + "Official Supporters Club / Brooklyn" wordmark together: a
    # bare crest alone can't be told apart from any other LFC-branded pass
    # someone might have in Wallet (official club membership, tickets,
    # etc.) — the wordmark is what actually says "this one's OLSC Brooklyn."
    logo_sizes = {"logo.png": (160, 50), "logo@2x.png": (320, 100)}
    for name, (w, h) in logo_sizes.items():
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        _paste_left_aligned(img, wordmark, margin_frac=0.06)
        img.save(pass_dir / name)


def _build_pass_json(config, pass_data, theme):
    secondary_fields = [
        {"key": "season", "label": "SEASON", "value": pass_data.season},
    ]

    # headerFields render in the top-right of the pass, next to the logo —
    # the one part of a Wallet pass that's still visible when it's
    # collapsed in a stack of other cards, not just when fully open. Next
    # match is exactly the thing worth being able to see at a glance
    # without tapping in, so it lives here instead of (or in addition to
    # duplicating in) secondaryFields, which only shows once expanded.
    header_fields = []
    if pass_data.next_match:
        header_fields.append({"key": "nextMatch", "label": "NEXT MATCH", "value": pass_data.next_match})

    pass_json = {
        "formatVersion": 1,
        "passTypeIdentifier": config.pass_type_id,
        "teamIdentifier": config.team_id,
        "organizationName": "OLSC Brooklyn",
        "serialNumber": pass_data.serial_number,
        "description": pass_data.description,
        "generic": {
            "headerFields": header_fields,
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
                **({"altText": pass_data.barcode_alt_text} if pass_data.barcode_alt_text else {}),
            }
        ],
        "backgroundColor": theme["background"],
        "foregroundColor": theme["foreground"],
        "labelColor": theme["label"],
    }
    if pass_data.locations:
        pass_json["locations"] = list(pass_data.locations)
    if pass_data.relevant_date:
        pass_json["relevantDate"] = pass_data.relevant_date
    if pass_data.expiration_date:
        pass_json["expirationDate"] = pass_data.expiration_date
    # Both fields are required together for Apple to treat this pass as
    # eligible for push updates — Wallet registers the device for updates
    # only when it sees a webServiceURL, and authenticationToken is what
    # it presents back on every subsequent web-service call for this pass.
    if pass_data.web_service_url and pass_data.auth_token:
        pass_json["webServiceURL"] = pass_data.web_service_url
        pass_json["authenticationToken"] = pass_data.auth_token
    return pass_json


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


def _extract_apns_cert_and_key(config):
    """Extract the pass-signing cert + private key as separate PEM files,
    for use as an APNs mutual-TLS client certificate. Apple doesn't issue a
    separate "push certificate" for Wallet passes — the same Pass Type ID
    certificate that signs the pass also authenticates the push, with the
    pass type identifier as the APNs topic. Caller must delete the
    returned directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix="olsc-apns-cert-"))
    cert_pem = temp_dir / "apns_cert.pem"
    key_pem = temp_dir / "apns_key.pem"
    _run_openssl(
        [
            "openssl", "pkcs12", "-in", str(config.pass_cert_p12),
            "-clcerts", "-nokeys", "-out", str(cert_pem),
            "-passin", "stdin", "-legacy",
        ],
        stdin_data=config.cert_password,
        retry_without_legacy=True,
    )
    _run_openssl(
        [
            "openssl", "pkcs12", "-in", str(config.pass_cert_p12),
            "-nocerts", "-nodes", "-out", str(key_pem),
            "-passin", "stdin", "-legacy",
        ],
        stdin_data=config.cert_password,
        retry_without_legacy=True,
    )
    return temp_dir, cert_pem, key_pem


# Apple's "Handling notification responses from APNs": these mean the
# token is gone and we must delete the device registration. Anything else
# (timeouts, 5xx) is a transient miss — leave the row so a later retry
# can still reach the phone.
_APNS_INVALID_TOKEN_REASONS = {
    "BadDeviceToken",
    "Unregistered",
    "ExpiredToken",
    "DeviceTokenNotForTopic",
}


def _apns_token_is_invalid(status_code, body_text):
    if status_code == 410:
        return True
    if status_code != 400:
        return False
    try:
        reason = json.loads(body_text or "{}").get("reason", "")
    except (ValueError, TypeError):
        reason = ""
    return reason in _APNS_INVALID_TOKEN_REASONS


def send_apns_pass_updates(config, push_tokens):
    """Fan out a Wallet pass-update push to every registered device.

    Apple's current APNs docs require `apns-push-type` (missing header
    can be delayed or dropped even when the POST returns 200) and, for a
    silent wake-up, `apns-priority: 5` (omitting it defaults to 10, which
    is a mismatch for an empty payload). Wallet's own spec still wants an
    empty JSON dictionary as the body, the Pass Type ID as the topic, and
    the same cert that signed the pass — those three are unchanged.

    Reuses one HTTP/2 connection and one cert extract for the whole
    fan-out (Apple: reuse the connection). Returns
    (sent_count, invalid_tokens) so the caller can delete dead tokens.
    """
    import httpx

    if not push_tokens:
        return 0, []

    temp_dir, cert_pem, key_pem = _extract_apns_cert_and_key(config)
    sent = 0
    invalid = []
    headers = {
        "apns-topic": config.pass_type_id,
        "apns-push-type": "background",
        "apns-priority": "5",
    }
    try:
        with httpx.Client(http2=True, cert=(str(cert_pem), str(key_pem)), timeout=10.0) as client:
            for push_token in push_tokens:
                try:
                    resp = client.post(
                        f"https://api.push.apple.com/3/device/{push_token}",
                        headers=headers,
                        json={},
                    )
                except Exception as e:
                    print(f"APNs push to {push_token[:12]}... errored: {e}")
                    continue
                if resp.status_code == 200:
                    sent += 1
                    continue
                print(f"APNs push to {push_token[:12]}... failed ({resp.status_code}): {resp.text}")
                if _apns_token_is_invalid(resp.status_code, resp.text):
                    invalid.append(push_token)
        return sent, invalid
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def send_apns_pass_update(config, push_token):
    """Tell one device that an installed pass has an update waiting.
    Returns True on success. Prefer send_apns_pass_updates for fan-out.
    """
    sent, _invalid = send_apns_pass_updates(config, [push_token])
    return sent == 1


def _zip_pass(pass_dir):
    out_path = pass_dir.parent / "member.pkpass"
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in pass_dir.iterdir():
            archive.write(file_path, file_path.name)
    return out_path.read_bytes()


def build_member_pkpass(pass_data, config=None):
    """Build and sign a .pkpass package, returning bytes."""
    temp_dir = Path(tempfile.mkdtemp(prefix="olsc-wallet-pass-"))
    try:
        config = config or load_apple_wallet_config(temp_dir / "certs")
        theme = PASS_THEMES["home"] if pass_data.is_home else PASS_THEMES["away"]
        pass_dir = temp_dir / "pass"
        pass_dir.mkdir(parents=True)
        (pass_dir / "pass.json").write_text(
            json.dumps(_build_pass_json(config, pass_data, theme)),
            encoding="utf-8",
        )
        _make_pass_images(pass_dir, theme)
        _write_manifest(pass_dir)
        _sign_manifest(pass_dir, config)
        return _zip_pass(pass_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
