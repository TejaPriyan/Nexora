"""MoodUI (adaptive interfaces) -- Milestone 3 of NEXORA.

Derives interaction-aware states (NORMAL, FAST, DIFFICULTY_HIGH, INACTIVE,
ERROR_HEAVY) purely from observable signals -- repeated/failed actions,
navigation loops, help requests, inactivity -- with explicit opt-in
and no hidden monitoring. Strictly avoids emotion-detection claims.
"""

from .engine import AdaptiveEngine
from .models import AdaptiveConfig, InteractionSignal, InteractionState, StateTransition
from .plugin import AdaptivePlugin, MoodUI

STATUS = "implemented"

__all__ = [
    "AdaptivePlugin",
    "MoodUI",
    "AdaptiveEngine",
    "AdaptiveConfig",
    "InteractionSignal",
    "InteractionState",
    "StateTransition",
    "STATUS",
]
