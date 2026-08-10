#!/usr/bin/env python3
"""
Export PassKit season data and build an offline analytics dashboard.

Reads PassKit credentials from .env / environment:
  PROGRAM_ID, API_BASE, PASSKIT_API_KEY, PASSKIT_PROJECT_KEY, TIMEZONE

Optional:
  FOOTBALL_DATA_API_KEY for matching check-in dates to Liverpool fixtures.
"""

import csv
import html
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


ROOT = Path(__file__).resolve().parent
EXPORT_ROOT = ROOT / "season_exports"
TEAM_ID_LIVERPOOL = 64


def env_value(key, default=""):
    value = os.getenv(key, default)
    return value.strip() if isinstance(value, str) else value


def require_config():
    load_dotenv()
    config = {
        "program_id": env_value("PROGRAM_ID"),
        "api_base": env_value("API_BASE", "https://api.pub2.passkit.io"),
        "api_key": env_value("PASSKIT_API_KEY"),
        "project_key": env_value("PASSKIT_PROJECT_KEY"),
        "timezone": env_value("TIMEZONE", "America/New_York"),
        "football_data_api_key": env_value("FOOTBALL_DATA_API_KEY"),
    }
    missing = [k for k in ("program_id", "api_key", "project_key") if not config[k]]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
    return config


def timezone(config):
    if ZoneInfo:
        return ZoneInfo(config["timezone"])
    raise SystemExit("Python zoneinfo is required for this export script.")


def passkit_headers(config):
    return {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
        "X-Project-Key": config["project_key"],
    }


def parse_ndjson(text):
    records = []
    errors = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append({"line": line_no, "error": str(exc), "raw": line[:500]})
            continue
        if "result" in payload:
            records.append(payload["result"])
        elif payload:
            records.append(payload)
    return records, errors


def request_json(config, method, path, **kwargs):
    url = f"{config['api_base'].rstrip('/')}{path}"
    response = requests.request(
        method,
        url,
        headers=passkit_headers(config),
        timeout=60,
        **kwargs,
    )
    response.raise_for_status()
    return response.json()


def list_passkit_records(config, path, limit=1000):
    records = []
    parse_errors = []
    offset = 0
    while True:
        payload = {"filters": {"limit": limit, "offset": offset}}
        url = f"{config['api_base'].rstrip('/')}{path}"
        response = requests.post(
            url,
            headers=passkit_headers(config),
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        page, errors = parse_ndjson(response.text)
        records.extend(page)
        parse_errors.extend(errors)
        if len(page) < limit:
            break
        offset += limit
    return records, parse_errors


def flatten(value, prefix=""):
    if isinstance(value, dict):
        out = {}
        for key, nested in value.items():
            child = f"{prefix}.{key}" if prefix else key
            out.update(flatten(nested, child))
        return out
    if isinstance(value, list):
        return {prefix: ",".join(str(item) for item in value)}
    return {prefix: value}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")


def write_ndjson(path, records):
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps({"result": record}, sort_keys=True, default=str))
            handle.write("\n")


def write_csv(path, records):
    flat_records = [flatten(record) for record in records]
    fieldnames = sorted({key for row in flat_records for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_records)


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def local_dt(value, tz):
    parsed = parse_time(value)
    return parsed.astimezone(tz) if parsed else None


def member_identity(member):
    person = (member or {}).get("person") or {}
    name = person.get("displayName") or "Unknown"
    email = (person.get("emailAddress") or "").lower()
    member_id = (member or {}).get("id") or email or name
    return member_id, name, email


def event_member_identity(event):
    return member_identity(event.get("member") or {})


def fetch_liverpool_matches(config, date_from, date_to, out_dir):
    api_key = config.get("football_data_api_key")
    if not api_key or not date_from or not date_to:
        return [], "FOOTBALL_DATA_API_KEY missing or date range unavailable"

    url = f"https://api.football-data.org/v4/teams/{TEAM_ID_LIVERPOOL}/matches"
    params = {
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
        "limit": 200,
    }
    response = requests.get(url, headers={"X-Auth-Token": api_key}, params=params, timeout=60)
    if response.status_code != 200:
        return [], f"football-data.org returned {response.status_code}: {response.text[:300]}"
    data = response.json()
    write_json(out_dir / "football_data_matches_raw.json", data)
    return sorted(data.get("matches", []), key=lambda match: match.get("utcDate", "")), None


def load_manual_overrides(tz):
    path = ROOT / "match_overrides.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not payload.get("enabled"):
        return []

    overrides = []
    for date_key, override in (payload.get("overrides") or {}).items():
        try:
            local_date = datetime.strptime(date_key, "%Y-%m-%d").date()
        except ValueError:
            continue
        label = override.get("pass_display") or override.get("opponent") or f"Override {date_key}"
        overrides.append(
            {
                "date": local_date,
                "label": label,
                "source": "manual override",
                "competition": override.get("competition", ""),
                "kickoff": override.get("time", ""),
            }
        )
    return overrides


def match_label(match, tz):
    utc_dt = parse_time(match.get("utcDate"))
    local = utc_dt.astimezone(tz) if utc_dt else None
    home = (match.get("homeTeam") or {}).get("name", "")
    away = (match.get("awayTeam") or {}).get("name", "")
    if home == "Liverpool FC":
        opponent = away
        prefix = "Liverpool vs"
    elif away == "Liverpool FC":
        opponent = home
        prefix = "Liverpool at"
    else:
        opponent = away or home or "Unknown opponent"
        prefix = "Liverpool"
    competition = (match.get("competition") or {}).get("name", "")
    score = match.get("score") or {}
    full_time = score.get("fullTime") or {}
    result = ""
    if full_time.get("home") is not None and full_time.get("away") is not None:
        result = f" ({full_time.get('home')}-{full_time.get('away')})"
    date_part = local.strftime("%Y-%m-%d") if local else match.get("utcDate", "")[:10]
    return {
        "date": local.date() if local else None,
        "label": f"{date_part} - {prefix} {opponent}{result}",
        "source": "football-data.org",
        "competition": competition,
        "kickoff": local.strftime("%I:%M %p").lstrip("0") if local else "",
    }


def build_match_index(matches, overrides, tz):
    by_date = {}
    for match in matches:
        item = match_label(match, tz)
        if item["date"]:
            by_date[item["date"]] = item
    for override in overrides:
        by_date[override["date"]] = override
    return by_date


def summarize(members, events, matches, match_fetch_error, config):
    tz = timezone(config)
    checkins = [event for event in events if event.get("eventType") == "EVENT_MEMBER_CHECKED_IN"]
    checkouts = [event for event in events if event.get("eventType") == "EVENT_MEMBER_CHECKED_OUT"]

    attendee_counts = Counter()
    attendee_details = {}
    checkins_by_date = Counter()
    checkins_by_hour = Counter()
    checkins_by_weekday = Counter()
    event_type_counts = Counter(event.get("eventType") or "UNKNOWN" for event in events)
    member_status_counts = Counter(member.get("status") or "UNKNOWN" for member in members)
    pass_status_counts = Counter((member.get("passMetaData") or {}).get("status") or "UNKNOWN" for member in members)
    install_device_counts = Counter()
    render_city_counts = Counter()

    first_checkin = None
    last_checkin = None
    overrides = load_manual_overrides(tz)
    match_index = build_match_index(matches, overrides, tz)

    for member in members:
        pass_meta = member.get("passMetaData") or {}
        devices = pass_meta.get("installDeviceAttributes") or []
        if isinstance(devices, list):
            for device in devices:
                install_device_counts[str(device)] += 1
        elif devices:
            install_device_counts[str(devices)] += 1
        location = pass_meta.get("renderLocation") or {}
        city = location.get("city") if isinstance(location, dict) else ""
        state = location.get("state") if isinstance(location, dict) else ""
        if city or state:
            render_city_counts[f"{city}, {state}".strip(", ")] += 1

    match_checkins = Counter()
    match_details = {}
    unmatched_dates = Counter()

    for event in checkins:
        member_id, name, email = event_member_identity(event)
        attendee_counts[member_id] += 1
        attendee_details[member_id] = {"member_id": member_id, "name": name, "email": email}

        local = local_dt(event.get("date") or event.get("created"), tz)
        if not local:
            continue
        first_checkin = local if first_checkin is None or local < first_checkin else first_checkin
        last_checkin = local if last_checkin is None or local > last_checkin else last_checkin
        checkins_by_date[local.date().isoformat()] += 1
        checkins_by_hour[local.strftime("%I %p").lstrip("0")] += 1
        checkins_by_weekday[local.strftime("%A")] += 1

        matched = match_index.get(local.date())
        if matched:
            key = matched["label"]
            match_checkins[key] += 1
            match_details[key] = matched
        else:
            key = f"{local.date().isoformat()} - Unmatched check-in date"
            unmatched_dates[key] += 1
            match_checkins[key] += 1
            match_details[key] = {"date": local.date(), "label": key, "source": "check-in date", "competition": "", "kickoff": ""}

    top_attendees = []
    for member_id, count in attendee_counts.most_common():
        details = attendee_details.get(member_id, {})
        top_attendees.append({**details, "checkins": count})

    busiest_matches = []
    for label, count in match_checkins.most_common():
        details = match_details.get(label, {})
        busiest_matches.append(
            {
                "match": label,
                "checkins": count,
                "source": details.get("source", ""),
                "competition": details.get("competition", ""),
                "kickoff": details.get("kickoff", ""),
            }
        )

    return {
        "generated_at": datetime.now(tz).isoformat(),
        "timezone": config["timezone"],
        "program_id": config["program_id"],
        "member_count": len(members),
        "event_count": len(events),
        "checkin_count": len(checkins),
        "checkout_count": len(checkouts),
        "unique_attendee_count": len(attendee_counts),
        "first_checkin": first_checkin.isoformat() if first_checkin else None,
        "last_checkin": last_checkin.isoformat() if last_checkin else None,
        "top_attendees": top_attendees,
        "busiest_matches": busiest_matches,
        "checkins_by_date": dict(sorted(checkins_by_date.items())),
        "checkins_by_hour": dict(checkins_by_hour.most_common()),
        "checkins_by_weekday": dict(checkins_by_weekday.most_common()),
        "event_type_counts": dict(event_type_counts.most_common()),
        "member_status_counts": dict(member_status_counts.most_common()),
        "pass_status_counts": dict(pass_status_counts.most_common()),
        "install_device_counts": dict(install_device_counts.most_common()),
        "render_city_counts": dict(render_city_counts.most_common(25)),
        "football_data_matches": len(matches),
        "football_data_error": match_fetch_error,
        "unmatched_checkin_dates": dict(unmatched_dates.most_common()),
    }


def write_stats_csvs(out_dir, stats):
    tables = {
        "top_attendees.csv": stats["top_attendees"],
        "busiest_matches.csv": stats["busiest_matches"],
        "checkins_by_date.csv": [{"date": key, "checkins": value} for key, value in stats["checkins_by_date"].items()],
        "checkins_by_hour.csv": [{"hour": key, "checkins": value} for key, value in stats["checkins_by_hour"].items()],
        "checkins_by_weekday.csv": [{"weekday": key, "checkins": value} for key, value in stats["checkins_by_weekday"].items()],
    }
    for filename, rows in tables.items():
        if not rows:
            continue
        with (out_dir / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def bars(title, rows, label_key, value_key, limit=12):
    rows = rows[:limit]
    if not rows:
        return f"<section><h2>{html.escape(title)}</h2><p>No data.</p></section>"
    max_value = max(row[value_key] for row in rows) or 1
    items = []
    for row in rows:
        label = html.escape(str(row[label_key]))
        value = row[value_key]
        width = max(3, int((value / max_value) * 100))
        items.append(
            f"<div class='bar-row'><div class='bar-label'>{label}</div>"
            f"<div class='bar-track'><div class='bar' style='width:{width}%'></div></div>"
            f"<div class='bar-value'>{value}</div></div>"
        )
    return f"<section><h2>{html.escape(title)}</h2>{''.join(items)}</section>"


def counter_bars(title, counter_dict, limit=12):
    rows = [{"label": key, "count": value} for key, value in counter_dict.items()]
    return bars(title, rows, "label", "count", limit)


def write_dashboard(out_dir, stats):
    top = stats["top_attendees"][0] if stats["top_attendees"] else None
    busiest = stats["busiest_matches"][0] if stats["busiest_matches"] else None
    cards = [
        ("Members backed up", stats["member_count"]),
        ("Member events backed up", stats["event_count"]),
        ("Check-ins", stats["checkin_count"]),
        ("Unique attendees", stats["unique_attendee_count"]),
        ("Check-outs", stats["checkout_count"]),
        ("Fixture matches loaded", stats["football_data_matches"]),
    ]
    card_html = "".join(
        f"<div class='card'><div class='metric'>{value}</div><div class='label'>{html.escape(label)}</div></div>"
        for label, value in cards
    )
    top_html = (
        f"<p><strong>Most check-ins:</strong> {html.escape(top['name'])} "
        f"({top['checkins']} check-ins, {html.escape(top.get('email') or 'no email')}).</p>"
        if top
        else "<p><strong>Most check-ins:</strong> No check-in records found.</p>"
    )
    busiest_html = (
        f"<p><strong>Busiest match/date:</strong> {html.escape(busiest['match'])} "
        f"with {busiest['checkins']} check-ins.</p>"
        if busiest
        else "<p><strong>Busiest match/date:</strong> No check-in records found.</p>"
    )
    warning = ""
    if stats.get("football_data_error"):
        warning = f"<p class='warning'>Fixture lookup note: {html.escape(stats['football_data_error'])}</p>"
    if stats.get("unmatched_checkin_dates"):
        warning += "<p class='warning'>Some check-in dates did not match a Liverpool fixture, so they are labeled as unmatched dates.</p>"

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OLSC Brooklyn Season Dashboard</title>
  <style>
    :root {{ color-scheme: dark; --red:#c8102e; --green:#00a65a; --bg:#101114; --panel:#191b20; --muted:#9fa6b2; --text:#f7f7f8; }}
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:radial-gradient(circle at top left, rgba(200,16,46,.35), transparent 32rem), var(--bg); color:var(--text); }}
    main {{ max-width:1180px; margin:0 auto; padding:40px 20px 64px; }}
    header {{ margin-bottom:26px; }}
    h1 {{ margin:0 0 8px; font-size:clamp(2rem, 4vw, 4rem); letter-spacing:-.04em; }}
    h2 {{ margin:0 0 18px; font-size:1.1rem; color:#fff; }}
    p {{ color:var(--muted); line-height:1.5; }}
    .grid {{ display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); margin:22px 0; }}
    .card, section {{ background:rgba(25,27,32,.88); border:1px solid rgba(255,255,255,.08); border-radius:18px; box-shadow:0 20px 70px rgba(0,0,0,.25); }}
    .card {{ padding:20px; }}
    .metric {{ font-size:2.1rem; font-weight:800; letter-spacing:-.04em; }}
    .label {{ color:var(--muted); font-size:.9rem; margin-top:4px; }}
    .insights {{ padding:22px; border-left:4px solid var(--red); }}
    .sections {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:16px; margin-top:16px; }}
    section {{ padding:22px; }}
    .bar-row {{ display:grid; grid-template-columns:minmax(115px, 1.4fr) 2fr 44px; align-items:center; gap:10px; margin:12px 0; }}
    .bar-label {{ color:#e8eaed; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:.92rem; }}
    .bar-track {{ height:12px; background:#2a2d35; border-radius:999px; overflow:hidden; }}
    .bar {{ height:100%; background:linear-gradient(90deg,var(--red),var(--green)); border-radius:999px; }}
    .bar-value {{ color:#fff; text-align:right; font-variant-numeric:tabular-nums; }}
    .warning {{ color:#ffd27d; }}
    a {{ color:#fff; }}
    footer {{ margin-top:26px; color:var(--muted); font-size:.9rem; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>OLSC Brooklyn Season Dashboard</h1>
      <p>Generated {html.escape(stats['generated_at'])} ({html.escape(stats['timezone'])}) from PassKit program <code>{html.escape(stats['program_id'])}</code>.</p>
    </header>
    <div class="grid">{card_html}</div>
    <div class="insights">
      {top_html}
      {busiest_html}
      <p><strong>Attendance window:</strong> {html.escape(str(stats.get('first_checkin') or 'n/a'))} to {html.escape(str(stats.get('last_checkin') or 'n/a'))}.</p>
      {warning}
    </div>
    <div class="sections">
      {bars("Top Attendees", stats["top_attendees"], "name", "checkins", 15)}
      {bars("Busiest Matches / Check-in Dates", stats["busiest_matches"], "match", "checkins", 15)}
      {counter_bars("Check-ins by Hour", stats["checkins_by_hour"], 12)}
      {counter_bars("Check-ins by Weekday", stats["checkins_by_weekday"], 7)}
      {counter_bars("Event Types", stats["event_type_counts"], 12)}
      {counter_bars("Member Statuses", stats["member_status_counts"], 12)}
      {counter_bars("Pass Install Statuses", stats["pass_status_counts"], 12)}
      {counter_bars("Render Cities", stats["render_city_counts"], 12)}
    </div>
    <footer>
      Raw backup files and CSVs live beside this dashboard. Open <code>season_stats.json</code> for the full machine-readable summary.
    </footer>
  </main>
</body>
</html>
"""
    (out_dir / "dashboard.html").write_text(html_doc, encoding="utf-8")


def main():
    config = require_config()
    stamp = datetime.now(timezone(config)).strftime("%Y%m%d_%H%M%S")
    out_dir = EXPORT_ROOT / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Exporting PassKit data to {out_dir}")
    write_json(out_dir / "export_config.json", {k: v for k, v in config.items() if "key" not in k})

    program = request_json(config, "GET", f"/members/program/{quote(config['program_id'])}")
    write_json(out_dir / "program.json", program)

    event_meta = request_json(config, "GET", f"/members/member/events/meta/{quote(config['program_id'])}")
    write_json(out_dir / "event_meta_keys.json", event_meta)

    members, member_errors = list_passkit_records(config, f"/members/member/list/{quote(config['program_id'])}")
    events, event_errors = list_passkit_records(config, f"/members/program/list/events/{quote(config['program_id'])}")

    write_ndjson(out_dir / "members_raw.ndjson", members)
    write_ndjson(out_dir / "member_events_raw.ndjson", events)
    write_json(out_dir / "members_raw.json", members)
    write_json(out_dir / "member_events_raw.json", events)
    write_csv(out_dir / "members.csv", members)
    write_csv(out_dir / "member_events.csv", events)
    write_json(out_dir / "parse_errors.json", {"members": member_errors, "events": event_errors})

    event_dates = [parse_time(event.get("date") or event.get("created")) for event in events]
    event_dates = [dt.date() for dt in event_dates if dt]
    if event_dates:
        date_from = min(event_dates) - timedelta(days=2)
        date_to = max(event_dates) + timedelta(days=14)
    else:
        date_from = None
        date_to = None

    matches, match_fetch_error = fetch_liverpool_matches(config, date_from, date_to, out_dir)
    stats = summarize(members, events, matches, match_fetch_error, config)
    write_json(out_dir / "season_stats.json", stats)
    write_stats_csvs(out_dir, stats)
    write_dashboard(out_dir, stats)

    latest = EXPORT_ROOT / "latest"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    try:
        latest.symlink_to(out_dir.name, target_is_directory=True)
    except OSError:
        pass

    top = stats["top_attendees"][0] if stats["top_attendees"] else None
    busiest = stats["busiest_matches"][0] if stats["busiest_matches"] else None
    print("Done.")
    print(f"Members: {stats['member_count']}")
    print(f"Events: {stats['event_count']} ({stats['checkin_count']} check-ins)")
    if top:
        print(f"Most check-ins: {top['name']} - {top['checkins']}")
    if busiest:
        print(f"Busiest match/date: {busiest['match']} - {busiest['checkins']}")
    print(f"Dashboard: {out_dir / 'dashboard.html'}")


if __name__ == "__main__":
    main()
