from __future__ import annotations

from collections import defaultdict
from typing import Optional

from .models import Listing, PriceResult
from .sources.base import PriceSource
from .sources.ebay import EbaySource
from .sources.tcgplayer import TCGPlayerSource


def get_sources(use_ebay: bool = True, use_tcgplayer: bool = True) -> list[PriceSource]:
    sources: list[PriceSource] = []
    if use_ebay:
        sources.append(EbaySource())
    if use_tcgplayer:
        sources.append(TCGPlayerSource())
    return sources


def search_prices(
    query: str,
    product_type: str = "single",
    grade: Optional[str] = None,
    max_results: int = 20,
    use_ebay: bool = True,
    use_tcgplayer: bool = True,
    condition: Optional[str] = None,
) -> list[PriceResult]:
    sources = get_sources(use_ebay, use_tcgplayer)
    results: list[PriceResult] = []

    for source in sources:
        result = source.search(
            query=query,
            product_type=product_type,
            grade=grade,
            max_results=max_results,
        )
        if condition:
            result.listings = [
                l for l in result.listings
                if condition.lower() in l.condition.lower()
            ]
        results.append(result)

    return results


def combine_results(results: list[PriceResult]) -> PriceResult:
    all_listings: list[Listing] = []
    for r in results:
        all_listings.extend(r.listings)

    return PriceResult(
        query=results[0].query if results else "",
        source="+".join(r.source for r in results),
        listings=all_listings,
    )


def group_by_grade(listings: list[Listing]) -> dict[str, PriceResult]:
    groups: dict[str, list[Listing]] = defaultdict(list)
    for l in listings:
        key = l.grade or "Ungraded"
        groups[key].append(l)

    return {
        grade: PriceResult(
            query=f"Grade: {grade}",
            source="",
            listings=lsts,
        )
        for grade, lsts in groups.items()
    }


def group_by_product_type(listings: list[Listing]) -> dict[str, PriceResult]:
    groups: dict[str, list[Listing]] = defaultdict(list)
    for l in listings:
        groups[l.product_type].append(l)

    return {
        ptype: PriceResult(
            query=f"Type: {ptype}",
            source="",
            listings=lsts,
        )
        for ptype, lsts in groups.items()
    }
