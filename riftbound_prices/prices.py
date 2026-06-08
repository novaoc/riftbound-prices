from __future__ import annotations

import asyncio
import random
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from .db import add_card, get_all_cards, get_stale_cards, update_card_price, card_count
from .models import Listing, PriceResult, TrackedCard
from .sources.base import PriceSource
from .sources.tcgplayer import TCGPlayerSource


def get_sources(use_ebay: bool = True, use_tcgplayer: bool = True) -> list[PriceSource]:
    sources: list[PriceSource] = []
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
        grade: PriceResult(query=f"Grade: {grade}", source="", listings=lsts)
        for grade, lsts in groups.items()
    }


def group_by_product_type(listings: list[Listing]) -> dict[str, PriceResult]:
    groups: dict[str, list[Listing]] = defaultdict(list)
    for l in listings:
        groups[l.product_type].append(l)

    return {
        ptype: PriceResult(query=f"Type: {ptype}", source="", listings=lsts)
        for ptype, lsts in groups.items()
    }


def discover_all_cards() -> int:
    source = TCGPlayerSource()
    try:
        listings = asyncio.run(source.discover_all())
    except Exception as e:
        print(f"  Discover error: {e}")
        return 0

    count = 0
    now = datetime.now(timezone.utc)
    for listing in listings:
        card = TrackedCard(
            name=listing.title,
            set_name=getattr(listing, "set_name", "") or "",
            rarity=listing.condition or "",
            product_type=listing.product_type,
            url=listing.url,
            last_price=listing.price,
            last_updated=now,
            is_foil="foil" in listing.title.lower(),
        )
        try:
            add_card(card)
            count += 1
        except Exception:
            continue

    return count


def update_tracked_cards() -> tuple[int, int]:
    stale = get_stale_cards()
    if not stale:
        return 0, 0

    source = TCGPlayerSource()
    updated = 0
    errors = 0

    for card in stale:
        price = asyncio.run(source.fetch_card_price(card.tcgplayer_id or 0))
        if price is not None and price > 0:
            update_card_price(card.id, price)
            updated += 1
        else:
            errors += 1

        import time
        time.sleep(random.uniform(1.0, 2.5))

    return updated, errors


def card_summary() -> list[dict]:
    cards = get_all_cards()
    stale_count = len([c for c in cards if c.is_stale()])
    return [
        {"total": len(cards), "stale": stale_count, "fresh": len(cards) - stale_count}
    ]
