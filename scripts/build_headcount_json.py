import os
import json
from datetime import datetime

from dotenv import load_dotenv
import pytz

# Placeholder SDK import
# from passkit import members


def load_config():
	load_dotenv()
	return {
		"PROGRAM_ID": os.getenv("PROGRAM_ID", ""),
		"TIMEZONE": os.getenv("TIMEZONE", "America/New_York"),
	}


def get_checked_in_count(program_id: str) -> int:
	# Replace with actual PassKit SDK call
	raise NotImplementedError("Integrate PassKit SDK: query members where status == CHECKED_IN")


def main():
	config = load_config()
	if not config["PROGRAM_ID"]:
		raise RuntimeError("PROGRAM_ID is required")

	count = get_checked_in_count(config["PROGRAM_ID"])
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

