from __future__ import annotations

import re
import urllib.parse
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from ..models import Listing, PriceResult
from ..utils import cache_get, cache_set
from .base import PriceSource

SEARCH_URL = "https://www.tcgplayer.com/search/riftbound-league-of-legends-trading-card-game/product"


class TCGPlayerSource(PriceSource):
    name = "TCGplayer"

    def __init__(self) -> None:
        self.client = httpx.Client(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
            timeout=15,
        )

    def search(
        self,
        query: str,
        product_type: str = "single",
        grade: Optional[str] = None,
        max_results: int = 20,
    ) -> PriceResult:
        search_query = self._build_query(query, product_type, grade)
        cache_key = f"tcgp:{search_query}:{max_results}"
        cached = cache_get(cache_key)
        if cached:
            return PriceResult(**cached)

        listings = self._fetch(search_query, max_results)
        result = PriceResult(query=query, source=self.name, listings=listings)
        cache_set(cache_key, {
            "query": result.query,
            "source": result.source,
            "listings": [l.__dict__ for l in result.listings],
        })
        return result

    def _build_query(self, query: str, product_type: str, grade: Optional[str]) -> str:
        parts = [query]
        if product_type == "sealed":
            parts.append("sealed")
        if grade:
            parts.append(grade)
        return " ".join(parts)

    def _fetch(self, query: str, max_results: int) -> list[Listing]:
        params = {
            "q": query,
            "view": "grid",
            "productLineName": "riftbound-league-of-legends-trading-card-game",
        }
        url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"

        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            return self._parse_search(resp.text)
        except Exception as e:
            print(f"  [TCGplayer error] {e}")
            return []

    def _parse_search(self, html: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings: list[Listing] = []

        cards = soup.select(
            "a[class*='product'], "
            "[class*='search-result'], "
            "[class*='listing'], "
            "article, "
            ".product-listing"
        )
        if not cards:
            cards = soup.find_all("a", href=re.compile(r"/product/\d+"))

        seen = set()
        for card in cards:
            try:
                title_el = card.select_one(
                    "[class*='name'], "
                    "[class*='title'], "
                    "[class*='card-name'], "
                    "h3, h2, h4"
                )
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not title or title in seen:
                    continue

                price_el = card.select_one(
                    "[class*='price'], "
                    "[class*='market'], "
                    "[data-price], "
                    "[class*='listing-price']"
                )
                if not price_el:
                    continue
                price_text = price_el.get_text(strip=True)

                url = card.get("href", "") if card.name == "a" else ""
                if not url:
                    link = card.select_one("a[href]")
                    if link:
                        url = link.get("href", "")
                if url and not url.startswith("http"):
                    url = f"https://www.tcgplayer.com{url}"

                price = self._parse_price(price_text)
                if price <= 0:
                    continue

                seen.add(title)

                grade = self._detect_grade(title)

                listings.append(Listing(
                    title=title,
                    price=price,
                    currency="USD",
                    condition="",
                    url=url,
                    source=self.name,
                    grade=grade,
                    product_type=self._detect_type(title),
                ))
            except Exception:
                continue

        return listings

    @staticmethod
    def _parse_price(text: str) -> float:
        cleaned = re.sub(r"[^\d.,]", "", text)
        if " - " in text:
            cleaned = cleaned.split(" - ")[0]
        cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _detect_grade(title: str) -> Optional[str]:
        patterns = {
            "PSA 10": r"PSA\s*10\b",
            "PSA 9": r"PSA\s*9\b(?!\.)",
            "PSA 8": r"PSA\s*8\b",
            "PSA 7": r"PSA\s*7\b",
            "BGS 10": r"BGS\s*10\b",
            "BGS 9.5": r"BGS\s*9\.5\b",
            "BGS 9": r"BGS\s*9\b(?!\.)",
            "CGC 10": r"CGC\s*10\b",
            "CGC 9.5": r"CGC\s*9\.5\b",
            "CGC 9": r"CGC\s*9\b(?!\.)",
        }
        for grade, pattern in patterns.items():
            if re.search(pattern, title, re.IGNORECASE):
                return grade
        return None

    @staticmethod
    def _detect_type(title: str) -> str:
        t = title.lower()
        if any(kw in t for kw in ("case", "cases")):
            return "case"
        if any(kw in t for kw in ("booster box", "display box", "boosterbox")):
            return "booster_box"
        if any(kw in t for kw in ("psa", "bgs", "cgc")):
            return "graded"
        if any(kw in t for kw in ("sealed", "factory sealed", "unopened", "pack")):
            return "sealed"
        return "single"

    def close(self) -> None:
        self.client.close()
