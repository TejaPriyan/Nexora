"""Data structures for TimeLoop (timeline/rewind) module."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class Snapshot:
    """A point-in-time state checkpoint with redacted sensitive fields."""

    id: str
    label: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "data": dict(self.data),
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


@dataclass
class DiffResult:
    """Detailed structural diff comparing two state snapshots."""

    from_id: str
    to_id: str
    added: Dict[str, Any] = field(default_factory=dict)
    removed: Dict[str, Any] = field(default_factory=dict)
    changed: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)

    @property
    def identical(self) -> bool:
        return not self.added and not self.removed and not self.changed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_id": self.from_id,
            "to_id": self.to_id,
            "identical": self.identical,
            "added": self.added,
            "removed": self.removed,
            "changed": {k: {"old": v[0], "new": v[1]} for k, v in self.changed.items()},
        }
