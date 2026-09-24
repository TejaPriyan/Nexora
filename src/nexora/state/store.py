"""NEXORA state store: a small observable key/value container used by App,
Runtime, and (in later milestones) modules such as Timeline and Ghost."""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from ..events import EventBus


class State:
    """A namespaced, observable state container.

    Every mutation emits a ``state.changed`` (or ``state.deleted``) event on
    the provided EventBus, if any, so other modules can react without
    polling.
    """

    def __init__(self, bus: Optional[EventBus] = None, *, source: str = "state") -> None:
        self._data: Dict[str, Any] = {}
        self._bus = bus
        self._source = source
        self._lock = threading.RLock()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            old = self._data.get(key)
            self._data[key] = value
        if self._bus is not None and old != value:
            self._bus.emit(
                "state.changed",
                source=self._source,
                payload={"key": key, "old": old, "new": value},
            )

    def update(self, values: Dict[str, Any]) -> None:
        for key, value in values.items():
            self.set(key, value)

    def delete(self, key: str) -> None:
        with self._lock:
            existed = key in self._data
            old = self._data.pop(key, None)
        if existed and self._bus is not None:
            self._bus.emit(
                "state.deleted",
                source=self._source,
                payload={"key": key, "old": old},
            )

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._data
