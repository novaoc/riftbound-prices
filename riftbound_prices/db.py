from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import TrackedCard, FRESHNESS_SECONDS

DB_DIR = Path.home() / ".cache" / "riftbound-prices"
DB_PATH = DB_DIR / "cards.db"


def _get_conn() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                set_name TEXT NOT NULL DEFAULT '',
                rarity TEXT NOT NULL DEFAULT '',
                product_type TEXT NOT NULL DEFAULT 'single',
                tcgplayer_id INTEGER,
                url TEXT NOT NULL DEFAULT '',
                last_price REAL NOT NULL DEFAULT 0.0,
                last_updated TEXT,
                is_foil INTEGER NOT NULL DEFAULT 0,
                UNIQUE(name, set_name, is_foil)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                price REAL NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cards_set ON cards(set_name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_card ON price_history(card_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_recorded ON price_history(recorded_at)
        """)


def add_card(card: TrackedCard) -> int:
    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT OR REPLACE INTO cards
               (name, set_name, rarity, product_type, tcgplayer_id, url,
                last_price, last_updated, is_foil)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                card.name, card.set_name, card.rarity, card.product_type,
                card.tcgplayer_id, card.url, card.last_price,
                card.last_updated.isoformat() if card.last_updated else None,
                int(card.is_foil),
            ),
        )
        return cur.lastrowid or 0


def update_card_price(card_id: int, price: float) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute(
            "UPDATE cards SET last_price = ?, last_updated = ? WHERE id = ?",
            (price, now, card_id),
        )
        conn.execute(
            "INSERT INTO price_history (card_id, price, recorded_at) VALUES (?, ?, ?)",
            (card_id, price, now),
        )


def get_all_cards() -> list[TrackedCard]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM cards ORDER BY set_name, name"
        ).fetchall()
    return [_row_to_card(r) for r in rows]


def get_stale_cards() -> list[TrackedCard]:
    cutoff = FRESHNESS_SECONDS
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM cards
               WHERE last_updated IS NULL
                  OR (strftime('%s','now') - strftime('%s', last_updated)) > ?""",
            (cutoff,),
        ).fetchall()
    return [_row_to_card(r) for r in rows]


def get_card_by_name(name: str, set_name: str = "", is_foil: bool = False) -> Optional[TrackedCard]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM cards WHERE name = ? AND set_name = ? AND is_foil = ?",
            (name, set_name, int(is_foil)),
        ).fetchone()
    return _row_to_card(row) if row else None


def get_card_by_id(card_id: int) -> Optional[TrackedCard]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    return _row_to_card(row) if row else None


def remove_card(card_id: int) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))


def remove_card_by_name(name: str, set_name: str = "", is_foil: bool = False) -> None:
    with _get_conn() as conn:
        conn.execute(
            "DELETE FROM cards WHERE name = ? AND set_name = ? AND is_foil = ?",
            (name, set_name, int(is_foil)),
        )


def card_count() -> int:
    with _get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]


def _row_to_card(row: sqlite3.Row) -> TrackedCard:
    last_updated = None
    if row["last_updated"]:
        last_updated = datetime.fromisoformat(row["last_updated"])
    return TrackedCard(
        id=row["id"],
        name=row["name"],
        set_name=row["set_name"],
        rarity=row["rarity"],
        product_type=row["product_type"],
        tcgplayer_id=row["tcgplayer_id"],
        url=row["url"],
        last_price=row["last_price"],
        last_updated=last_updated,
        is_foil=bool(row["is_foil"]),
    )
