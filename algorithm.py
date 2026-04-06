"""
FPL Algorithm Module
====================
Core recommendation logic for Fantasy Premier League.
All functions are pure and stateless — they accept data as inputs and return results.
No API calls or side effects.
"""


# Position mapping: FPL element_type ID -> position name
POSITION_MAP = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

# Default form values by position (used when data is missing)
DEFAULT_FORM = {"GK": 4.0, "DEF": 4.5, "MID": 5.0, "FWD": 4.5}

# Formation for rotation: positions and counts
FORMATION = {"GK": 1, "DEF": 4, "MID": 5, "FWD": 1}


def build_lookup_tables(data):
    """
    Build lookup tables from raw FPL data for efficient access.

    Args:
        data: dict from load_all_data() with bootstrap, fixtures, etc.

    Returns:
        dict with:
            - players_by_id: {player_id: player_dict}
            - teams_by_id: {team_id: team_dict}
            - fixtures_by_gw: {gw_number: [fixture_list]}
            - position_map: {element_type: position_name}
            - current_gw: int
    """
    bootstrap = data.get("bootstrap", {})
    fixtures = data.get("fixtures", [])

    # Players indexed by ID
    players_by_id = {}
    for player in bootstrap.get("elements", []):
        players_by_id[player["id"]] = player

    # Teams indexed by ID
    teams_by_id = {}
    for team in bootstrap.get("teams", []):
        teams_by_id[team["id"]] = team

    # Fixtures grouped by gameweek
    fixtures_by_gw = {}
    for fixture in fixtures:
        gw = fixture.get("event")
        if gw is not None:
            if gw not in fixtures_by_gw:
                fixtures_by_gw[gw] = []
            fixtures_by_gw[gw].append(fixture)

    return {
        "players_by_id": players_by_id,
        "teams_by_id": teams_by_id,
        "fixtures_by_gw": fixtures_by_gw,
        "position_map": POSITION_MAP,
        "current_gw": data.get("current_gw", 1),
    }


def get_player_fixtures(player_id, player_team_id, fixtures_by_gw, current_gw, num_gw=5):
    """
    Get upcoming fixtures for a player over the next N gameweeks.

    Args:
        player_id: FPL player ID
        player_team_id: player's team ID
        fixtures_by_gw: {gw: [fixtures]} from build_lookup_tables
        current_gw: current gameweek number
        num_gw: number of gameweeks to look ahead (default 5)

    Returns:
        list of dicts, each with:
            - gw: gameweek number
            - opponent_team: opponent team ID
            - is_home: bool
            - difficulty: difficulty rating (1-5)
    """
    upcoming = []
    for gw in range(current_gw + 1, current_gw + num_gw + 1):
        gw_fixtures = fixtures_by_gw.get(gw, [])
        for fixture in gw_fixtures:
            if fixture.get("team_h") == player_team_id:
                upcoming.append({
                    "gw": gw,
                    "opponent_team": fixture["team_a"],
                    "is_home": True,
                    "difficulty": fixture.get("team_h_difficulty", 3),
                })
            elif fixture.get("team_a") == player_team_id:
                upcoming.append({
                    "gw": gw,
                    "opponent_team": fixture["team_h"],
                    "is_home": False,
                    "difficulty": fixture.get("team_a_difficulty", 3),
                })
    return upcoming


def calculate_projected_points(player, fixtures, position_map=None):
    """
    Calculate projected points for a player over upcoming fixtures.

    Formula: projected = (form * 0.6) + (form * (1 + avg_fixture_adj) * 0.4)
    Where fixture_adj = (3 - difficulty) * 0.1 per fixture

    Args:
        player: player dict from FPL API
        fixtures: list of upcoming fixture dicts from get_player_fixtures
        position_map: optional position map (unused, kept for API compat)

    Returns:
        float: projected points over the fixture period
    """
    # Get player form (points per game)
    form = 0.0
    try:
        form = float(player.get("points_per_game", 0))
    except (ValueError, TypeError):
        form = 0.0

    # Fallback to position default if form is 0
    if form == 0:
        pos_id = player.get("element_type", 3)
        pos_name = POSITION_MAP.get(pos_id, "MID")
        form = DEFAULT_FORM.get(pos_name, 4.5)

    # Status adjustment
    status = player.get("status", "a")
    if status == "u":  # Unavailable
        form *= 0.5
    elif status == "d":  # Doubtful
        form *= 0.7
    elif status == "i":  # Injured
        form *= 0.0
    elif status == "s":  # Suspended
        form *= 0.0

    # Calculate fixture adjustment
    if not fixtures:
        # No fixture data — return form-only estimate
        return round(form * 5, 2)  # Assume 5 GWs at base form

    fixture_adjustments = []
    for fix in fixtures:
        difficulty = fix.get("difficulty", 3)
        adj = (3 - difficulty) * 0.1
        fixture_adjustments.append(adj)

    avg_adj = sum(fixture_adjustments) / len(fixture_adjustments)

    # Projected points per game, multiplied by number of fixtures
    projected_per_game = (form * 0.6) + (form * (1 + avg_adj) * 0.4)
    projected_total = projected_per_game * len(fixtures)

    return round(projected_total, 2)


def rank_player_scores(data, exclude_player_ids=None, num_gw=5):
    """
    Rank all available players by projected points.

    Args:
        data: dict from load_all_data()
        exclude_player_ids: set/list of player IDs to exclude
        num_gw: gameweeks to look ahead (default 5)

    Returns:
        list of dicts sorted by projected_points descending, each with:
            - player_id, name, team, team_name, position, price,
              ownership, projected_points, fixtures, status, form
    """
    if exclude_player_ids is None:
        exclude_player_ids = set()
    else:
        exclude_player_ids = set(exclude_player_ids)

    tables = build_lookup_tables(data)
    players_by_id = tables["players_by_id"]
    teams_by_id = tables["teams_by_id"]
    fixtures_by_gw = tables["fixtures_by_gw"]
    current_gw = tables["current_gw"]

    ranked = []
    for pid, player in players_by_id.items():
        # Skip excluded players
        if pid in exclude_player_ids:
            continue

        # Skip unavailable/injured/suspended players
        status = player.get("status", "a")
        if status in ("i", "s"):
            continue

        # Get player's upcoming fixtures
        team_id = player.get("team", 0)
        fixtures = get_player_fixtures(pid, team_id, fixtures_by_gw, current_gw, num_gw)

        # Calculate projected points
        projected = calculate_projected_points(player, fixtures)

        # Get team name
        team_info = teams_by_id.get(team_id, {})
        team_name = team_info.get("short_name", "???")

        # Position name
        pos_id = player.get("element_type", 3)
        position = POSITION_MAP.get(pos_id, "MID")

        ranked.append({
            "player_id": pid,
            "name": player.get("web_name", "Unknown"),
            "team": team_id,
            "team_name": team_name,
            "position": position,
            "element_type": pos_id,
            "price": player.get("now_cost", 0) / 10,  # Convert to millions
            "ownership": float(player.get("selected_by_percent", 0)),
            "projected_points": projected,
            "fixtures": fixtures,
            "status": status,
            "form": player.get("points_per_game", "0"),
            "total_points": player.get("total_points", 0),
            "minutes": player.get("minutes", 0),
        })

    # Sort by projected points descending
    ranked.sort(key=lambda x: x["projected_points"], reverse=True)
    return ranked


def _get_squad_players(data):
    """
    Get detailed info for all players in the user's squad.

    Returns list of player dicts with projected points and squad position.
    """
    tables = build_lookup_tables(data)
    players_by_id = tables["players_by_id"]
    teams_by_id = tables["teams_by_id"]
    fixtures_by_gw = tables["fixtures_by_gw"]
    current_gw = tables["current_gw"]

    squad = data.get("squad", {})
    picks = squad.get("picks", [])

    squad_players = []
    for pick in picks:
        pid = pick.get("element")
        player = players_by_id.get(pid)
        if not player:
            continue

        team_id = player.get("team", 0)
        team_info = teams_by_id.get(team_id, {})
        fixtures = get_player_fixtures(pid, team_id, fixtures_by_gw, current_gw)
        projected = calculate_projected_points(player, fixtures)

        pos_id = player.get("element_type", 3)

        squad_players.append({
            "player_id": pid,
            "name": player.get("web_name", "Unknown"),
            "team": team_id,
            "team_name": team_info.get("short_name", "???"),
            "position": POSITION_MAP.get(pos_id, "MID"),
            "element_type": pos_id,
            "price": player.get("now_cost", 0) / 10,
            "selling_price": player.get("now_cost", 0) / 10,  # Simplified
            "ownership": float(player.get("selected_by_percent", 0)),
            "projected_points": projected,
            "fixtures": fixtures,
            "status": player.get("status", "a"),
            "form": player.get("points_per_game", "0"),
            "total_points": player.get("total_points", 0),
            "minutes": player.get("minutes", 0),
            "is_captain": pick.get("is_captain", False),
            "is_vice_captain": pick.get("is_vice_captain", False),
            "squad_position": pick.get("position", 0),
            "multiplier": pick.get("multiplier", 1),
        })

    return squad_players


def get_transfer_recommendations(data, exclude_player_ids=None, max_transfers=2, num_gw=5):
    """
    Generate transfer recommendations: who to sell and who to buy.

    Algorithm:
    1. Rank squad players by projected points (ascending = weakest first)
    2. For each weak player, find the best replacement at same position
    3. Check budget feasibility
    4. Apply -4 pt penalty for transfers beyond free transfers
    5. Only recommend if net gain > 0

    Args:
        data: dict from load_all_data()
        exclude_player_ids: player IDs that cannot be sold
        max_transfers: max number of transfers to recommend (default 2)
        num_gw: gameweeks to look ahead (default 5)

    Returns:
        dict with:
            - current_squad_rating: total projected points of current squad
            - optimized_squad_rating: projected points after recommended transfers
            - recommendations: list of transfer dicts
            - transfers_out: list of players to sell
            - transfers_in: list of players to buy
    """
    if exclude_player_ids is None:
        exclude_player_ids = set()
    else:
        exclude_player_ids = set(exclude_player_ids)

    # Get current squad with projections
    squad_players = _get_squad_players(data)
    if not squad_players:
        return {
            "current_squad_rating": 0,
            "optimized_squad_rating": 0,
            "recommendations": [],
            "transfers_out": [],
            "transfers_in": [],
        }

    # Current squad rating
    current_rating = sum(p["projected_points"] for p in squad_players)

    # Get bank balance
    user_info = data.get("user_info", {})
    bank = user_info.get("last_deadline_bank", 0) / 10  # Convert to millions

    # Free transfers: use entry_history if available, default to 2
    squad_data = data.get("squad", {})
    entry_history = squad_data.get("entry_history", {})
    free_transfers = entry_history.get("event_transfers", None)
    if free_transfers is None or free_transfers < 1:
        free_transfers = 2

    # Squad player IDs (to exclude from replacement search)
    squad_ids = set(p["player_id"] for p in squad_players)

    # Rank all non-squad players
    all_ranked = rank_player_scores(data, exclude_player_ids=squad_ids, num_gw=num_gw)

    # Sort squad by effective points ascending (weakest first)
    # Bench players (position 12-15) contribute ~20% of their value (auto-sub probability)
    BENCH_WEIGHT = 0.2
    sellable = [p for p in squad_players if p["player_id"] not in exclude_player_ids]
    for p in sellable:
        p["is_starter"] = p.get("squad_position", 0) <= 11
        p["effective_points"] = p["projected_points"] * (1.0 if p["is_starter"] else BENCH_WEIGHT)
    sellable.sort(key=lambda x: x["effective_points"])

    recommendations = []
    transfers_out = []
    transfers_in = []
    available_bank = bank
    transfer_count = 0

    for weak_player in sellable:
        if transfer_count >= max_transfers:
            break

        # Find best replacement at same position
        pos = weak_player["element_type"]
        budget = available_bank + weak_player["price"]

        best_replacement = None
        for candidate in all_ranked:
            if candidate["element_type"] != pos:
                continue
            if candidate["price"] > budget:
                continue
            if candidate["player_id"] in squad_ids:
                continue
            best_replacement = candidate
            break  # First match is highest projected

        if best_replacement is None:
            continue

        # Calculate points delta
        points_delta = best_replacement["projected_points"] - weak_player["projected_points"]

        # Apply -4 point penalty for transfers beyond free
        penalty = 0
        if transfer_count >= free_transfers:
            penalty = -4
        net_delta = points_delta + penalty

        # Only recommend if net gain is positive
        if net_delta <= 0:
            continue

        price_delta = best_replacement["price"] - weak_player["price"]
        is_valid = best_replacement["price"] <= budget

        recommendations.append({
            "transfer_out": {
                "player_id": weak_player["player_id"],
                "name": weak_player["name"],
                "team_name": weak_player["team_name"],
                "position": weak_player["position"],
                "price": weak_player["price"],
                "projected_points": weak_player["projected_points"],
                "is_starter": weak_player.get("is_starter", True),
            },
            "transfer_in": {
                "player_id": best_replacement["player_id"],
                "name": best_replacement["name"],
                "team_name": best_replacement["team_name"],
                "position": best_replacement["position"],
                "price": best_replacement["price"],
                "projected_points": best_replacement["projected_points"],
                "ownership": best_replacement["ownership"],
            },
            "points_delta": round(points_delta, 2),
            "net_points_delta": round(net_delta, 2),
            "price_delta": round(price_delta, 1),
            "penalty": penalty,
            "is_valid": is_valid,
        })

        transfers_out.append(weak_player)
        transfers_in.append(best_replacement)

        # Update budget and squad tracking
        available_bank = budget - best_replacement["price"]
        squad_ids.discard(weak_player["player_id"])
        squad_ids.add(best_replacement["player_id"])
        transfer_count += 1

    # Calculate optimized rating
    optimized_rating = current_rating + sum(r["net_points_delta"] for r in recommendations)

    return {
        "current_squad_rating": round(current_rating, 2),
        "optimized_squad_rating": round(optimized_rating, 2),
        "recommendations": recommendations,
        "transfers_out": transfers_out,
        "transfers_in": transfers_in,
        "lookahead_gw": num_gw,
    }


def get_captain_recommendations(data, num_suggestions=5):
    """
    Get top captain picks for the next gameweek.

    Ranks squad players by single-GW projected points.

    Args:
        data: dict from load_all_data()
        num_suggestions: number of captain picks to return (default 5)

    Returns:
        list of dicts, each with:
            - rank, player_id, name, team_name, position,
              projected_points, fixture, ownership
    """
    tables = build_lookup_tables(data)
    players_by_id = tables["players_by_id"]
    teams_by_id = tables["teams_by_id"]
    fixtures_by_gw = tables["fixtures_by_gw"]
    current_gw = tables["current_gw"]
    next_gw = current_gw + 1

    squad = data.get("squad", {})
    picks = squad.get("picks", [])

    candidates = []
    for pick in picks:
        pid = pick.get("element")
        player = players_by_id.get(pid)
        if not player:
            continue

        team_id = player.get("team", 0)
        team_info = teams_by_id.get(team_id, {})

        # Get next GW fixture only
        fixtures = get_player_fixtures(pid, team_id, fixtures_by_gw, current_gw, num_gw=1)
        projected = calculate_projected_points(player, fixtures)

        # Build fixture info for display
        fixture_info = None
        if fixtures:
            fix = fixtures[0]
            opp_team = teams_by_id.get(fix["opponent_team"], {})
            fixture_info = {
                "opponent": opp_team.get("short_name", "???"),
                "is_home": fix["is_home"],
                "difficulty": fix["difficulty"],
            }

        pos_id = player.get("element_type", 3)
        candidates.append({
            "player_id": pid,
            "name": player.get("web_name", "Unknown"),
            "team_name": team_info.get("short_name", "???"),
            "position": POSITION_MAP.get(pos_id, "MID"),
            "projected_points": projected,
            "fixture": fixture_info,
            "ownership": float(player.get("selected_by_percent", 0)),
            "form": player.get("points_per_game", "0"),
        })

    # Sort by projected points descending
    candidates.sort(key=lambda x: x["projected_points"], reverse=True)

    # Add rank
    result = []
    for i, c in enumerate(candidates[:num_suggestions]):
        c["rank"] = i + 1
        result.append(c)

    return result


def get_rotation_strategy(data, num_gw=5):
    """
    Generate optimal lineup for each of the next N gameweeks.

    For each GW, selects the best formation (1 GK, 4 DEF, 5 MID, 1 FWD)
    from the squad based on that GW's fixture difficulty.

    Args:
        data: dict from load_all_data()
        num_gw: number of gameweeks to plan (default 5)

    Returns:
        dict with:
            - strategy: list of GW plans, each with:
                - gw: gameweek number
                - starting_xi: list of 11 players
                - bench: list of 4 players
                - captain: captain player dict
                - total_projected: projected points for the GW
            - total_projected_points: sum of all GW projections
    """
    tables = build_lookup_tables(data)
    players_by_id = tables["players_by_id"]
    teams_by_id = tables["teams_by_id"]
    fixtures_by_gw = tables["fixtures_by_gw"]
    current_gw = tables["current_gw"]

    squad = data.get("squad", {})
    picks = squad.get("picks", [])

    strategy = []
    total_projected = 0

    for gw_offset in range(1, num_gw + 1):
        target_gw = current_gw + gw_offset

        # Calculate each squad player's projected points for this specific GW
        gw_players = []
        for pick in picks:
            pid = pick.get("element")
            player = players_by_id.get(pid)
            if not player:
                continue

            team_id = player.get("team", 0)
            team_info = teams_by_id.get(team_id, {})

            # Get fixture for this specific GW
            fixtures = []
            gw_fixtures = fixtures_by_gw.get(target_gw, [])
            for fixture in gw_fixtures:
                if fixture.get("team_h") == team_id:
                    fixtures.append({
                        "gw": target_gw,
                        "opponent_team": fixture["team_a"],
                        "is_home": True,
                        "difficulty": fixture.get("team_h_difficulty", 3),
                    })
                elif fixture.get("team_a") == team_id:
                    fixtures.append({
                        "gw": target_gw,
                        "opponent_team": fixture["team_h"],
                        "is_home": False,
                        "difficulty": fixture.get("team_a_difficulty", 3),
                    })

            projected = calculate_projected_points(player, fixtures) if fixtures else 0

            pos_id = player.get("element_type", 3)
            opp_name = "???"
            if fixtures:
                opp_info = teams_by_id.get(fixtures[0]["opponent_team"], {})
                opp_name = opp_info.get("short_name", "???")

            gw_players.append({
                "player_id": pid,
                "name": player.get("web_name", "Unknown"),
                "team_name": team_info.get("short_name", "???"),
                "position": POSITION_MAP.get(pos_id, "MID"),
                "element_type": pos_id,
                "projected_points": round(projected, 2),
                "fixture": {
                    "opponent": opp_name,
                    "is_home": fixtures[0]["is_home"] if fixtures else True,
                    "difficulty": fixtures[0]["difficulty"] if fixtures else 3,
                } if fixtures else None,
                "status": player.get("status", "a"),
            })

        # Select best XI using greedy formation selection
        starting_xi = _select_best_xi(gw_players)
        starting_ids = set(p["player_id"] for p in starting_xi)
        bench = [p for p in gw_players if p["player_id"] not in starting_ids]

        # Captain = highest projected in starting XI
        captain = max(starting_xi, key=lambda x: x["projected_points"]) if starting_xi else None
        if captain:
            captain["is_captain"] = True

        gw_total = sum(p["projected_points"] for p in starting_xi)
        # Captain gets double points
        if captain:
            gw_total += captain["projected_points"]

        strategy.append({
            "gw": target_gw,
            "starting_xi": starting_xi,
            "bench": bench,
            "captain": captain,
            "total_projected": round(gw_total, 2),
        })
        total_projected += gw_total

    return {
        "strategy": strategy,
        "total_projected_points": round(total_projected, 2),
    }


def _select_best_xi(players):
    """
    Select the best 11 players using formation: 1 GK, 4 DEF, 5 MID, 1 FWD.

    Greedily picks the highest-projected player for each position slot.

    Args:
        players: list of player dicts with element_type and projected_points

    Returns:
        list of 11 player dicts (the starting XI)
    """
    # Group by position
    by_position = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in players:
        pos = POSITION_MAP.get(p.get("element_type", 3), "MID")
        by_position[pos].append(p)

    # Sort each position by projected points descending
    for pos in by_position:
        by_position[pos].sort(key=lambda x: x["projected_points"], reverse=True)

    # Pick best for each formation slot
    xi = []
    for pos, count in FORMATION.items():
        available = by_position.get(pos, [])
        xi.extend(available[:count])

    return xi


def get_squad_display(data):
    """
    Get squad data formatted for display in the frontend.

    Returns:
        dict with:
            - squad: list of player dicts grouped by position
            - bank: float (millions)
            - free_transfers: int
            - points: int
            - rank: int
            - current_gw: int
    """
    squad_players = _get_squad_players(data)
    user_info = data.get("user_info", {})

    # Group by position
    grouped = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in squad_players:
        pos = p.get("position", "MID")
        if pos in grouped:
            grouped[pos].append(p)

    return {
        "squad": squad_players,
        "squad_by_position": grouped,
        "bank": user_info.get("last_deadline_bank", 0) / 10,
        "free_transfers": 2,  # Simplified default
        "points": user_info.get("summary_overall_points", 0),
        "rank": user_info.get("summary_overall_rank", 0),
        "current_gw": data.get("current_gw", 1),
        "lookahead_gw": 5,
    }


def get_leagues_display(data):
    """
    Extract user's leagues from user_info.

    Returns:
        dict with:
            - classic: list of classic leagues [{id, name, rank, total_entries}]
            - h2h: list of H2H leagues
    """
    user_info = data.get("user_info", {})
    leagues = user_info.get("leagues", {})

    classic = []
    for league in leagues.get("classic", []):
        classic.append({
            "id": league.get("id"),
            "name": league.get("name", "Unknown League"),
            "rank": league.get("entry_rank"),
            "last_rank": league.get("entry_last_rank"),
            "total_entries": league.get("league", {}) if isinstance(league.get("league"), dict) else None,
        })

    h2h = []
    for league in leagues.get("h2h", []):
        h2h.append({
            "id": league.get("id"),
            "name": league.get("name", "Unknown League"),
            "rank": league.get("entry_rank"),
            "last_rank": league.get("entry_last_rank"),
        })

    return {"classic": classic, "h2h": h2h}


def get_rival_analysis(data, rival_picks, rival_info=None):
    """
    Compare user's squad against a rival's squad.

    Args:
        data: dict from load_all_data() (user's data)
        rival_picks: rival's squad picks (from fetch_rival_squad)
        rival_info: optional rival user info

    Returns:
        dict with:
            - shared: players both teams have
            - user_only: players only the user has
            - rival_only: players only the rival has
            - differential_score: how different the squads are (0-100%)
    """
    tables = build_lookup_tables(data)
    players_by_id = tables["players_by_id"]
    teams_by_id = tables["teams_by_id"]

    # User's player IDs
    user_squad = data.get("squad", {})
    user_picks = user_squad.get("picks", [])
    user_ids = set(p.get("element") for p in user_picks)

    # Rival's player IDs
    rival_pick_list = rival_picks.get("picks", [])
    rival_ids = set(p.get("element") for p in rival_pick_list)

    shared_ids = user_ids & rival_ids
    user_only_ids = user_ids - rival_ids
    rival_only_ids = rival_ids - user_ids

    def _player_info(pid):
        player = players_by_id.get(pid, {})
        team_id = player.get("team", 0)
        team_info = teams_by_id.get(team_id, {})
        pos_id = player.get("element_type", 3)
        fixtures = get_player_fixtures(
            pid, team_id, tables["fixtures_by_gw"], tables["current_gw"]
        )
        projected = calculate_projected_points(player, fixtures)
        return {
            "player_id": pid,
            "name": player.get("web_name", "Unknown"),
            "team_name": team_info.get("short_name", "???"),
            "position": POSITION_MAP.get(pos_id, "MID"),
            "price": player.get("now_cost", 0) / 10,
            "projected_points": projected,
            "ownership": float(player.get("selected_by_percent", 0)),
        }

    shared = [_player_info(pid) for pid in shared_ids if pid in players_by_id]
    user_only = [_player_info(pid) for pid in user_only_ids if pid in players_by_id]
    rival_only = [_player_info(pid) for pid in rival_only_ids if pid in players_by_id]

    # Sort by projected points
    shared.sort(key=lambda x: x["projected_points"], reverse=True)
    user_only.sort(key=lambda x: x["projected_points"], reverse=True)
    rival_only.sort(key=lambda x: x["projected_points"], reverse=True)

    total_players = len(user_ids | rival_ids)
    differential_pct = round((len(user_only_ids) + len(rival_only_ids)) / max(total_players, 1) * 100, 1)

    return {
        "shared": shared,
        "user_only": user_only,
        "rival_only": rival_only,
        "shared_count": len(shared),
        "differential_count": len(user_only_ids) + len(rival_only_ids),
        "differential_score": differential_pct,
        "rival_info": {
            "name": rival_info.get("player_first_name", "") + " " + rival_info.get("player_last_name", "") if rival_info else "Rival",
            "team_name": rival_info.get("name", "Unknown") if rival_info else "Unknown",
            "points": rival_info.get("summary_overall_points", 0) if rival_info else 0,
            "rank": rival_info.get("summary_overall_rank", 0) if rival_info else 0,
        },
    }


def get_chip_recommendations(data):
    """
    Recommend optimal chip usage based on fixtures and squad strength.

    Evaluates:
        - Bench Boost: best when all 15 players have good fixtures
        - Triple Captain: best when top player has an easy fixture
        - Free Hit: best when many squad players have hard/blank fixtures
        - Wildcard: best when squad has many underperformers

    Returns:
        dict with:
            - available_chips: list of chips still available
            - recommendations: list of chip recommendations with GW and value
    """
    tables = build_lookup_tables(data)
    players_by_id = tables["players_by_id"]
    teams_by_id = tables["teams_by_id"]
    fixtures_by_gw = tables["fixtures_by_gw"]
    current_gw = tables["current_gw"]

    # Determine which chips are used
    history = data.get("history", {})
    used_chips = history.get("chips", [])
    used_chip_names = set(c.get("name", "").lower() for c in used_chips)

    ALL_CHIPS = ["wildcard", "freehit", "bboost", "3xc"]
    CHIP_LABELS = {
        "wildcard": "Wildcard",
        "freehit": "Free Hit",
        "bboost": "Bench Boost",
        "3xc": "Triple Captain",
    }

    # Check availability (wildcard can be used twice: before and after GW19)
    available = []
    for chip in ALL_CHIPS:
        if chip == "wildcard":
            # Count wildcard uses
            wc_uses = sum(1 for c in used_chips if c.get("name", "").lower() == "wildcard")
            if wc_uses < 2:
                available.append(chip)
        elif chip not in used_chip_names:
            available.append(chip)

    # Get squad picks
    squad = data.get("squad", {})
    picks = squad.get("picks", [])

    # Evaluate each GW for chip value
    num_gw = 8  # Look ahead 8 GWs for chip planning
    gw_analysis = []

    for gw_offset in range(1, num_gw + 1):
        target_gw = current_gw + gw_offset

        # Calculate each squad player's projected points for this GW
        starters = []
        bench = []
        for pick in picks:
            pid = pick.get("element")
            player = players_by_id.get(pid)
            if not player:
                continue

            team_id = player.get("team", 0)
            fixtures = []
            gw_fixtures = fixtures_by_gw.get(target_gw, [])
            for fixture in gw_fixtures:
                if fixture.get("team_h") == team_id:
                    fixtures.append({
                        "difficulty": fixture.get("team_h_difficulty", 3),
                        "is_home": True,
                    })
                elif fixture.get("team_a") == team_id:
                    fixtures.append({
                        "difficulty": fixture.get("team_a_difficulty", 3),
                        "is_home": False,
                    })

            projected = calculate_projected_points(player, fixtures) if fixtures else 0
            squad_pos = pick.get("position", 0)

            entry = {
                "player_id": pid,
                "name": player.get("web_name", "Unknown"),
                "projected": round(projected, 2),
                "has_fixture": len(fixtures) > 0,
            }

            if squad_pos <= 11:
                starters.append(entry)
            else:
                bench.append(entry)

        starter_total = sum(p["projected"] for p in starters)
        bench_total = sum(p["projected"] for p in bench)
        best_player = max(starters, key=lambda x: x["projected"]) if starters else None
        blank_count = sum(1 for p in starters if not p["has_fixture"])

        gw_analysis.append({
            "gw": target_gw,
            "starter_total": round(starter_total, 2),
            "bench_total": round(bench_total, 2),
            "best_captain_value": round(best_player["projected"], 2) if best_player else 0,
            "best_captain_name": best_player["name"] if best_player else "?",
            "blank_starters": blank_count,
            "all_total": round(starter_total + bench_total, 2),
        })

    # Generate recommendations for each available chip
    recommendations = []

    if "bboost" in available:
        # Best GW for Bench Boost = highest bench contribution
        best_bb = max(gw_analysis, key=lambda x: x["bench_total"])
        recommendations.append({
            "chip": "bboost",
            "label": "Bench Boost",
            "best_gw": best_bb["gw"],
            "value": best_bb["bench_total"],
            "reason": f"Bench contributes {best_bb['bench_total']:.1f} pts in GW{best_bb['gw']}",
            "gw_values": [{"gw": g["gw"], "value": round(g["bench_total"], 1)} for g in gw_analysis],
        })

    if "3xc" in available:
        # Best GW for Triple Captain = highest single captain value
        best_tc = max(gw_analysis, key=lambda x: x["best_captain_value"])
        recommendations.append({
            "chip": "3xc",
            "label": "Triple Captain",
            "best_gw": best_tc["gw"],
            "value": best_tc["best_captain_value"],
            "reason": f"{best_tc['best_captain_name']} projected {best_tc['best_captain_value']:.1f} pts in GW{best_tc['gw']}",
            "gw_values": [{"gw": g["gw"], "value": round(g["best_captain_value"], 1)} for g in gw_analysis],
        })

    if "freehit" in available:
        # Best GW for Free Hit = most starters with blanks or lowest starter total
        best_fh = min(gw_analysis, key=lambda x: x["starter_total"])
        recommendations.append({
            "chip": "freehit",
            "label": "Free Hit",
            "best_gw": best_fh["gw"],
            "value": best_fh["starter_total"],
            "reason": f"Squad only projects {best_fh['starter_total']:.1f} pts in GW{best_fh['gw']} — rebuild for one week",
            "gw_values": [{"gw": g["gw"], "value": round(g["starter_total"], 1)} for g in gw_analysis],
        })

    if "wildcard" in available:
        # Wildcard: compare current squad strength vs top available players
        squad_players = _get_squad_players(data)
        current_total = sum(p["projected_points"] for p in squad_players)
        avg_projected = current_total / max(len(squad_players), 1)
        weak_count = sum(1 for p in squad_players if p["projected_points"] < avg_projected * 0.6)
        recommendations.append({
            "chip": "wildcard",
            "label": "Wildcard",
            "best_gw": current_gw + 1,
            "value": weak_count,
            "reason": f"{weak_count} players underperforming (below 60% of squad avg)",
            "gw_values": [],
        })

    # Sort by value descending (most impactful chip first)
    recommendations.sort(key=lambda x: x["value"], reverse=True)

    return {
        "available_chips": [{"chip": c, "label": CHIP_LABELS[c]} for c in available],
        "used_chips": [{"chip": c.get("name", ""), "gw": c.get("event")} for c in used_chips],
        "recommendations": recommendations,
    }


def get_player_details(data, player_id):
    """
    Get detailed stats for a single player.

    Args:
        data: dict from load_all_data()
        player_id: FPL player ID

    Returns:
        dict with player details or None if not found
    """
    tables = build_lookup_tables(data)
    player = tables["players_by_id"].get(player_id)
    if not player:
        return None

    team_id = player.get("team", 0)
    team_info = tables["teams_by_id"].get(team_id, {})
    fixtures = get_player_fixtures(
        player_id, team_id,
        tables["fixtures_by_gw"], tables["current_gw"]
    )
    projected = calculate_projected_points(player, fixtures)
    pos_id = player.get("element_type", 3)

    # Resolve opponent team names in fixtures
    fixtures_with_names = []
    for fix in fixtures:
        opp_info = tables["teams_by_id"].get(fix["opponent_team"], {})
        fixtures_with_names.append({
            **fix,
            "opponent_name": opp_info.get("short_name", "???"),
        })

    return {
        "player_id": player_id,
        "name": player.get("web_name", "Unknown"),
        "full_name": f"{player.get('first_name', '')} {player.get('second_name', '')}",
        "team": team_id,
        "team_name": team_info.get("short_name", "???"),
        "position": POSITION_MAP.get(pos_id, "MID"),
        "price": player.get("now_cost", 0) / 10,
        "ownership": float(player.get("selected_by_percent", 0)),
        "form": player.get("points_per_game", "0"),
        "total_points": player.get("total_points", 0),
        "minutes": player.get("minutes", 0),
        "goals_scored": player.get("goals_scored", 0),
        "assists": player.get("assists", 0),
        "clean_sheets": player.get("clean_sheets", 0),
        "status": player.get("status", "a"),
        "news": player.get("news", ""),
        "projected_points": projected,
        "fixtures": fixtures_with_names,
    }
