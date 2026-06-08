from __future__ import annotations

import re
from typing import Optional

import httpx

from ..models import Listing, PriceResult
from ..utils import load_config, cache_get, cache_set
from .base import PriceSource

FINDING_API = "https://svcs.ebay.com/services/search/FindingService/v1"


class EbaySource(PriceSource):
    name = "eBay"

    def __init__(self) -> None:
        config = load_config()
        app_id = config.get("ebay_app_id", "")
        if not app_id:
            app_id = _prompt_for_app_id()
        self.app_id = app_id

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
        if product_type == "sealed":
            parts.append("sealed")
        return " ".join(parts)

    def _fetch(self, keywords: str, max_results: int) -> list[Listing]:
        params = {
            "OPERATION-NAME": "findItemsByKeywords",
            "SERVICE-VERSION": "1.0.0",
            "SECURITY-APPNAME": self.app_id,
            "GLOBAL-ID": "EBAY-US",
            "RESPONSE-DATA-FORMAT": "JSON",
            "REST-PAYLOAD": "",
            "keywords": keywords,
            "paginationInput.entriesPerPage": max_results,
            "sortOrder": "EndTimeSoonest",
            "itemFilter(0).name": "SoldItemsOnly",
            "itemFilter(0).value": "true",
        }

        try:
            resp = httpx.get(FINDING_API, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  [eBay API error] {e}")
            return []

        return self._parse_response(data)

    def _parse_response(self, data: dict) -> list[Listing]:
        listings: list[Listing] = []
        items = (
            data.get("findItemsByKeywordsResponse", [{}])[0]
            .get("searchResult", [{}])[0]
            .get("item", [])
        )

        for item in items:
            try:
                title = item.get("title", [""])[0]
                price_str = (
                    item.get("sellingStatus", [{}])[0]
                    .get("currentPrice", [{}])[0]
                    .get("__value__", "0")
                )
                currency = (
                    item.get("sellingStatus", [{}])[0]
                    .get("currentPrice", [{}])[0]
                    .get("@currencyId", "USD")
                )
                condition = (
                    item.get("condition", [{}])[0]
                    .get("conditionDisplayName", [""])[0]
                )
                url = item.get("viewItemURL", [""])[0]
                listing_type = (
                    item.get("sellingStatus", [{}])[0]
                    .get("listingType", [""])[0]
                )
                end_time = item.get("listingInfo", [{}])[0].get("endTime", [""])[0]

                price = float(price_str) if price_str else 0.0
                if price <= 0:
                    continue

                grade = self._detect_grade(title)

                listings.append(Listing(
                    title=title,
                    price=price,
                    currency=currency,
                    condition=condition,
                    url=url,
                    source=self.name,
                    date_sold=end_time,
                    is_auction=(listing_type == "Auction"),
                    grade=grade,
                    product_type=self._detect_type(title),
                ))
            except (IndexError, KeyError, ValueError, TypeError):
                continue

        return listings

    @staticmethod
    def _detect_grade(title: str) -> Optional[str]:
        patterns = {
            "PSA 10": r"PSA\s*10",
            "PSA 9": r"PSA\s*9",
            "PSA 8": r"PSA\s*8",
            "PSA 7": r"PSA\s*7",
            "BGS 10": r"BGS\s*10",
            "BGS 9.5": r"BGS\s*9\.5",
            "BGS 9": r"BGS\s*9",
            "CGC 10": r"CGC\s*10",
            "CGC 9.5": r"CGC\s*9\.5",
            "CGC 9": r"CGC\s*9",
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
        if any(kw in t for kw in ("sealed", "factory sealed", "unopened")):
            return "sealed"
        return "single"


def _prompt_for_app_id() -> str:
    msg = (
        "\n  eBay App ID not found!\n"
        "  1. Go to https://developer.ebay.com → Create App → get App ID (Client ID)\n"
        "  2. Run:  riftbound-prices config --set-ebay-app-id YOUR_APP_ID\n"
        "  Or set env:  export EBAY_APP_ID=your_app_id\n"
    )
    print(msg)
    import os
    env_id = os.environ.get("EBAY_APP_ID", "")
    if env_id:
        print(f"  [using EBAY_APP_ID from environment]")
        return env_id
    return ""
