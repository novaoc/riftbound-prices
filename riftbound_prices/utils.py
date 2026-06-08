from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional, Any

CACHE_DIR = Path.home() / ".cache" / "riftbound-prices"
CACHE_TTL = 3600


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
        path.unlink(missing_ok=True)
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
