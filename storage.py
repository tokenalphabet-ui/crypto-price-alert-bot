"""SQLite storage for alerts."""

from __future__ import annotations

import sqlite3

from alerts import Alert

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    coin_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    kind TEXT NOT NULL,
    value REAL NOT NULL,
    base_price REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

COLUMNS = "id, chat_id, coin_id, symbol, kind, value, base_price"


class Storage:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def add(self, chat_id: int, coin_id: str, symbol: str, kind: str,
            value: float, base_price: float) -> int:
        cur = self.conn.execute(
            "INSERT INTO alerts (chat_id, coin_id, symbol, kind, value, base_price) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, coin_id, symbol, kind, value, base_price),
        )
        self.conn.commit()
        return cur.lastrowid

    def _rows(self, sql: str, params: tuple = ()) -> list[Alert]:
        return [Alert(*row) for row in self.conn.execute(sql, params)]

    def all(self) -> list[Alert]:
        return self._rows(f"SELECT {COLUMNS} FROM alerts ORDER BY id")

    def for_chat(self, chat_id: int) -> list[Alert]:
        return self._rows(
            f"SELECT {COLUMNS} FROM alerts WHERE chat_id = ? ORDER BY id", (chat_id,)
        )

    def count_for_chat(self, chat_id: int) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE chat_id = ?", (chat_id,)
        ).fetchone()[0]

    def delete(self, chat_id: int, alert_id: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM alerts WHERE id = ? AND chat_id = ?", (alert_id, chat_id)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def clear(self, chat_id: int) -> int:
        cur = self.conn.execute("DELETE FROM alerts WHERE chat_id = ?", (chat_id,))
        self.conn.commit()
        return cur.rowcount

    def remove(self, alert_id: int) -> None:
        self.conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
