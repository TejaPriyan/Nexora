"""Local-first key/value storage backed by SQLite.

No network calls, no telemetry. This is the shared persistence primitive
future modules (Recall/Memory, TimeLoop/Timeline) will build on.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple

DEFAULT_DIR = Path.home() / ".nexora"


class LocalStore:
    """A tiny namespaced key/value store on top of SQLite.

    Values are JSON-encoded. Safe to use from multiple threads within one
    process (guarded by a lock); this is not a distributed store.
    """

    def __init__(self, name: str = "nexora", *, base_dir: Optional[Path] = None) -> None:
        base = base_dir or DEFAULT_DIR
        base = Path(base)
        base.mkdir(parents=True, exist_ok=True)
        self._path = base / f"{name}.sqlite3"
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kv (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (namespace, key)
            )
            """
        )
        self._conn.commit()

    @property
    def path(self) -> Path:
        return self._path

    def set(self, key: str, value: Any, *, namespace: str = "default") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO kv (namespace, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(namespace, key) DO UPDATE SET value=excluded.value",
                (namespace, key, json.dumps(value)),
            )
            self._conn.commit()

    def get(self, key: str, default: Any = None, *, namespace: str = "default") -> Any:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM kv WHERE namespace=? AND key=?",
                (namespace, key),
            ).fetchone()
        return json.loads(row[0]) if row else default

    def delete(self, key: str, *, namespace: str = "default") -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM kv WHERE namespace=? AND key=?", (namespace, key)
            )
            self._conn.commit()

    def keys(self, *, namespace: str = "default") -> List[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key FROM kv WHERE namespace=?", (namespace,)
            ).fetchall()
        return [r[0] for r in rows]

    def items(self, *, namespace: str = "default") -> Iterable[Tuple[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key, value FROM kv WHERE namespace=?", (namespace,)
            ).fetchall()
        return [(k, json.loads(v)) for k, v in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
