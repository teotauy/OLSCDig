#!/usr/bin/env python3
"""Decode Google Wallet service account base64 from the macOS clipboard."""

import base64
import json
import subprocess
import sys


def main():
    raw = subprocess.check_output(["pbpaste"], text=True)
    compact = "".join(raw.split())

    print(f"Clipboard length: {len(compact)}")
    if len(compact) < 500:
        print("That is too short. Copy the actual Render secret value, not the env var name.")
        return 1

    try:
        decoded = base64.b64decode(compact, validate=True)
        data = json.loads(decoded)
    except Exception as exc:
        print(f"Could not decode clipboard as base64 service account JSON: {exc}")
        return 1

    print(f"client_email: {data.get('client_email') or '(missing)'}")
    print(f"project_id: {data.get('project_id') or '(missing)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
