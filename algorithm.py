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

    # Sort squad by projected points ascending (weakest first)
    sellable = [p for p in squad_players if p["player_id"] not in exclude_player_ids]
    sellable.sort(key=lambda x: x["projected_points"])

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
