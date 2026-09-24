"""Recall (memory) plugin for NEXORA."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional, Sequence

from ..plugins.base import Plugin
from .models import MemoryItem
from .store import MemoryStore

if TYPE_CHECKING:
    from ..app import App
    from ..events import Event


class MemoryPlugin(Plugin):
    """Recall: persistent, structured application memory plugin.

    Provides `remember()`, `search()`, `ask()`, `forget()`, and `timeline()`
    backed by `LocalStore` and scrubbed by `SecretRedactor`.
    Operates strictly locally without any network dependencies.
    """

    name: ClassVar[str] = "memory"
    requires_extra: ClassVar[Optional[str]] = None
    milestone: ClassVar[str] = "M4"

    def __init__(
        self,
        app: "App",
        *,
        store: Optional[MemoryStore] = None,
    ) -> None:
        super().__init__(app)
        self._store = store or MemoryStore()
        self._registered = False
        self._started = False
        self._unsubscribers: List[Callable[[], None]] = []

    @property
    def store(self) -> MemoryStore:
        return self._store

    # --- Lifecycle Hooks ---

    def on_register(self) -> None:
        if self._registered:
            return
        self._registered = True
        self._subscribe_events()

    def on_start(self) -> None:
        self._started = True

    def on_stop(self) -> None:
        self._started = False

    # --- Event Subscriptions ---

    def _subscribe_events(self) -> None:
        bus = self.app.bus
        self._sub(bus, "memory.remember", self._on_remember_event)
        self._sub(bus, "memory.forget", self._on_forget_event)
        self._sub(bus, "memory.clear", self._on_clear_event)

    def _sub(self, bus: Any, event_type: str, handler: Callable[[Any], None]) -> None:
        h = bus.on(event_type, handler)
        self._unsubscribers.append(lambda: bus.off(event_type, h))

    def _on_remember_event(self, event: "Event") -> None:
        p = event.payload
        key = p.get("key") or p.get("content")
        if key:
            self.remember(
                key,
                value=p.get("value"),
                tags=p.get("tags"),
                metadata=p.get("metadata"),
            )

    def _on_forget_event(self, event: "Event") -> None:
        key = event.payload.get("key") or event.payload.get("id")
        if key:
            self.forget(key)

    def _on_clear_event(self, event: "Event") -> None:
        self.clear()

    # --- Public API ---

    def remember(
        self,
        key_or_content: str,
        value: Any = None,
        *,
        tags: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        now: Optional[float] = None,
    ) -> MemoryItem:
        """Persist a memory item and emit `memory.remembered` on EventBus."""
        item = self._store.remember(
            key_or_content,
            value=value,
            tags=tags,
            metadata=metadata,
            now=now,
        )
        self.app.bus.emit(
            "memory.remembered",
            source="memory",
            payload={
                "id": item.id,
                "tags": item.tags,
                "timestamp": item.timestamp,
            },
        )
        return item

    def get(self, key: str) -> Optional[MemoryItem]:
        """Retrieve a memory item by key."""
        return self._store.get(key)

    def search(
        self,
        query: str,
        *,
        tags: Optional[Sequence[str]] = None,
        limit: int = 10,
    ) -> List[MemoryItem]:
        """Search memory items by query and tags."""
        return self._store.search(query, tags=tags, limit=limit)

    def ask(self, question: str) -> Optional[str]:
        """Query stored memories for a relevant answer without external APIs."""
        return self._store.ask(question)

    def forget(self, key: str) -> bool:
        """Remove a memory item and emit `memory.forgotten` on EventBus."""
        existed = self._store.forget(key)
        if existed:
            self.app.bus.emit(
                "memory.forgotten",
                source="memory",
                payload={"id": key},
            )
        return existed

    def timeline(
        self,
        *,
        limit: Optional[int] = None,
        reverse: bool = False,
    ) -> List[MemoryItem]:
        """Retrieve memories in chronological order."""
        return self._store.timeline(limit=limit, reverse=reverse)

    def clear(self) -> None:
        """Clear all memories and emit `memory.cleared` on EventBus."""
        self._store.clear()
        self.app.bus.emit("memory.cleared", source="memory", payload={})


# Alias
Recall = MemoryPlugin
