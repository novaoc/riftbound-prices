# Riftbound Prices

A CLI tool to track **Riftbound TCG** (League of Legends TCG) card prices from your device — no server needed, no API keys required.

## Features

- **Single cards** — search by card name and set (e.g. "Ahri Origins", "Yasuo Spiritforged")
- **Sealed product** — booster boxes, cases, displays (e.g. "Spiritforged Booster Box")
- **Graded cards** — PSA, BGS, CGC grades detected automatically from listing titles
- **Multiple sources** — scrapes eBay sold listings + TCGplayer market prices (no API keys)
- **Cached results** — avoids re-fetching the same data within 1 hour
- **Pretty terminal output** — tables with average/median/min/max prices

## Quick Start

```bash
pip install -r requirements.txt
pip install -e .

riftbound-prices search "Ahri"
```

## Examples

```bash
# Single cards
riftbound-prices search "Ahri Origins"
riftbound-prices search "Yasuo" --condition "Near Mint"

# Sealed product
riftbound-prices search "Spiritforged Booster Box" --type sealed
riftbound-prices search "Origins Case" --type sealed

# Graded cards
riftbound-prices search "Ahri" --grade "PSA 10"
riftbound-prices search "Yasuo" --type graded

# Group results
riftbound-prices search "Ahri" --group-by grade
riftbound-prices search "Riftbound" --type sealed --group-by type

# Use only one source
riftbound-prices search "Ahri" --no-tcgplayer
```

## How It Works

```
riftbound-prices search "Ahri Origins"
  ├── eBay (scraped)    → sold listing prices from ebay.com
  ├── TCGplayer (scraped) → market prices from tcgplayer.com
  └── CLI output → table + summary stats
```

Data is cached at `~/.cache/riftbound-prices/` for 1 hour.

## Project

```
riftbound-prices/
├── riftbound_prices/
│   ├── cli.py          # CLI entry point
│   ├── prices.py       # Price aggregation
│   ├── models.py       # Data models
│   ├── utils.py        # Caching, formatting
│   └── sources/
│       ├── ebay.py     # eBay sold listing scraper
│       └── tcgplayer.py # TCGplayer scraper
├── setup.py
├── requirements.txt
└── README.md
```
