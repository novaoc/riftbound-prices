from __future__ import annotations

import asyncio
import random
import re
from typing import Optional

from ..models import Listing, PriceResult
from ..utils import cache_get, cache_set
from .base import PriceSource

SEARCH_BASE = "https://www.tcgplayer.com/search/riftbound-league-of-legends-trading-card-game/product"
SET_NAMES = [
    "Origins",
    "Origins: Proving Grounds",
    "Spiritforged",
    "Unleashed",
    "Vendetta",
    "Radiance",
]

_EVAL_JS = """
() => {{
    const items = [];
    const seen = new Set();
    const cards = document.querySelectorAll('section.product-card__product');
    if (!cards.length) return [];

    for (const card of cards) {{
        const nameEl = card.querySelector('span.product-card__title');
        if (!nameEl) continue;
        const name = nameEl.textContent.trim();
        if (!name || seen.has(name)) continue;

        const setEl = card.querySelector('h4.product-card__set-name');
        const set = setEl ? setEl.textContent.trim() : '';

        const rarityEl = card.querySelector('section.product-card__rarity');
        const rarity = rarityEl ? rarityEl.textContent.trim() : '';

        const priceEl = card.querySelector('.inventory__price-with-shipping');
        const marketPriceEl = card.querySelector('.product-card__market-price--value');

        let price = 0;
        let marketPrice = 0;

        if (priceEl) {{
            const cleaned = priceEl.textContent.trim().replace(/[^\\d.,]/g, '').replace(/,/g, '');
            price = parseFloat(cleaned) || 0;
        }}
        if (marketPriceEl) {{
            const cleaned = marketPriceEl.textContent.trim().replace(/[^\\d.,]/g, '').replace(/,/g, '');
            marketPrice = parseFloat(cleaned) || 0;
        }}
        if (price === 0 && marketPrice > 0) price = marketPrice;
        if (price <= 0) continue;
        seen.add(name);

        const parentLink = card.closest('a[href]');
        const href = parentLink ? parentLink.href : '';

        const t = name.toLowerCase();
        const gradeMatch = name.match(/PSA\\s*10?|BGS\\s*9?\\.?5?|CGC\\s*9?\\.?5?/i);
        const grade = gradeMatch ? gradeMatch[0].toUpperCase() : null;
        let productType = 'single';
        if (/booster|display|case/i.test(t)) productType = 'sealed';
        else if (/psa|bgs|cgc/i.test(t)) productType = 'graded';
        else if (/sleeves|playmat|accessory/i.test(t)) productType = 'accessory';

        items.push({{
            title: name,
            price: price,
            currency: 'USD',
            condition: rarity,
            url: href,
            source: 'TCGplayer',
            grade: grade,
            product_type: productType,
            set_name: set,
        }});
    }}

    return items.slice(0, {max_results});
}}
"""


class TCGPlayerSource(PriceSource):
    name = "TCGplayer"

    def search(
        self,
        query: str,
        product_type: str = "single",
        grade: Optional[str] = None,
        max_results: int = 20,
    ) -> PriceResult:
        cache_key = f"tcgp:search:{query}:{product_type}:{max_results}"
        cached = cache_get(cache_key)
        if cached:
            cached["listings"] = [Listing(**l) if isinstance(l, dict) else l for l in cached.get("listings", [])]
            return PriceResult(**cached)

        try:
            listings = asyncio.run(self._fetch_search(query, max_results))
        except Exception as e:
            print(f"  [TCGplayer error] {e}")
            listings = []

        result = PriceResult(query=query, source=self.name, listings=listings)
        cache_set(cache_key, {
            "query": result.query,
            "source": result.source,
            "listings": [l.__dict__ for l in result.listings],
        })
        return result

    async def discover_all(self) -> list[Listing]:
        all_listings: list[Listing] = []
        for set_name in SET_NAMES:
            try:
                listings = await self._fetch_search(set_name, 500)
                all_listings.extend(listings)
                await asyncio.sleep(random.uniform(2.0, 4.0))
            except Exception:
                continue
        return all_listings

    async def _fetch_search(self, query: str, max_results: int) -> list[Listing]:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=random.choice(_USER_AGENTS),
                locale="en-US",
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()

            url = f"{SEARCH_BASE}?q={query}&view=grid"
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)

            js = _EVAL_JS.format(max_results=max_results)
            raw = await page.evaluate(js)
            if not raw:
                raw = []

            await browser.close()

            keys = Listing.__dataclass_fields__
            return [Listing(**{k: v for k, v in item.items() if k in keys}) for item in raw]


_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
]
