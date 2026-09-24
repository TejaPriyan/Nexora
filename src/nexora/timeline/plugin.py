"""TimeLoop (timeline) plugin for NEXORA."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional, Sequence, Union

from ..plugins.base import Plugin
from .engine import TimeLoopEngine
from .models import DiffResult, Snapshot

if TYPE_CHECKING:
    from ..app import App
    from ..events import Event


class TimelinePlugin(Plugin):
    """TimeLoop: runtime application state versioning, diff, and rewind plugin.

    Acts as 'git for application state': creates point-in-time snapshots,
    computes structural diffs, and supports rewinding and restoring state.
    Every snapshot is scrubbed through `SecretRedactor` with support for
    custom exclusion keys via `.ignore()`.
    """

    name: ClassVar[str] = "timeline"
    requires_extra: ClassVar[Optional[str]] = None
    milestone: ClassVar[str] = "M5"

    def __init__(
        self,
        app: "App",
        *,
        auto_checkpoint: bool = False,
        ignore_keys: Sequence[str] = (),
    ) -> None:
        super().__init__(app)
        self.auto_checkpoint = auto_checkpoint
        self._engine = TimeLoopEngine(ignore_keys=ignore_keys)

        self._registered = False
        self._started = False
        self._unsubscribers: List[Callable[[], None]] = []

    @property
    def engine(self) -> TimeLoopEngine:
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
        self._sub(bus, "timeline.create", self._on_create_checkpoint_event)
        self._sub(bus, "timeline.restore_request", self._on_restore_checkpoint_event)
        self._sub(bus, "timeline.rewind_request", self._on_rewind_event)

        if self.auto_checkpoint:
            self._sub(bus, "state.changed", self._on_state_changed_event)

    def _sub(self, bus: Any, event_type: str, handler: Callable[[Any], None]) -> None:
        h = bus.on(event_type, handler)
        self._unsubscribers.append(lambda: bus.off(event_type, h))

    def _on_create_checkpoint_event(self, event: "Event") -> None:
        p = event.payload
        label = p.get("label", "event_checkpoint")
        data = p.get("data")
        self.checkpoint(label, data=data, metadata=p.get("metadata"))

    def _on_restore_checkpoint_event(self, event: "Event") -> None:
        snap_id = event.payload.get("id") or event.payload.get("snapshot_id")
        if snap_id:
            self.restore(snap_id)

    def _on_rewind_event(self, event: "Event") -> None:
        steps = int(event.payload.get("steps", 1))
        self.rewind(steps=steps)

    def _on_state_changed_event(self, event: "Event") -> None:
        key = event.payload.get("key", "state")
        self.checkpoint(f"auto_state_{key}")

    # --- Public API ---

    def ignore(self, *keys: str) -> "TimelinePlugin":
        """Add sensitive field names to the secret redaction exclusion list."""
        self._engine.ignore(*keys)
        return self

    def checkpoint(
        self,
        label: str,
        data: Optional[Dict[str, Any]] = None,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        now: Optional[float] = None,
    ) -> Snapshot:
        """Create a state snapshot and emit `timeline.checkpoint` on EventBus.

        If `data` is omitted, captures the current snapshot of `app.state`.
        """
        if data is None:
            data = self.app.state.snapshot()

        snapshot = self._engine.checkpoint(label, data, metadata=metadata, now=now)

        self.app.bus.emit(
            "timeline.checkpoint",
            source="timeline",
            payload={
                "id": snapshot.id,
                "label": snapshot.label,
                "timestamp": snapshot.timestamp,
                "keys_count": len(snapshot.data),
            },
        )
        return snapshot

    def snapshot(self) -> Optional[Snapshot]:
        """Return the latest active checkpoint snapshot."""
        return self._engine.snapshot()

    def get(self, snapshot_id: str) -> Optional[Snapshot]:
        """Retrieve a snapshot by ID."""
        return self._engine.get(snapshot_id)

    def history(self) -> List[Snapshot]:
        """Return chronological history of all checkpoints."""
        return self._engine.history()

    def restore(self, snapshot_id: str, *, apply_to_state: bool = True) -> Snapshot:
        """Restore state to a past snapshot ID.

        If `apply_to_state` is True, updates `app.state` to match snapshot data.
        """
        snap = self._engine.restore(snapshot_id)

        if apply_to_state:
            # Sync back into App state
            for k, v in snap.data.items():
                self.app.state.set(k, v)

        self.app.bus.emit(
            "timeline.restored",
            source="timeline",
            payload={
                "id": snap.id,
                "label": snap.label,
                "timestamp": snap.timestamp,
            },
        )
        return snap

    def rewind(self, steps: int = 1, *, apply_to_state: bool = True) -> Snapshot:
        """Rewind timeline by `steps` checkpoints."""
        snap = self._engine.rewind(steps=steps)

        if apply_to_state:
            for k, v in snap.data.items():
                self.app.state.set(k, v)

        self.app.bus.emit(
            "timeline.rewound",
            source="timeline",
            payload={
                "id": snap.id,
                "label": snap.label,
                "steps": steps,
            },
        )
        return snap

    def forward(self, steps: int = 1, *, apply_to_state: bool = True) -> Snapshot:
        """Fast-forward timeline by `steps` checkpoints."""
        snap = self._engine.forward(steps=steps)

        if apply_to_state:
            for k, v in snap.data.items():
                self.app.state.set(k, v)

        self.app.bus.emit(
            "timeline.forwarded",
            source="timeline",
            payload={
                "id": snap.id,
                "label": snap.label,
                "steps": steps,
            },
        )
        return snap

    def diff(
        self,
        source: Union[str, Snapshot, Dict[str, Any]],
        target: Union[str, Snapshot, Dict[str, Any]],
    ) -> DiffResult:
        """Compute the structural diff between two snapshots or dictionaries."""
        return self._engine.diff(source, target)

    def clear(self) -> None:
        """Clear timeline snapshots."""
        self._engine.clear()


# Alias
TimeLoop = TimelinePlugin
