"""Data models and state definitions for MoodUI / adaptive interfaces."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class InteractionState(str, Enum):
    """Interaction-aware UI states derived purely from observable telemetry."""

    NORMAL = "NORMAL"
    FAST = "FAST"
    DIFFICULTY_HIGH = "DIFFICULTY_HIGH"
    INACTIVE = "INACTIVE"
    ERROR_HEAVY = "ERROR_HEAVY"


@dataclass(frozen=True)
class InteractionSignal:
    """An observable signal recorded from the EventBus or application."""

    signal_type: str
    name: str
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)
    duration: Optional[float] = None
    success: bool = True


@dataclass(frozen=True)
class StateTransition:
    """Record of an interaction-aware state transition."""

    from_state: InteractionState
    to_state: InteractionState
    reason: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdaptiveConfig:
    """Thresholds and parameters governing interaction state inference."""

    # Error sensitivity
    error_threshold: int = 3
    error_window_seconds: float = 10.0

    # Fast cadence detection (power-user flow)
    fast_action_count: int = 4
    fast_window_seconds: float = 2.0

    # Inactivity detection
    inactivity_timeout_seconds: float = 5.0

    # Repeated action detection (friction)
    repeated_action_threshold: int = 3
    repeated_action_window_seconds: float = 5.0

    # Navigation loop detection (friction)
    navigation_history_size: int = 6
    navigation_loop_min_repeats: int = 2

    # Normal recovery threshold (consecutive successful actions to return to NORMAL)
    recovery_action_count: int = 2
