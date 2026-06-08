from __future__ import annotations

import argparse
import sys
import os
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

__version__ = "0.1.0"
from .models import Listing, PriceResult
from .prices import search_prices, combine_results, group_by_grade, group_by_product_type
from .utils import format_price, load_config, save_config

console = Console()
out = Console()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="riftbound-prices",
        description="Riftbound TCG Price Tracker — search card prices from eBay & TCGplayer",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command")

    # --- search ---
    search = sub.add_parser("search", help="Search for card/ product prices")
    search.add_argument("query", nargs="+", help="Card name, product, or search terms")
    search.add_argument("--type", choices=["single", "sealed", "graded"], default="single",
                        help="Product type (default: single)")
    search.add_argument("--grade", help="Filter by grade (e.g. 'PSA 10', 'BGS 9.5')")
    search.add_argument("--condition", help="Filter by condition (e.g. 'Near Mint', 'New')")
    search.add_argument("--max", type=int, default=20, help="Max results per source (default: 20)")
    search.add_argument("--no-ebay", action="store_true", help="Skip eBay source")
    search.add_argument("--no-tcgplayer", action="store_true", help="Skip TCGplayer source")
    search.add_argument("--group-by", choices=["grade", "type", "none"], default="none",
                        help="Group results by grade or product type")

    # --- config ---
    config_parser = sub.add_parser("config", help="Configure settings")
    config_parser.add_argument("--set-ebay-app-id", help="Set eBay App ID (Client ID)")
    config_parser.add_argument("--show", action="store_true", help="Show current config")

    args = parser.parse_args()

    if args.command == "config":
        handle_config(args)
        return
    elif args.command == "search":
        handle_search(args)
    else:
        if hasattr(args, "query") and args.query:
            handle_search(args)
        else:
            parser.print_help()


def handle_config(args: argparse.Namespace) -> None:
    config = load_config()

    if args.set_ebay_app_id:
        config["ebay_app_id"] = args.set_ebay_app_id
        save_config(config)
        out.print("[green]✓[/green] eBay App ID saved to ~/.config/riftbound-prices/config.json")
        return

    if args.show:
        table = Table("Key", "Value", title="Configuration")
        table.add_row("ebay_app_id", config.get("ebay_app_id", "Not set"))
        out.print(table)
        return

    out.print("[yellow]Usage:[/yellow] riftbound-prices config --set-ebay-app-id YOUR_APP_ID")
    out.print("       riftbound-prices config --show")


def handle_search(args: argparse.Namespace) -> None:
    query = " ".join(args.query)
    product_type = args.type
    grade = args.grade
    condition = args.condition
    max_results = args.max
    use_ebay = not args.no_ebay
    use_tcgplayer = not args.no_tcgplayer
    group_by = args.group_by

    out.print(f"\n[bold]Searching:[/bold] {query}")
    out.print(f"  Product type: {product_type}  |  Sources: ", end="")
    if use_ebay:
        out.print("eBay ", end="")
    if use_tcgplayer:
        out.print("TCGplayer ", end="")
    out.print()
    if grade:
        out.print(f"  Grade filter: {grade}")
    if condition:
        out.print(f"  Condition filter: {condition}")
    out.print()

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
        out.print("[yellow]No results found. Try a different query or check your config.[/yellow]")
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
    table.add_column("Title", width=50, overflow="fold")
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

    out.print(table)


def _render_summary(result: PriceResult) -> None:
    if not result.prices:
        return

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()

    summary.add_row("Results:", str(result.sample_size))
    summary.add_row("Average:", format_price(result.average_price))
    summary.add_row("Median:", format_price(result.median_price))
    summary.add_row("Low:", format_price(result.min_price))
    summary.add_row("High:", format_price(result.max_price))

    panel = Panel(summary, title="[bold]Price Summary[/bold]")
    out.print(panel)


if __name__ == "__main__":
    main()
