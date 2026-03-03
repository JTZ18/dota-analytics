"""Scrape all data from OpenDota API for the friend group."""

import json
from pathlib import Path

from scripts.config import PLAYERS, GAME_MODES, HISTOGRAM_FIELDS, DATA_RAW
from scripts.api_client import fetch


def scrape_player(name: str, account_id: int):
    """Scrape all endpoints for a single player."""
    base = DATA_RAW / "players" / str(account_id)
    base.mkdir(parents=True, exist_ok=True)

    print(f"  Scraping profile...")
    fetch(f"/players/{account_id}", cache_path=base / "profile.json")

    print(f"  Scraping win/loss...")
    fetch(f"/players/{account_id}/wl", cache_path=base / "wl.json")

    print(f"  Scraping heroes...")
    fetch(f"/players/{account_id}/heroes", cache_path=base / "heroes.json")

    print(f"  Scraping totals...")
    fetch(f"/players/{account_id}/totals", cache_path=base / "totals.json")

    print(f"  Scraping counts...")
    fetch(f"/players/{account_id}/counts", cache_path=base / "counts.json")

    print(f"  Scraping rankings...")
    fetch(f"/players/{account_id}/rankings", cache_path=base / "rankings.json")

    print(f"  Scraping recent matches...")
    fetch(f"/players/{account_id}/recentMatches", cache_path=base / "recent_matches.json")

    print(f"  Scraping peers...")
    fetch(f"/players/{account_id}/peers", cache_path=base / "peers.json")

    print(f"  Scraping wordcloud...")
    fetch(f"/players/{account_id}/wordcloud", cache_path=base / "wordcloud.json")

    # Match history — fetch ALL matches (no game_mode filter on API, we filter later)
    print(f"  Scraping match history...")
    fetch(
        f"/players/{account_id}/matches",
        params={"significant": 0},
        cache_path=base / "matches.json",
    )

    # Histograms for key stats
    for field in HISTOGRAM_FIELDS:
        print(f"  Scraping histogram: {field}...")
        fetch(
            f"/players/{account_id}/histograms/{field}",
            cache_path=base / f"histogram_{field}.json",
        )

    print(f"  Done with {name}!")


def scrape_heroes():
    """Scrape hero reference data."""
    heroes_dir = DATA_RAW / "heroes"
    heroes_dir.mkdir(parents=True, exist_ok=True)

    print("Scraping hero list...")
    heroes = fetch("/heroes", cache_path=heroes_dir / "heroes.json")

    print("Scraping hero stats...")
    fetch("/heroStats", cache_path=heroes_dir / "hero_stats.json")

    print("Scraping hero matchups...")
    for hero in heroes:
        hero_id = hero["id"]
        fetch(
            f"/heroes/{hero_id}/matchups",
            cache_path=heroes_dir / f"matchups_{hero_id}.json",
        )
    print("Done with heroes!")


def scrape_shared_matches():
    """Find matches where 2+ friends played together and fetch full details."""
    print("Finding shared matches...")
    all_account_ids = set(PLAYERS.values())

    # Collect all match IDs per player
    player_matches: dict[int, set[int]] = {}
    for name, account_id in PLAYERS.items():
        matches_file = DATA_RAW / "players" / str(account_id) / "matches.json"
        if matches_file.exists():
            matches = json.loads(matches_file.read_text())
            player_matches[account_id] = {m["match_id"] for m in matches}
        else:
            print(f"  WARNING: No matches file for {name}, run player scrape first")
            player_matches[account_id] = set()

    # Find matches with 2+ friends
    from collections import Counter
    match_counter = Counter()
    for account_id, match_ids in player_matches.items():
        for mid in match_ids:
            match_counter[mid] += 1

    shared_match_ids = {mid for mid, count in match_counter.items() if count >= 2}
    print(f"  Found {len(shared_match_ids)} matches with 2+ friends")

    # Fetch full match details (these are the most expensive calls)
    matches_dir = DATA_RAW / "matches"
    matches_dir.mkdir(parents=True, exist_ok=True)

    for i, match_id in enumerate(sorted(shared_match_ids)):
        cache_path = matches_dir / f"{match_id}.json"
        if cache_path.exists():
            continue
        if i % 50 == 0:
            print(f"  Fetching match details: {i}/{len(shared_match_ids)}...")
        try:
            fetch(f"/matches/{match_id}", cache_path=cache_path)
        except Exception as e:
            print(f"  WARNING: Failed to fetch match {match_id}: {e}")

    print(f"  Done fetching shared match details!")


def scrape_all():
    """Run the full scrape pipeline."""
    # 1. Hero reference data
    scrape_heroes()

    # 2. Per-player data
    for name, account_id in PLAYERS.items():
        print(f"\n--- Scraping {name} ({account_id}) ---")
        scrape_player(name, account_id)

    # 3. Shared match details
    scrape_shared_matches()

    print("\n=== SCRAPE COMPLETE ===")


if __name__ == "__main__":
    scrape_all()
