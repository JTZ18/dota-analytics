"""
EDA and insight generation for Dota 2 friend-group analytics.

Loads all processed CSVs from data/processed/ and computes analytics
insights, saving them as data/processed/insights.json.

Usage:
    uv run python -m scripts.insights
"""

import ast
import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from scripts.config import DATA_PROCESSED, PLAYERS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW_EPOCH = time.time()
TIME_TIERS = {
    "all": 0,
    "2y": NOW_EPOCH - 2 * 365.25 * 86400,
    "1y": NOW_EPOCH - 1 * 365.25 * 86400,
}


def _safe(val):
    """Convert numpy/pandas types to native Python for JSON serialization."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        v = float(val)
        if np.isnan(v) or np.isinf(v):
            return None
        return round(v, 4)
    if isinstance(val, np.bool_):
        return bool(val)
    if isinstance(val, (np.ndarray,)):
        return [_safe(x) for x in val]
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    if isinstance(val, float):
        if np.isnan(val) or np.isinf(val):
            return None
        return round(val, 4)
    return val


def _clean_dict(d: dict) -> dict:
    """Recursively convert a dict's values to JSON-safe types."""
    out = {}
    for k, v in d.items():
        k = _safe(k)
        if isinstance(v, dict):
            out[k] = _clean_dict(v)
        elif isinstance(v, list):
            out[k] = [_clean_dict(i) if isinstance(i, dict) else _safe(i) for i in v]
        else:
            out[k] = _safe(v)
    return out


def _filter_time(df: pd.DataFrame, tier: str, time_col: str = "start_time") -> pd.DataFrame:
    """Filter a DataFrame to rows within the given time tier."""
    cutoff = TIME_TIERS[tier]
    if cutoff == 0:
        return df
    return df[df[time_col] >= cutoff]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data() -> dict:
    """Load all processed CSVs and JSON files."""
    data = {}
    data["profiles"] = pd.read_csv(DATA_PROCESSED / "player_profiles.csv")
    data["totals"] = pd.read_csv(DATA_PROCESSED / "player_totals.csv")
    data["heroes_played"] = pd.read_csv(DATA_PROCESSED / "player_heroes.csv")
    data["match_history"] = pd.read_csv(DATA_PROCESSED / "match_history.csv")
    data["peers"] = pd.read_csv(DATA_PROCESSED / "peers.csv")
    data["heroes"] = pd.read_csv(DATA_PROCESSED / "heroes.csv")
    data["shared_players"] = pd.read_csv(DATA_PROCESSED / "shared_match_players.csv")
    data["shared_meta"] = pd.read_csv(DATA_PROCESSED / "shared_match_meta.csv")
    with open(DATA_PROCESSED / "wordclouds.json") as f:
        data["wordclouds"] = json.load(f)
    return data


# ---------------------------------------------------------------------------
# 1. Player cards
# ---------------------------------------------------------------------------

def compute_player_cards(data: dict) -> list:
    """For each player: name, account_id, avatar, rank_tier, total_games, win_rate,
    top 3 heroes (by games), avg kills/deaths/assists — across time tiers."""
    profiles = data["profiles"]
    totals = data["totals"]
    heroes_played = data["heroes_played"]
    match_history = data["match_history"]

    cards = []
    for _, row in profiles.iterrows():
        name = row["name"]
        aid = int(row["account_id"])

        # Totals-based stats (all-time only from player_totals)
        t = totals[totals["account_id"] == aid]
        avg_kills_all = float(t["kills_avg"].iloc[0]) if len(t) else None
        avg_deaths_all = float(t["deaths_avg"].iloc[0]) if len(t) else None
        avg_assists_all = float(t["assists_avg"].iloc[0]) if len(t) else None

        # Per-tier stats from match_history
        tiers = {}
        player_matches = match_history[match_history["account_id"] == aid]
        for tier_name in TIME_TIERS:
            mh = _filter_time(player_matches, tier_name)
            total_games = len(mh)
            wins = int(mh["won"].sum()) if total_games > 0 else 0
            wr = round(wins / total_games, 4) if total_games > 0 else None

            # Avg KDA from match_history for this tier
            ak = round(float(mh["kills"].mean()), 2) if total_games > 0 else None
            ad = round(float(mh["deaths"].mean()), 2) if total_games > 0 else None
            aa = round(float(mh["assists"].mean()), 2) if total_games > 0 else None

            # Top 3 heroes by games for this tier
            if tier_name == "all":
                # Use player_heroes for all-time (more complete)
                ph = heroes_played[heroes_played["account_id"] == aid]
                top3 = (
                    ph.nlargest(3, "games")[["hero_name", "games", "wins", "win_rate"]]
                    .to_dict("records")
                )
            else:
                # Compute from match_history for time-limited tiers
                hero_stats = (
                    mh.groupby("hero_id")
                    .agg(games=("won", "size"), wins=("won", "sum"))
                    .reset_index()
                )
                if len(hero_stats) > 0:
                    hero_stats["win_rate"] = round(hero_stats["wins"] / hero_stats["games"], 4)
                    # Merge hero names
                    heroes_ref = data["heroes"][["id", "localized_name"]].rename(
                        columns={"id": "hero_id", "localized_name": "hero_name"}
                    )
                    hero_stats = hero_stats.merge(heroes_ref, on="hero_id", how="left")
                    top3 = (
                        hero_stats.nlargest(3, "games")[["hero_name", "games", "wins", "win_rate"]]
                        .to_dict("records")
                    )
                else:
                    top3 = []

            tiers[tier_name] = _clean_dict({
                "total_games": total_games,
                "wins": wins,
                "win_rate": wr,
                "avg_kills": ak,
                "avg_deaths": ad,
                "avg_assists": aa,
                "top_heroes": top3,
            })

        card = {
            "name": name,
            "account_id": aid,
            "avatar": row.get("avatar", ""),
            "rank_tier": _safe(row.get("rank_tier")),
            "tiers": tiers,
        }
        cards.append(_clean_dict(card))

    return cards


# ---------------------------------------------------------------------------
# 2. Superlatives
# ---------------------------------------------------------------------------

def compute_superlatives(data: dict) -> list:
    """Data-backed fun awards across time tiers."""
    totals = data["totals"]
    heroes_played = data["heroes_played"]
    match_history = data["match_history"]
    heroes_ref = data["heroes"][["id", "localized_name"]].rename(
        columns={"id": "hero_id", "localized_name": "hero_name"}
    )

    results = []

    for tier_name in TIME_TIERS:
        mh = _filter_time(match_history, tier_name)

        # Per-player aggregates from match_history for this tier
        player_agg = (
            mh.groupby("player_name")
            .agg(
                avg_kills=("kills", "mean"),
                avg_deaths=("deaths", "mean"),
                avg_assists=("assists", "mean"),
                total_games=("won", "size"),
                total_duration=("duration", "sum"),
                total_wins=("won", "sum"),
            )
            .reset_index()
        )
        player_agg["avg_duration"] = player_agg["total_duration"] / player_agg["total_games"]

        # For GPM/XPM/hero_damage/tower_damage/healing/APM/last_hits we use player_totals
        # for all-time. For 2y/1y we estimate from match_history if columns exist; otherwise
        # fall back to totals (which are all-time approximation).
        # player_totals doesn't have time-tier data so for non-all tiers we note that.
        # For superlatives from totals, we only use "all" tier.

        # ---------- From match_history aggregates ----------
        sup_list = []

        # The Feeder — highest avg deaths
        if len(player_agg) > 0:
            r = player_agg.loc[player_agg["avg_deaths"].idxmax()]
            sup_list.append({
                "title": "The Feeder",
                "description": "Highest average deaths per game",
                "player": r["player_name"],
                "value": round(float(r["avg_deaths"]), 2),
                "stat": "avg_deaths",
            })

            # The Slayer — highest avg kills
            r = player_agg.loc[player_agg["avg_kills"].idxmax()]
            sup_list.append({
                "title": "The Slayer",
                "description": "Highest average kills per game",
                "player": r["player_name"],
                "value": round(float(r["avg_kills"]), 2),
                "stat": "avg_kills",
            })

            # The Team Player — highest avg assists
            r = player_agg.loc[player_agg["avg_assists"].idxmax()]
            sup_list.append({
                "title": "The Team Player",
                "description": "Highest average assists per game",
                "player": r["player_name"],
                "value": round(float(r["avg_assists"]), 2),
                "stat": "avg_assists",
            })

            # The Grinder — most total games played
            r = player_agg.loc[player_agg["total_games"].idxmax()]
            sup_list.append({
                "title": "The Grinder",
                "description": "Most total games played",
                "player": r["player_name"],
                "value": int(r["total_games"]),
                "stat": "total_games",
            })

            # KDA King — best (kills+assists)/deaths ratio
            kda_agg = (
                mh.groupby("player_name")
                .agg(total_kills=("kills", "sum"), total_deaths=("deaths", "sum"), total_assists=("assists", "sum"))
                .reset_index()
            )
            kda_agg["kda_ratio"] = (kda_agg["total_kills"] + kda_agg["total_assists"]) / kda_agg["total_deaths"].replace(0, 1)
            r = kda_agg.loc[kda_agg["kda_ratio"].idxmax()]
            sup_list.append({
                "title": "KDA King",
                "description": "Best (kills+assists)/deaths ratio",
                "player": r["player_name"],
                "value": round(float(r["kda_ratio"]), 2),
                "stat": "kda_ratio",
            })

            # The Survivor — lowest avg deaths
            r = player_agg.loc[player_agg["avg_deaths"].idxmin()]
            sup_list.append({
                "title": "The Survivor",
                "description": "Lowest average deaths per game",
                "player": r["player_name"],
                "value": round(float(r["avg_deaths"]), 2),
                "stat": "avg_deaths",
            })

            # Late Night Warrior — highest % of games between hours 0-5 (UTC)
            late_night = (
                mh.groupby("player_name")
                .apply(lambda g: (g["hour"].between(0, 5).sum()) / len(g) if len(g) > 0 else 0)
                .reset_index(name="late_pct")
            )
            r = late_night.loc[late_night["late_pct"].idxmax()]
            sup_list.append({
                "title": "Late Night Warrior",
                "description": "Highest % of games played between midnight and 5 AM (UTC)",
                "player": r["player_name"],
                "value": round(float(r["late_pct"]) * 100, 1),
                "stat": "late_night_pct",
            })

            # Cliff Jungler — longest avg game duration when losing
            losses = mh[~mh["won"]]
            if len(losses) > 0:
                loss_dur = (
                    losses.groupby("player_name")["duration"]
                    .mean()
                    .reset_index(name="avg_loss_duration")
                )
                r = loss_dur.loc[loss_dur["avg_loss_duration"].idxmax()]
                sup_list.append({
                    "title": "Cliff Jungler",
                    "description": "Longest average game duration when losing",
                    "player": r["player_name"],
                    "value": round(float(r["avg_loss_duration"]), 0),
                    "stat": "avg_loss_duration_sec",
                })

        # ---------- From player_totals (all-time only, reused for 2y/1y as approximation) ----------
        if tier_name == "all":
            # The Farmer — highest avg GPM
            r = totals.loc[totals["gold_per_min_avg"].idxmax()]
            sup_list.append({
                "title": "The Farmer",
                "description": "Highest average gold per minute",
                "player": r["player_name"],
                "value": round(float(r["gold_per_min_avg"]), 1),
                "stat": "avg_gpm",
            })

            # The XP Sponge — highest avg XPM
            r = totals.loc[totals["xp_per_min_avg"].idxmax()]
            sup_list.append({
                "title": "The XP Sponge",
                "description": "Highest average XP per minute",
                "player": r["player_name"],
                "value": round(float(r["xp_per_min_avg"]), 1),
                "stat": "avg_xpm",
            })

            # The Damage Dealer — highest avg hero damage
            r = totals.loc[totals["hero_damage_avg"].idxmax()]
            sup_list.append({
                "title": "The Damage Dealer",
                "description": "Highest average hero damage per game",
                "player": r["player_name"],
                "value": round(float(r["hero_damage_avg"]), 0),
                "stat": "avg_hero_damage",
            })

            # The Rat — highest avg tower damage
            r = totals.loc[totals["tower_damage_avg"].idxmax()]
            sup_list.append({
                "title": "The Rat",
                "description": "Highest average tower damage per game",
                "player": r["player_name"],
                "value": round(float(r["tower_damage_avg"]), 0),
                "stat": "avg_tower_damage",
            })

            # The Healer — highest avg hero healing
            r = totals.loc[totals["hero_healing_avg"].idxmax()]
            sup_list.append({
                "title": "The Healer",
                "description": "Highest average hero healing per game",
                "player": r["player_name"],
                "value": round(float(r["hero_healing_avg"]), 0),
                "stat": "avg_hero_healing",
            })

            # The Tryhard — highest avg APM
            r = totals.loc[totals["actions_per_min_avg"].idxmax()]
            sup_list.append({
                "title": "The Tryhard",
                "description": "Highest average actions per minute",
                "player": r["player_name"],
                "value": round(float(r["actions_per_min_avg"]), 1),
                "stat": "avg_apm",
            })

            # Last Hit Machine — highest avg last hits
            r = totals.loc[totals["last_hits_avg"].idxmax()]
            sup_list.append({
                "title": "Last Hit Machine",
                "description": "Highest average last hits per game",
                "player": r["player_name"],
                "value": round(float(r["last_hits_avg"]), 1),
                "stat": "avg_last_hits",
            })

        # ---------- From player_heroes ----------
        if tier_name == "all":
            # One Trick Pony — most games on a single hero
            hp = heroes_played.copy()
            idx = hp["games"].idxmax()
            r = hp.loc[idx]
            sup_list.append({
                "title": "One Trick Pony",
                "description": "Most games on a single hero",
                "player": r["player_name"],
                "value": int(r["games"]),
                "stat": "max_hero_games",
                "hero": r["hero_name"],
            })

            # Hero Hopper — most unique heroes played
            hero_counts = hp.groupby("player_name")["hero_id"].nunique().reset_index(name="unique_heroes")
            r = hero_counts.loc[hero_counts["unique_heroes"].idxmax()]
            sup_list.append({
                "title": "Hero Hopper",
                "description": "Most unique heroes played",
                "player": r["player_name"],
                "value": int(r["unique_heroes"]),
                "stat": "unique_heroes",
            })
        else:
            # Time-limited one-trick / hero hopper from match_history
            hero_games = mh.groupby(["player_name", "hero_id"]).size().reset_index(name="games")
            if len(hero_games) > 0:
                hero_games = hero_games.merge(heroes_ref, on="hero_id", how="left")
                idx = hero_games["games"].idxmax()
                r = hero_games.loc[idx]
                sup_list.append({
                    "title": "One Trick Pony",
                    "description": "Most games on a single hero",
                    "player": r["player_name"],
                    "value": int(r["games"]),
                    "stat": "max_hero_games",
                    "hero": r.get("hero_name", "Unknown"),
                })

                unique_heroes = hero_games.groupby("player_name")["hero_id"].nunique().reset_index(name="unique_heroes")
                r = unique_heroes.loc[unique_heroes["unique_heroes"].idxmax()]
                sup_list.append({
                    "title": "Hero Hopper",
                    "description": "Most unique heroes played",
                    "player": r["player_name"],
                    "value": int(r["unique_heroes"]),
                    "stat": "unique_heroes",
                })

        results.append({
            "tier": tier_name,
            "awards": [_clean_dict(s) for s in sup_list],
        })

    return results


# ---------------------------------------------------------------------------
# 3. Duo chemistry
# ---------------------------------------------------------------------------

def compute_duo_chemistry(data: dict) -> dict:
    """Heatmap of with_win_rate for every player pair, plus best/worst duos."""
    peers = data["peers"]

    # Build heatmap: player -> peer -> win_rate
    heatmap = {}
    for _, row in peers.iterrows():
        pname = row["player_name"]
        peer = row["peer_name"]
        if pname not in heatmap:
            heatmap[pname] = {}
        heatmap[pname][peer] = {
            "with_games": _safe(row["with_games"]),
            "with_win": _safe(row["with_win"]),
            "with_win_rate": _safe(row["with_win_rate"]),
        }

    # Best and worst duos (min 10 games)
    qualified = peers[peers["with_games"] >= 10].copy()
    if len(qualified) > 0:
        # Deduplicate pairs (A->B and B->A are both in peers)
        # Take average of both directions for a symmetric view
        pairs = {}
        for _, row in qualified.iterrows():
            key = tuple(sorted([row["player_name"], row["peer_name"]]))
            if key not in pairs:
                pairs[key] = {"games": [], "win_rate": []}
            pairs[key]["games"].append(int(row["with_games"]))
            pairs[key]["win_rate"].append(float(row["with_win_rate"]))

        duo_list = []
        for (p1, p2), vals in pairs.items():
            avg_games = sum(vals["games"]) / len(vals["games"])
            avg_wr = sum(vals["win_rate"]) / len(vals["win_rate"])
            duo_list.append({
                "player1": p1,
                "player2": p2,
                "games": round(avg_games),
                "win_rate": round(avg_wr, 4),
            })

        duo_list.sort(key=lambda x: x["win_rate"], reverse=True)
        best = duo_list[:10]
        worst = list(reversed(duo_list[-10:]))
    else:
        best = []
        worst = []

    return _clean_dict({
        "heatmap": heatmap,
        "best_duos": best,
        "worst_duos": worst,
    })


# ---------------------------------------------------------------------------
# 4. Hero synergies
# ---------------------------------------------------------------------------

def compute_hero_synergies(data: dict) -> list:
    """For friends on the same team in the same match, compute win rate for every
    (player1+hero1, player2+hero2) pair. Min 3 games. Top 100 by games."""
    sp = data["shared_players"]

    # We need to find pairs of friends on the same team in the same match.
    # Same team means same is_radiant value.
    # Self-join on match_id where both are on the same team.
    df = sp[["match_id", "account_id", "player_name", "hero_id", "hero_name", "is_radiant", "won"]].copy()

    # Self-join: all pairs in same match, same team
    merged = df.merge(df, on="match_id", suffixes=("_1", "_2"))
    # Remove self-pairs and ensure ordering to deduplicate
    merged = merged[merged["account_id_1"] < merged["account_id_2"]]
    # Same team
    merged = merged[merged["is_radiant_1"] == merged["is_radiant_2"]]

    # Group by the player+hero combo
    grouped = (
        merged.groupby([
            "player_name_1", "hero_name_1",
            "player_name_2", "hero_name_2",
        ])
        .agg(
            games=("won_1", "size"),
            wins=("won_1", "sum"),
        )
        .reset_index()
    )
    grouped["win_rate"] = grouped["wins"] / grouped["games"]

    # Min 3 games threshold
    qualified = grouped[grouped["games"] >= 3].copy()

    # Top 100 by games
    top100 = qualified.nlargest(100, "games")

    result = []
    for _, row in top100.iterrows():
        result.append({
            "player1": row["player_name_1"],
            "hero1": row["hero_name_1"],
            "player2": row["player_name_2"],
            "hero2": row["hero_name_2"],
            "games": int(row["games"]),
            "wins": int(row["wins"]),
            "win_rate": round(float(row["win_rate"]), 4),
        })

    return result


# ---------------------------------------------------------------------------
# 5. Party size effect
# ---------------------------------------------------------------------------

def compute_party_size_effect(data: dict) -> list:
    """Group by party_size, compute games and win_rate — across time tiers."""
    mh = data["match_history"]
    results = []

    for tier_name in TIME_TIERS:
        df = _filter_time(mh, tier_name)
        # Drop NaN party_size
        df_valid = df.dropna(subset=["party_size"]).copy()
        df_valid["party_size"] = df_valid["party_size"].astype(int)

        grouped = (
            df_valid.groupby("party_size")
            .agg(games=("won", "size"), wins=("won", "sum"))
            .reset_index()
        )
        grouped["win_rate"] = round(grouped["wins"] / grouped["games"], 4)

        results.append({
            "tier": tier_name,
            "data": [
                _clean_dict({
                    "party_size": int(row["party_size"]),
                    "games": int(row["games"]),
                    "wins": int(row["wins"]),
                    "win_rate": float(row["win_rate"]),
                })
                for _, row in grouped.iterrows()
            ],
        })

    return results


# ---------------------------------------------------------------------------
# 6. Time patterns
# ---------------------------------------------------------------------------

def compute_time_patterns(data: dict) -> dict:
    """Win rate by hour of day, by day of week, and per-player by hour — across time tiers."""
    mh = data["match_history"]
    results = {}

    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for tier_name in TIME_TIERS:
        df = _filter_time(mh, tier_name)

        # By hour
        by_hour = (
            df.groupby("hour")
            .agg(games=("won", "size"), wins=("won", "sum"))
            .reset_index()
        )
        by_hour["win_rate"] = round(by_hour["wins"] / by_hour["games"], 4)
        by_hour = by_hour.sort_values("hour")

        # By day of week
        by_dow = (
            df.groupby("day_of_week")
            .agg(games=("won", "size"), wins=("won", "sum"))
            .reset_index()
        )
        by_dow["win_rate"] = round(by_dow["wins"] / by_dow["games"], 4)
        # Order by day
        by_dow["day_order"] = by_dow["day_of_week"].map({d: i for i, d in enumerate(dow_order)})
        by_dow = by_dow.sort_values("day_order").drop(columns=["day_order"])

        # Per-player by hour
        player_hour = (
            df.groupby(["player_name", "hour"])
            .agg(games=("won", "size"), wins=("won", "sum"))
            .reset_index()
        )
        player_hour["win_rate"] = round(player_hour["wins"] / player_hour["games"], 4)

        per_player = {}
        for pname, grp in player_hour.groupby("player_name"):
            grp = grp.sort_values("hour")
            per_player[pname] = [
                _clean_dict({"hour": int(r["hour"]), "games": int(r["games"]), "win_rate": float(r["win_rate"])})
                for _, r in grp.iterrows()
            ]

        results[tier_name] = _clean_dict({
            "by_hour": by_hour[["hour", "games", "wins", "win_rate"]].to_dict("records"),
            "by_day_of_week": by_dow[["day_of_week", "games", "wins", "win_rate"]].to_dict("records"),
            "per_player_by_hour": per_player,
        })

    return results


# ---------------------------------------------------------------------------
# 7. Performance trends
# ---------------------------------------------------------------------------

def compute_performance_trends(data: dict) -> list:
    """Monthly win rate per player (year-month buckets)."""
    mh = data["match_history"]

    # Create year-month column
    mh = mh.copy()
    mh["year_month"] = mh["year"].astype(str) + "-" + mh["month"].astype(str).str.zfill(2)

    trends = (
        mh.groupby(["player_name", "year_month"])
        .agg(games=("won", "size"), wins=("won", "sum"))
        .reset_index()
    )
    trends["win_rate"] = round(trends["wins"] / trends["games"], 4)
    trends = trends.sort_values(["player_name", "year_month"])

    result = []
    for pname, grp in trends.groupby("player_name"):
        result.append({
            "player": pname,
            "months": [
                _clean_dict({
                    "year_month": r["year_month"],
                    "games": int(r["games"]),
                    "wins": int(r["wins"]),
                    "win_rate": float(r["win_rate"]),
                })
                for _, r in grp.iterrows()
            ],
        })

    return result


# ---------------------------------------------------------------------------
# 8. Role profiles
# ---------------------------------------------------------------------------

def compute_role_profiles(data: dict) -> dict:
    """For each player, weight hero roles by games played to determine role tendencies."""
    heroes_played = data["heroes_played"]
    heroes_ref = data["heroes"]

    # Parse the roles column (stored as string repr of a list)
    heroes_ref = heroes_ref.copy()
    heroes_ref["roles_list"] = heroes_ref["roles"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else []
    )

    # Merge hero roles with player hero data
    merged = heroes_played.merge(
        heroes_ref[["id", "roles_list"]].rename(columns={"id": "hero_id"}),
        on="hero_id",
        how="left",
    )

    profiles = {}
    for pname, grp in merged.groupby("player_name"):
        role_weights = {}
        total_games = int(grp["games"].sum())
        for _, row in grp.iterrows():
            games = int(row["games"])
            roles = row["roles_list"] if isinstance(row["roles_list"], list) else []
            for role in roles:
                role_weights[role] = role_weights.get(role, 0) + games

        # Normalize to percentages
        if total_games > 0:
            role_pcts = {
                role: round(count / total_games * 100, 1)
                for role, count in sorted(role_weights.items(), key=lambda x: -x[1])
            }
        else:
            role_pcts = {}

        profiles[pname] = {
            "total_games": total_games,
            "role_weights": role_pcts,
        }

    return _clean_dict(profiles)


# ---------------------------------------------------------------------------
# 9. Wordcloud insights
# ---------------------------------------------------------------------------

def compute_wordcloud_insights(data: dict) -> dict:
    """Top 20 words per player from wordclouds.json."""
    wc = data["wordclouds"]
    result = {}
    for player, words in wc.items():
        # Sort by count descending, take top 20
        sorted_words = sorted(words.items(), key=lambda x: -x[1])[:20]
        result[player] = [{"word": w, "count": c} for w, c in sorted_words]
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading processed data...")
    data = load_data()

    insights = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    print("Computing player cards...")
    insights["player_cards"] = compute_player_cards(data)

    print("Computing superlatives...")
    insights["superlatives"] = compute_superlatives(data)

    print("Computing duo chemistry...")
    insights["duo_chemistry"] = compute_duo_chemistry(data)

    print("Computing hero synergies...")
    insights["hero_synergies"] = compute_hero_synergies(data)

    print("Computing party size effect...")
    insights["party_size_effect"] = compute_party_size_effect(data)

    print("Computing time patterns...")
    insights["time_patterns"] = compute_time_patterns(data)

    print("Computing performance trends...")
    insights["performance_trends"] = compute_performance_trends(data)

    print("Computing role profiles...")
    insights["role_profiles"] = compute_role_profiles(data)

    print("Computing wordcloud insights...")
    insights["wordclouds"] = compute_wordcloud_insights(data)

    out_path = DATA_PROCESSED / "insights.json"
    with open(out_path, "w") as f:
        json.dump(insights, f, indent=2, default=_safe)

    print(f"Insights saved to {out_path}")
    print(f"  Keys: {list(insights.keys())}")
    print(f"  Player cards: {len(insights['player_cards'])}")
    print(f"  Superlatives tiers: {len(insights['superlatives'])}")
    print(f"  Hero synergies: {len(insights['hero_synergies'])}")
    print(f"  Performance trends: {len(insights['performance_trends'])} players")


if __name__ == "__main__":
    main()
