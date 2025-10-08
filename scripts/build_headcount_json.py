import os
import json
import requests
from datetime import datetime

from dotenv import load_dotenv
import pytz


def load_config():
	load_dotenv()
	return {
		"PROGRAM_ID": os.getenv("PROGRAM_ID", ""),
		"API_BASE": os.getenv("API_BASE", "https://api.pub1.passkit.io"),
		"API_KEY": os.getenv("PASSKIT_API_KEY", ""),
		"PROJECT_KEY": os.getenv("PASSKIT_PROJECT_KEY", ""),
		"TIMEZONE": os.getenv("TIMEZONE", "America/New_York"),
	}


def get_checked_in_count(config: dict) -> int:
	"""Return the count of members with status == CHECKED_IN using PassKit REST API."""
	headers = {
		"Authorization": f"Bearer {config['API_KEY']}",
		"Content-Type": "application/json",
	}
	
	if config.get("PROJECT_KEY"):
		headers["X-Project-Key"] = config["PROJECT_KEY"]
	
	url = f"{config['API_BASE']}/membership/members"
	params = {
		"programId": config["PROGRAM_ID"],
		"status": "CHECKED_IN"
	}
	
	try:
		response = requests.get(url, headers=headers, params=params, timeout=30)
		response.raise_for_status()
		data = response.json()
		
		members = data.get("members", [])
		return len(members)
		
	except requests.exceptions.RequestException as e:
		raise RuntimeError(f"Failed to fetch members: {e}")


def main():
	config = load_config()
	if not config["PROGRAM_ID"]:
		raise RuntimeError("PROGRAM_ID is required")

	count = get_checked_in_count(config)
	now = datetime.now(pytz.timezone(config["TIMEZONE"]))
	payload = {
		"count": int(count),
		"updated_at": now.isoformat(timespec="seconds"),
	}

	os.makedirs("public", exist_ok=True)
	with open("public/headcount.json", "w") as f:
		json.dump(payload, f)
	print("Wrote public/headcount.json")


if __name__ == "__main__":
	main()

