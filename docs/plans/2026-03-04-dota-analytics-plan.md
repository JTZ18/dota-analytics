# Dota 2 Friend Group Analytics — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Scrape all Dota 2 data for 11 friends from OpenDota API, perform EDA and ML analysis, and present fun + competitive insights via interactive HTML playgrounds.

**Architecture:** Python data pipeline (scrape → process → analyze → model → visualize). Raw API responses cached as JSON, processed into pandas DataFrames. Insights pre-computed and embedded as JSON in Playground HTML files.

**Tech Stack:** Python 3.12, uv (package manager), requests, pandas, numpy, scikit-learn, Chart.js (CDN in playground HTML)

---

## Phase 1: Project Setup

### Task 1: Initialize uv project and directory structure

**Files:**
- Create: `pyproject.toml` (via uv init)
- Create: `scripts/__init__.py`
- Create: `scripts/config.py`
- Create: `data/raw/.gitkeep`
- Create: `data/processed/.gitkeep`

**Step 1: Initialize uv project**

Run:
```bash
cd /Users/jon/code/fun/dota-analytics
uv init --no-readme
```

**Step 2: Add dependencies**

Run:
```bash
uv add requests pandas numpy scikit-learn pyarrow
```

**Step 3: Create directory structure**

Run:
```bash
mkdir -p scripts data/raw data/processed data/raw/players data/raw/matches data/raw/heroes playground
touch scripts/__init__.py data/raw/.gitkeep data/processed/.gitkeep
```

**Step 4: Create config.py with player data and API settings**

Create `scripts/config.py`:
```python
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

API_BASE = "https://api.opendota.com/api"
REQUEST_DELAY = 1.1  # seconds between API calls (60/min limit)

PLAYERS = {
    "bread": 107007554,
    "cremfresh": 1254415,
    "Breaze": 99686578,
    "Freecss": 110926483,
    "Maegix": 107872884,
    "Imi bne": 140869118,
    "Kob": 139410877,
    "harry ron": 107969010,
    "rabbs": 482479226,
    "Saic": 138451133,
    "Bartolomeo": 86098817,
}

# Game mode IDs: 1 = All Pick, 22 = All Pick (Ranked), 23 = Turbo
GAME_MODES = [1, 22, 23]

# Histogram fields to fetch
HISTOGRAM_FIELDS = [
    "kills", "deaths", "assists", "kda", "gold_per_min", "xp_per_min",
    "last_hits", "denies", "hero_damage", "tower_damage", "hero_healing",
    "duration", "actions_per_min",
]
```

**Step 5: Initialize git repo and commit**

Run:
```bash
git init
echo "__pycache__/\n*.pyc\n.venv/\ndata/raw/players/\ndata/raw/matches/\ndata/raw/heroes/\n.python-version" > .gitignore
git add -A
git commit -m "feat: initialize project with uv, directory structure, and config"
```

---

## Phase 2: Data Collection

### Task 2: Build the API client with rate limiting and caching

**Files:**
- Create: `scripts/api_client.py`

**Step 1: Create the API client**

Create `scripts/api_client.py`:
```python
"""OpenDota API client with rate limiting and local caching."""

import json
import time
from pathlib import Path

import requests

from scripts.config import API_BASE, REQUEST_DELAY, DATA_RAW

_last_request_time = 0.0


def _rate_limit():
    """Enforce minimum delay between API requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()


def fetch(endpoint: str, params: dict | None = None, cache_path: Path | None = None) -> dict | list:
    """Fetch from OpenDota API with caching and rate limiting.

    Args:
        endpoint: API path like '/players/107969010'
        params: Optional query parameters
        cache_path: If provided, cache response to this file and return cached version if it exists
    """
    if cache_path and cache_path.exists():
        return json.loads(cache_path.read_text())

    _rate_limit()
    url = f"{API_BASE}{endpoint}"
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2))

    return data
```

**Step 2: Quick smoke test**

Run:
```bash
uv run python -c "from scripts.api_client import fetch; print(fetch('/heroes')[0]['localized_name'])"
```
Expected: Prints a hero name like "Anti-Mage"

**Step 3: Commit**

```bash
git add scripts/api_client.py
git commit -m "feat: add OpenDota API client with rate limiting and caching"
```

---

### Task 3: Build the data scraper — player data

**Files:**
- Create: `scripts/scrape.py`

**Step 1: Create the scraper for all per-player endpoints**

Create `scripts/scrape.py`:
```python
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
```

**Step 2: Commit**

```bash
git add scripts/scrape.py
git commit -m "feat: add full data scraper for players, heroes, and shared matches"
```

**Step 3: Run the scraper**

Run:
```bash
uv run python -m scripts.scrape
```

This will take a while (rate limited at ~1 req/sec). Expected: ~200+ API calls for player data, ~150 for hero matchups, then variable number for shared match details. All responses cached as JSON in `data/raw/`.

**Step 4: Verify data was scraped**

Run:
```bash
ls data/raw/players/ | head
ls data/raw/heroes/ | head
ls data/raw/matches/ | head
find data/raw -name "*.json" | wc -l
```

Expected: Directories populated with JSON files. Should see 100+ files total.

---

## Phase 3: Data Processing

### Task 4: Process raw data into clean DataFrames

**Files:**
- Create: `scripts/process.py`

**Step 1: Create the processing script**

Create `scripts/process.py`:
```python
"""Process raw JSON API responses into clean pandas DataFrames."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np

from scripts.config import PLAYERS, GAME_MODES, DATA_RAW, DATA_PROCESSED


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text())


def process_player_profiles() -> pd.DataFrame:
    """Create a player profiles DataFrame."""
    rows = []
    for name, account_id in PLAYERS.items():
        profile_data = load_json(DATA_RAW / "players" / str(account_id) / "profile.json")
        wl_data = load_json(DATA_RAW / "players" / str(account_id) / "wl.json")
        profile = profile_data.get("profile", {})
        rows.append({
            "account_id": account_id,
            "name": name,
            "persona": profile.get("personaname", name),
            "avatar": profile.get("avatarfull", ""),
            "rank_tier": profile_data.get("rank_tier"),
            "wins": wl_data.get("win", 0),
            "losses": wl_data.get("lose", 0),
            "total_games": wl_data.get("win", 0) + wl_data.get("lose", 0),
            "win_rate": wl_data.get("win", 0) / max(1, wl_data.get("win", 0) + wl_data.get("lose", 0)),
        })
    df = pd.DataFrame(rows)
    df.to_csv(DATA_PROCESSED / "player_profiles.csv", index=False)
    return df


def process_player_heroes() -> pd.DataFrame:
    """Create a per-player per-hero stats DataFrame."""
    heroes_list = load_json(DATA_RAW / "heroes" / "heroes.json")
    hero_names = {h["id"]: h["localized_name"] for h in heroes_list}

    rows = []
    for name, account_id in PLAYERS.items():
        heroes_data = load_json(DATA_RAW / "players" / str(account_id) / "heroes.json")
        for h in heroes_data:
            hero_id = int(h["hero_id"])
            games = h.get("games", 0)
            if games == 0:
                continue
            rows.append({
                "account_id": account_id,
                "player_name": name,
                "hero_id": hero_id,
                "hero_name": hero_names.get(hero_id, f"Unknown({hero_id})"),
                "games": games,
                "wins": h.get("win", 0),
                "win_rate": h.get("win", 0) / max(1, games),
                "last_played": h.get("last_played", 0),
            })
    df = pd.DataFrame(rows)
    df.to_csv(DATA_PROCESSED / "player_heroes.csv", index=False)
    return df


def process_player_totals() -> pd.DataFrame:
    """Create a player totals (aggregate stats) DataFrame."""
    rows = []
    for name, account_id in PLAYERS.items():
        totals_data = load_json(DATA_RAW / "players" / str(account_id) / "totals.json")
        row = {"account_id": account_id, "player_name": name}
        for stat in totals_data:
            field = stat["field"]
            n = stat.get("n", 0)
            total = stat.get("sum", 0)
            row[f"{field}_total"] = total
            row[f"{field}_n"] = n
            row[f"{field}_avg"] = total / max(1, n)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(DATA_PROCESSED / "player_totals.csv", index=False)
    return df


def process_match_history() -> pd.DataFrame:
    """Process all player match histories into a single DataFrame.
    Filter to All Pick + Turbo only. Add derived time columns."""
    rows = []
    for name, account_id in PLAYERS.items():
        matches = load_json(DATA_RAW / "players" / str(account_id) / "matches.json")
        for m in matches:
            game_mode = m.get("game_mode")
            if game_mode not in GAME_MODES:
                continue
            start_time = m.get("start_time", 0)
            dt = datetime.fromtimestamp(start_time, tz=timezone.utc) if start_time else None
            player_slot = m.get("player_slot", 0)
            is_radiant = player_slot < 128
            radiant_win = m.get("radiant_win", False)
            won = (is_radiant and radiant_win) or (not is_radiant and not radiant_win)
            rows.append({
                "account_id": account_id,
                "player_name": name,
                "match_id": m.get("match_id"),
                "hero_id": m.get("hero_id"),
                "start_time": start_time,
                "datetime": dt,
                "year": dt.year if dt else None,
                "month": dt.month if dt else None,
                "hour": dt.hour if dt else None,
                "day_of_week": dt.strftime("%A") if dt else None,
                "duration": m.get("duration", 0),
                "game_mode": game_mode,
                "lobby_type": m.get("lobby_type"),
                "kills": m.get("kills", 0),
                "deaths": m.get("deaths", 0),
                "assists": m.get("assists", 0),
                "player_slot": player_slot,
                "is_radiant": is_radiant,
                "radiant_win": radiant_win,
                "won": won,
                "party_size": m.get("party_size"),
                "average_rank": m.get("average_rank"),
            })
    df = pd.DataFrame(rows)
    df.to_csv(DATA_PROCESSED / "match_history.csv", index=False)
    return df


def process_peers() -> pd.DataFrame:
    """Process peer data — filter to only friends in our group."""
    friend_ids = set(PLAYERS.values())
    id_to_name = {v: k for k, v in PLAYERS.items()}
    rows = []
    for name, account_id in PLAYERS.items():
        peers = load_json(DATA_RAW / "players" / str(account_id) / "peers.json")
        for p in peers:
            peer_id = p.get("account_id")
            if peer_id not in friend_ids:
                continue
            rows.append({
                "player_id": account_id,
                "player_name": name,
                "peer_id": peer_id,
                "peer_name": id_to_name.get(peer_id, "Unknown"),
                "with_games": p.get("with_games", 0),
                "with_win": p.get("with_win", 0),
                "with_win_rate": p.get("with_win", 0) / max(1, p.get("with_games", 0)),
                "against_games": p.get("against_games", 0),
                "against_win": p.get("against_win", 0),
                "with_gpm_sum": p.get("with_gpm_sum", 0),
                "with_xpm_sum": p.get("with_xpm_sum", 0),
                "last_played": p.get("last_played", 0),
            })
    df = pd.DataFrame(rows)
    df.to_csv(DATA_PROCESSED / "peers.csv", index=False)
    return df


def process_heroes_reference() -> pd.DataFrame:
    """Process hero reference data."""
    heroes = load_json(DATA_RAW / "heroes" / "heroes.json")
    df = pd.DataFrame(heroes)
    df.to_csv(DATA_PROCESSED / "heroes.csv", index=False)
    return df


def process_shared_matches() -> pd.DataFrame:
    """Process full match details for shared matches.
    Extract per-player stats for friends only."""
    friend_ids = set(PLAYERS.values())
    id_to_name = {v: k for k, v in PLAYERS.items()}
    heroes_list = load_json(DATA_RAW / "heroes" / "heroes.json")
    hero_names = {h["id"]: h["localized_name"] for h in heroes_list}

    matches_dir = DATA_RAW / "matches"
    rows = []
    match_meta_rows = []

    for match_file in sorted(matches_dir.glob("*.json")):
        try:
            match = load_json(match_file)
        except Exception:
            continue

        match_id = match.get("match_id")
        start_time = match.get("start_time", 0)
        dt = datetime.fromtimestamp(start_time, tz=timezone.utc) if start_time else None
        duration = match.get("duration", 0)
        radiant_win = match.get("radiant_win", False)
        game_mode = match.get("game_mode")

        players = match.get("players", [])
        friends_in_match = []

        for p in players:
            aid = p.get("account_id")
            if aid not in friend_ids:
                continue
            player_slot = p.get("player_slot", 0)
            is_radiant = player_slot < 128
            won = (is_radiant and radiant_win) or (not is_radiant and not radiant_win)
            hero_id = p.get("hero_id", 0)

            friends_in_match.append({
                "account_id": aid,
                "player_name": id_to_name.get(aid, "Unknown"),
                "is_radiant": is_radiant,
                "won": won,
                "hero_id": hero_id,
            })

            rows.append({
                "match_id": match_id,
                "account_id": aid,
                "player_name": id_to_name.get(aid, "Unknown"),
                "hero_id": hero_id,
                "hero_name": hero_names.get(hero_id, f"Unknown({hero_id})"),
                "start_time": start_time,
                "datetime": dt,
                "year": dt.year if dt else None,
                "hour": dt.hour if dt else None,
                "day_of_week": dt.strftime("%A") if dt else None,
                "duration": duration,
                "game_mode": game_mode,
                "radiant_win": radiant_win,
                "is_radiant": is_radiant,
                "won": won,
                "kills": p.get("kills", 0),
                "deaths": p.get("deaths", 0),
                "assists": p.get("assists", 0),
                "gold_per_min": p.get("gold_per_min", 0),
                "xp_per_min": p.get("xp_per_min", 0),
                "hero_damage": p.get("hero_damage", 0),
                "tower_damage": p.get("tower_damage", 0),
                "hero_healing": p.get("hero_healing", 0),
                "last_hits": p.get("last_hits", 0),
                "denies": p.get("denies", 0),
                "net_worth": p.get("net_worth", 0),
                "lane": p.get("lane"),
                "lane_role": p.get("lane_role"),
                "party_size": p.get("party_size"),
                "actions_per_min": p.get("actions_per_min", 0),
                "rank_tier": p.get("rank_tier"),
                "obs_placed": p.get("obs_placed", 0),
                "sen_placed": p.get("sen_placed", 0),
                "teamfight_participation": p.get("teamfight_participation", 0),
            })

        # Match-level metadata for shared matches
        if len(friends_in_match) >= 2:
            # Determine which friends were on the same team
            radiant_friends = [f for f in friends_in_match if f["is_radiant"]]
            dire_friends = [f for f in friends_in_match if not f["is_radiant"]]
            same_team = len(radiant_friends) >= 2 or len(dire_friends) >= 2

            match_meta_rows.append({
                "match_id": match_id,
                "start_time": start_time,
                "duration": duration,
                "game_mode": game_mode,
                "radiant_win": radiant_win,
                "num_friends": len(friends_in_match),
                "same_team": same_team,
                "friend_names": "|".join(sorted(f["player_name"] for f in friends_in_match)),
                "friend_heroes": "|".join(str(f["hero_id"]) for f in friends_in_match),
            })

    df_players = pd.DataFrame(rows)
    df_players.to_csv(DATA_PROCESSED / "shared_match_players.csv", index=False)

    df_meta = pd.DataFrame(match_meta_rows)
    df_meta.to_csv(DATA_PROCESSED / "shared_match_meta.csv", index=False)

    return df_players, df_meta


def process_wordclouds() -> dict:
    """Process wordcloud data for each player. Return dict of player_name -> word_counts."""
    result = {}
    for name, account_id in PLAYERS.items():
        wc_file = DATA_RAW / "players" / str(account_id) / "wordcloud.json"
        if wc_file.exists():
            wc = load_json(wc_file)
            # wordcloud is a dict of {word: count}
            if isinstance(wc, dict) and "my_word_counts" in wc:
                result[name] = wc["my_word_counts"]
            elif isinstance(wc, dict):
                result[name] = wc
    # Save as JSON since it's nested
    import json
    with open(DATA_PROCESSED / "wordclouds.json", "w") as f:
        json.dump(result, f, indent=2)
    return result


def process_all():
    """Run the full processing pipeline."""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print("Processing player profiles...")
    profiles = process_player_profiles()
    print(f"  {len(profiles)} players")

    print("Processing player heroes...")
    heroes = process_player_heroes()
    print(f"  {len(heroes)} player-hero combinations")

    print("Processing player totals...")
    totals = process_player_totals()
    print(f"  {len(totals)} players with totals")

    print("Processing match history...")
    matches = process_match_history()
    print(f"  {len(matches)} match records (All Pick + Turbo)")

    print("Processing peers...")
    peers = process_peers()
    print(f"  {len(peers)} peer relationships")

    print("Processing heroes reference...")
    heroes_ref = process_heroes_reference()
    print(f"  {len(heroes_ref)} heroes")

    print("Processing shared matches...")
    shared_players, shared_meta = process_shared_matches()
    print(f"  {len(shared_players)} player records in shared matches")
    print(f"  {len(shared_meta)} shared matches total")

    print("Processing wordclouds...")
    wc = process_wordclouds()
    print(f"  {len(wc)} players with wordcloud data")

    print("\n=== PROCESSING COMPLETE ===")


if __name__ == "__main__":
    process_all()
```

**Step 2: Run the processor**

Run:
```bash
uv run python -m scripts.process
```

Expected: All CSV files created in `data/processed/`.

**Step 3: Verify output**

Run:
```bash
ls -la data/processed/
uv run python -c "import pandas as pd; df = pd.read_csv('data/processed/match_history.csv'); print(f'Matches: {len(df)}'); print(df.columns.tolist())"
```

**Step 4: Commit**

```bash
git add scripts/process.py
git commit -m "feat: add data processing pipeline for all player and match data"
```

---

## Phase 4: Exploratory Data Analysis & Insights

### Task 5: EDA and insight generation

**Files:**
- Create: `scripts/eda.py`
- Create: `scripts/insights.py`

This is the largest task — we generate all the computed insights that the frontend will display. The EDA script explores the data and the insights script computes structured results.

**Step 1: Create the EDA + insights generation script**

Create `scripts/insights.py`:
```python
"""Generate all insights from processed data for the playground frontend."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

import pandas as pd
import numpy as np

from scripts.config import PLAYERS, DATA_PROCESSED, DATA_RAW

# Time tier cutoffs (unix timestamps)
NOW = datetime.now(timezone.utc).timestamp()
ONE_YEAR_AGO = NOW - 365.25 * 24 * 3600
TWO_YEARS_AGO = NOW - 2 * 365.25 * 24 * 3600


def load_data():
    """Load all processed DataFrames."""
    return {
        "profiles": pd.read_csv(DATA_PROCESSED / "player_profiles.csv"),
        "heroes_per_player": pd.read_csv(DATA_PROCESSED / "player_heroes.csv"),
        "totals": pd.read_csv(DATA_PROCESSED / "player_totals.csv"),
        "match_history": pd.read_csv(DATA_PROCESSED / "match_history.csv"),
        "peers": pd.read_csv(DATA_PROCESSED / "peers.csv"),
        "heroes_ref": pd.read_csv(DATA_PROCESSED / "heroes.csv"),
        "shared_players": pd.read_csv(DATA_PROCESSED / "shared_match_players.csv"),
        "shared_meta": pd.read_csv(DATA_PROCESSED / "shared_match_meta.csv"),
    }


def time_filter(df, tier="all", time_col="start_time"):
    """Filter DataFrame by time tier."""
    if tier == "1y":
        return df[df[time_col] >= ONE_YEAR_AGO]
    elif tier == "2y":
        return df[df[time_col] >= TWO_YEARS_AGO]
    return df  # all-time


def compute_player_cards(data):
    """Generate 'baseball card' data for each player."""
    profiles = data["profiles"]
    heroes = data["heroes_per_player"]
    totals = data["totals"]

    cards = []
    for _, p in profiles.iterrows():
        name = p["name"]
        aid = p["account_id"]

        # Top 3 heroes by games played
        player_heroes = heroes[heroes["account_id"] == aid].nlargest(3, "games")
        top_heroes = [
            {"name": row["hero_name"], "games": int(row["games"]), "win_rate": round(row["win_rate"], 3)}
            for _, row in player_heroes.iterrows()
        ]

        # Get avg stats from totals
        player_totals = totals[totals["account_id"] == aid]
        avg_kills = float(player_totals["kills_avg"].iloc[0]) if len(player_totals) > 0 else 0
        avg_deaths = float(player_totals["deaths_avg"].iloc[0]) if len(player_totals) > 0 else 0
        avg_assists = float(player_totals["assists_avg"].iloc[0]) if len(player_totals) > 0 else 0

        cards.append({
            "name": name,
            "account_id": int(aid),
            "avatar": p.get("avatar", ""),
            "rank_tier": int(p["rank_tier"]) if pd.notna(p["rank_tier"]) else None,
            "total_games": int(p["total_games"]),
            "win_rate": round(float(p["win_rate"]), 4),
            "top_heroes": top_heroes,
            "avg_kills": round(avg_kills, 1),
            "avg_deaths": round(avg_deaths, 1),
            "avg_assists": round(avg_assists, 1),
        })
    return cards


def compute_superlatives(data):
    """Compute fun awards/superlatives backed by data."""
    totals = data["totals"]
    match_history = data["match_history"]
    heroes = data["heroes_per_player"]

    awards = []

    # Helper to get player name for max/min of a column
    def award_for_max(col, title, description_template):
        if col in totals.columns:
            idx = totals[col].idxmax()
            row = totals.loc[idx]
            val = round(float(row[col]), 2)
            awards.append({
                "title": title,
                "player": row["player_name"],
                "value": val,
                "description": description_template.format(player=row["player_name"], value=val),
            })

    def award_for_min(col, title, description_template):
        if col in totals.columns:
            idx = totals[col].idxmin()
            row = totals.loc[idx]
            val = round(float(row[col]), 2)
            awards.append({
                "title": title,
                "player": row["player_name"],
                "value": val,
                "description": description_template.format(player=row["player_name"], value=val),
            })

    # Deaths king
    award_for_max("deaths_avg", "The Feeder",
                  "{player} averages {value} deaths per game")

    # Kills king
    award_for_max("kills_avg", "The Slayer",
                  "{player} averages {value} kills per game")

    # Assist lord
    award_for_max("assists_avg", "The Team Player",
                  "{player} averages {value} assists per game")

    # GPM king
    award_for_max("gold_per_min_avg", "The Farmer",
                  "{player} averages {value} gold per minute")

    # XPM
    award_for_max("xp_per_min_avg", "The XP Sponge",
                  "{player} averages {value} XP per minute")

    # Hero damage
    award_for_max("hero_damage_avg", "The Damage Dealer",
                  "{player} averages {value} hero damage per game")

    # Tower damage
    award_for_max("tower_damage_avg", "The Rat",
                  "{player} averages {value} tower damage per game — split push specialist")

    # Hero healing
    award_for_max("hero_healing_avg", "The Healer",
                  "{player} averages {value} hero healing per game")

    # Actions per minute
    award_for_max("actions_per_min_avg", "The Tryhard",
                  "{player} has {value} APM — the sweatiest player")

    # Lowest deaths
    award_for_min("deaths_avg", "The Survivor",
                  "{player} averages only {value} deaths per game")

    # Most last hits
    award_for_max("last_hits_avg", "Last Hit Machine",
                  "{player} averages {value} last hits per game")

    # One Trick Pony — most games on a single hero
    max_hero_games = heroes.groupby("player_name").apply(
        lambda g: g.nlargest(1, "games").iloc[0]
    ).reset_index(drop=True)
    otp_idx = max_hero_games["games"].idxmax()
    otp = max_hero_games.loc[otp_idx]
    awards.append({
        "title": "One Trick Pony",
        "player": otp["player_name"],
        "value": int(otp["games"]),
        "description": f"{otp['player_name']} has played {int(otp['games'])} games on {otp['hero_name']}",
    })

    # Hero Hopper — most unique heroes played
    unique_heroes = heroes[heroes["games"] >= 1].groupby("player_name")["hero_id"].nunique()
    hopper_name = unique_heroes.idxmax()
    hopper_count = int(unique_heroes.max())
    awards.append({
        "title": "Hero Hopper",
        "player": hopper_name,
        "value": hopper_count,
        "description": f"{hopper_name} has played {hopper_count} different heroes",
    })

    # Late Night Warrior — highest % of games after midnight (0:00 - 5:00 local)
    # Using UTC hour as proxy (they can be in any timezone, but relative comparison still works)
    if "hour" in match_history.columns:
        late_night = match_history[match_history["hour"].isin([0, 1, 2, 3, 4, 5])]
        all_games_count = match_history.groupby("player_name").size()
        late_games_count = late_night.groupby("player_name").size()
        late_pct = (late_games_count / all_games_count).dropna()
        if len(late_pct) > 0:
            night_owl = late_pct.idxmax()
            awards.append({
                "title": "Late Night Warrior",
                "player": night_owl,
                "value": round(float(late_pct.max()) * 100, 1),
                "description": f"{night_owl} plays {round(float(late_pct.max()) * 100, 1)}% of games between midnight and 5 AM (UTC)",
            })

    # Longest average game duration with a loss
    losses = match_history[match_history["won"] == False]
    avg_loss_duration = losses.groupby("player_name")["duration"].mean()
    if len(avg_loss_duration) > 0:
        cliff = avg_loss_duration.idxmax()
        awards.append({
            "title": "Cliff Jungler",
            "player": cliff,
            "value": round(float(avg_loss_duration.max()) / 60, 1),
            "description": f"{cliff}'s losses average {round(float(avg_loss_duration.max()) / 60, 1)} minutes — suffering the longest",
        })

    # Most games played overall
    games_per_player = match_history.groupby("player_name").size()
    grinder = games_per_player.idxmax()
    awards.append({
        "title": "The Grinder",
        "player": grinder,
        "value": int(games_per_player.max()),
        "description": f"{grinder} has played {int(games_per_player.max())} All Pick + Turbo games",
    })

    # Highest KDA ratio
    kda_per_player = match_history.groupby("player_name").agg(
        kills=("kills", "mean"), deaths=("deaths", "mean"), assists=("assists", "mean")
    )
    kda_per_player["kda"] = (kda_per_player["kills"] + kda_per_player["assists"]) / kda_per_player["deaths"].clip(lower=1)
    kda_king = kda_per_player["kda"].idxmax()
    awards.append({
        "title": "KDA King",
        "player": kda_king,
        "value": round(float(kda_per_player["kda"].max()), 2),
        "description": f"{kda_king} has the best KDA ratio at {round(float(kda_per_player['kda'].max()), 2)}",
    })

    return awards


def compute_duo_chemistry(data):
    """Compute win rate heatmap for every pair of friends."""
    peers = data["peers"]
    players = list(PLAYERS.keys())

    heatmap = {}
    for _, row in peers.iterrows():
        p1 = row["player_name"]
        p2 = row["peer_name"]
        key = f"{p1}|{p2}"
        heatmap[key] = {
            "player1": p1,
            "player2": p2,
            "with_games": int(row["with_games"]),
            "with_wins": int(row["with_win"]),
            "with_win_rate": round(float(row["with_win_rate"]), 4),
            "against_games": int(row["against_games"]),
        }

    # Best and worst duos
    pairs = list(heatmap.values())
    pairs_with_enough_games = [p for p in pairs if p["with_games"] >= 10]
    if pairs_with_enough_games:
        best_duo = max(pairs_with_enough_games, key=lambda x: x["with_win_rate"])
        worst_duo = min(pairs_with_enough_games, key=lambda x: x["with_win_rate"])
    else:
        best_duo = None
        worst_duo = None

    return {
        "heatmap": heatmap,
        "best_duo": best_duo,
        "worst_duo": worst_duo,
        "players": players,
    }


def compute_hero_synergies(data):
    """For shared matches, compute hero pair win rates among friends."""
    shared = data["shared_players"]
    if shared.empty:
        return []

    # Group by match_id, get all friend hero picks on the same team
    match_groups = shared.groupby("match_id")
    pair_stats = defaultdict(lambda: {"wins": 0, "games": 0})

    for match_id, group in match_groups:
        # Only look at friends on the same team
        radiant = group[group["is_radiant"] == True]
        dire = group[group["is_radiant"] == False]

        for team in [radiant, dire]:
            if len(team) < 2:
                continue
            won = team["won"].iloc[0]
            players_in_team = list(team.itertuples())
            for i in range(len(players_in_team)):
                for j in range(i + 1, len(players_in_team)):
                    p1 = players_in_team[i]
                    p2 = players_in_team[j]
                    # Create canonical key
                    key = tuple(sorted([
                        (p1.player_name, p1.hero_name),
                        (p2.player_name, p2.hero_name),
                    ]))
                    pair_stats[key]["games"] += 1
                    if won:
                        pair_stats[key]["wins"] += 1

    synergies = []
    for (p1_info, p2_info), stats in pair_stats.items():
        if stats["games"] >= 3:  # minimum games threshold
            synergies.append({
                "player1": p1_info[0],
                "hero1": p1_info[1],
                "player2": p2_info[0],
                "hero2": p2_info[1],
                "games": stats["games"],
                "wins": stats["wins"],
                "win_rate": round(stats["wins"] / stats["games"], 4),
            })

    synergies.sort(key=lambda x: (-x["games"], -x["win_rate"]))
    return synergies


def compute_party_size_effect(data):
    """How does party size affect win rate?"""
    matches = data["match_history"]
    if "party_size" not in matches.columns:
        return []

    party_stats = matches.groupby("party_size").agg(
        games=("won", "count"),
        wins=("won", "sum"),
    ).reset_index()
    party_stats["win_rate"] = party_stats["wins"] / party_stats["games"]

    return [
        {
            "party_size": int(row["party_size"]) if pd.notna(row["party_size"]) else None,
            "games": int(row["games"]),
            "wins": int(row["wins"]),
            "win_rate": round(float(row["win_rate"]), 4),
        }
        for _, row in party_stats.iterrows()
    ]


def compute_time_patterns(data):
    """Win rate by hour of day and day of week."""
    matches = data["match_history"]

    hour_stats = matches.groupby("hour").agg(
        games=("won", "count"), wins=("won", "sum")
    ).reset_index()
    hour_stats["win_rate"] = hour_stats["wins"] / hour_stats["games"]

    dow_stats = matches.groupby("day_of_week").agg(
        games=("won", "count"), wins=("won", "sum")
    ).reset_index()
    dow_stats["win_rate"] = dow_stats["wins"] / dow_stats["games"]

    # Per-player hour stats
    player_hour = matches.groupby(["player_name", "hour"]).agg(
        games=("won", "count"), wins=("won", "sum")
    ).reset_index()
    player_hour["win_rate"] = player_hour["wins"] / player_hour["games"]

    return {
        "by_hour": hour_stats.to_dict("records"),
        "by_day_of_week": dow_stats.to_dict("records"),
        "player_by_hour": player_hour.to_dict("records"),
    }


def compute_performance_trends(data):
    """Win rate over time (monthly) per player."""
    matches = data["match_history"].copy()
    matches["year_month"] = matches["year"].astype(str) + "-" + matches["month"].astype(str).str.zfill(2)

    trends = matches.groupby(["player_name", "year_month"]).agg(
        games=("won", "count"), wins=("won", "sum")
    ).reset_index()
    trends["win_rate"] = trends["wins"] / trends["games"]
    trends = trends.sort_values(["player_name", "year_month"])

    return trends.to_dict("records")


def compute_role_profiles(data):
    """Determine each player's role tendencies based on their most-played heroes."""
    heroes_ref = data["heroes_ref"]
    heroes_per_player = data["heroes_per_player"]

    # Build hero -> roles mapping
    hero_roles = {}
    for _, h in heroes_ref.iterrows():
        roles = h.get("roles", "[]")
        if isinstance(roles, str):
            try:
                roles = json.loads(roles.replace("'", '"'))
            except Exception:
                roles = []
        hero_roles[h["id"]] = roles

    profiles = {}
    for name in PLAYERS.keys():
        player_heroes = heroes_per_player[heroes_per_player["player_name"] == name]
        # Weight roles by games played
        role_weights = defaultdict(float)
        total_games = player_heroes["games"].sum()
        for _, row in player_heroes.iterrows():
            hero_id = row["hero_id"]
            games = row["games"]
            for role in hero_roles.get(hero_id, []):
                role_weights[role] += games

        # Normalize
        if total_games > 0:
            role_weights = {r: round(w / total_games, 3) for r, w in role_weights.items()}

        profiles[name] = dict(sorted(role_weights.items(), key=lambda x: -x[1]))

    return profiles


def compute_wordcloud_insights(data):
    """Load wordcloud data and find most-said words per player."""
    wc_path = DATA_PROCESSED / "wordclouds.json"
    if not wc_path.exists():
        return {}

    with open(wc_path) as f:
        wordclouds = json.load(f)

    insights = {}
    for name, words in wordclouds.items():
        if not words:
            continue
        sorted_words = sorted(words.items(), key=lambda x: -x[1])[:20]
        insights[name] = [{"word": w, "count": c} for w, c in sorted_words]

    return insights


def generate_all_insights():
    """Generate all insights and save as a single JSON file for the frontend."""
    print("Loading processed data...")
    data = load_data()

    print("Computing player cards...")
    cards = compute_player_cards(data)

    print("Computing superlatives...")
    superlatives = compute_superlatives(data)

    print("Computing duo chemistry...")
    duo = compute_duo_chemistry(data)

    print("Computing hero synergies...")
    synergies = compute_hero_synergies(data)

    print("Computing party size effect...")
    party = compute_party_size_effect(data)

    print("Computing time patterns...")
    time_patterns = compute_time_patterns(data)

    print("Computing performance trends...")
    trends = compute_performance_trends(data)

    print("Computing role profiles...")
    roles = compute_role_profiles(data)

    print("Computing wordcloud insights...")
    wordclouds = compute_wordcloud_insights(data)

    # Compile all insights
    all_insights = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "player_cards": cards,
        "superlatives": superlatives,
        "duo_chemistry": duo,
        "hero_synergies": synergies[:100],  # top 100
        "party_size_effect": party,
        "time_patterns": time_patterns,
        "performance_trends": trends,
        "role_profiles": roles,
        "wordclouds": wordclouds,
    }

    output_path = DATA_PROCESSED / "insights.json"
    with open(output_path, "w") as f:
        json.dump(all_insights, f, indent=2, default=str)

    print(f"\nAll insights saved to {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
    return all_insights


if __name__ == "__main__":
    generate_all_insights()
```

**Step 2: Run insights generation**

Run:
```bash
uv run python -m scripts.insights
```

**Step 3: Verify output**

Run:
```bash
uv run python -c "
import json
with open('data/processed/insights.json') as f:
    data = json.load(f)
print('Keys:', list(data.keys()))
print('Players:', len(data['player_cards']))
print('Awards:', len(data['superlatives']))
print('Hero synergies:', len(data['hero_synergies']))
"
```

**Step 4: Commit**

```bash
git add scripts/insights.py
git commit -m "feat: add EDA and insights generation for all analytics categories"
```

---

## Phase 5: ML Models

### Task 6: Train win prediction and hero recommendation models

**Files:**
- Create: `scripts/model.py`

**Step 1: Create the ML model training script**

Create `scripts/model.py`:
```python
"""Train ML models for win prediction and hero recommendation."""

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder

from scripts.config import PLAYERS, DATA_PROCESSED, DATA_RAW


def build_team_features(data_processed: Path):
    """Build feature matrix from shared matches for win prediction.

    Features per match:
    - Binary: which friends are playing (11 features)
    - Hero IDs for each friend (one-hot or encoded)
    - Party size
    - Average team win rate
    - Hour of day
    """
    shared = pd.read_csv(data_processed / "shared_match_players.csv")
    profiles = pd.read_csv(data_processed / "player_profiles.csv")
    player_heroes_df = pd.read_csv(data_processed / "player_heroes.csv")

    # Player win rate lookup
    wr_lookup = dict(zip(profiles["account_id"], profiles["win_rate"]))

    # Player-hero win rate lookup
    ph_wr = {}
    for _, row in player_heroes_df.iterrows():
        ph_wr[(row["account_id"], row["hero_id"])] = row["win_rate"]

    # Group shared matches by match_id, only keep matches where friends are on same team
    match_groups = shared.groupby("match_id")

    feature_rows = []
    labels = []

    player_names = list(PLAYERS.keys())
    player_ids = list(PLAYERS.values())

    for match_id, group in match_groups:
        # Get friends on the winning/same team
        radiant_friends = group[group["is_radiant"] == True]
        dire_friends = group[group["is_radiant"] == False]

        for team_friends in [radiant_friends, dire_friends]:
            if len(team_friends) < 2:
                continue

            won = bool(team_friends["won"].iloc[0])

            features = {}

            # Which friends are in this match
            for i, pid in enumerate(player_ids):
                features[f"player_{player_names[i]}"] = int(pid in team_friends["account_id"].values)

            # Number of friends
            features["num_friends"] = len(team_friends)

            # Average win rate of friends in match
            friend_wrs = [wr_lookup.get(aid, 0.5) for aid in team_friends["account_id"]]
            features["avg_friend_wr"] = np.mean(friend_wrs)

            # Average player-hero win rate
            ph_wrs = [ph_wr.get((row.account_id, row.hero_id), 0.5) for row in team_friends.itertuples()]
            features["avg_player_hero_wr"] = np.mean(ph_wrs)

            # Hour of day
            features["hour"] = int(team_friends["hour"].iloc[0]) if pd.notna(team_friends["hour"].iloc[0]) else 12

            # Game duration as proxy for game difficulty
            features["duration"] = int(team_friends["duration"].iloc[0])

            feature_rows.append(features)
            labels.append(int(won))

    X = pd.DataFrame(feature_rows).fillna(0)
    y = np.array(labels)

    return X, y


def train_win_predictor(data_processed: Path):
    """Train a win prediction model."""
    print("Building features...")
    X, y = build_team_features(data_processed)
    print(f"  Dataset: {len(X)} samples, {X.shape[1]} features")
    print(f"  Win rate: {y.mean():.3f}")

    if len(X) < 50:
        print("  Not enough data for reliable ML. Skipping model training.")
        return None, None, None

    # Remove duration (it's a leak — you don't know duration before the game)
    X_train = X.drop(columns=["duration"], errors="ignore")

    print("Training GradientBoosting model...")
    model = GradientBoostingClassifier(
        n_estimators=100, max_depth=3, random_state=42, min_samples_leaf=5
    )

    scores = cross_val_score(model, X_train, y, cv=min(5, len(X_train) // 10 + 1), scoring="accuracy")
    print(f"  Cross-val accuracy: {scores.mean():.3f} +/- {scores.std():.3f}")

    # Train on full data
    model.fit(X_train, y)

    # Feature importances
    importances = dict(zip(X_train.columns, model.feature_importances_))
    importances = dict(sorted(importances.items(), key=lambda x: -x[1]))

    print("  Top features:")
    for feat, imp in list(importances.items())[:10]:
        print(f"    {feat}: {imp:.4f}")

    return model, importances, {
        "accuracy": round(float(scores.mean()), 4),
        "std": round(float(scores.std()), 4),
        "n_samples": len(X),
        "n_features": X_train.shape[1],
        "win_rate_baseline": round(float(y.mean()), 4),
    }


def compute_hero_recommendations(data_processed: Path):
    """For each player, compute which heroes they should pick based on:
    1. Their personal win rate on the hero
    2. Games played (experience)
    3. Synergy with common teammates' hero pools
    """
    player_heroes = pd.read_csv(data_processed / "player_heroes.csv")
    shared = pd.read_csv(data_processed / "shared_match_players.csv")

    recommendations = {}
    for name in PLAYERS.keys():
        ph = player_heroes[player_heroes["player_name"] == name]
        # Score = win_rate * log(games + 1) — balances win rate with experience
        ph = ph.copy()
        ph["score"] = ph["win_rate"] * np.log1p(ph["games"])
        top = ph.nlargest(10, "score")
        recommendations[name] = [
            {
                "hero_name": row["hero_name"],
                "hero_id": int(row["hero_id"]),
                "games": int(row["games"]),
                "wins": int(row["wins"]),
                "win_rate": round(float(row["win_rate"]), 4),
                "score": round(float(row["score"]), 3),
            }
            for _, row in top.iterrows()
        ]

    return recommendations


def generate_ml_insights():
    """Run all ML tasks and save results."""
    print("=== ML Model Training ===\n")

    model, importances, metrics = train_win_predictor(DATA_PROCESSED)

    print("\nComputing hero recommendations...")
    recommendations = compute_hero_recommendations(DATA_PROCESSED)

    results = {
        "win_predictor": {
            "metrics": metrics,
            "feature_importances": importances if importances else {},
        },
        "hero_recommendations": recommendations,
    }

    output_path = DATA_PROCESSED / "ml_insights.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nML insights saved to {output_path}")
    return results


if __name__ == "__main__":
    generate_ml_insights()
```

**Step 2: Run model training**

Run:
```bash
uv run python -m scripts.model
```

**Step 3: Verify output**

Run:
```bash
uv run python -c "
import json
with open('data/processed/ml_insights.json') as f:
    data = json.load(f)
print('Win predictor metrics:', data['win_predictor']['metrics'])
print('Hero recs for first player:', list(data['hero_recommendations'].keys())[0])
"
```

**Step 4: Commit**

```bash
git add scripts/model.py
git commit -m "feat: add ML win prediction model and hero recommendation engine"
```

---

## Phase 6: Combine All Insights for Frontend

### Task 7: Create a master insights export that merges everything

**Files:**
- Create: `scripts/export.py`

**Step 1: Create the export script**

Create `scripts/export.py`:
```python
"""Combine all insights into a single JSON payload for the playground frontend."""

import json
from scripts.config import DATA_PROCESSED


def export_all():
    """Merge insights.json and ml_insights.json into a single frontend payload."""
    with open(DATA_PROCESSED / "insights.json") as f:
        insights = json.load(f)

    ml_path = DATA_PROCESSED / "ml_insights.json"
    if ml_path.exists():
        with open(ml_path) as f:
            ml = json.load(f)
        insights["ml"] = ml
    else:
        insights["ml"] = None

    output_path = DATA_PROCESSED / "frontend_data.json"
    with open(output_path, "w") as f:
        json.dump(insights, f, indent=2, default=str)

    print(f"Frontend data exported to {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    export_all()
```

**Step 2: Run export**

Run:
```bash
uv run python -m scripts.export
```

**Step 3: Commit**

```bash
git add scripts/export.py
git commit -m "feat: add export script to combine all insights for frontend"
```

---

## Phase 7: Interactive Playground Frontend

### Task 8: Create the interactive HTML playground using the Playground skill

**Prerequisites:** `data/processed/frontend_data.json` must exist with all insights.

**Step 1: Invoke the playground skill**

Use the `playground:playground` skill to create an interactive HTML playground that:

1. Reads the data from `data/processed/frontend_data.json` (embedded as a JS const in the HTML)
2. Has these sections as tabs/pages:
   - **Group Overview**: Baseball cards for each player
   - **Superlatives & Awards**: Fun data-backed awards
   - **Duo Chemistry**: Heatmap + drill-down
   - **Hero Synergies**: Best player+hero combos
   - **Dream Team Builder**: Select 5 friends, see recommendations
   - **Performance Trends**: Time series charts
   - **Head-to-Head**: Compare any two players
   - **Time Patterns**: Win rate by hour/day
   - **Word Clouds**: Chat patterns

3. Uses Chart.js via CDN for charts
4. Dark theme (Dota 2 aesthetic)
5. All data embedded as `const DATA = {...}` at the top of the file

**Step 2: Commit the playground**

```bash
git add playground/
git commit -m "feat: add interactive Dota 2 analytics playground dashboard"
```

---

## Execution Order Summary

| Task | Phase | Description | Depends On |
|------|-------|-------------|------------|
| 1 | Setup | Init uv project + config | — |
| 2 | Scrape | API client | Task 1 |
| 3 | Scrape | Full data scraper | Task 2 |
| 4 | Process | Clean data into DataFrames | Task 3 |
| 5 | Analyze | EDA + insights generation | Task 4 |
| 6 | ML | Win prediction + hero recs | Task 4 |
| 7 | Export | Combine all insights | Tasks 5, 6 |
| 8 | Frontend | Playground dashboard | Task 7 |

Tasks 5 and 6 can run in parallel after Task 4 completes.
