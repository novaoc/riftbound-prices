from __future__ import annotations

import argparse
import sys

from rich.table import Table
from rich.panel import Panel

from .models import Listing, PriceResult
from .prices import search_prices, combine_results, group_by_grade, group_by_product_type
from .utils import format_price

__version__ = "0.1.0"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="riftbound-prices",
        description="Riftbound TCG Price Tracker — search card prices from eBay & TCGplayer",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("query", nargs="+", help="Card name, product, or search terms")
    parser.add_argument("--type", choices=["single", "sealed", "graded"], default="single",
                        help="Product type (default: single)")
    parser.add_argument("--grade", help="Filter by grade (e.g. 'PSA 10', 'BGS 9.5')")
    parser.add_argument("--condition", help="Filter by condition (e.g. 'Near Mint', 'New')")
    parser.add_argument("--max", type=int, default=20, help="Max results per source (default: 20)")
    parser.add_argument("--no-ebay", action="store_true", help="Skip eBay source")
    parser.add_argument("--no-tcgplayer", action="store_true", help="Skip TCGplayer source")
    parser.add_argument("--group-by", choices=["grade", "type", "none"], default="none",
                        help="Group results by grade or product type")

    args = parser.parse_args()

    query = " ".join(args.query)
    product_type = args.type
    grade = args.grade
    condition = args.condition
    max_results = args.max
    use_ebay = not args.no_ebay
    use_tcgplayer = not args.no_tcgplayer
    group_by = args.group_by

    print(f"\n  Searching: {query}")
    print(f"  Type: {product_type}  |  Sources: ", end="")
    if use_ebay:
        print("eBay ", end="")
    if use_tcgplayer:
        print("TCGplayer ", end="")
    print()
    if grade:
        print(f"  Grade filter: {grade}")
    if condition:
        print(f"  Condition filter: {condition}")
    print()

    results = search_prices(
        query=query,
        product_type=product_type,
        grade=grade,
        max_results=max_results,
        use_ebay=use_ebay,
        use_tcgplayer=use_tcgplayer,
        condition=condition,
    )

    if not results or all(r.sample_size == 0 for r in results):
        print("  No results found. Try a different query.")
        return

    combined = combine_results(results)

    if group_by == "grade":
        groups = group_by_grade(combined.listings)
        for grade_name, grp in groups.items():
            _render_table(grp, title=f"Grade: {grade_name}")
    elif group_by == "type":
        groups = group_by_product_type(combined.listings)
        for type_name, grp in groups.items():
            _render_table(grp, title=f"Type: {type_name}")
    else:
        _render_table(combined, title="Results")

    _render_summary(combined)


def _render_table(result: PriceResult, title: str = "Results") -> None:
    if not result.listings:
        return

    table = Table(
        title=title,
        show_header=True,
        header_style="bold magenta",
        title_justify="left",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Price", justify="right", width=10)
    table.add_column("Title", width=55, overflow="fold")
    table.add_column("Source", width=12)
    table.add_column("Condition", width=14)
    table.add_column("Grade", width=10)

    for i, listing in enumerate(result.listings[:30], 1):
        price_str = format_price(listing.price, listing.currency)
        table.add_row(
            str(i),
            price_str,
            listing.title[:80],
            listing.source,
            listing.condition[:20] if listing.condition else "-",
            listing.grade or "-",
        )

    print(table)


def _render_summary(result: PriceResult) -> None:
    if not result.prices:
        return

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()

    summary.add_row("Listings:", str(result.sample_size))
    summary.add_row("Average:", format_price(result.average_price))
    summary.add_row("Median:", format_price(result.median_price))
    summary.add_row("Low:", format_price(result.min_price))
    summary.add_row("High:", format_price(result.max_price))

    panel = Panel(summary, title="[bold]Price Summary[/bold]")
    print(panel)


if __name__ == "__main__":
    main()
