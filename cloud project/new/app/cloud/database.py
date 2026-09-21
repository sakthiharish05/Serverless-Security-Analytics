"""
DynamoDB-compatible NoSQL database abstraction.

Provides a unified interface for storing and querying structured data,
with implementations for both local SQLite and AWS DynamoDB.
"""

import json
import sqlite3
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class DatabaseClient(ABC):
    """Abstract base class for DynamoDB-like NoSQL database."""

    @abstractmethod
    def put_item(self, table: str, item: Dict[str, Any]) -> bool:
        """Store an item in the table."""
        pass

    @abstractmethod
    def get_item(self, table: str, key: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Get an item by its primary key."""
        pass

    @abstractmethod
    def query(self, table: str, filters: Optional[Dict[str, Any]] = None,
              limit: int = 100) -> List[Dict[str, Any]]:
        """Query items with optional filters. Returns list of matching items."""
        pass

    @abstractmethod
    def update_item(self, table: str, key: Dict[str, str],
                    updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update specific attributes of an item."""
        pass

    @abstractmethod
    def delete_item(self, table: str, key: Dict[str, str]) -> bool:
        """Delete an item by its primary key."""
        pass

    @abstractmethod
    def scan(self, table: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Scan all items in a table (expensive, use sparingly)."""
        pass

    @abstractmethod
    def get_item_count(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get count of items matching filters."""
        pass


class LocalDatabaseClient(DatabaseClient):
    """
    Local SQLite implementation of DynamoDB-like storage.

    Uses SQLite with JSON columns to mimic DynamoDB's schemaless item storage.
    Thread-safe with connection pooling per thread.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        """Initialize database tables."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                table_name TEXT NOT NULL,
                item_id TEXT NOT NULL,
                data JSON NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (table_name, item_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_table
            ON items(table_name)
        """)
        conn.commit()

    def put_item(self, table: str, item: Dict[str, Any]) -> bool:
        """Store an item in SQLite."""
        item_id = item.get("id", item.get("pk", ""))
        if not item_id:
            return False

        now = datetime.utcnow().isoformat() + "Z"
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO items (table_name, item_id, data, created_at, updated_at)
               VALUES (?, ?, ?, COALESCE(
                   (SELECT created_at FROM items WHERE table_name = ? AND item_id = ?),
                   ?
               ), ?)""",
            (table, item_id, json.dumps(item), table, item_id, now, now),
        )
        conn.commit()
        return True

    def get_item(self, table: str, key: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Get an item from SQLite by primary key."""
        item_id = key.get("id", key.get("pk", ""))
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data FROM items WHERE table_name = ? AND item_id = ?",
            (table, item_id),
        ).fetchone()

        if row:
            return json.loads(row["data"])
        return None

    def query(self, table: str, filters: Optional[Dict[str, Any]] = None,
              limit: int = 100) -> List[Dict[str, Any]]:
        """Query items from SQLite with optional filters."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT data FROM items WHERE table_name = ? ORDER BY updated_at DESC LIMIT ?",
            (table, limit),
        ).fetchall()

        items = [json.loads(row["data"]) for row in rows]

        # Apply in-memory filters (simulates DynamoDB filter expressions)
        if filters:
            filtered = []
            for item in items:
                match = True
                for key, value in filters.items():
                    if item.get(key) != value:
                        match = False
                        break
                if match:
                    filtered.append(item)
            return filtered

        return items

    def update_item(self, table: str, key: Dict[str, str],
                    updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an item in SQLite."""
        existing = self.get_item(table, key)
        if not existing:
            return None

        existing.update(updates)
        existing["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self.put_item(table, existing)
        return existing

    def delete_item(self, table: str, key: Dict[str, str]) -> bool:
        """Delete an item from SQLite."""
        item_id = key.get("id", key.get("pk", ""))
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM items WHERE table_name = ? AND item_id = ?",
            (table, item_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def scan(self, table: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Scan all items in a table."""
        return self.query(table, limit=limit)

    def get_item_count(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get count of items in a table."""
        if filters:
            return len(self.query(table, filters=filters, limit=10000))

        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM items WHERE table_name = ?",
            (table,),
        ).fetchone()
        return row["cnt"] if row else 0


class DynamoDBClient(DatabaseClient):
    """
    AWS DynamoDB implementation of NoSQL database.

    Uses boto3 to interact with real DynamoDB tables.
    Requires valid AWS credentials and pre-created tables.
    """

    def __init__(self, region: str = "us-east-1"):
        import boto3
        self.dynamodb = boto3.resource("dynamodb", region_name=region)

    def _get_table(self, table_name: str):
        """Get a DynamoDB table resource."""
        return self.dynamodb.Table(table_name)

    def put_item(self, table: str, item: Dict[str, Any]) -> bool:
        """Store an item in DynamoDB."""
        try:
            self._get_table(table).put_item(Item=item)
            return True
        except Exception as e:
            print(f"DynamoDB put_item error: {e}")
            return False

    def get_item(self, table: str, key: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Get an item from DynamoDB by primary key."""
        try:
            response = self._get_table(table).get_item(Key=key)
            return response.get("Item")
        except Exception:
            return None

    def query(self, table: str, filters: Optional[Dict[str, Any]] = None,
              limit: int = 100) -> List[Dict[str, Any]]:
        """Query items from DynamoDB with filters via scan + filter."""
        try:
            from boto3.dynamodb.conditions import Attr

            scan_kwargs = {"Limit": limit}
            if filters:
                filter_expr = None
                for key, value in filters.items():
                    condition = Attr(key).eq(value)
                    filter_expr = condition if filter_expr is None else (filter_expr & condition)
                if filter_expr:
                    scan_kwargs["FilterExpression"] = filter_expr

            response = self._get_table(table).scan(**scan_kwargs)
            return response.get("Items", [])
        except Exception as e:
            print(f"DynamoDB query error: {e}")
            return []

    def update_item(self, table: str, key: Dict[str, str],
                    updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an item in DynamoDB."""
        try:
            update_parts = []
            expr_values = {}
            expr_names = {}

            for i, (attr, value) in enumerate(updates.items()):
                placeholder = f":val{i}"
                name_placeholder = f"#attr{i}"
                update_parts.append(f"{name_placeholder} = {placeholder}")
                expr_values[placeholder] = value
                expr_names[name_placeholder] = attr

            response = self._get_table(table).update_item(
                Key=key,
                UpdateExpression="SET " + ", ".join(update_parts),
                ExpressionAttributeValues=expr_values,
                ExpressionAttributeNames=expr_names,
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except Exception as e:
            print(f"DynamoDB update_item error: {e}")
            return None

    def delete_item(self, table: str, key: Dict[str, str]) -> bool:
        """Delete an item from DynamoDB."""
        try:
            self._get_table(table).delete_item(Key=key)
            return True
        except Exception:
            return False

    def scan(self, table: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Scan all items in a DynamoDB table."""
        try:
            response = self._get_table(table).scan(Limit=limit)
            return response.get("Items", [])
        except Exception:
            return []

    def get_item_count(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get approximate item count from DynamoDB."""
        if filters:
            return len(self.query(table, filters=filters, limit=10000))
        try:
            response = self._get_table(table).scan(Select="COUNT")
            return response.get("Count", 0)
        except Exception:
            return 0
