import os
import json
import time
import requests


BASE_URL = "https://api.openf1.org/v1"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

YEARS = [2023, 2024]
REQUEST_DELAY = 0.3  # seconds


def _cache_path(name: str) -> str:
    return os.path.join(DATA_DIR, f"{name}.json")


def _load_cache(name: str):
    path = _cache_path(name)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def _save_cache(name: str, data) -> None:
    with open(_cache_path(name), "w") as f:
        json.dump(data, f)


def _get(endpoint: str, params: dict = None, retries: int = 3) -> list:
    # GETs a single page from the API and returns [] on any error (noise-tolerant).
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            print(f"  [HTTP error] {e} — skipping")
            return []
        except requests.exceptions.Timeout:
            print(f"  [Timeout] attempt {attempt + 1}/{retries} for {url}")
            time.sleep(2 ** attempt)
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"  [Request error] {e}")
            return []
    return []

def fetch_meetings(force: bool = False) -> list:
    # Fetch all meetings for 2023, 2024; Returns a flat list of meeting dicts.
    cache_name = "meetings"
    if not force:
        cached = _load_cache(cache_name)
        if cached is not None:
            print(f"[cache] Loaded {len(cached)} meetings from cache.")
            return cached

    all_meetings = []
    for year in YEARS:
        print(f"  Fetching meetings for {year}...")
        rows = _get("meetings", params={"year": year})
        all_meetings.extend(rows)
        time.sleep(REQUEST_DELAY)

    _save_cache(cache_name, all_meetings)
    print(f"[API] Fetched {len(all_meetings)} meetings.")
    return all_meetings


def fetch_sessions(meeting_keys: list[int], force: bool = False) -> list:
    # Fetches all sessions for the given meeting keys.
    cache_name = "sessions"
    if not force:
        cached = _load_cache(cache_name)
        if cached is not None:
            print(f"[cache] Loaded {len(cached)} sessions from cache.")
            return cached

    all_sessions = []
    for mk in meeting_keys:
        rows = _get("sessions", params={"meeting_key": mk})
        all_sessions.extend(rows)
        time.sleep(REQUEST_DELAY)

    _save_cache(cache_name, all_sessions)
    print(f"[API] Fetched {len(all_sessions)} sessions.")
    return all_sessions


def fetch_laps_for_session(session_key: int) -> list:
    # Fetch all laps for a single session
    cache_name = f"laps_{session_key}"
    cached = _load_cache(cache_name)
    if cached is not None:
        return cached

    print(f"  Fetching laps for session {session_key}...")
    rows = _get("laps", params={"session_key": session_key})
    _save_cache(cache_name, rows)
    time.sleep(REQUEST_DELAY)
    return rows


def fetch_all_laps(session_keys: list[int], force: bool = False) -> list:

    # Fetch laps for ALL sessions, bulk fetch produces 10,000+ records across a full season. Progress is printed so the user knows it's working.
    cache_name = "laps_all"
    if not force:
        cached = _load_cache(cache_name)
        if cached is not None:
            print(f"[cache] Loaded {len(cached)} lap records from cache.")
            return cached

    all_laps = []
    total = len(session_keys)
    for i, sk in enumerate(session_keys, 1):
        print(f"  [{i}/{total}] Fetching laps for session {sk}...", end="\r")
        rows = fetch_laps_for_session(sk)
        all_laps.extend(rows)
    print()

    _save_cache(cache_name, all_laps)
    print(f"[API] Fetched {len(all_laps)} total lap records.")
    return all_laps


def load_all_data(force: bool = False) -> tuple[list, list, list]:

    # Top-level loader: returns (meetings, sessions, laps); uses cache when available.

    meetings = fetch_meetings(force=force)
    session_keys_from_meetings = [m["meeting_key"] for m in meetings if "meeting_key" in m]
    sessions = fetch_sessions(session_keys_from_meetings, force=force)
    session_keys = [s["session_key"] for s in sessions if "session_key" in s]
    laps = fetch_all_laps(session_keys, force=force)
    return meetings, sessions, laps
