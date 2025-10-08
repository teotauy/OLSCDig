import os
import time
import json
import requests
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
import pytz


REFRESH_SECONDS = int(os.getenv("REFRESH_SECONDS", "5"))


def load_config():
	load_dotenv()
	config = {
		"PROGRAM_ID": os.getenv("PROGRAM_ID", ""),
		"API_BASE": os.getenv("API_BASE", "https://api.pub1.passkit.io"),
		"API_KEY": os.getenv("PASSKIT_API_KEY", ""),
		"PROJECT_KEY": os.getenv("PASSKIT_PROJECT_KEY", ""),
		"TIMEZONE": os.getenv("TIMEZONE", "America/New_York"),
	}
	missing = [k for k, v in config.items() if k in ("PROGRAM_ID", "API_KEY", "PROJECT_KEY") and not v]
	if missing:
		raise RuntimeError(f"Missing required config env vars: {', '.join(missing)}")
	return config


def get_checked_in_count(config: dict) -> int:
	"""Return the count of members with status == CHECKED_IN using PassKit REST API."""
	headers = {
		"Authorization": f"Bearer {config['API_KEY']}",
		"Content-Type": "application/json",
	}
	
	# Add project key header if provided
	if config.get("PROJECT_KEY"):
		headers["X-Project-Key"] = config["PROJECT_KEY"]
	
	# First, let's see what the actual API structure looks like
	url = f"{config['API_BASE']}/membership/members"
	params = {
		"programId": config["PROGRAM_ID"]
	}
	
	try:
		response = requests.get(url, headers=headers, params=params, timeout=30)
		response.raise_for_status()
		data = response.json()
		
		print(f"API Response structure: {data}")
		
		# For now, return 0 until we figure out the correct field
		# TODO: Update this once we know the correct field for check-in status
		return 0
		
	except requests.exceptions.RequestException as e:
		raise RuntimeError(f"Failed to fetch members: {e}")


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

