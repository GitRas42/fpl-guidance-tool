"""
FPL Data Fetcher Module
=======================
Pure I/O layer for fetching data from the official Fantasy Premier League API.
No business logic — just data retrieval, caching, and error handling.
"""

import json
import os
import time
import requests

# FPL API base URL
BASE_URL = "https://fantasy.premierleague.com/api"

# Cache settings
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_DURATION = 300  # 5 minutes in seconds

# In-memory cache
_cache = {}


def _ensure_cache_dir():
    """Create cache directory if it doesn't exist."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def _get_cached(key):
    """
    Return cached data if it exists and hasn't expired.
    Checks in-memory cache first, then JSON file fallback.
    """
    # Check in-memory cache
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["timestamp"] < CACHE_DURATION:
            return entry["data"]

    # Check JSON file fallback
    filepath = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                file_data = json.load(f)
            if time.time() - file_data.get("timestamp", 0) < CACHE_DURATION:
                _cache[key] = file_data
                return file_data["data"]
        except (json.JSONDecodeError, IOError):
            pass

    return None


def _set_cached(key, data):
    """Store data in both in-memory cache and JSON file."""
    entry = {"data": data, "timestamp": time.time()}
    _cache[key] = entry

    # Save to JSON file
    _ensure_cache_dir()
    filepath = os.path.join(CACHE_DIR, f"{key}.json")
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(entry, f)
    except IOError:
        pass  # Silently fail on file write errors


def _fetch_with_retry(url, max_retries=3, timeout=10):
    """
    Fetch URL with retry logic.

    Args:
        url: The URL to fetch
        max_retries: Number of retry attempts (default 3)
        timeout: Request timeout in seconds (default 10)

    Returns:
        Parsed JSON response as dict/list

    Raises:
        requests.RequestException: If all retries fail
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout, headers={
                "User-Agent": "FPL-Guidance-Tool/1.0"
            })
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))  # Incremental backoff
    raise last_error


def fetch_bootstrap_static():
    """
    Fetch all static FPL data: players, teams, fixtures, gameweeks.

    Returns:
        dict with keys:
            - elements: list of all players
            - teams: list of all teams
            - events: list of all gameweeks
            - element_types: list of position types
    """
    cache_key = "bootstrap_static"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    data = _fetch_with_retry(f"{BASE_URL}/bootstrap-static/")
    _set_cached(cache_key, data)
    return data


def fetch_fixtures():
    """
    Fetch all fixtures with difficulty ratings.

    Returns:
        list of fixtures, each with:
            - event: gameweek number
            - team_h: home team ID
            - team_a: away team ID
            - team_h_difficulty: home difficulty (1-5)
            - team_a_difficulty: away difficulty (1-5)
            - finished: bool
    """
    cache_key = "fixtures"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    data = _fetch_with_retry(f"{BASE_URL}/fixtures/")
    _set_cached(cache_key, data)
    return data


def fetch_user_info(team_id):
    """
    Fetch user's team info: points, rank, bank, transfers.

    Args:
        team_id: FPL team ID (integer)

    Returns:
        dict with keys:
            - id: team ID
            - summary_overall_points: total points
            - summary_overall_rank: overall rank
            - last_deadline_bank: bank balance (in tenths, e.g. 50 = 5.0m)
            - last_deadline_total_transfers: total transfers made
            - current_event: current gameweek number
    """
    cache_key = f"user_info_{team_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    data = _fetch_with_retry(f"{BASE_URL}/entry/{team_id}/")
    _set_cached(cache_key, data)
    return data


def fetch_user_squad(team_id):
    """
    Fetch user's current 15-player squad for the current gameweek.

    Args:
        team_id: FPL team ID (integer)

    Returns:
        dict with keys:
            - active_chip: currently active chip (or None)
            - automatic_subs: list of auto-subs
            - entry_history: GW history (points, bank, transfers)
            - picks: list of 15 picks, each with:
                - element: player ID
                - position: squad position (1-15)
                - is_captain: bool
                - is_vice_captain: bool
                - multiplier: points multiplier
    """
    cache_key = f"user_squad_{team_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    # Get current gameweek from bootstrap data
    bootstrap = fetch_bootstrap_static()
    current_gw = None
    for event in bootstrap.get("events", []):
        if event.get("is_current"):
            current_gw = event["id"]
            break

    if current_gw is None:
        # Fallback: find the latest finished gameweek
        for event in reversed(bootstrap.get("events", [])):
            if event.get("finished"):
                current_gw = event["id"]
                break

    if current_gw is None:
        current_gw = 1

    data = _fetch_with_retry(f"{BASE_URL}/entry/{team_id}/event/{current_gw}/picks/")
    _set_cached(cache_key, data)
    return data


def fetch_user_transfers(team_id):
    """
    Fetch user's transfer history.

    Args:
        team_id: FPL team ID (integer)

    Returns:
        list of transfers, each with:
            - element_in: player bought ID
            - element_out: player sold ID
            - event: gameweek of transfer
            - time: timestamp
    """
    cache_key = f"user_transfers_{team_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    data = _fetch_with_retry(f"{BASE_URL}/entry/{team_id}/transfers/")
    _set_cached(cache_key, data)
    return data


def load_all_data(team_id):
    """
    Orchestrate all API calls and return combined data.

    Args:
        team_id: FPL team ID (integer)

    Returns:
        dict with keys:
            - bootstrap: all static FPL data
            - fixtures: all fixtures
            - user_info: user's team info
            - squad: user's current squad picks
            - transfers: user's transfer history
            - current_gw: current gameweek number
    """
    try:
        bootstrap = fetch_bootstrap_static()
    except Exception as e:
        # Try loading from JSON fallback
        fallback_path = os.path.join(CACHE_DIR, "bootstrap_static.json")
        if os.path.exists(fallback_path):
            with open(fallback_path, "r", encoding="utf-8") as f:
                bootstrap = json.load(f).get("data", {})
        else:
            raise Exception(f"Failed to fetch FPL data and no cache available: {e}")

    # Determine current gameweek
    current_gw = None
    for event in bootstrap.get("events", []):
        if event.get("is_current"):
            current_gw = event["id"]
            break
    if current_gw is None:
        for event in reversed(bootstrap.get("events", [])):
            if event.get("finished"):
                current_gw = event["id"]
                break
    if current_gw is None:
        current_gw = 1

    # Fetch remaining data
    try:
        fixtures = fetch_fixtures()
    except Exception:
        fixtures = []

    try:
        user_info = fetch_user_info(team_id)
    except Exception:
        user_info = {}

    try:
        squad = fetch_user_squad(team_id)
    except Exception:
        squad = {"picks": []}

    try:
        transfers = fetch_user_transfers(team_id)
    except Exception:
        transfers = []

    return {
        "bootstrap": bootstrap,
        "fixtures": fixtures,
        "user_info": user_info,
        "squad": squad,
        "transfers": transfers,
        "current_gw": current_gw,
    }


def clear_cache():
    """Clear all in-memory and file caches."""
    global _cache
    _cache = {}
    if os.path.exists(CACHE_DIR):
        for filename in os.listdir(CACHE_DIR):
            filepath = os.path.join(CACHE_DIR, filename)
            try:
                os.remove(filepath)
            except IOError:
                pass
