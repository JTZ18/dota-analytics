import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

API_BASE = "https://api.opendota.com/api"

# Load API key from .env if present
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

OPENDOTA_API_KEY = os.environ.get("OPENDOTA_API_KEY")
REQUEST_DELAY = 0.02 if OPENDOTA_API_KEY else 1.1  # 3000/min with key, 60/min without

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
