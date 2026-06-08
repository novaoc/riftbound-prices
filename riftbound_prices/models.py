from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

FRESHNESS_SECONDS = 86400


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Listing:
    title: str
    price: float
    currency: str = "USD"
    condition: str = ""
    url: str = ""
    source: str = ""
    date_sold: Optional[str] = None
    is_auction: bool = False
    grade: Optional[str] = None
    product_type: str = "single"


@dataclass
class PriceResult:
    query: str
    source: str
    listings: list[Listing] = field(default_factory=list)

    @property
    def sample_size(self) -> int:
        return len(self.listings)

    @property
    def prices(self) -> list[float]:
        return [l.price for l in self.listings if l.price > 0]

    @property
    def average_price(self) -> float:
        p = self.prices
        return round(sum(p) / len(p), 2) if p else 0.0

    @property
    def median_price(self) -> float:
        p = sorted(self.prices)
        n = len(p)
        if n == 0:
            return 0.0
        mid = n // 2
        if n % 2 == 0:
            return round((p[mid - 1] + p[mid]) / 2, 2)
        return round(p[mid], 2)

    @property
    def min_price(self) -> float:
        return round(min(self.prices), 2) if self.prices else 0.0

    @property
    def max_price(self) -> float:
        return round(max(self.prices), 2) if self.prices else 0.0


@dataclass
class TrackedCard:
    name: str
    set_name: str
    rarity: str = ""
    product_type: str = "single"
    tcgplayer_id: Optional[int] = None
    url: str = ""
    last_price: float = 0.0
    last_updated: Optional[datetime] = None
    is_foil: bool = False
    id: Optional[int] = None

    def is_stale(self) -> bool:
        if self.last_updated is None:
            return True
        age = (now_utc() - self.last_updated).total_seconds()
        return age > FRESHNESS_SECONDS

    @property
    def age_seconds(self) -> float:
        if self.last_updated is None:
            return float("inf")
        return (now_utc() - self.last_updated).total_seconds()

    @property
    def age_hours(self) -> float:
        return self.age_seconds / 3600
