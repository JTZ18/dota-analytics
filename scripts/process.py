"""
Process raw JSON API responses into clean pandas DataFrames.

Reads from data/raw/ and writes CSVs to data/processed/.
Run with: uv run python -m scripts.process
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from scripts.config import DATA_PROCESSED, DATA_RAW, GAME_MODES, PLAYERS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    """Load a JSON file, returning None if missing or corrupt."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _hero_lookup() -> dict[int, str]:
    """Return a dict mapping hero_id -> localized_name."""
    heroes = _load_json(DATA_RAW / "heroes" / "heroes.json")
    if heroes is None:
        return {}
    return {h["id"]: h["localized_name"] for h in heroes}


def _player_id_to_name() -> dict[int, str]:
    """Return a dict mapping account_id -> player name from config."""
    return {v: k for k, v in PLAYERS.items()}


def _friend_ids() -> set[int]:
    """Return the set of all friend account IDs."""
    return set(PLAYERS.values())


# ---------------------------------------------------------------------------
# 1. Player Profiles
# ---------------------------------------------------------------------------

def process_player_profiles() -> pd.DataFrame:
    """Process player profile + win/loss data into player_profiles.csv."""
    rows = []
    for name, account_id in PLAYERS.items():
        profile_data = _load_json(DATA_RAW / "players" / str(account_id) / "profile.json")
        wl_data = _load_json(DATA_RAW / "players" / str(account_id) / "wl.json")
        if profile_data is None:
            continue

        p = profile_data.get("profile", {})
        wins = wl_data.get("win", 0) if wl_data else 0
        losses = wl_data.get("lose", 0) if wl_data else 0
        total = wins + losses

        rows.append({
            "name": name,
            "account_id": account_id,
            "avatar": p.get("avatarfull", ""),
            "rank_tier": profile_data.get("rank_tier"),
            "wins": wins,
            "losses": losses,
            "total_games": total,
            "win_rate": round(wins / total, 4) if total > 0 else 0.0,
        })

    df = pd.DataFrame(rows)
    df.to_csv(DATA_PROCESSED / "player_profiles.csv", index=False)
    print(f"  player_profiles.csv: {len(df)} rows")
    return df


# ---------------------------------------------------------------------------
# 2. Player Heroes
# ---------------------------------------------------------------------------

def process_player_heroes() -> pd.DataFrame:
    """Process per-hero stats for each player into player_heroes.csv."""
    hero_names = _hero_lookup()
    rows = []

    for name, account_id in PLAYERS.items():
        heroes_data = _load_json(DATA_RAW / "players" / str(account_id) / "heroes.json")
        if heroes_data is None:
            continue

        for h in heroes_data:
            hero_id = int(h["hero_id"])
            games = h.get("games", 0)
            wins = h.get("win", 0)
            rows.append({
                "account_id": account_id,
                "player_name": name,
                "hero_id": hero_id,
                "hero_name": hero_names.get(hero_id, f"Unknown ({hero_id})"),
                "games": games,
                "wins": wins,
                "win_rate": round(wins / games, 4) if games > 0 else 0.0,
                "last_played": h.get("last_played"),
            })

    df = pd.DataFrame(rows)
    df.to_csv(DATA_PROCESSED / "player_heroes.csv", index=False)
    print(f"  player_heroes.csv: {len(df)} rows")
    return df


# ---------------------------------------------------------------------------
# 3. Player Totals
# ---------------------------------------------------------------------------

def process_player_totals() -> pd.DataFrame:
    """Process aggregate stats for each player into player_totals.csv."""
    rows = []

    for name, account_id in PLAYERS.items():
        totals_data = _load_json(DATA_RAW / "players" / str(account_id) / "totals.json")
        if totals_data is None:
            continue

        row: dict = {"account_id": account_id, "player_name": name}
        for entry in totals_data:
            field = entry["field"]
            n = entry.get("n", 0)
            total = entry.get("sum", 0)
            row[f"{field}_total"] = total
            row[f"{field}_n"] = n
            row[f"{field}_avg"] = round(total / n, 4) if n > 0 else 0.0

        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(DATA_PROCESSED / "player_totals.csv", index=False)
    print(f"  player_totals.csv: {len(df)} rows")
    return df


# ---------------------------------------------------------------------------
# 4. Match History
# ---------------------------------------------------------------------------

def process_match_history() -> pd.DataFrame:
    """Process match history for all players, filtered to GAME_MODES, into match_history.csv."""
    rows = []

    for name, account_id in PLAYERS.items():
        matches_data = _load_json(DATA_RAW / "players" / str(account_id) / "matches.json")
        if matches_data is None:
            continue

        for m in matches_data:
            game_mode = m.get("game_mode")
            if game_mode not in GAME_MODES:
                continue

            player_slot = m.get("player_slot", 0)
            is_radiant = player_slot < 128
            radiant_win = m.get("radiant_win", False)
            won = (is_radiant and radiant_win) or (not is_radiant and not radiant_win)

            start_time = m.get("start_time")
            dt = datetime.fromtimestamp(start_time, tz=timezone.utc) if start_time else None

            rows.append({
                "account_id": account_id,
                "player_name": name,
                "match_id": m.get("match_id"),
                "hero_id": m.get("hero_id"),
                "start_time": start_time,
                "datetime": dt.isoformat() if dt else None,
                "year": dt.year if dt else None,
                "month": dt.month if dt else None,
                "hour": dt.hour if dt else None,
                "day_of_week": dt.strftime("%A") if dt else None,
                "duration": m.get("duration"),
                "game_mode": game_mode,
                "lobby_type": m.get("lobby_type"),
                "kills": m.get("kills"),
                "deaths": m.get("deaths"),
                "assists": m.get("assists"),
                "player_slot": player_slot,
                "is_radiant": is_radiant,
                "radiant_win": radiant_win,
                "won": won,
                "party_size": m.get("party_size"),
                "average_rank": m.get("average_rank"),
            })

    df = pd.DataFrame(rows)
    df.to_csv(DATA_PROCESSED / "match_history.csv", index=False)
    print(f"  match_history.csv: {len(df)} rows")
    return df


# ---------------------------------------------------------------------------
# 5. Peers
# ---------------------------------------------------------------------------

def process_peers() -> pd.DataFrame:
    """Process peer data, keeping only friend-to-friend relationships, into peers.csv."""
    id_to_name = _player_id_to_name()
    friend_ids = _friend_ids()
    rows = []

    for name, account_id in PLAYERS.items():
        peers_data = _load_json(DATA_RAW / "players" / str(account_id) / "peers.json")
        if peers_data is None:
            continue

        for peer in peers_data:
            peer_id = peer.get("account_id")
            if peer_id not in friend_ids:
                continue

            with_games = peer.get("with_games", 0) or 0
            with_win = peer.get("with_win", 0) or 0

            rows.append({
                "player_id": account_id,
                "player_name": name,
                "peer_id": peer_id,
                "peer_name": id_to_name.get(peer_id, str(peer_id)),
                "with_games": with_games,
                "with_win": with_win,
                "with_win_rate": round(with_win / with_games, 4) if with_games > 0 else 0.0,
                "against_games": peer.get("against_games", 0) or 0,
                "against_win": peer.get("against_win", 0) or 0,
            })

    df = pd.DataFrame(rows)
    df.to_csv(DATA_PROCESSED / "peers.csv", index=False)
    print(f"  peers.csv: {len(df)} rows")
    return df


# ---------------------------------------------------------------------------
# 6. Heroes Reference
# ---------------------------------------------------------------------------

def process_heroes_reference() -> pd.DataFrame:
    """Process the hero reference list into heroes.csv."""
    heroes_data = _load_json(DATA_RAW / "heroes" / "heroes.json")
    if heroes_data is None:
        print("  heroes.csv: SKIPPED (no data)")
        return pd.DataFrame()

    df = pd.DataFrame(heroes_data)
    df.to_csv(DATA_PROCESSED / "heroes.csv", index=False)
    print(f"  heroes.csv: {len(df)} rows")
    return df


# ---------------------------------------------------------------------------
# 7. Shared Matches
# ---------------------------------------------------------------------------

def process_shared_matches() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process detailed match files for matches involving 2+ friends.

    Outputs:
      - shared_match_players.csv: per-player stats for friends in shared matches
      - shared_match_meta.csv: match-level metadata
    """
    friend_ids = _friend_ids()
    id_to_name = _player_id_to_name()
    hero_names = _hero_lookup()

    matches_dir = DATA_RAW / "matches"
    if not matches_dir.exists():
        print("  shared_match_players.csv: SKIPPED (no matches dir)")
        print("  shared_match_meta.csv: SKIPPED (no matches dir)")
        return pd.DataFrame(), pd.DataFrame()

    player_rows = []
    meta_rows = []

    match_files = list(matches_dir.glob("*.json"))
    total = len(match_files)
    print(f"  Processing {total} match files...")

    for i, mf in enumerate(match_files):
        if (i + 1) % 2000 == 0:
            print(f"    ... {i + 1}/{total}")

        match_data = _load_json(mf)
        if match_data is None:
            continue

        players = match_data.get("players", [])
        if not players:
            continue

        # Find friends in this match
        friend_players = []
        for p in players:
            aid = p.get("account_id")
            if aid in friend_ids:
                friend_players.append(p)

        if len(friend_players) < 2:
            continue

        match_id = match_data.get("match_id")
        start_time = match_data.get("start_time")
        duration = match_data.get("duration")
        game_mode = match_data.get("game_mode")
        radiant_win = match_data.get("radiant_win")

        # Per-player rows
        friend_names_list = []
        friend_heroes_list = []
        friend_teams = []

        for p in friend_players:
            aid = p.get("account_id")
            pname = id_to_name.get(aid, str(aid))
            player_slot = p.get("player_slot", 0)
            is_radiant = player_slot < 128
            won = (is_radiant and radiant_win) or (not is_radiant and not radiant_win)
            hero_id = p.get("hero_id")

            friend_names_list.append(pname)
            friend_heroes_list.append(str(hero_id) if hero_id else "")
            friend_teams.append("radiant" if is_radiant else "dire")

            player_rows.append({
                "match_id": match_id,
                "account_id": aid,
                "player_name": pname,
                "hero_id": hero_id,
                "hero_name": hero_names.get(hero_id, ""),
                "player_slot": player_slot,
                "is_radiant": is_radiant,
                "won": won,
                "kills": p.get("kills"),
                "deaths": p.get("deaths"),
                "assists": p.get("assists"),
                "gold_per_min": p.get("gold_per_min"),
                "xp_per_min": p.get("xp_per_min"),
                "hero_damage": p.get("hero_damage"),
                "tower_damage": p.get("tower_damage"),
                "hero_healing": p.get("hero_healing"),
                "last_hits": p.get("last_hits"),
                "denies": p.get("denies"),
                "net_worth": p.get("net_worth"),
                "lane": p.get("lane"),
                "lane_role": p.get("lane_role"),
                "party_size": p.get("party_size"),
                "actions_per_min": p.get("actions_per_min"),
                "obs_placed": p.get("obs_placed"),
                "sen_placed": p.get("sen_placed"),
                "teamfight_participation": p.get("teamfight_participation"),
                "rank_tier": p.get("rank_tier"),
            })

        # Determine if 2+ friends were on the same team
        same_team = len(friend_teams) != len(set(friend_teams))

        meta_rows.append({
            "match_id": match_id,
            "start_time": start_time,
            "duration": duration,
            "game_mode": game_mode,
            "radiant_win": radiant_win,
            "num_friends": len(friend_players),
            "same_team": same_team,
            "friend_names": "|".join(friend_names_list),
            "friend_heroes": "|".join(friend_heroes_list),
        })

    df_players = pd.DataFrame(player_rows)
    df_meta = pd.DataFrame(meta_rows)

    df_players.to_csv(DATA_PROCESSED / "shared_match_players.csv", index=False)
    df_meta.to_csv(DATA_PROCESSED / "shared_match_meta.csv", index=False)

    print(f"  shared_match_players.csv: {len(df_players)} rows")
    print(f"  shared_match_meta.csv: {len(df_meta)} rows")
    return df_players, df_meta


# ---------------------------------------------------------------------------
# 8. Wordclouds
# ---------------------------------------------------------------------------

def process_wordclouds() -> dict:
    """Process wordcloud data into wordclouds.json (player_name -> {word: count})."""
    result = {}

    for name, account_id in PLAYERS.items():
        wc_data = _load_json(DATA_RAW / "players" / str(account_id) / "wordcloud.json")
        if wc_data is None:
            continue
        # Use my_word_counts (what the player actually said)
        result[name] = wc_data.get("my_word_counts", {})

    out_path = DATA_PROCESSED / "wordclouds.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    total_words = sum(len(v) for v in result.values())
    print(f"  wordclouds.json: {len(result)} players, {total_words} unique words total")
    return result


# ---------------------------------------------------------------------------
# 9. Process All
# ---------------------------------------------------------------------------

def process_all() -> None:
    """Run all processing steps and print a summary."""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Processing raw data into clean DataFrames")
    print("=" * 60)
    t0 = time.time()

    print("\n[1/8] Player profiles")
    profiles = process_player_profiles()

    print("\n[2/8] Player heroes")
    heroes = process_player_heroes()

    print("\n[3/8] Player totals")
    totals = process_player_totals()

    print("\n[4/8] Match history")
    match_hist = process_match_history()

    print("\n[5/8] Peers")
    peers = process_peers()

    print("\n[6/8] Heroes reference")
    heroes_ref = process_heroes_reference()

    print("\n[7/8] Shared matches")
    shared_players, shared_meta = process_shared_matches()

    print("\n[8/8] Wordclouds")
    wordclouds = process_wordclouds()

    elapsed = time.time() - t0
    print("\n" + "=" * 60)
    print(f"All done in {elapsed:.1f}s")
    print("=" * 60)

    # Summary
    print("\nOutput summary:")
    print(f"  player_profiles.csv    : {len(profiles)} rows")
    print(f"  player_heroes.csv      : {len(heroes)} rows")
    print(f"  player_totals.csv      : {len(totals)} rows")
    print(f"  match_history.csv      : {len(match_hist)} rows")
    print(f"  peers.csv              : {len(peers)} rows")
    print(f"  heroes.csv             : {len(heroes_ref)} rows")
    print(f"  shared_match_players.csv: {len(shared_players)} rows")
    print(f"  shared_match_meta.csv  : {len(shared_meta)} rows")
    print(f"  wordclouds.json        : {len(wordclouds)} players")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    process_all()
