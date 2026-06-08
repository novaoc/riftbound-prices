# Riftbound Prices

A CLI tool to track **Riftbound TCG** (League of Legends TCG) card prices from your device — no server needed.

## Features

- **Single cards** — search by card name and set (e.g. "Ahri Origins", "Yasuo Spiritforged")
- **Sealed product** — booster boxes, cases, displays (e.g. "Spiritforged Booster Box")
- **Graded cards** — PSA, BGS, CGC grades detected automatically from listing titles
- **Multiple sources** — eBay sold listings + TCGplayer market prices
- **Cached results** — avoids re-fetching the same data within 1 hour
- **Pretty terminal output** — tables with average/median/min/max prices

## Quick Start

```bash
# Install
pip install -r requirements.txt
pip install -e .

# Set up eBay API (free, required for eBay source)
riftbound-prices config --set-ebay-app-id YOUR_EBAY_APP_ID

# Search for a card
riftbound-prices search "Ahri" --type single
```

## Search Examples

```bash
# Single cards
riftbound-prices search "Ahri Origins"
riftbound-prices search "Yasuo" --condition "Near Mint"

# Sealed product
riftbound-prices search "Spiritforged Booster Box" --type sealed
riftbound-prices search "Origins Case" --type sealed

# Graded cards
riftbound-prices search "Ahri" --type graded
riftbound-prices search "Yasuo" --grade "PSA 10"

# Group results by grade or product type
riftbound-prices search "Ahri" --group-by grade
riftbound-prices search "Riftbound" --type sealed --group-by type

# Use only one source
riftbound-prices search "Ahri" --no-tcgplayer
riftbound-prices search "Ahri" --no-ebay
```

## Setup

### 1. eBay API (for sold listing prices)

1. Go to [ebay.com/developer](https://developer.ebay.com/)
2. Sign in and create a **New Application** (free)
3. Copy your **App ID** (also called Client ID)
4. Configure it:

```bash
riftbound-prices config --set-ebay-app-id YOUR_APP_ID
```

Or set an environment variable:

```bash
export EBAY_APP_ID=your_app_id
```

### 2. TCGplayer

TCGplayer uses public page scraping — no API key needed.

## How It Works

```
User runs: riftbound-prices search "Ahri Origins"
  ├── eBay API → sold listing prices (real transactions)
  ├── TCGplayer → current market prices
  └── CLI output → table + summary stats
```

Data is cached locally at `~/.config/riftbound-prices/cache/` for 1 hour.

## Project

```
riftbound-prices/
├── riftbound_prices/
│   ├── cli.py          # CLI entry point
│   ├── prices.py       # Price aggregation
│   ├── models.py       # Data models
│   ├── utils.py        # Caching, config, formatting
│   └── sources/
│       ├── ebay.py     # eBay Finding API
│       └── tcgplayer.py # TCGplayer scraper
├── setup.py
├── requirements.txt
└── README.md
```
