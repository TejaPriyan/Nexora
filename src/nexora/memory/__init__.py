"""Recall (persistent memory) -- Milestone 4 of NEXORA.

Structured, persistent memory (remember, search, ask, forget, timeline)
backed by LocalStore and SecretRedactor. Free of external AI dependencies
with all data remaining local.
"""

from .models import MemoryItem
from .plugin import MemoryPlugin, Recall
from .store import MemoryStore

STATUS = "implemented"

__all__ = [
    "MemoryPlugin",
    "Recall",
    "MemoryStore",
    "MemoryItem",
    "STATUS",
]
