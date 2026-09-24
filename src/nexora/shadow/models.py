"""Data structures for Shadow (observability) module."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class FunctionProfile:
    """Execution timing and reliability profile for an observed function."""

    name: str
    call_count: int = 0
    total_duration: float = 0.0
    min_duration: float = float("inf")
    max_duration: float = 0.0
    error_count: int = 0
    last_called: float = field(default_factory=time.time)

    @property
    def avg_duration(self) -> float:
        return self.total_duration / self.call_count if self.call_count > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "call_count": self.call_count,
            "total_duration": self.total_duration,
            "min_duration": self.min_duration if self.min_duration != float("inf") else 0.0,
            "max_duration": self.max_duration,
            "avg_duration": self.avg_duration,
            "error_count": self.error_count,
            "last_called": self.last_called,
        }


@dataclass
class ObservedEvent:
    """Observational record of events flowing on the bus."""

    event_type: str
    count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    sources: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "sources": sorted(self.sources),
        }


@dataclass(frozen=True)
class ObservedError:
    """Genuinely observed application error with traceback details."""

    error_type: str
    message: str
    source: str
    timestamp: float = field(default_factory=time.time)
    traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp,
            "traceback": self.traceback,
        }


@dataclass(frozen=True)
class DependencyLink:
    """Observed call or interaction link between components."""

    caller: str
    callee: str
    call_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "caller": self.caller,
            "callee": self.callee,
            "call_count": self.call_count,
        }


@dataclass
class ObservabilitySnapshot:
    """Complete point-in-time observational model of application execution."""

    timestamp: float
    total_events: int
    total_function_calls: int
    total_errors: int
    functions: Dict[str, Dict[str, Any]]
    event_counts: Dict[str, int]
    errors: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
