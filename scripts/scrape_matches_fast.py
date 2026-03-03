"""Fast concurrent downloader for shared match details."""

import json
import concurrent.futures
from pathlib import Path

from scripts.config import PLAYERS, DATA_RAW, OPENDOTA_API_KEY, API_BASE

import requests

SESSION = requests.Session()


def download_match(match_id: int) -> tuple[int, bool]:
    """Download a single match detail."""
    cache_path = DATA_RAW / "matches" / f"{match_id}.json"
    if cache_path.exists():
        return match_id, True

    try:
        params = {}
        if OPENDOTA_API_KEY:
            params["api_key"] = OPENDOTA_API_KEY
        resp = SESSION.get(f"{API_BASE}/matches/{match_id}", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data))
        return match_id, True
    except Exception as e:
        return match_id, False


def main():
    from collections import Counter

    # Find shared matches
    player_matches = {}
    for name, account_id in PLAYERS.items():
        f = DATA_RAW / "players" / str(account_id) / "matches.json"
        if f.exists():
            matches = json.loads(f.read_text())
            player_matches[account_id] = {m["match_id"] for m in matches}

    counter = Counter()
    for aid, mids in player_matches.items():
        for mid in mids:
            counter[mid] += 1

    shared_ids = sorted(mid for mid, c in counter.items() if c >= 2)

    # Filter to only those not yet downloaded
    remaining = [mid for mid in shared_ids if not (DATA_RAW / "matches" / f"{mid}.json").exists()]
    print(f"Total shared matches: {len(shared_ids)}")
    print(f"Already downloaded: {len(shared_ids) - len(remaining)}")
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("All done!")
        return

    # Download concurrently with 20 workers
    downloaded = 0
    failed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(download_match, mid): mid for mid in remaining}
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            match_id, success = future.result()
            if success:
                downloaded += 1
            else:
                failed += 1
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{len(remaining)} (downloaded: {downloaded}, failed: {failed})")

    print(f"\nDone! Downloaded: {downloaded}, Failed: {failed}")


if __name__ == "__main__":
    main()
