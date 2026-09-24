"""NEXORA Event System.

Every module in NEXORA communicates through a central, in-process event
bus. Events are the one integration point every other subsystem (state,
plugins, runtime, and eventually ghost/world/memory/etc.) is built on top
of, per the NEXORA architecture (see docs/ARCHITECTURE.md).
"""

from __future__ import annotations

import fnmatch
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

EventHandler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """A single event flowing through the NEXORA event bus."""

    type: str
    source: str = "unknown"
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EventBus:
    """A thread-safe, synchronous pub/sub event bus.

    Handlers run synchronously, in subscription order, on the thread that
    called ``emit``. That keeps behavior predictable and easy to test.
    Subscriptions may be an exact event type ("task.started"), a glob
    pattern ("task.*"), or the wildcard "*" for every event.
    """

    def __init__(self, *, history_limit: int = 1000) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._lock = threading.RLock()
        self._history: List[Event] = []
        self._history_limit = history_limit

    def on(
        self, event_type: str, handler: Optional[EventHandler] = None
    ):
        """Subscribe ``handler`` to ``event_type``.

        Can be used as a plain call (``bus.on("x", handler)``) or as a
        decorator (``@bus.on("x")``) when ``handler`` is omitted.
        """

        if handler is None:

            def decorator(fn: EventHandler) -> EventHandler:
                self.on(event_type, fn)
                return fn

            return decorator

        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)
        return handler

    def off(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def emit(
        self,
        type: str,
        *,
        source: str = "unknown",
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        event = Event(
            type=type,
            source=source,
            payload=payload or {},
            metadata=metadata or {},
        )
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_limit:
                self._history.pop(0)
            patterns = list(self._handlers.items())

        for pattern, handlers in patterns:
            if pattern == type or pattern == "*" or fnmatch.fnmatch(type, pattern):
                for handler in list(handlers):
                    handler(event)
        return event

    def history(self, event_type: Optional[str] = None) -> List[Event]:
        with self._lock:
            if event_type is None:
                return list(self._history)
            return [e for e in self._history if e.type == event_type]

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()
