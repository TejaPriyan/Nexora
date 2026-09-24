"""TimeLoop (timeline / rewind) -- Milestone 5 of NEXORA.

Git for runtime application state: checkpoint, snapshot, restore, rewind,
and diff for tracked objects. Always scrubs data through SecretRedactor
and respects custom `.ignore()` lists. Never claims perfect secret detection.
"""

from .engine import TimeLoopEngine
from .models import DiffResult, Snapshot
from .plugin import TimelinePlugin, TimeLoop

STATUS = "implemented"

__all__ = [
    "TimelinePlugin",
    "TimeLoop",
    "TimeLoopEngine",
    "Snapshot",
    "DiffResult",
    "STATUS",
]
