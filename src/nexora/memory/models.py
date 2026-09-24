"""Data structures for Recall (memory) module."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MemoryItem:
    """A persistent, structured memory entry."""

    id: str
    content: str
    value: Any = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "value": self.value,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryItem:
        return cls(
            id=data["id"],
            content=data["content"],
            value=data.get("value"),
            tags=list(data.get("tags", [])),
            metadata=dict(data.get("metadata", {})),
            timestamp=float(data.get("timestamp", 0.0)),
        )
