from __future__ import annotations

import re
import urllib.parse
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from ..models import Listing, PriceResult
from ..utils import cache_get, cache_set
from .base import PriceSource

SEARCH_URL = "https://www.ebay.com/sch/i.html"


class EbaySource(PriceSource):
    name = "eBay"

    def __init__(self) -> None:
        self.client = httpx.Client(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
            timeout=20,
        )

    def search(
        self,
        query: str,
        product_type: str = "single",
        grade: Optional[str] = None,
        max_results: int = 20,
    ) -> PriceResult:
        keywords = self._build_keywords(query, product_type, grade)
        cache_key = f"ebay:{keywords}:{max_results}"
        cached = cache_get(cache_key)
        if cached:
            return PriceResult(**cached)

        listings = self._fetch(keywords, max_results)
        result = PriceResult(query=query, source=self.name, listings=listings)
        cache_set(cache_key, {
            "query": result.query,
            "source": result.source,
            "listings": [l.__dict__ for l in result.listings],
        })
        return result

    def _build_keywords(self, query: str, product_type: str, grade: Optional[str]) -> str:
        parts = ["riftbound", query]
        if grade:
            parts.append(grade)
        return " ".join(parts)

    def _fetch(self, keywords: str, max_results: int) -> list[Listing]:
        params = {
            "_nkw": keywords,
            "LH_Sold": "1",
            "LH_Complete": "1",
            "_ipg": str(min(max_results, 240)),
            "LH_TitleDesc": "0",
            "rt": "nc",
        }
        url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"

        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            return self._parse_listings(resp.text)
        except Exception as e:
            print(f"  [eBay scrape error] {e}")
            return []

    def _parse_listings(self, html: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings: list[Listing] = []

        items = soup.select("li.s-item, .s-item__wrapper")
        if not items:
            items = soup.select("[data-viewport]")

        for item in items:
            try:
                title_el = item.select_one(".s-item__title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not title or title in ("Shop on eBay",):
                    continue

                price_el = item.select_one(".s-item__price")
                if not price_el:
                    continue
                price_text = price_el.get_text(strip=True)

                link_el = item.select_one(".s-item__link")
                url = ""
                if link_el and link_el.get("href"):
                    url = link_el["href"]
                elif link_el:
                    parent = link_el.find_parent("a")
                    if parent and parent.get("href"):
                        url = parent["href"]

                subtitle_el = item.select_one(
                    ".s-item__subtitle, .s-item__itemSubtitle, "
                    ".SECONDARY_INFO"
                )
                condition = subtitle_el.get_text(strip=True) if subtitle_el else ""

                price = self._parse_price(price_text)
                if price <= 0:
                    continue

                grade = self._detect_grade(title)

                listings.append(Listing(
                    title=title,
                    price=price,
                    currency="USD",
                    condition=condition,
                    url=url,
                    source=self.name,
                    date_sold="",
                    is_auction=False,
                    grade=grade,
                    product_type=self._detect_type(title),
                ))
            except Exception:
                continue

        return listings

    @staticmethod
    def _parse_price(text: str) -> float:
        cleaned = re.sub(r"[^\d.,]", "", text)
        if " to " in text:
            cleaned = cleaned.split(" to ")[0]
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
