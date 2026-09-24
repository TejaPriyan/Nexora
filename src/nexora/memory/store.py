"""Memory store for Recall, backed by LocalStore with automatic secret redaction."""

from __future__ import annotations

import re
import threading
import time
from typing import Any, Dict, List, Optional, Sequence

from ..security import SecretRedactor
from ..storage import LocalStore
from .models import MemoryItem

_STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or",
    "is", "are", "was", "were", "what", "where", "how", "why", "who", "which",
    "my", "your", "our", "their", "it", "this", "that", "these", "those",
}


def _tokenize(text: str) -> List[str]:
    """Tokenize string into normalized lowercase alphanumeric terms."""
    return [w for w in re.findall(r"\w+", text.lower()) if w not in _STOP_WORDS]


class MemoryStore:
    """Thread-safe persistent memory store utilizing LocalStore.

    Every saved memory item is scrubbed through SecretRedactor to ensure
    sensitive credentials or secrets are never persisted in plain text.
    Operates strictly locally with zero external network calls.
    """

    NAMESPACE = "recall_memories"

    def __init__(
        self,
        local_store: Optional[LocalStore] = None,
        *,
        redactor: Optional[SecretRedactor] = None,
    ) -> None:
        self._store = local_store or LocalStore(name="nexora_memory")
        self._redactor = redactor or SecretRedactor()
        self._lock = threading.RLock()

    @property
    def redactor(self) -> SecretRedactor:
        return self._redactor

    def remember(
        self,
        key_or_content: str,
        value: Any = None,
        *,
        tags: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        now: Optional[float] = None,
    ) -> MemoryItem:
        """Store a structured memory item with automatic secret redaction."""
        with self._lock:
            t = now if now is not None else time.time()
            clean_tags = [str(tag).lower() for tag in (tags or [])]

            # Redact dictionary fields
            clean_value = (
                self._redactor.redact(value)
                if isinstance(value, dict)
                else value
            )
            clean_meta = (
                self._redactor.redact(metadata)
                if isinstance(metadata, dict)
                else (metadata or {})
            )

            # Redact string content if it matches sensitive patterns
            content_str = str(key_or_content)
            for sensitive_key in self._redactor._extra | {
                "password", "secret", "token", "api_key", "credential", "private_key"
            }:
                # Pattern matches key=value or key: value
                pattern = rf"(?i)\b({re.escape(sensitive_key)})\s*[:=]\s*([^\s,]+)"
                content_str = re.sub(pattern, rf"\1: ***REDACTED***", content_str)

            # Formulate unique ID
            item_id = str(key_or_content)

            item = MemoryItem(
                id=item_id,
                content=content_str,
                value=clean_value,
                tags=clean_tags,
                metadata=clean_meta,
                timestamp=t,
            )

            self._store.set(item.id, item.to_dict(), namespace=self.NAMESPACE)
            return item

    def get(self, key: str) -> Optional[MemoryItem]:
        """Retrieve a specific memory item by key."""
        with self._lock:
            data = self._store.get(key, default=None, namespace=self.NAMESPACE)
            if data is None:
                return None
            return MemoryItem.from_dict(data)

    def search(
        self,
        query: str,
        *,
        tags: Optional[Sequence[str]] = None,
        limit: int = 10,
    ) -> List[MemoryItem]:
        """Search memory items matching query keywords and optional tags."""
        with self._lock:
            query_tokens = set(_tokenize(query))
            tag_filters = {t.lower() for t in (tags or [])}

            results: List[Tuple[float, MemoryItem]] = []

            for key, data in self._store.items(namespace=self.NAMESPACE):
                item = MemoryItem.from_dict(data)

                # Tag filtering
                if tag_filters and not tag_filters.intersection(set(item.tags)):
                    continue

                # Search scoring
                score = 0.0
                content_lower = item.content.lower()
                id_lower = item.id.lower()

                # Exact query substring
                if query.lower() in content_lower or query.lower() in id_lower:
                    score += 10.0

                # Token matching
                matched_tokens = 0
                for token in query_tokens:
                    if token in id_lower:
                        score += 3.0
                        matched_tokens += 1
                    elif token in content_lower:
                        score += 2.0
                        matched_tokens += 1
                    elif any(token in t for t in item.tags):
                        score += 2.5
                        matched_tokens += 1
                    elif item.value is not None and token in str(item.value).lower():
                        score += 1.0
                        matched_tokens += 1

                # If any tokens matched or no query tokens (tag-only query)
                if score > 0 or (not query_tokens and tag_filters):
                    results.append((score, item))

            # Sort descending by score, then recency
            results.sort(key=lambda r: (r[0], r[1].timestamp), reverse=True)
            return [item for _, item in results[:limit]]

    def ask(self, question: str) -> Optional[str]:
        """Deterministic, local retrieval answering based on remembered context.

        Requires no external AI API: searches top matching memories and formats
        a direct answer from the matching memory content or value.
        """
        matches = self.search(question, limit=3)
        if not matches:
            return None

        top = matches[0]
        # If value is available and structured, format value with content
        if top.value is not None:
            return f"{top.content}: {top.value}"
        return top.content

    def forget(self, key: str) -> bool:
        """Remove a memory item by key. Returns True if existed."""
        with self._lock:
            if self._store.get(key, default=None, namespace=self.NAMESPACE) is not None:
                self._store.delete(key, namespace=self.NAMESPACE)
                return True
            return False

    def timeline(
        self,
        *,
        limit: Optional[int] = None,
        reverse: bool = False,
    ) -> List[MemoryItem]:
        """Return all memories ordered chronologically by timestamp."""
        with self._lock:
            items = [
                MemoryItem.from_dict(data)
                for _, data in self._store.items(namespace=self.NAMESPACE)
            ]
            items.sort(key=lambda m: m.timestamp, reverse=reverse)
            if limit is not None:
                return items[:limit]
            return items

    def clear(self) -> None:
        """Clear all stored memories."""
        with self._lock:
            keys = self._store.keys(namespace=self.NAMESPACE)
            for k in keys:
                self._store.delete(k, namespace=self.NAMESPACE)
