import msal
import requests
import json
import os
from datetime import datetime, timedelta, date, time

from config import CLIENT_ID, AUTHORITY, SCOPES, WORK_START_HOUR, WORK_END_HOUR

TOKEN_CACHE_FILE = os.path.join(os.path.dirname(__file__), "token_cache.json")


def _get_msal_app():
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_FILE):
        cache.deserialize(open(TOKEN_CACHE_FILE, "r").read())

    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache,
    )
    return app, cache


def get_token():
    app, cache = _get_msal_app()

    # Try silent first (uses cached token)
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    # Fall back to interactive browser login
    if not result:
        result = app.acquire_token_interactive(scopes=SCOPES)

    # Persist cache
    if cache.has_state_changed:
        open(TOKEN_CACHE_FILE, "w").write(cache.serialize())

    if "access_token" in result:
        return result["access_token"]

    raise Exception(
        f"Authentication failed: {result.get('error_description', result.get('error', 'Unknown'))}"
    )


def get_user_info():
    token = get_token()
    resp = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 200:
        return resp.json()
    return {}


def get_calendar_events(start_date: date, end_date: date) -> list:
    """Fetch calendar events between two dates (inclusive)."""
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Prefer": 'outlook.timezone="UTC"',
    }

    start_str = f"{start_date}T00:00:00Z"
    end_str = f"{end_date}T23:59:59Z"

    url = "https://graph.microsoft.com/v1.0/me/calendarView"
    params = {
        "startDateTime": start_str,
        "endDateTime": end_str,
        "$select": "subject,start,end,isAllDay,showAs,location",
        "$orderby": "start/dateTime",
        "$top": 200,
    }

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 200:
        return resp.json().get("value", [])

    raise Exception(f"Graph API error {resp.status_code}: {resp.text}")


def parse_event_time(dt_str: str) -> datetime:
    """Parse Graph API datetime string to naive datetime (UTC)."""
    dt_str = dt_str.rstrip("Z").split(".")[0]
    return datetime.fromisoformat(dt_str)


def get_free_slots(for_date: date, tz_offset_hours: int = -7) -> list:
    """
    Return free time slots within work hours for a given date.
    tz_offset_hours: your local UTC offset (e.g. -7 for PDT, -5 for CDT)
    """
    events = get_calendar_events(for_date, for_date)

    work_start = datetime.combine(for_date, time(WORK_START_HOUR, 0))
    work_end = datetime.combine(for_date, time(WORK_END_HOUR, 0))

    # Build list of busy blocks (convert UTC → local by adding tz_offset_hours)
    busy = []
    for ev in events:
        if ev.get("isAllDay"):
            continue
        if ev.get("showAs") not in ("busy", "tentative", "oof"):
            continue
        s = parse_event_time(ev["start"]["dateTime"]) + timedelta(hours=tz_offset_hours)
        e = parse_event_time(ev["end"]["dateTime"]) + timedelta(hours=tz_offset_hours)
        # Clamp to work hours
        s = max(s, work_start)
        e = min(e, work_end)
        if s < e:
            busy.append((s, e))

    busy.sort()

    # Merge overlapping blocks
    merged = []
    for s, e in busy:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append([s, e])

    # Find gaps
    free_slots = []
    cursor = work_start
    for s, e in merged:
        if cursor < s:
            mins = int((s - cursor).total_seconds() / 60)
            if mins >= 15:
                free_slots.append({"start": cursor, "end": s, "duration_minutes": mins})
        cursor = max(cursor, e)

    if cursor < work_end:
        mins = int((work_end - cursor).total_seconds() / 60)
        if mins >= 15:
            free_slots.append({"start": cursor, "end": work_end, "duration_minutes": mins})

    return free_slots


def get_week_events(week_start: date) -> dict:
    """Return events grouped by date for the work week."""
    week_end = week_start + timedelta(days=4)  # Mon–Fri
    events = get_calendar_events(week_start, week_end)

    grouped = {}
    for ev in events:
        if ev.get("isAllDay"):
            continue
        ev_date = ev["start"]["dateTime"][:10]
        grouped.setdefault(ev_date, []).append(ev)

    return grouped
