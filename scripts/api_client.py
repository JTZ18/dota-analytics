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
