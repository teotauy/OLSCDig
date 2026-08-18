#!/usr/bin/env python3
"""Google Wallet Generic pass link generation for OLSC Brooklyn."""

import base64
import json
import os
import re
from urllib.parse import urlparse

from google.auth import jwt
from google.oauth2 import service_account


class GoogleWalletConfigError(RuntimeError):
    """Raised when Google Wallet configuration is incomplete or invalid."""


def _env(key, default=""):
    value = os.getenv(key, default)
    return value.strip() if isinstance(value, str) else value


def _localized(value):
    return {
        "defaultValue": {
            "language": "en-US",
            "value": value,
        }
    }


def _safe_suffix(value, max_length=120):
    suffix = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._-")
    return (suffix or "pass")[:max_length]


def _load_service_account_info():
    encoded = _env("GOOGLE_WALLET_SERVICE_ACCOUNT_JSON_BASE64")
    if not encoded:
        raise GoogleWalletConfigError("GOOGLE_WALLET_SERVICE_ACCOUNT_JSON_BASE64 is not set")
    try:
        return json.loads(base64.b64decode("".join(encoded.split())).decode("utf-8"))
    except Exception as exc:
        raise GoogleWalletConfigError(f"Could not decode Google service account JSON: {exc}") from exc


def _load_credentials():
    info = _load_service_account_info()
    return service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/wallet_object.issuer"],
    )


def google_wallet_configured():
    return bool(_env("GOOGLE_WALLET_ISSUER_ID") and _env("GOOGLE_WALLET_SERVICE_ACCOUNT_JSON_BASE64"))


def _origin_for(base_url):
    parsed = urlparse(base_url)
    return parsed.netloc or parsed.path


def build_google_wallet_save_url(
    *,
    member_id,
    display_name,
    season_name,
    serial_number,
    barcode_value,
    next_match="",
    base_url,
    is_home=True,
):
    """Build a Google Wallet save URL containing a Generic Class/Object JWT."""
    issuer_id = _env("GOOGLE_WALLET_ISSUER_ID")
    if not issuer_id:
        raise GoogleWalletConfigError("GOOGLE_WALLET_ISSUER_ID is not set")

    credentials = _load_credentials()
    class_suffix = _safe_suffix(_env("GOOGLE_WALLET_CLASS_SUFFIX", f"olsc_brooklyn_digital_id_{season_name}_v2"))
    object_suffix = _safe_suffix(f"member_{member_id}_{serial_number}")
    class_id = f"{issuer_id}.{class_suffix}"
    object_id = f"{issuer_id}.{object_suffix}"
    wordmark = "olsc_wordmark_white.png" if is_home else "olsc_wordmark_red.png"
    background = "#e31b23" if is_home else "#ffffff"

    generic_class = {"id": class_id}

    text_modules = [
        {
            "id": "season",
            "header": "Season",
            "body": season_name,
        },
        {
            "id": "instructions",
            "header": "At the door",
            "body": "Show this Digital ID to be scanned.",
        },
    ]
    if next_match:
        text_modules.insert(0, {
            "id": "next_match",
            "header": "Next match",
            "body": next_match,
        })

    generic_object = {
        "id": object_id,
        "classId": class_id,
        "state": "ACTIVE",
        "cardTitle": _localized("OLSC Brooklyn Digital ID"),
        "header": _localized(display_name),
        "subheader": _localized(season_name),
        "hexBackgroundColor": background,
        "barcode": {
            "type": "QR_CODE",
            "value": barcode_value,
            "alternateText": "OLSC Brooklyn",
        },
        "textModulesData": text_modules,
        "logo": {
            "sourceUri": {
                "uri": f"{base_url}/wallet/assets/{wordmark}",
            },
            "contentDescription": _localized("OLSC Brooklyn Official Supporters Club"),
        },
    }

    claims = {
        "iss": credentials.service_account_email,
        "aud": "google",
        "origins": [_origin_for(base_url)],
        "typ": "savetowallet",
        "payload": {
            "genericClasses": [generic_class],
            "genericObjects": [generic_object],
        },
    }

    token = jwt.encode(credentials.signer, claims)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return f"https://pay.google.com/gp/v/save/{token}"
