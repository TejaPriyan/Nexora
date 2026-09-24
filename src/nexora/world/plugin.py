"""CodeWorld plugin: 2D visualization of application execution and state."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional, Sequence, Tuple

from ..plugins.base import Plugin
from .models import Entity, World
from .renderer import HAS_PYGAME, Renderer

if TYPE_CHECKING:
    from ..app import App
    from ..events import Event


class WorldPlugin(Plugin):
    """CodeWorld: 2D visualization of NEXORA application execution and state.

    Provides an in-memory ``World`` of ``Entity`` objects that can be
    created, moved, inspected, and related to each other.  Every mutation
    emits an event on the shared ``EventBus`` so other modules (e.g.
    GhostUI) can observe world changes.

    The plugin also listens to existing EventBus events:

    - ``task.started`` / ``task.completed`` / ``task.failed`` →
      auto-creates entities representing tasks.
    - ``state.changed`` → updates entity properties when state keys
      are associated with entities.
    - ``world.*`` events emitted by external code to drive the world
      programmatically.

    An optional ``Renderer`` (pygame-based, requires ``nexora[world]``)
    can be started to visualise the world in a 2D window.  The World
    model itself is pure Python stdlib and works without pygame.
    """

    name: ClassVar[str] = "world"
    requires_extra: ClassVar[Optional[str]] = "world"
    milestone: ClassVar[str] = "M2"

    def __init__(
        self,
        app: "App",
        *,
        auto_tasks: bool = True,
        auto_render: bool = False,
        render_width: int = 960,
        render_height: int = 640,
        render_title: str = "NEXORA CodeWorld",
        render_fps: int = 30,
    ) -> None:
        super().__init__(app)
        self.world = World()
        self.auto_tasks = auto_tasks
        self.auto_render = auto_render
        self.render_width = render_width
        self.render_height = render_height
        self.render_title = render_title
        self.render_fps = render_fps

        self._renderer: Optional[Renderer] = None
        self._render_thread: Optional[threading.Thread] = None
        self._registered = False
        self._started = False
        self._task_counter = 0

    # --- Lifecycle ---

    def on_register(self) -> None:
        if self._registered:
            return
        self._registered = True
        # Wire world model → EventBus
        self.world._on_change = self._on_world_change
        self._subscribe_events()

    def on_start(self) -> None:
        self._started = True
        self.app.bus.emit(
            "world.started",
            source="world",
            payload={"entity_count": len(self.world)},
        )
        if self.auto_render and HAS_PYGAME:
            self.open_renderer()

    def on_stop(self) -> None:
        if not self._started:
            return
        self.close_renderer()
        self.app.bus.emit(
            "world.stopped",
            source="world",
            payload={"entity_count": len(self.world)},
        )
        self._started = False

    # --- EventBus bridge ---

    def _on_world_change(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Called by World model on every mutation → emit onto the shared bus."""
        self.app.bus.emit(event_type, source="world", payload=payload)

    def _subscribe_events(self) -> None:
        bus = self.app.bus

        # Auto-create entities for tasks
        if self.auto_tasks:
            bus.on("task.started", self._on_task_started)
            bus.on("task.completed", self._on_task_completed)
            bus.on("task.failed", self._on_task_failed)

        # External world commands via events
        bus.on("world.create", self._on_world_create_event)
        bus.on("world.remove", self._on_world_remove_event)
        bus.on("world.move", self._on_world_move_event)
        bus.on("world.relate", self._on_world_relate_event)
        bus.on("world.set_prop", self._on_world_set_prop_event)

    # --- Task auto-entities ---

    def _on_task_started(self, event: "Event") -> None:
        task_name = str(event.payload.get("task", "unknown"))
        eid = f"task:{task_name}"
        self._task_counter += 1
        x = 80.0 + (self._task_counter - 1) * 100.0
        y = 200.0
        self.world.create(
            kind="task",
            entity_id=eid,
            label=task_name,
            x=x,
            y=y,
            color="#f9c74f",
            shape="rect",
            properties={"status": "running"},
        )

    def _on_task_completed(self, event: "Event") -> None:
        task_name = str(event.payload.get("task", "unknown"))
        eid = f"task:{task_name}"
        ent = self.world.get(eid)
        if ent is not None:
            ent.color = "#43aa8b"
            self.world.set_prop(eid, "status", "completed")
            dur = event.payload.get("duration_seconds")
            if dur is not None:
                self.world.set_prop(eid, "duration", f"{dur:.4f}s")

    def _on_task_failed(self, event: "Event") -> None:
        task_name = str(event.payload.get("task", "unknown"))
        eid = f"task:{task_name}"
        ent = self.world.get(eid)
        if ent is not None:
            ent.color = "#e63946"
            self.world.set_prop(eid, "status", "failed")
            err = event.payload.get("error")
            if err:
                self.world.set_prop(eid, "error", str(err))

    # --- External world command events ---

    def _on_world_create_event(self, event: "Event") -> None:
        p = event.payload
        self.world.create(
            kind=p.get("kind", "entity"),
            x=float(p.get("x", 0)),
            y=float(p.get("y", 0)),
            label=p.get("label"),
            color=p.get("color", "#4ea8de"),
            size=float(p.get("size", 20)),
            shape=p.get("shape", "circle"),
            entity_id=p.get("entity_id"),
            properties=p.get("properties"),
        )

    def _on_world_remove_event(self, event: "Event") -> None:
        eid = event.payload.get("entity_id")
        if eid:
            self.world.remove(eid)

    def _on_world_move_event(self, event: "Event") -> None:
        eid = event.payload.get("entity_id")
        if eid:
            x = float(event.payload.get("x", 0))
            y = float(event.payload.get("y", 0))
            self.world.move(eid, x, y)

    def _on_world_relate_event(self, event: "Event") -> None:
        p = event.payload
        source_id = p.get("source_id")
        target_id = p.get("target_id")
        rel_name = p.get("rel_name", "related")
        if source_id and target_id:
            self.world.relate(source_id, rel_name, target_id)

    def _on_world_set_prop_event(self, event: "Event") -> None:
        p = event.payload
        eid = p.get("entity_id")
        key = p.get("key")
        value = p.get("value")
        if eid and key is not None:
            self.world.set_prop(eid, key, value)

    # --- Renderer management ---

    @property
    def renderer(self) -> Optional[Renderer]:
        return self._renderer

    def open_renderer(self, **kwargs: Any) -> Renderer:
        """Create and start the 2D renderer in a background thread."""
        if not HAS_PYGAME:
            raise ImportError(
                "CodeWorld renderer requires 'pygame'. "
                "Install it with: pip install nexora[world]"
            )
        if self._renderer is not None and self._renderer.is_open:
            return self._renderer
        self._renderer = Renderer(
            self.world,
            width=kwargs.get("width", self.render_width),
            height=kwargs.get("height", self.render_height),
            title=kwargs.get("title", self.render_title),
            fps=kwargs.get("fps", self.render_fps),
        )
        self._render_thread = self._renderer.run_loop_in_thread()
        return self._renderer

    def close_renderer(self) -> None:
        """Close the renderer window if open."""
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
            self._render_thread = None

    # --- Convenience helpers (same pattern as GhostPlugin) ---

    def create(
        self,
        kind: str = "entity",
        *,
        x: float = 0.0,
        y: float = 0.0,
        label: Optional[str] = None,
        color: str = "#4ea8de",
        size: float = 20.0,
        shape: str = "circle",
        entity_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Entity:
        """Create a new entity in the world."""
        return self.world.create(
            kind=kind,
            x=x,
            y=y,
            label=label,
            color=color,
            size=size,
            shape=shape,
            entity_id=entity_id,
            properties=properties,
        )

    def remove(self, entity_id: str) -> Optional[Entity]:
        """Remove an entity from the world."""
        return self.world.remove(entity_id)

    def move(self, entity_id: str, x: float, y: float) -> None:
        """Move an entity to an absolute position."""
        self.world.move(entity_id, x, y)

    def move_by(self, entity_id: str, dx: float, dy: float) -> None:
        """Move an entity by a relative offset."""
        self.world.move_by(entity_id, dx, dy)

    def relate(self, source_id: str, rel_name: str, target_id: str) -> None:
        """Add a relationship between entities."""
        self.world.relate(source_id, rel_name, target_id)

    def unrelate(self, source_id: str, rel_name: str, target_id: str) -> None:
        """Remove a relationship between entities."""
        self.world.unrelate(source_id, rel_name, target_id)

    def set_prop(self, entity_id: str, key: str, value: Any) -> None:
        """Set a property on an entity."""
        self.world.set_prop(entity_id, key, value)

    def get(self, entity_id: str) -> Optional[Entity]:
        """Look up an entity by ID."""
        return self.world.get(entity_id)

    def entities(self) -> List[Entity]:
        """Return all entities."""
        return self.world.entities()

    def entities_by_kind(self, kind: str) -> List[Entity]:
        """Return all entities matching the given kind."""
        return self.world.entities_by_kind(kind)

    def entities_near(self, x: float, y: float, radius: float) -> List[Entity]:
        """Return all entities within radius of (x, y)."""
        return self.world.entities_near(x, y, radius)

    def entities_in_rect(self, x1: float, y1: float, x2: float, y2: float) -> List[Entity]:
        """Return all entities inside the bounding rectangle."""
        return self.world.entities_in_rect(x1, y1, x2, y2)

    def snapshot(self) -> List[Dict[str, Any]]:
        """Return a serialisable snapshot of the world."""
        return self.world.snapshot()


# Alias
CodeWorld = WorldPlugin
