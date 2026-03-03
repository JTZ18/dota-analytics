"""
Train ML models for Dota 2 analytics:
  1. Win Prediction — GradientBoostingClassifier predicting team wins
  2. Hero Recommendation — score-based hero ranking per player

Outputs: data/processed/ml_insights.json
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_score

from scripts.config import DATA_PROCESSED, PLAYERS


# ---------------------------------------------------------------------------
# 1. Win Prediction Model
# ---------------------------------------------------------------------------

def build_win_prediction_features() -> tuple[pd.DataFrame, pd.Series]:
    """
    Build the feature matrix for win prediction.

    Each row = one match. Features:
      - 11 binary flags: one per friend indicating presence on the team
      - num_friends: count of friends on the team
      - avg_friend_wr: average overall win rate of friends in the match
      - avg_player_hero_wr: average hero-specific win rate for each friend
      - hour: hour of day (UTC) when the match started

    Label: won (bool)
    """
    players_df = pd.read_csv(DATA_PROCESSED / "shared_match_players.csv")
    profiles_df = pd.read_csv(DATA_PROCESSED / "player_profiles.csv")
    heroes_df = pd.read_csv(DATA_PROCESSED / "player_heroes.csv")
    meta_df = pd.read_csv(DATA_PROCESSED / "shared_match_meta.csv")

    # Map player name -> overall win rate
    wr_map = dict(zip(profiles_df["name"], profiles_df["win_rate"]))

    # Map (account_id, hero_id) -> player-hero win rate
    hero_wr_map = dict(
        zip(
            zip(heroes_df["account_id"], heroes_df["hero_id"]),
            heroes_df["win_rate"],
        )
    )

    # Canonical ordered list of player names (for binary flag columns)
    player_names = sorted(PLAYERS.keys())

    # Join start_time from meta to compute hour
    start_map = dict(zip(meta_df["match_id"], meta_df["start_time"]))

    # Group players by match — all friends are on the same team per meta
    grouped = players_df.groupby("match_id")

    rows: list[dict] = []
    for match_id, grp in grouped:
        # All friends in this match share the same team (same_team=True for
        # every match in our dataset), so we just take the first row's outcome.
        won = grp["won"].iloc[0]
        num_friends = len(grp)

        # Binary flags for each player
        names_in_match = set(grp["player_name"])
        flags = {f"has_{name}": int(name in names_in_match) for name in player_names}

        # Average overall win rate of friends in the match
        friend_wrs = [wr_map.get(n, 0.5) for n in names_in_match]
        avg_friend_wr = float(np.mean(friend_wrs))

        # Average player-hero-specific win rate
        hero_wrs = []
        for _, row in grp.iterrows():
            key = (row["account_id"], row["hero_id"])
            hw = hero_wr_map.get(key)
            if hw is not None:
                hero_wrs.append(hw)
            else:
                hero_wrs.append(0.5)  # fallback
        avg_player_hero_wr = float(np.mean(hero_wrs))

        # Hour of day (UTC)
        ts = start_map.get(match_id)
        hour = int(pd.Timestamp(ts, unit="s", tz="UTC").hour) if ts else 12

        row_dict = {
            "match_id": match_id,
            "won": won,
            "num_friends": num_friends,
            "avg_friend_wr": avg_friend_wr,
            "avg_player_hero_wr": avg_player_hero_wr,
            "hour": hour,
        }
        row_dict.update(flags)
        rows.append(row_dict)

    df = pd.DataFrame(rows)

    feature_cols = (
        [f"has_{n}" for n in player_names]
        + ["num_friends", "avg_friend_wr", "avg_player_hero_wr", "hour"]
    )
    X = df[feature_cols]
    y = df["won"].astype(int)

    return X, y


def train_win_predictor(X: pd.DataFrame, y: pd.Series) -> dict:
    """Train a GradientBoostingClassifier with cross-validation."""
    clf = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
    )

    n_folds = min(10, max(5, len(X) // 100))
    scores = cross_val_score(clf, X, y, cv=n_folds, scoring="accuracy")

    # Fit on full data for feature importances
    clf.fit(X, y)

    importances = dict(zip(X.columns, clf.feature_importances_.tolist()))
    importances = dict(
        sorted(importances.items(), key=lambda kv: kv[1], reverse=True)
    )

    baseline = float(y.mean()) if y.mean() >= 0.5 else float(1 - y.mean())

    metrics = {
        "accuracy": round(float(scores.mean()), 4),
        "std": round(float(scores.std()), 4),
        "n_samples": int(len(X)),
        "n_features": int(X.shape[1]),
        "cv_folds": n_folds,
        "win_rate_baseline": round(baseline, 4),
    }

    return {
        "metrics": metrics,
        "feature_importances": {k: round(v, 4) for k, v in importances.items()},
    }


# ---------------------------------------------------------------------------
# 2. Hero Recommendation Engine
# ---------------------------------------------------------------------------

def build_hero_recommendations() -> dict:
    """
    For each player, rank heroes by score = win_rate * log(games + 1).
    Return top 10 per player.
    """
    heroes_df = pd.read_csv(DATA_PROCESSED / "player_heroes.csv")

    heroes_df["score"] = heroes_df["win_rate"] * np.log(heroes_df["games"] + 1)

    recommendations: dict[str, list[dict]] = {}
    for name, grp in heroes_df.groupby("player_name"):
        top = grp.nlargest(10, "score")
        recs = []
        for _, row in top.iterrows():
            recs.append(
                {
                    "hero_name": row["hero_name"],
                    "hero_id": int(row["hero_id"]),
                    "games": int(row["games"]),
                    "wins": int(row["wins"]),
                    "win_rate": round(float(row["win_rate"]), 4),
                    "score": round(float(row["score"]), 4),
                }
            )
        recommendations[str(name)] = recs

    return recommendations


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("DOTA 2 ML MODELS")
    print("=" * 60)

    # --- Win Prediction ---
    print("\n[1/2] Building win prediction features...")
    X, y = build_win_prediction_features()
    print(f"      Feature matrix: {X.shape[0]} samples x {X.shape[1]} features")
    print(f"      Win rate: {y.mean():.4f}")

    print("      Training GradientBoostingClassifier with cross-validation...")
    win_result = train_win_predictor(X, y)
    m = win_result["metrics"]
    print(f"      CV Accuracy:  {m['accuracy']:.4f} +/- {m['std']:.4f}")
    print(f"      Baseline:     {m['win_rate_baseline']:.4f}")
    print(f"      Lift vs base: {m['accuracy'] - m['win_rate_baseline']:+.4f}")

    print("\n      Top feature importances:")
    for feat, imp in list(win_result["feature_importances"].items())[:8]:
        print(f"        {feat:30s} {imp:.4f}")

    # --- Hero Recommendations ---
    print("\n[2/2] Building hero recommendations...")
    hero_recs = build_hero_recommendations()
    for name, recs in sorted(hero_recs.items()):
        top = recs[0]
        print(
            f"      {name:15s} -> #{1} {top['hero_name']:20s} "
            f"({top['games']} games, {top['win_rate']:.0%} WR, score={top['score']:.2f})"
        )

    # --- Save ---
    output = {
        "win_predictor": win_result,
        "hero_recommendations": hero_recs,
    }

    out_path = DATA_PROCESSED / "ml_insights.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
