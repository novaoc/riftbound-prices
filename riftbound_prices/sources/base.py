from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..models import PriceResult


class PriceSource(ABC):
    name: str = ""

    @abstractmethod
    def search(
        self,
        query: str,
        product_type: str = "single",
        grade: Optional[str] = None,
        max_results: int = 20,
    ) -> PriceResult:
        ...
