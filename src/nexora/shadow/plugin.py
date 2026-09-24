"""Shadow (observability) plugin for NEXORA."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional, Union

from ..plugins.base import Plugin
from .engine import ShadowEngine
from .models import (
    DependencyLink,
    FunctionProfile,
    ObservabilitySnapshot,
    ObservedError,
    ObservedEvent,
)

if TYPE_CHECKING:
    from ..app import App
    from ..events import Event


class ShadowPlugin(Plugin):
    """Shadow: live observational model of a running application.

    Instruments functions, tracks event frequencies, measures real execution
    timings, captures errors, and maps component dependencies.
    Reliable observability first, with zero synthetic numbers or placeholder data.
    """

    name: ClassVar[str] = "shadow"
    requires_extra: ClassVar[Optional[str]] = None
    milestone: ClassVar[str] = "M6"

    def __init__(self, app: "App", *, engine: Optional[ShadowEngine] = None) -> None:
        super().__init__(app)
        self._engine = engine or ShadowEngine()
        self._registered = False
        self._started = False
        self._unsubscribers: List[Callable[[], None]] = []
        self._task_start_times: Dict[str, float] = {}

    @property
    def engine(self) -> ShadowEngine:
        return self._engine

    # --- Lifecycle Hooks ---

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

        # Observe all events
        h_all = bus.on("*", self._on_any_event)
        self._unsubscribers.append(lambda: bus.off("*", h_all))

        # Task lifecycle precision timing
        self._sub(bus, "task.started", self._on_task_started)
        self._sub(bus, "task.completed", self._on_task_completed)
        self._sub(bus, "task.failed", self._on_task_failed)

        # Errors
        self._sub(bus, "error", self._on_error_event)
        self._sub(bus, "error.*", self._on_error_event)

    def _sub(self, bus: Any, event_type: str, handler: Callable[[Any], None]) -> None:
        h = bus.on(event_type, handler)
        self._unsubscribers.append(lambda: bus.off(event_type, h))

    def _on_any_event(self, event: "Event") -> None:
        self._engine.track_event(event.type, event.source or "unknown")

    def _on_task_started(self, event: "Event") -> None:
        task_name = str(event.payload.get("task", event.source or "unknown"))
        self._task_start_times[task_name] = time.perf_counter()

    def _on_task_completed(self, event: "Event") -> None:
        task_name = str(event.payload.get("task", event.source or "unknown"))
        start_t = self._task_start_times.pop(task_name, None)
        if start_t is not None:
            duration = time.perf_counter() - start_t
        else:
            duration = float(event.payload.get("duration_seconds", 0.0))
        self._engine.track_function_call(f"task:{task_name}", duration, success=True)

    def _on_task_failed(self, event: "Event") -> None:
        task_name = str(event.payload.get("task", event.source or "unknown"))
        err_msg = str(event.payload.get("error", "Task execution failed"))
        start_t = self._task_start_times.pop(task_name, None)
        duration = time.perf_counter() - start_t if start_t is not None else 0.0

        self._engine.track_function_call(f"task:{task_name}", duration, success=False, error_msg=err_msg)
        self._engine.record_error("TaskError", err_msg, f"task:{task_name}")

        self.app.bus.emit(
            "shadow.alert",
            source="shadow",
            payload={"error": err_msg, "source": f"task:{task_name}"},
        )

    def _on_error_event(self, event: "Event") -> None:
        err_msg = str(event.payload.get("error") or event.payload.get("message") or "Unknown error")
        self._engine.record_error("AppError", err_msg, event.source or "app")

    # --- Public API ---

    def trace(
        self,
        func_or_name: Optional[Union[Callable[..., Any], str]] = None,
    ) -> Any:
        """Trace decorator measuring genuine function execution time and errors."""
        return self._engine.trace(func_or_name)

    def span(self, name: str) -> Any:
        """Context manager measuring execution time of a code block."""
        return self._engine.span(name)

    def function_stats(
        self,
        name: Optional[str] = None,
    ) -> Union[Optional[FunctionProfile], Dict[str, FunctionProfile]]:
        return self._engine.function_stats(name)

    def event_stats(self) -> Dict[str, ObservedEvent]:
        return self._engine.event_stats()

    def errors(self) -> List[ObservedError]:
        return self._engine.error_log()

    def dependencies(self) -> List[DependencyLink]:
        return self._engine.dependencies()

    def snapshot(self) -> ObservabilitySnapshot:
        return self._engine.snapshot()

    def reset(self) -> None:
        self._engine.reset()
        self._task_start_times.clear()


# Alias
Shadow = ShadowPlugin
