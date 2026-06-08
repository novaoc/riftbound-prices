from __future__ import annotations

import argparse

from rich.table import Table
from rich.panel import Panel
from rich import print

from .db import (
    add_card,
    card_count,
    get_all_cards,
    get_card_by_name,
    init_db,
    remove_card_by_name,
)
from .models import PriceResult, TrackedCard
from .prices import (
    combine_results,
    discover_all_cards,
    group_by_grade,
    group_by_product_type,
    search_prices,
    update_tracked_cards,
)
from .utils import format_price

__version__ = "0.2.0"


def main() -> None:
    init_db()

    parser = argparse.ArgumentParser(
        prog="riftbound-prices",
        description="Riftbound TCG Price Tracker — track card prices from TCGplayer",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command")

    search_parser = sub.add_parser("search", help="Search for card prices")
    search_parser.add_argument("query", nargs="+", help="Card name or search terms")
    search_parser.add_argument("--type", choices=["single", "sealed", "graded"], default="single")
    search_parser.add_argument("--grade", help="Filter by grade (e.g. 'PSA 10')")
    search_parser.add_argument("--condition", help="Filter by condition (e.g. 'Near Mint')")
    search_parser.add_argument("--max", type=int, default=20, help="Max results per source")
    search_parser.add_argument("--group-by", choices=["grade", "type", "none"], default="none")

    track_parser = sub.add_parser("track", help="Add a card to the tracking list")
    track_parser.add_argument("name", help="Card name")
    track_parser.add_argument("--set", "-s", dest="set_name", default="", help="Set name")
    track_parser.add_argument("--rarity", "-r", default="", help="Rarity")
    track_parser.add_argument("--foil", action="store_true", help="Foil version")

    untrack_parser = sub.add_parser("untrack", help="Remove a card from tracking")
    untrack_parser.add_argument("name", help="Card name")
    untrack_parser.add_argument("--set", "-s", dest="set_name", default="")

    sub.add_parser("list", help="Show all tracked cards and their prices")

    sub.add_parser("update", help="Update prices for stale tracked cards")

    sub.add_parser("discover", help="Discover all Riftbound cards from TCGplayer")

    sub.add_parser("status", help="Show database status")

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args)
    elif args.command == "track":
        cmd_track(args)
    elif args.command == "untrack":
        cmd_untrack(args)
    elif args.command == "list":
        cmd_list()
    elif args.command == "update":
        cmd_update()
    elif args.command == "discover":
        cmd_discover()
    elif args.command == "status":
        cmd_status()
    else:
        parser.print_help()


def cmd_search(args: argparse.Namespace) -> None:
    query = " ".join(args.query)
    print(f"\n  Searching: {query}")
    print(f"  Type: {args.type}")
    if args.grade:
        print(f"  Grade: {args.grade}")
    if args.condition:
        print(f"  Condition: {args.condition}")
    print()

    results = search_prices(
        query=query,
        product_type=args.type,
        grade=args.grade,
        max_results=args.max,
        condition=args.condition,
    )

    if not results or all(r.sample_size == 0 for r in results):
        print("  No results found. Try a different query.")
        return

    combined = combine_results(results)

    if args.group_by == "grade":
        groups = group_by_grade(combined.listings)
        for grade_name, grp in groups.items():
            _render_table(grp, title=f"Grade: {grade_name}")
    elif args.group_by == "type":
        groups = group_by_product_type(combined.listings)
        for type_name, grp in groups.items():
            _render_table(grp, title=f"Type: {type_name}")
    else:
        _render_table(combined, title="Results")

    _render_summary(combined)


def cmd_track(args: argparse.Namespace) -> None:
    existing = get_card_by_name(args.name, args.set_name, args.foil)
    if existing:
        print(f"  Already tracking '{args.name}'")
        return

    card = TrackedCard(
        name=args.name,
        set_name=args.set_name or "",
        rarity=args.rarity or "",
        product_type="single",
        is_foil=args.foil,
    )
    card_id = add_card(card)
    print(f"  Added '{args.name}' to tracking (ID: {card_id})")


def cmd_untrack(args: argparse.Namespace) -> None:
    remove_card_by_name(args.name, args.set_name)
    print(f"  Removed '{args.name}' from tracking")


def cmd_list() -> None:
    cards = get_all_cards()
    if not cards:
        print("  No cards tracked yet. Use 'riftbound-prices discover' or 'riftbound-prices track'")
        return

    table = Table(title=f"Tracked Cards ({len(cards)})", show_header=True, header_style="bold green", safe_box=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Card", width=35)
    table.add_column("Set", width=20)
    table.add_column("Price", justify="right", width=10)
    table.add_column("Updated", width=20)
    table.add_column("Status", width=10)

    for i, card in enumerate(cards, 1):
        price_str = format_price(card.last_price) if card.last_price else "-"
        updated = card.last_updated.strftime("%Y-%m-%d %H:%M") if card.last_updated else "-"
        status = "FRESH" if not card.is_stale() else "STALE"
        status_style = "green" if status == "FRESH" else "yellow"

        table.add_row(
            str(i),
            card.name,
            card.set_name or "-",
            price_str,
            updated,
            f"[{status_style}]{status}[/{status_style}]",
        )

    print(table)
    print(f"\n  Total: {len(cards)} cards tracked")
    stale = len([c for c in cards if c.is_stale()])
    fresh = len(cards) - stale
    print(f"  Fresh: {fresh}  |  Stale: {stale}")
    if stale > 0:
        print(f"  Run 'riftbound-prices update' to refresh stale prices")


def cmd_update() -> None:
    print("  Checking for stale cards...")
    updated, errors = update_tracked_cards()
    if updated == 0 and errors == 0:
        print("  All cards are fresh! (updated within 24h)")
    else:
        print(f"  Updated: {updated}  |  Errors: {errors}")


def cmd_discover() -> None:
    print("  Discovering all Riftbound cards from TCGplayer...")
    print("  This will take a minute (loading each set page)")
    count = discover_all_cards()
    total = card_count()
    print(f"\n  Added {count} new cards to database")
    print(f"  Total cards in database: {total}")


def cmd_status() -> None:
    total = card_count()
    print(f"\n  Database: ~/.cache/riftbound-prices/cards.db")
    print(f"  Cards tracked: {total}")
    if total > 0:
        cards = get_all_cards()
        stale = len([c for c in cards if c.is_stale()])
        print(f"  Fresh: {total - stale}  |  Stale: {stale}  |  TTL: 24h")
    print(f"  Cache: ~/.cache/riftbound-prices/ (json files, 24h TTL)")


def _render_table(result: PriceResult, title: str = "Results") -> None:
    if not result.listings:
        return

    table = Table(
        title=title,
        show_header=True,
        header_style="bold magenta",
        title_justify="left",
        safe_box=True,
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
