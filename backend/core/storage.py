"""Storage abstraction and SQLite implementation."""
from abc import ABC, abstractmethod
from pathlib import Path
import json
import sqlite3
from typing import Any


class StorageBackend(ABC):
    """Define the persistence contract used by the API and workers."""

    @abstractmethod
    def list_transactions(self, month: str | None = None, query: str = "") -> list[dict[str, Any]]: ...

    @abstractmethod
    def save_transaction(self, transaction: dict[str, Any]) -> dict[str, Any]: ...


class SQLiteStorage(StorageBackend):
    """Persist the single-user ledger in SQLite with parameterized queries."""

    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self):
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY, amount REAL NOT NULL, currency TEXT NOT NULL,
                    merchant TEXT NOT NULL, merchant_raw TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '', classified INTEGER NOT NULL DEFAULT 0,
                    payment_mode TEXT NOT NULL, source TEXT NOT NULL, bank TEXT NOT NULL DEFAULT '',
                    email_message_id TEXT UNIQUE, date TEXT NOT NULL, ts INTEGER NOT NULL,
                    deleted_at TEXT, parse_failed INTEGER NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS budgets (category TEXT PRIMARY KEY, monthly_limit REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS goals (id TEXT PRIMARY KEY, name TEXT NOT NULL, target REAL NOT NULL, saved REAL NOT NULL, emoji TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS merchant_rules (merchant_key TEXT PRIMARY KEY, category TEXT NOT NULL, confirmations INTEGER NOT NULL);
            """)

    def list_transactions(self, month=None, query=""):
        clauses = ["deleted_at IS NULL"]
        params: list[Any] = []
        if month:
            clauses.append("date LIKE ?")
            params.append(f"{month}-%")
        if query:
            clauses.append("(merchant LIKE ? OR category LIKE ? OR notes LIKE ?)")
            needle = f"%{query}%"
            params.extend([needle, needle, needle])
        with self._connect() as db:
            rows = db.execute(f"SELECT * FROM transactions WHERE {' AND '.join(clauses)} ORDER BY ts DESC", params).fetchall()
        return [self._row(row) for row in rows]

    def save_transaction(self, transaction):
        fields = ["id", "amount", "currency", "merchant", "merchant_raw", "category", "classified", "payment_mode", "source", "bank", "email_message_id", "date", "ts", "deleted_at", "parse_failed", "notes"]
        values = [transaction.get(field) for field in fields]
        with self._connect() as db:
            db.execute(f"INSERT OR REPLACE INTO transactions ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", values)
        return transaction

    def classify(self, transaction_id, category):
        with self._connect() as db:
            db.execute("UPDATE transactions SET category = ?, classified = 1 WHERE id = ?", (category, transaction_id))
            row = db.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        return self._row(row) if row else None

    def delete_transaction(self, transaction_id):
        with self._connect() as db:
            db.execute("UPDATE transactions SET deleted_at = datetime('now') WHERE id = ?", (transaction_id,))

    def budgets(self):
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT category, monthly_limit FROM budgets ORDER BY category")]

    def save_budget(self, category, monthly_limit):
        with self._connect() as db:
            db.execute("INSERT INTO budgets(category, monthly_limit) VALUES(?, ?) ON CONFLICT(category) DO UPDATE SET monthly_limit=excluded.monthly_limit", (category, monthly_limit))

    def goals(self):
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM goals ORDER BY name")]

    def save_goal(self, goal):
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO goals(id,name,target,saved,emoji) VALUES(?,?,?,?,?)", tuple(goal[field] for field in ("id", "name", "target", "saved", "emoji")))
        return goal

    def delete_goal(self, goal_id):
        with self._connect() as db:
            db.execute("DELETE FROM goals WHERE id = ?", (goal_id,))

    def summary(self, month):
        transactions = self.list_transactions(month)
        income = sum(item["amount"] for item in transactions if item["amount"] > 0)
        expense = sum(-item["amount"] for item in transactions if item["amount"] < 0)
        categories = {}
        for item in transactions:
            if item["amount"] < 0:
                categories[item["category"] or "Other"] = categories.get(item["category"] or "Other", 0) + -item["amount"]
        return {"income": income, "expense": expense, "balance": income - expense, "entries": len(transactions), "categories": categories}

    @staticmethod
    def _row(row):
        item = dict(row)
        item["classified"] = bool(item["classified"])
        item["parse_failed"] = bool(item["parse_failed"])
        return item


def create_storage(path: str) -> StorageBackend:
    """Create the configured persistence adapter."""
    return SQLiteStorage(path)
