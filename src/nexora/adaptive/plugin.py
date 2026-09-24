"""AdaptivePlugin (MoodUI): interaction-aware adaptive interface system for NEXORA.

Derives interface states (NORMAL, FAST, DIFFICULTY_HIGH, INACTIVE, ERROR_HEAVY)
purely from observable interaction telemetry flowing on the EventBus.

Strict privacy model:
- Explicit opt-in required via PermissionManager (scope "adaptive.observe")
- Zero observation occurs without permission
- No emotion-detection claims: models interaction friction and cadence only
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional

from ..plugins.base import Plugin
from .engine import AdaptiveEngine
from .models import AdaptiveConfig, InteractionState, StateTransition

if TYPE_CHECKING:
    from ..app import App
    from ..events import Event


class AdaptivePlugin(Plugin):
    """MoodUI: interaction-aware adaptive interface plugin.

    Observes application events (tasks, actions, errors, navigation, help)
    and derives interaction states (NORMAL, FAST, DIFFICULTY_HIGH, INACTIVE,
    ERROR_HEAVY) to enable responsive, self-adjusting interfaces.

    Privacy & Permission Gate:
    Observation is strictly gated behind `nexora.security.PermissionManager`.
    No telemetry is captured or evaluated until permission scope
    `"adaptive.observe"` is explicitly granted.
    """

    name: ClassVar[str] = "adaptive"
    requires_extra: ClassVar[Optional[str]] = None
    milestone: ClassVar[str] = "M3"

    PERMISSION_SCOPE: ClassVar[str] = "adaptive.observe"

    def __init__(
        self,
        app: "App",
        *,
        config: Optional[AdaptiveConfig] = None,
        permission_scope: Optional[str] = None,
    ) -> None:
        super().__init__(app)
        self.permission_scope = permission_scope or self.PERMISSION_SCOPE
        self.config = config or AdaptiveConfig()

        self._engine = AdaptiveEngine(
            config=self.config,
            on_transition=self._handle_state_transition,
        )

        self._registered = False
        self._started = False
        self._unsubscribers: List[Callable[[], None]] = []
        self._listeners: List[Callable[[StateTransition], None]] = []

    # --- Permission Gate ---

    def is_permitted(self) -> bool:
        """Check if caller has explicitly granted permission to observe telemetry."""
        perms = self.app.runtime.permissions
        return perms.is_granted(self.permission_scope) or perms.is_granted("adaptive")

    def require_permission(self) -> None:
        """Raise PermissionDenied if observation permission is not granted."""
        if not self.is_permitted():
            self.app.runtime.permissions.require(self.permission_scope)

    def opt_in(self, *, reason: str = "caller opted into adaptive UI") -> None:
        """Explicitly grant permission to observe interaction telemetry."""
        self.app.runtime.permissions.grant(self.permission_scope, reason=reason)

    def opt_out(self, *, reason: str = "caller opted out of adaptive UI") -> None:
        """Revoke permission to observe interaction telemetry."""
        self.app.runtime.permissions.revoke(self.permission_scope, reason=reason)

    # --- Plugin Lifecycle Hooks ---

    def on_register(self) -> None:
        if self._registered:
            return
        self._registered = True
        self._subscribe_events()

    def on_start(self) -> None:
        self._started = True

    def on_stop(self) -> None:
        self._started = False

    # --- Event Subscriptions ---

    def _subscribe_events(self) -> None:
        bus = self.app.bus

        # Tasks
        self._sub(bus, "task.started", self._on_task_started)
        self._sub(bus, "task.completed", self._on_task_completed)
        self._sub(bus, "task.failed", self._on_task_failed)

        # Actions & Interactions
        self._sub(bus, "action", self._on_action_event)
        self._sub(bus, "action.*", self._on_action_event)
        self._sub(bus, "interaction", self._on_action_event)
        self._sub(bus, "interaction.*", self._on_action_event)

        # Navigation
        self._sub(bus, "navigation", self._on_navigation_event)
        self._sub(bus, "navigation.*", self._on_navigation_event)
        self._sub(bus, "nav", self._on_navigation_event)

        # Help
        self._sub(bus, "help", self._on_help_event)
        self._sub(bus, "help.*", self._on_help_event)
        self._sub(bus, "help.requested", self._on_help_event)

        # Errors
        self._sub(bus, "error", self._on_error_event)
        self._sub(bus, "error.*", self._on_error_event)

        # Shadow Observability alerts (interoperability)
        self._sub(bus, "shadow.alert", self._on_shadow_alert)

        # Inactivity check trigger
        self._sub(bus, "adaptive.inactivity_check", self._on_inactivity_check_event)

    def _sub(self, bus: Any, event_type: str, handler: Callable[[Any], None]) -> None:
        h = bus.on(event_type, handler)
        self._unsubscribers.append(lambda: bus.off(event_type, h))

    # --- Event Handlers (Gated behind PermissionManager) ---

    def _on_task_started(self, event: "Event") -> None:
        if not self.is_permitted():
            return
        task_name = str(event.payload.get("task", event.source or "unknown"))
        self._engine.record_action(task_name, success=True, payload=event.payload)

    def _on_task_completed(self, event: "Event") -> None:
        if not self.is_permitted():
            return
        task_name = str(event.payload.get("task", event.source or "unknown"))
        duration = event.payload.get("duration_seconds")
        self._engine.record_action(task_name, success=True, duration=duration, payload=event.payload)

    def _on_task_failed(self, event: "Event") -> None:
        if not self.is_permitted():
            return
        task_name = str(event.payload.get("task", event.source or "unknown"))
        self._engine.record_error(task_name, payload=event.payload)

    def _on_action_event(self, event: "Event") -> None:
        if not self.is_permitted():
            return
        action_name = str(event.payload.get("action", event.source or "action"))
        success = bool(event.payload.get("success", True))
        duration = event.payload.get("duration")
        self._engine.record_action(action_name, success=success, duration=duration, payload=event.payload)

    def _on_navigation_event(self, event: "Event") -> None:
        if not self.is_permitted():
            return
        route = str(event.payload.get("to") or event.payload.get("route") or event.payload.get("destination") or "view")
        self._engine.record_navigation(route, payload=event.payload)

    def _on_help_event(self, event: "Event") -> None:
        if not self.is_permitted():
            return
        topic = str(event.payload.get("topic") or event.source or "general")
        self._engine.record_help_request(topic, payload=event.payload)

    def _on_error_event(self, event: "Event") -> None:
        if not self.is_permitted():
            return
        err_msg = str(event.payload.get("error") or event.payload.get("message") or "unspecified_error")
        self._engine.record_error(err_msg, payload=event.payload)

    def _on_shadow_alert(self, event: "Event") -> None:
        if not self.is_permitted():
            return
        err_msg = str(event.payload.get("error") or event.payload.get("message") or "shadow_alert")
        self._engine.record_error(f"shadow:{err_msg}", payload=event.payload)

    def _on_inactivity_check_event(self, event: "Event") -> None:
        if not self.is_permitted():
            return
        now = event.payload.get("now")
        self._engine.check_inactivity(now=now)

    # --- Internal Dispatch ---

    def _handle_state_transition(self, transition: StateTransition) -> None:
        # Emit on shared bus for other modules (e.g. GhostUI, CodeWorld, or caller)
        self.app.bus.emit(
            "adaptive.state_changed",
            source="adaptive",
            payload={
                "previous_state": transition.from_state.value,
                "current_state": transition.to_state.value,
                "reason": transition.reason,
                "timestamp": transition.timestamp,
                "metadata": transition.metadata,
            },
        )

        # Notify custom listeners
        for listener in self._listeners:
            try:
                listener(transition)
            except Exception:
                pass

    # --- Convenience Public API ---

    @property
    def engine(self) -> AdaptiveEngine:
        """Return the underlying AdaptiveEngine instance."""
        return self._engine

    @property
    def current_state(self) -> InteractionState:
        """Return the current interaction-aware interface state."""
        return self._engine.current_state

    @property
    def state(self) -> InteractionState:
        """Alias for current_state."""
        return self._engine.current_state

    @property
    def history(self) -> List[StateTransition]:
        """Return chronological state transitions recorded since start/reset."""
        return self._engine.transitions

    def on_state_change(self, callback: Callable[[StateTransition], None]) -> Callable[[], None]:
        """Register a callback for state changes. Returns an unsubscribe function."""
        self._listeners.append(callback)
        return lambda: self._listeners.remove(callback) if callback in self._listeners else None

    def record_action(
        self,
        name: str,
        *,
        success: bool = True,
        duration: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> InteractionState:
        """Programmatically record an action (requires permission)."""
        self.require_permission()
        return self._engine.record_action(name, success=success, duration=duration, payload=payload)

    def record_error(
        self,
        name: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
    ) -> InteractionState:
        """Programmatically record an error (requires permission)."""
        self.require_permission()
        return self._engine.record_error(name, payload=payload)

    def record_navigation(
        self,
        destination: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
    ) -> InteractionState:
        """Programmatically record navigation (requires permission)."""
        self.require_permission()
        return self._engine.record_navigation(destination, payload=payload)

    def record_help_request(
        self,
        topic: str = "general",
        *,
        payload: Optional[Dict[str, Any]] = None,
    ) -> InteractionState:
        """Programmatically record a help request (requires permission)."""
        self.require_permission()
        return self._engine.record_help_request(topic, payload=payload)

    def check_inactivity(self, now: Optional[float] = None) -> InteractionState:
        """Check and update inactivity state (requires permission)."""
        if not self.is_permitted():
            return self.current_state
        return self._engine.check_inactivity(now=now)

    def reset(self) -> None:
        """Reset internal telemetry and transitions."""
        self._engine.reset()


# Alias
MoodUI = AdaptivePlugin
