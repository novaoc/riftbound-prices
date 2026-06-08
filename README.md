# Riftbound Prices

A CLI tool to track **Riftbound TCG** (League of Legends TCG) card prices from TCGplayer — with persistent tracking, 24h caching, and intelligent rate limiting.

## Features

- **Search cards** — search by card name with prices from TCGplayer
- **Track cards** — add cards to a persistent tracking database (SQLite)
- **Discover all cards** — auto-discover every Riftbound card across all sets
- **24h cache** — prices are cached for 24 hours to avoid unnecessary requests
- **Smart throttling** — random delays and rotating user agents to avoid being blocked
- **Price history** — every price update is recorded in the database
- **Pretty output** — formatted tables with market prices

## Quick Start

```bash
pip install -r requirements.txt
pip install -e .

export PATH="$HOME/Library/Python/3.9/bin:$PATH"  # if needed

riftbound-prices status
```

## Commands

```
riftbound-prices search "Ahri"
  └─ Search TCGplayer for current card prices

riftbound-prices track "Ahri - Inquisitive" --set Origins
  └─ Add a card to your tracking database

riftbound-prices list
  └─ Show all tracked cards with prices and freshness status

riftbound-prices update
  └─ Refresh prices for cards that are >24h old

riftbound-prices discover
  └─ Auto-discover ALL Riftbound cards from TCGplayer

riftbound-prices untrack "Card Name"
  └─ Remove a card from tracking

riftbound-prices status
  └─ Show database stats
```

## How It Works

```
riftbound-prices search "Ahri"
  └── TCGplayer (Playwright) → renders search page, extracts market prices
  └── Cache stored at ~/.cache/riftbound-prices/ (24h TTL)

riftbound-prices discover
  └── Iterates all Riftbound sets on TCGplayer
  └── Adds every card to the SQLite database

riftbound-prices update
  └── Checks each tracked card's last_updated timestamp
  └── Only fetches prices for cards >24h old
```

## Data Storage

- **Database**: `~/.cache/riftbound-prices/cards.db` (SQLite)
- **Cache**: `~/.cache/riftbound-prices/*.json` (search result cache, 24h TTL)
- **History**: Every price update is recorded in the `price_history` table

## Requirements

- Python 3.9+
- Playwright (installed automatically with `pip install`)
- Chromium browser (auto-downloaded by Playwright on first run)
