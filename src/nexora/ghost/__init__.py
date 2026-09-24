"""GhostUI: automatic rich terminal UI derived from App and EventBus activity.

Milestone 1 of NEXORA. Automatically renders interfaces -- tasks, progress
bars, logs, metrics, tables, errors, and status -- purely from App and
EventBus activity using `rich`.
"""

from .plugin import GhostPlugin, GhostUI
from .records import LogRecord, MetricRecord, ProgressRecord, TaskRecord

STATUS = "implemented"

__all__ = [
    "GhostPlugin",
    "GhostUI",
    "TaskRecord",
    "ProgressRecord",
    "MetricRecord",
    "LogRecord",
    "STATUS",
]
