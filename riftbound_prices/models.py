from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


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
    product_type: str = "single"  # single, sealed, graded


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
