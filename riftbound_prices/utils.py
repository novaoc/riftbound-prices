from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional, Any

CONFIG_DIR = Path.home() / ".config" / "riftbound-prices"
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_DIR = CONFIG_DIR / "cache"
CACHE_TTL = 3600  # 1 hour


def load_config() -> dict[str, Any]:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
    return CACHE_DIR / f"{safe}.json"


def cache_get(key: str) -> Optional[Any]:
    path = get_cache_path(key)
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > CACHE_TTL:
        return None
    with open(path) as f:
        return json.load(f)


def cache_set(key: str, data: Any) -> None:
    path = get_cache_path(key)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def format_price(amount: float, currency: str = "USD") -> str:
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
    sym = symbols.get(currency, "$")
    if currency == "JPY":
        return f"{sym}{int(amount)}"
    return f"{sym}{amount:.2f}"
