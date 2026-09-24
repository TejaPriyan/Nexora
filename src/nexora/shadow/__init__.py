"""Shadow (live observability) module for NEXORA.

Builds a live observational model of a running application:
functions, events, state, execution timing, errors, dependencies.
Targeted at reliable, genuine observability -- zero synthetic or faked numbers.
"""

from .engine import ShadowEngine
from .models import (
    DependencyLink,
    FunctionProfile,
    ObservabilitySnapshot,
    ObservedError,
    ObservedEvent,
)
from .plugin import Shadow, ShadowPlugin

STATUS = "implemented"

__all__ = [
    "STATUS",
    "ShadowPlugin",
    "Shadow",
    "ShadowEngine",
    "FunctionProfile",
    "ObservedEvent",
    "ObservedError",
    "DependencyLink",
    "ObservabilitySnapshot",
]
