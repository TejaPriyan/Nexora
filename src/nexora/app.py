"""NEXORA App: the top-level entry point most users interact with."""

from __future__ import annotations

import time
import traceback
from typing import Any, Callable, Dict, List, Optional

from .config import Config
from .events import EventBus
from .plugins import Plugin, available_features
from .runtime import Runtime
from .state import State


class _Task:
    __slots__ = ("func", "name")

    def __init__(self, func: Callable[..., Any], name: Optional[str] = None) -> None:
        self.func = func
        self.name = name or func.__name__


class App:
    """The main NEXORA application object.

    ``App(features=[...])`` declares which optional modules should be
    attached. Only ``nexora`` core ships in this milestone; feature modules
    are registered as plugins (see ``nexora.plugins``) and today report an
    honest "not implemented yet" error the moment you actually try to use
    one, rather than silently doing nothing or faking behavior.
    """

    def __init__(
        self,
        features: Optional[List[str]] = None,
        *,
        config: Optional[Config] = None,
    ) -> None:
        self.runtime = Runtime(config=config)
        self._tasks: Dict[str, _Task] = {}
        for feature in features or []:
            self.runtime.register(self, feature)

    # -- convenience passthroughs ------------------------------------
    @property
    def bus(self) -> EventBus:
        return self.runtime.bus

    @property
    def state(self) -> State:
        return self.runtime.state

    @property
    def config(self) -> Config:
        return self.runtime.config

    @property
    def permissions(self) -> Any:
        return self.runtime.permissions

    @property
    def ghost(self) -> Optional[Any]:
        """Return the active GhostPlugin instance if attached, else None."""
        return self.runtime.plugins.get("ghost")

    @property
    def world(self) -> Optional[Any]:
        """Return the active WorldPlugin instance if attached, else None."""
        return self.runtime.plugins.get("world")

    @property
    def adaptive(self) -> Optional[Any]:
        """Return the active AdaptivePlugin (MoodUI) instance if attached, else None."""
        return self.runtime.plugins.get("adaptive")

    @property
    def mood(self) -> Optional[Any]:
        """Alias for app.adaptive."""
        return self.runtime.plugins.get("adaptive")

    @property
    def memory(self) -> Optional[Any]:
        """Return the active MemoryPlugin (Recall) instance if attached, else None."""
        return self.runtime.plugins.get("memory")

    @property
    def recall(self) -> Optional[Any]:
        """Alias for app.memory."""
        return self.runtime.plugins.get("memory")

    @property
    def timeline(self) -> Optional[Any]:
        """Return the active TimelinePlugin (TimeLoop) instance if attached, else None."""
        return self.runtime.plugins.get("timeline")

    @property
    def timeloop(self) -> Optional[Any]:
        """Alias for app.timeline."""
        return self.runtime.plugins.get("timeline")

    @property
    def shadow(self) -> Optional[Any]:
        """Return the active ShadowPlugin instance if attached, else None."""
        return self.runtime.plugins.get("shadow")

    @property
    def vision(self) -> Optional[Any]:
        """Return the active VisionPlugin (ScreenMind) instance if attached, else None."""
        return self.runtime.plugins.get("vision")

    @property
    def screenmind(self) -> Optional[Any]:
        """Alias for app.vision."""
        return self.runtime.plugins.get("vision")

    @property
    def worldforge(self) -> Optional[Any]:
        """Return the active WorldForgePlugin instance if attached, else None."""
        return self.runtime.plugins.get("worldforge")

    @property
    def agentbox(self) -> Optional[Any]:
        """Return the active AgentBoxPlugin instance if attached, else None."""
        return self.runtime.plugins.get("agentbox")

    # -- feature management -------------------------------------------
    def use(self, feature: str) -> Plugin:
        return self.runtime.register(self, feature)

    @staticmethod
    def available_features() -> List[str]:
        return sorted(available_features().keys())

    # -- tasks -----------------------------------------------------------
    def task(
        self,
        func: Optional[Callable[..., Any]] = None,
        *,
        name: Optional[str] = None,
    ):
        """Register a function as a NEXORA task.

        Wraps the call with ``task.started`` / ``task.completed`` /
        ``task.failed`` events and basic timing -- independent of whether
        GhostUI (which will later *render* this) is installed. Can be used
        as ``@app.task`` or ``@app.task(name="...")``.
        """

        def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
            task = _Task(f, name)
            self._tasks[task.name] = task

            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return self._run_task(task, args, kwargs)

            wrapper.__wrapped__ = f  # type: ignore[attr-defined]
            wrapper.task_name = task.name  # type: ignore[attr-defined]
            return wrapper

        if func is not None:
            return decorator(func)
        return decorator

    def _run_task(self, task: _Task, args: tuple, kwargs: dict) -> Any:
        self.bus.emit("task.started", source=task.name, payload={"task": task.name})
        start = time.perf_counter()
        try:
            result = task.func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - intentionally broad, re-raised
            duration = time.perf_counter() - start
            self.bus.emit(
                "task.failed",
                source=task.name,
                payload={
                    "task": task.name,
                    "duration_seconds": duration,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
            raise
        duration = time.perf_counter() - start
        self.bus.emit(
            "task.completed",
            source=task.name,
            payload={"task": task.name, "duration_seconds": duration},
        )
        return result

    @property
    def tasks(self) -> List[str]:
        return list(self._tasks)

    # -- lifecycle -----------------------------------------------------
    def run(self, *, raise_on_task_error: bool = True) -> None:
        """Start every registered plugin, then run every registered task in
        registration order.

        This is intentionally simple in this milestone: there is no
        scheduler, no async event loop, and no GhostUI rendering yet. It
        exists so ``App`` is genuinely usable today, not just a stub --
        every task run still goes through ``_run_task`` so
        ``task.started`` / ``task.completed`` / ``task.failed`` events fire
        exactly as they do when a task is called directly.
        """
        self.runtime.start()
        try:
            for task in self._tasks.values():
                try:
                    self._run_task(task, (), {})
                except Exception:
                    if raise_on_task_error:
                        raise
        finally:
            self.runtime.stop()
