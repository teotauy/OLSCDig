import os
import time
import json
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
import pytz

# Placeholder imports for PassKit SDK
# from passkit import members


REFRESH_SECONDS = int(os.getenv("REFRESH_SECONDS", "5"))


def load_config():
	load_dotenv()
	config = {
		"PROGRAM_ID": os.getenv("PROGRAM_ID", ""),
		"API_HOST": os.getenv("API_HOST", "grpc.pub1.passkit.io"),
		"TIMEZONE": os.getenv("TIMEZONE", "America/New_York"),
		"CERTIFICATE_PEM": os.getenv("CERTIFICATE_PEM", "certs/certificate.pem"),
		"CA_CHAIN_PEM": os.getenv("CA_CHAIN_PEM", "certs/ca-chain.pem"),
		"KEY_PEM": os.getenv("KEY_PEM", "certs/key.pem"),
		"KEY_PASSWORD": os.getenv("KEY_PASSWORD", ""),
	}
	missing = [k for k, v in config.items() if k in ("PROGRAM_ID",) and not v]
	if missing:
		raise RuntimeError(f"Missing required config env vars: {', '.join(missing)}")
	return config


def get_checked_in_count(config: dict) -> int:
	"""Return the count of members with status == CHECKED_IN.
	Replace the body with actual PassKit SDK calls.
	"""
	# Example outline (pseudo):
	# client = members.MembersClient(... credentials from CERTIFICATE/KEY ...)
	# resp = client.ListMembers(program_id=config["PROGRAM_ID"], status="CHECKED_IN")
	# return len(resp.members)
	# For now, raise if not implemented.
	raise NotImplementedError("Integrate PassKit SDK: query members where status == CHECKED_IN")


def fmt_now_tz(tz_name: str) -> str:
	tz = pytz.timezone(tz_name)
	return datetime.now(tz).isoformat(timespec="seconds")


def main():
	config = load_config()
	print("Starting capacity monitor. Ctrl+C to stop.")
	print(f"Program: {config['PROGRAM_ID']}  TZ: {config['TIMEZONE']}  Host: {config['API_HOST']}")
	while True:
		try:
			count = get_checked_in_count(config)
			now = fmt_now_tz(config["TIMEZONE"])
			print(f"[{now}] CHECKED_IN headcount: {count}")
		except KeyboardInterrupt:
			print("Stopping...")
			break
		except NotImplementedError as nie:
			print(f"TODO: {nie}")
			time.sleep(REFRESH_SECONDS)
		except Exception as e:
			print(f"Error: {e}")
			time.sleep(REFRESH_SECONDS)
		time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
	main()

