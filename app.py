"""
FPL Guidance Tool — Flask REST API
===================================
Production-ready orchestration layer.
Serves both the API and the React frontend build.
"""

import datetime
import logging
import os
import sys
import time
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import algorithm
import data_fetcher

# --- Configuration ---

PORT = int(os.environ.get("PORT", 5000))
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT", 60))

# --- App Setup ---

# Serve React build from /static folder (built by build.sh)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app = Flask(__name__, static_folder=static_dir, static_url_path="")
CORS(app, origins=ALLOWED_ORIGINS.split(","))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# --- Rate Limiting (in-memory, per IP) ---

_rate_store = {}


def _check_rate_limit():
    """Returns True if request should be blocked."""
    ip = request.remote_addr or "unknown"
    now = time.time()
    window_start = now - 60

    if ip not in _rate_store:
        _rate_store[ip] = []

    # Purge old entries
    _rate_store[ip] = [t for t in _rate_store[ip] if t > window_start]
    if len(_rate_store[ip]) >= RATE_LIMIT_PER_MINUTE:
        return True

    _rate_store[ip].append(now)
    return False


def rate_limited(f):
    """Decorator that applies rate limiting to an endpoint."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if _check_rate_limit():
            return jsonify({"error": "Rate limit exceeded. Try again in a minute."}), 429
        return f(*args, **kwargs)
    return wrapper


# --- Input Validation ---

def _get_team_id():
    """Get and validate team_id from query params or global settings."""
    team_id = request.args.get("team_id", type=int)
    if team_id is None:
        team_id = settings.get("team_id")
    if team_id is None:
        return None, "team_id is required"
    if not (1 <= team_id <= 20_000_000):
        return None, "team_id must be between 1 and 20,000,000"
    return team_id, None


def _clamp(value, min_val, max_val, default):
    """Clamp an integer value to a range, with fallback default."""
    if value is None:
        return default
    return max(min_val, min(max_val, value))


# --- Global Settings ---

settings = {
    "team_id": None,
    "exclude_player_ids": [],
    "max_transfers": 2,
    "lookahead_gw": 5,
    "optimization_criteria": "projected_points",
    "rival_ids": [],
}

# --- Data Cache ---

_data_cache = {}


def _get_data(team_id, refresh=False):
    """Load data for a team, using cache unless refresh requested."""
    if refresh or team_id not in _data_cache:
        if refresh:
            data_fetcher.clear_cache()
        log.info("Fetching FPL data for team %s (refresh=%s)", team_id, refresh)
        _data_cache[team_id] = data_fetcher.load_all_data(team_id)
    return _data_cache[team_id]


# --- Serve React Frontend ---

@app.route("/")
def serve_frontend():
    """Serve the React app's index.html."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(static_dir, "index.html")
    return jsonify({
        "message": "FPL Guidance Tool API is running. Frontend not built yet — run build.sh first.",
        "api_docs": "/api/health",
    })


@app.route("/<path:path>")
def serve_static_or_fallback(path):
    """Serve static files, or fall back to index.html for client-side routing."""
    file_path = os.path.join(static_dir, path)
    if os.path.isfile(file_path):
        return send_from_directory(static_dir, path)
    # SPA fallback
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(static_dir, "index.html")
    return jsonify({"error": "Not found"}), 404


# --- API: Health Check ---

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })


# --- API: Settings ---

@app.route("/api/settings", methods=["GET"])
@rate_limited
def get_settings():
    return jsonify(settings)


@app.route("/api/settings", methods=["POST"])
@rate_limited
def update_settings():
    body = request.get_json(silent=True) or {}

    if "team_id" in body:
        tid = body["team_id"]
        if isinstance(tid, int) and 1 <= tid <= 20_000_000:
            settings["team_id"] = tid

    if "exclude_player_ids" in body:
        ids = body["exclude_player_ids"]
        if isinstance(ids, list) and len(ids) <= 15:
            settings["exclude_player_ids"] = [int(i) for i in ids if isinstance(i, (int, float))]

    if "max_transfers" in body:
        settings["max_transfers"] = _clamp(int(body["max_transfers"]), 1, 5, 2)

    if "lookahead_gw" in body:
        settings["lookahead_gw"] = _clamp(int(body["lookahead_gw"]), 1, 10, 5)

    if "optimization_criteria" in body:
        criteria = body["optimization_criteria"]
        if criteria in ("projected_points", "form", "fixture_difficulty"):
            settings["optimization_criteria"] = criteria

    return jsonify({"status": "updated", "settings": settings})


# --- API: Squad ---

@app.route("/api/squad")
@rate_limited
def get_squad():
    team_id, err = _get_team_id()
    if err:
        return jsonify({"error": err}), 400

    try:
        refresh = request.args.get("refresh", "false").lower() == "true"
        data = _get_data(team_id, refresh=refresh)
        result = algorithm.get_squad_display(data)
        return jsonify(result)
    except Exception as e:
        log.exception("Error fetching squad for team %s", team_id)
        return jsonify({"error": "Failed to load squad. Check your team ID and try again."}), 500


# --- API: Player Stats ---

@app.route("/api/player/<int:player_id>/stats")
@rate_limited
def get_player_stats(player_id):
    team_id, err = _get_team_id()
    if err:
        return jsonify({"error": err}), 400

    if not (1 <= player_id <= 1000):
        return jsonify({"error": "Invalid player ID"}), 400

    try:
        data = _get_data(team_id)
        result = algorithm.get_player_details(data, player_id)
        if result is None:
            return jsonify({"error": "Player not found"}), 404
        return jsonify(result)
    except Exception as e:
        log.exception("Error fetching player %s stats", player_id)
        return jsonify({"error": "Failed to load player stats."}), 500


# --- API: Fixtures ---

@app.route("/api/fixtures")
@rate_limited
def get_fixtures():
    team_id, err = _get_team_id()
    if err:
        return jsonify({"error": err}), 400

    try:
        data = _get_data(team_id)
        tables = algorithm.build_lookup_tables(data)

        gw_from = _clamp(request.args.get("gw_from", type=int), 1, 38, tables["current_gw"] + 1)
        gw_to = _clamp(request.args.get("gw_to", type=int), gw_from, 38, gw_from + 4)

        fixtures_list = []
        for gw in range(gw_from, gw_to + 1):
            gw_fixtures = tables["fixtures_by_gw"].get(gw, [])
            for fix in gw_fixtures:
                home_team = tables["teams_by_id"].get(fix.get("team_h"), {})
                away_team = tables["teams_by_id"].get(fix.get("team_a"), {})
                fixtures_list.append({
                    "gameweek": gw,
                    "home_team": home_team.get("short_name", "???"),
                    "away_team": away_team.get("short_name", "???"),
                    "home_team_id": fix.get("team_h"),
                    "away_team_id": fix.get("team_a"),
                    "home_difficulty": fix.get("team_h_difficulty", 3),
                    "away_difficulty": fix.get("team_a_difficulty", 3),
                    "finished": fix.get("finished", False),
                })

        return jsonify({"fixtures": fixtures_list, "gw_from": gw_from, "gw_to": gw_to})
    except Exception as e:
        log.exception("Error fetching fixtures")
        return jsonify({"error": "Failed to load fixtures."}), 500


# --- API: Recommendations ---

@app.route("/api/recommendations")
@rate_limited
def get_recommendations():
    team_id, err = _get_team_id()
    if err:
        return jsonify({"error": err}), 400

    try:
        data = _get_data(team_id)
        max_transfers = _clamp(request.args.get("max_transfers", type=int), 1, 5, settings["max_transfers"])
        lookahead = _clamp(request.args.get("lookahead_gw", type=int), 1, 10, settings["lookahead_gw"])
        exclude = settings.get("exclude_player_ids", [])

        result = algorithm.get_transfer_recommendations(
            data,
            exclude_player_ids=exclude,
            max_transfers=max_transfers,
            num_gw=lookahead,
        )
        return jsonify(result)
    except Exception as e:
        log.exception("Error calculating recommendations for team %s", team_id)
        return jsonify({"error": "Failed to calculate recommendations."}), 500


# --- API: Captain Picks ---

@app.route("/api/captains")
@rate_limited
def get_captains():
    team_id, err = _get_team_id()
    if err:
        return jsonify({"error": err}), 400

    try:
        data = _get_data(team_id)
        num = _clamp(request.args.get("num_suggestions", type=int), 1, 15, 5)
        result = algorithm.get_captain_recommendations(data, num_suggestions=num)
        return jsonify({"captains": result})
    except Exception as e:
        log.exception("Error calculating captains for team %s", team_id)
        return jsonify({"error": "Failed to calculate captain picks."}), 500


# --- API: Leagues ---

@app.route("/api/leagues")
@rate_limited
def get_leagues():
    team_id, err = _get_team_id()
    if err:
        return jsonify({"error": err}), 400

    try:
        data = _get_data(team_id)
        result = algorithm.get_leagues_display(data)
        return jsonify(result)
    except Exception as e:
        log.exception("Error fetching leagues for team %s", team_id)
        return jsonify({"error": "Failed to load leagues."}), 500


@app.route("/api/leagues/<int:league_id>/standings")
@rate_limited
def get_league_standings(league_id):
    team_id, err = _get_team_id()
    if err:
        return jsonify({"error": err}), 400

    if not (1 <= league_id <= 100_000_000):
        return jsonify({"error": "Invalid league ID"}), 400

    try:
        standings = data_fetcher.fetch_league_standings(league_id)
        return jsonify(standings)
    except Exception as e:
        log.exception("Error fetching standings for league %s", league_id)
        return jsonify({"error": "Failed to load league standings."}), 500


# --- API: Rivals ---

@app.route("/api/rivals", methods=["GET"])
@rate_limited
def get_rivals():
    return jsonify({"rival_ids": settings.get("rival_ids", [])})


@app.route("/api/rivals", methods=["POST"])
@rate_limited
def set_rivals():
    body = request.get_json(silent=True) or {}
    rival_ids = body.get("rival_ids", [])
    if isinstance(rival_ids, list) and len(rival_ids) <= 10:
        settings["rival_ids"] = [int(i) for i in rival_ids if isinstance(i, (int, float))]
    return jsonify({"status": "updated", "rival_ids": settings.get("rival_ids", [])})


@app.route("/api/rivals/<int:rival_team_id>/analysis")
@rate_limited
def get_rival_analysis(rival_team_id):
    team_id, err = _get_team_id()
    if err:
        return jsonify({"error": err}), 400

    if not (1 <= rival_team_id <= 20_000_000):
        return jsonify({"error": "Invalid rival team ID"}), 400

    try:
        data = _get_data(team_id)
        current_gw = data.get("current_gw", 1)
        rival_picks = data_fetcher.fetch_rival_squad(rival_team_id, current_gw)
        rival_info = data_fetcher.fetch_user_info(rival_team_id)
        result = algorithm.get_rival_analysis(data, rival_picks, rival_info)
        return jsonify(result)
    except Exception as e:
        log.exception("Error analyzing rival %s", rival_team_id)
        return jsonify({"error": "Failed to analyze rival."}), 500


# --- API: Chip Recommendations ---

@app.route("/api/chips")
@rate_limited
def get_chips():
    team_id, err = _get_team_id()
    if err:
        return jsonify({"error": err}), 400

    try:
        data = _get_data(team_id)
        result = algorithm.get_chip_recommendations(data)
        return jsonify(result)
    except Exception as e:
        log.exception("Error calculating chip recommendations for team %s", team_id)
        return jsonify({"error": "Failed to calculate chip recommendations."}), 500


# --- API: Rotation Strategy ---

@app.route("/api/rotation")
@rate_limited
def get_rotation():
    team_id, err = _get_team_id()
    if err:
        return jsonify({"error": err}), 400

    try:
        data = _get_data(team_id)
        num_gw = _clamp(request.args.get("num_gw", type=int), 1, 10, settings["lookahead_gw"])
        result = algorithm.get_rotation_strategy(data, num_gw=num_gw)
        return jsonify(result)
    except Exception as e:
        log.exception("Error calculating rotation for team %s", team_id)
        return jsonify({"error": "Failed to calculate rotation strategy."}), 500


# --- Entry Point ---

if __name__ == "__main__":
    log.info("=" * 50)
    log.info("FPL Guidance Tool")
    log.info("Running on http://localhost:%s", PORT)
    log.info("=" * 50)
    app.run(debug=DEBUG, port=PORT, host="0.0.0.0")
