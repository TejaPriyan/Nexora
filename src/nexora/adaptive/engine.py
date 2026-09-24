"""Interaction-aware state detection engine for MoodUI.

Derives interface states (NORMAL, FAST, DIFFICULTY_HIGH, INACTIVE, ERROR_HEAVY)
purely from observable interaction telemetry:
- Repeated actions on identical targets
- Consecutive or high-frequency errors
- Navigation cycles (ping-ponging between routes)
- Help / documentation requests
- Periods of inactivity exceeding configured timeouts
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Deque, List, Optional

from .models import AdaptiveConfig, InteractionSignal, InteractionState, StateTransition


class AdaptiveEngine:
    """Thread-safe engine for evaluating interaction telemetry against rule thresholds."""

    def __init__(
        self,
        config: Optional[AdaptiveConfig] = None,
        *,
        on_transition: Optional[Callable[[StateTransition], None]] = None,
    ) -> None:
        self.config = config or AdaptiveConfig()
        self._on_transition = on_transition

        self._lock = threading.RLock()
        self._current_state = InteractionState.NORMAL
        self._transitions: List[StateTransition] = []

        # Ring buffers for tracking recent signals
        self._recent_errors: Deque[InteractionSignal] = deque(maxlen=20)
        self._recent_actions: Deque[InteractionSignal] = deque(maxlen=30)
        self._recent_navs: Deque[str] = deque(maxlen=self.config.navigation_history_size)

        self._consecutive_errors: int = 0
        self._consecutive_successes: int = 0
        self._last_interaction_time: float = time.time()

    @property
    def current_state(self) -> InteractionState:
        with self._lock:
            return self._current_state

    @property
    def transitions(self) -> List[StateTransition]:
        with self._lock:
            return list(self._transitions)

    def set_transition_callback(self, callback: Optional[Callable[[StateTransition], None]]) -> None:
        with self._lock:
            self._on_transition = callback

    def record_action(
        self,
        name: str,
        *,
        success: bool = True,
        duration: Optional[float] = None,
        payload: Optional[dict] = None,
        now: Optional[float] = None,
    ) -> InteractionState:
        """Record an application action or task completion."""
        t = now if now is not None else time.time()
        sig = InteractionSignal(
            signal_type="action",
            name=name,
            timestamp=t,
            payload=payload or {},
            duration=duration,
            success=success,
        )

        with self._lock:
            self._last_interaction_time = t
            self._recent_actions.append(sig)

            if success:
                self._consecutive_errors = 0
                self._consecutive_successes += 1
                return self._evaluate_success_state(sig, t)
            else:
                self._consecutive_errors += 1
                self._consecutive_successes = 0
                self._recent_errors.append(sig)
                return self._evaluate_error_state(sig, t)

    def record_error(
        self,
        name: str,
        *,
        payload: Optional[dict] = None,
        now: Optional[float] = None,
    ) -> InteractionState:
        """Record an error or task failure signal."""
        return self.record_action(name, success=False, payload=payload, now=now)

    def record_navigation(
        self,
        destination: str,
        *,
        payload: Optional[dict] = None,
        now: Optional[float] = None,
    ) -> InteractionState:
        """Record a navigation or view transition."""
        t = now if now is not None else time.time()
        sig = InteractionSignal(
            signal_type="navigation",
            name=destination,
            timestamp=t,
            payload=payload or {},
        )

        with self._lock:
            self._last_interaction_time = t
            self._recent_actions.append(sig)
            self._recent_navs.append(destination)

            # Check for navigation loop (e.g. A -> B -> A -> B)
            if self._detect_navigation_loop():
                return self._transition_to(
                    InteractionState.DIFFICULTY_HIGH,
                    reason=f"Navigation loop detected across routes: {list(self._recent_navs)}",
                    now=t,
                    metadata={"routes": list(self._recent_navs)},
                )

            # If currently in INACTIVE or recovering, evaluate normal flow
            if self._current_state in (InteractionState.INACTIVE, InteractionState.DIFFICULTY_HIGH):
                self._consecutive_successes += 1
                if self._consecutive_successes >= self.config.recovery_action_count:
                    return self._transition_to(
                        InteractionState.NORMAL,
                        reason="Standard navigation resumed after disruption",
                        now=t,
                    )

            return self._current_state

    def record_help_request(
        self,
        topic: str = "general",
        *,
        payload: Optional[dict] = None,
        now: Optional[float] = None,
    ) -> InteractionState:
        """Record a user or system help/doc request."""
        t = now if now is not None else time.time()
        sig = InteractionSignal(
            signal_type="help",
            name=topic,
            timestamp=t,
            payload=payload or {},
        )

        with self._lock:
            self._last_interaction_time = t
            self._recent_actions.append(sig)
            return self._transition_to(
                InteractionState.DIFFICULTY_HIGH,
                reason=f"Help requested for topic: {topic!r}",
                now=t,
                metadata={"topic": topic},
            )

    def check_inactivity(self, now: Optional[float] = None) -> InteractionState:
        """Check if elapsed time since last interaction exceeds inactivity timeout."""
        t = now if now is not None else time.time()
        with self._lock:
            idle_seconds = t - self._last_interaction_time
            if idle_seconds >= self.config.inactivity_timeout_seconds:
                if self._current_state != InteractionState.INACTIVE:
                    return self._transition_to(
                        InteractionState.INACTIVE,
                        reason=f"No interaction for {idle_seconds:.1f}s (threshold: {self.config.inactivity_timeout_seconds}s)",
                        now=t,
                        metadata={"idle_seconds": idle_seconds},
                    )
            return self._current_state

    def reset(self, initial_state: InteractionState = InteractionState.NORMAL) -> None:
        """Reset internal telemetry and buffers."""
        with self._lock:
            self._current_state = initial_state
            self._transitions.clear()
            self._recent_errors.clear()
            self._recent_actions.clear()
            self._recent_navs.clear()
            self._consecutive_errors = 0
            self._consecutive_successes = 0
            self._last_interaction_time = time.time()

    # --- Internal evaluation helpers ---

    def _evaluate_error_state(self, sig: InteractionSignal, now: float) -> InteractionState:
        # Check consecutive errors
        if self._consecutive_errors >= self.config.error_threshold:
            return self._transition_to(
                InteractionState.ERROR_HEAVY,
                reason=f"{self._consecutive_errors} consecutive failed actions encountered",
                now=now,
                metadata={"consecutive_errors": self._consecutive_errors, "last_error": sig.name},
            )

        # Check error rate in recent window
        recent_err_count = sum(
            1 for err in self._recent_errors
            if now - err.timestamp <= self.config.error_window_seconds
        )
        if recent_err_count >= self.config.error_threshold:
            return self._transition_to(
                InteractionState.ERROR_HEAVY,
                reason=f"{recent_err_count} errors in past {self.config.error_window_seconds}s",
                now=now,
                metadata={"recent_errors": recent_err_count},
            )

        return self._current_state

    def _evaluate_success_state(self, sig: InteractionSignal, now: float) -> InteractionState:
        # 1. Check for repeated actions (friction / difficulty)
        repeated_count = self._count_recent_repeated_action(sig.name, now)
        if repeated_count >= self.config.repeated_action_threshold:
            return self._transition_to(
                InteractionState.DIFFICULTY_HIGH,
                reason=f"Action {sig.name!r} repeated {repeated_count} times in short duration",
                now=now,
                metadata={"action": sig.name, "count": repeated_count},
            )

        # 2. Check for FAST cadence (power-user rapid actions)
        recent_successes = [
            act for act in self._recent_actions
            if act.success and now - act.timestamp <= self.config.fast_window_seconds
        ]
        if len(recent_successes) >= self.config.fast_action_count:
            return self._transition_to(
                InteractionState.FAST,
                reason=f"{len(recent_successes)} actions completed within {self.config.fast_window_seconds}s cadence",
                now=now,
                metadata={"action_count": len(recent_successes)},
            )

        # 3. If currently in ERROR_HEAVY, DIFFICULTY_HIGH, or INACTIVE, transition back to NORMAL
        if self._current_state in (
            InteractionState.ERROR_HEAVY,
            InteractionState.DIFFICULTY_HIGH,
            InteractionState.INACTIVE,
            InteractionState.FAST,
        ):
            if self._consecutive_successes >= self.config.recovery_action_count:
                return self._transition_to(
                    InteractionState.NORMAL,
                    reason=f"Normal interaction cadence resumed ({self._consecutive_successes} successful actions)",
                    now=now,
                )

        return self._current_state

    def _count_recent_repeated_action(self, name: str, now: float) -> int:
        count = 0
        for act in reversed(self._recent_actions):
            if now - act.timestamp > self.config.repeated_action_window_seconds:
                break
            if act.name == name:
                count += 1
            else:
                # Continuous run or strictly same action
                pass
        return count

    def _detect_navigation_loop(self) -> bool:
        """Detect cyclic back-and-forth patterns in recent navigation history."""
        navs = list(self._recent_navs)
        if len(navs) < 4:
            return False

        # Pattern 1: A -> B -> A -> B (2-step oscillation)
        if len(navs) >= 4 and navs[-1] == navs[-3] and navs[-2] == navs[-4] and navs[-1] != navs[-2]:
            return True

        # Pattern 2: A -> B -> C -> A -> B -> C (3-step loop)
        if len(navs) >= 6 and navs[-1] == navs[-4] and navs[-2] == navs[-5] and navs[-3] == navs[-6]:
            return True

        return False

    def _transition_to(
        self,
        new_state: InteractionState,
        reason: str,
        now: float,
        metadata: Optional[dict] = None,
    ) -> InteractionState:
        if self._current_state == new_state:
            return self._current_state

        prev = self._current_state
        self._current_state = new_state
        trans = StateTransition(
            from_state=prev,
            to_state=new_state,
            reason=reason,
            timestamp=now,
            metadata=metadata or {},
        )
        self._transitions.append(trans)

        callback = self._on_transition
        if callback is not None:
            try:
                callback(trans)
            except Exception:
                pass

        return self._current_state
