"""Data structures for GhostUI activity tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union


@dataclass
class TaskRecord:
    name: str
    status: str = "running"  # "running", "completed", "failed"
    start_time: float = 0.0
    end_time: Optional[float] = None
    duration: Optional[float] = None
    error: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class ProgressRecord:
    name: str
    completed: float = 0.0
    total: float = 100.0
    unit: str = ""
    description: str = ""
    updated_at: float = 0.0


@dataclass
class MetricRecord:
    name: str
    value: Any
    unit: Optional[str] = None
    count: int = 1
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LogRecord:
    message: str
    level: str = "INFO"
    source: str = "app"
    timestamp: Union[str, datetime] = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
