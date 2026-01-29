"""
Persistent docstore implementation using SQLite for FAISS parent document retriever.

This module provides a persistent storage solution for parent documents,
replacing the InMemoryStore to ensure data persistence across restarts.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Iterator
from langchain_core.stores import BaseStore
from django_app_rag.logging import get_logger_loguru

logger = get_logger_loguru(__name__)


class SQLiteDocStore(BaseStore[str, str]):
    """
    A persistent document store using SQLite.

    This store implements the LangChain BaseStore interface and provides
    persistent storage for parent documents in the FAISS parent document retriever.
    """

    def __init__(self, db_path: str):
        """
        Initialize the SQLite docstore.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"SQLiteDocStore initialized at {self.db_path}")

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS docstore (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_key ON docstore(key)
            """)
            conn.commit()

    def mget(self, keys: Sequence[str]) -> List[Optional[str]]:
        """
        Get multiple values by their keys.

        Args:
            keys: Sequence of keys to retrieve

        Returns:
            List of values (or None if key not found)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(keys))
            query = f"SELECT key, value FROM docstore WHERE key IN ({placeholders})"
            cursor.execute(query, keys)
            results = dict(cursor.fetchall())

        return [results.get(key) for key in keys]

    def mset(self, key_value_pairs: Sequence[tuple[str, str]]) -> None:
        """
        Set multiple key-value pairs.

        Args:
            key_value_pairs: Sequence of (key, value) tuples to store
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT OR REPLACE INTO docstore (key, value) VALUES (?, ?)",
                key_value_pairs
            )
            conn.commit()
        logger.debug(f"Stored {len(key_value_pairs)} documents")

    def mdelete(self, keys: Sequence[str]) -> None:
        """
        Delete multiple keys.

        Args:
            keys: Sequence of keys to delete
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(keys))
            query = f"DELETE FROM docstore WHERE key IN ({placeholders})"
            cursor.execute(query, keys)
            conn.commit()
        logger.debug(f"Deleted {len(keys)} documents")

    def yield_keys(self, prefix: Optional[str] = None) -> Iterator[str]:
        """
        Yield all keys in the store, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys

        Yields:
            Keys in the store
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if prefix:
                query = "SELECT key FROM docstore WHERE key LIKE ?"
                cursor.execute(query, (f"{prefix}%",))
            else:
                query = "SELECT key FROM docstore"
                cursor.execute(query)

            for row in cursor:
                yield row[0]

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the docstore.

        Returns:
            Dictionary with statistics (count, size)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM docstore")
            count = cursor.fetchone()[0]

            cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
            size_bytes = cursor.fetchone()[0]

        return {
            "document_count": count,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2)
        }

    def clear(self) -> None:
        """Clear all documents from the store."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM docstore")
            conn.commit()
        logger.info("Docstore cleared")
