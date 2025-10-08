import os
import requests
from datetime import datetime
from typing import List

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


def is_midnight_local(tz_name: str) -> bool:
	tz = pytz.timezone(tz_name)
	now = datetime.now(tz)
	return now.hour == 0


def list_checked_in_member_ids(config) -> List[str]:
	"""Return list of member IDs where status == CHECKED_IN using PassKit REST API."""
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
		return [member.get("id") for member in members if member.get("id")]
		
	except requests.exceptions.RequestException as e:
		raise RuntimeError(f"Failed to list checked-in members: {e}")


def checkout_members(config, member_ids: List[str]) -> int:
	"""Set status to CHECKED_OUT for each member id using PassKit REST API.
	Return number successfully updated.
	"""
	headers = {
		"Authorization": f"Bearer {config['API_KEY']}",
		"Content-Type": "application/json",
	}
	
	if config.get("PROJECT_KEY"):
		headers["X-Project-Key"] = config["PROJECT_KEY"]
	
	success_count = 0
	
	for member_id in member_ids:
		try:
			# Update member status to CHECKED_OUT
			url = f"{config['API_BASE']}/membership/members/{member_id}"
			payload = {
				"status": "CHECKED_OUT"
			}
			
			response = requests.patch(url, headers=headers, json=payload, timeout=30)
			response.raise_for_status()
			success_count += 1
			
		except requests.exceptions.RequestException as e:
			print(f"Failed to checkout member {member_id}: {e}")
			continue
	
	return success_count


def main():
	config = load_config()
	if not config["PROGRAM_ID"]:
		raise RuntimeError("PROGRAM_ID is required")

	# Optional timezone guard: only act at midnight local
	if not is_midnight_local(config["TIMEZONE"]):
		print("Not midnight in local timezone; exiting without changes.")
		return

	print("Listing CHECKED_IN members...")
	member_ids = list_checked_in_member_ids(config)
	print(f"Found {len(member_ids)} members to check out.")
	if not member_ids:
		print("Nothing to do.")
		return

	updated = checkout_members(config, member_ids)
	print(f"Checked out {updated} members.")


if __name__ == "__main__":
	main()

