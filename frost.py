"""Fetch air temperature observations from the MET Norway Frost API."""

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

OBSERVATIONS_URL = "https://frost.met.no/observations/v0.jsonld"
CLIENT_ID_FILE = Path(__file__).parent / "client_id.txt"


@dataclass(frozen=True)
class Reading:
    time: datetime
    temperature: float


def get_client_id():
    """Read the client ID from FROST_CLIENT_ID, or from client_id.txt (gitignored)."""
    client_id = os.environ.get("FROST_CLIENT_ID")
    if client_id:
        return client_id.strip()
    if CLIENT_ID_FILE.exists():
        return CLIENT_ID_FILE.read_text().strip()
    raise SystemExit(
        "No Frost client ID found. Set FROST_CLIENT_ID or put it in client_id.txt."
    )


def fetch_temperatures(station, start, end):
    """Return readings for one station between start and end, sorted by time.

    start and end are dates. If Frost returns the same time more than once,
    only the first value is kept.
    """
    params = {
        "sources": station,
        "referencetime": f"{start.isoformat()}/{end.isoformat()}",
        "elements": "air_temperature",
        # Frost returns several series per station; keep only the standard one:
        # 2 m above ground, one value every 10 minutes.
        "levels": "2",
        "timeresolutions": "PT10M",
    }
    response = requests.get(OBSERVATIONS_URL, params=params, auth=(get_client_id(), ""))
    response.raise_for_status()

    by_time = {}
    for item in response.json()["data"]:
        time = datetime.fromisoformat(item["referenceTime"])
        for observation in item["observations"]:
            by_time.setdefault(time, observation["value"])

    return [Reading(time, by_time[time]) for time in sorted(by_time)]

