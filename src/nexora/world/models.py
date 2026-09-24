"""Data models for CodeWorld entities and relationships."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class Entity:
    """A single entity in the CodeWorld.

    Entities have an ID, a kind (type label), a 2D position, optional
    display properties (colour, size, label, shape), and arbitrary
    user-defined properties.  Relationships to other entities are stored
    as ``(relationship_name, target_entity_id)`` pairs.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    kind: str = "entity"
    x: float = 0.0
    y: float = 0.0
    label: Optional[str] = None
    color: str = "#4ea8de"
    size: float = 20.0
    shape: str = "circle"  # "circle", "rect", "diamond"
    visible: bool = True
    properties: Dict[str, Any] = field(default_factory=dict)
    relationships: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def display_label(self) -> str:
        return self.label or self.kind

    def relate(self, rel_name: str, target_id: str) -> None:
        """Add a named relationship to another entity."""
        pair = (rel_name, target_id)
        if pair not in self.relationships:
            self.relationships.append(pair)

    def unrelate(self, rel_name: str, target_id: str) -> None:
        """Remove a named relationship."""
        pair = (rel_name, target_id)
        if pair in self.relationships:
            self.relationships.remove(pair)

    def move(self, x: float, y: float) -> Tuple[float, float]:
        """Move to absolute position; return (old_x, old_y)."""
        old = (self.x, self.y)
        self.x, self.y = x, y
        return old

    def move_by(self, dx: float, dy: float) -> Tuple[float, float]:
        """Move by a relative offset; return (old_x, old_y)."""
        return self.move(self.x + dx, self.y + dy)

    def set_prop(self, key: str, value: Any) -> Any:
        """Set a user-defined property; return old value."""
        old = self.properties.get(key)
        self.properties[key] = value
        return old

    def get_prop(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "x": self.x,
            "y": self.y,
            "label": self.label,
            "color": self.color,
            "size": self.size,
            "shape": self.shape,
            "visible": self.visible,
            "properties": dict(self.properties),
            "relationships": list(self.relationships),
        }


class World:
    """A container of entities with spatial queries and thread-safe mutation.

    The World is the in-memory model that CodeWorld renders.  All mutations
    go through methods on this class so the ``WorldPlugin`` can emit events
    on the shared EventBus for each change.
    """

    def __init__(self) -> None:
        self._entities: Dict[str, Entity] = {}
        self._lock = threading.RLock()
        # Optional callback the WorldPlugin sets to be notified of changes
        self._on_change: Optional[Callable[[str, Dict[str, Any]], None]] = None

    def _notify(self, event_type: str, payload: Dict[str, Any]) -> None:
        if self._on_change is not None:
            self._on_change(event_type, payload)

    # --- Entity CRUD ---

    def add(self, entity: Entity) -> Entity:
        """Add an entity to the world."""
        with self._lock:
            self._entities[entity.id] = entity
        self._notify("world.entity.added", {"entity_id": entity.id, **entity.to_dict()})
        return entity

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
        """Create a new entity and add it to the world."""
        ent = Entity(
            id=entity_id or uuid.uuid4().hex[:12],
            kind=kind,
            x=x,
            y=y,
            label=label,
            color=color,
            size=size,
            shape=shape,
            properties=properties or {},
        )
        return self.add(ent)

    def remove(self, entity_id: str) -> Optional[Entity]:
        """Remove an entity by ID; return the removed entity or None."""
        with self._lock:
            ent = self._entities.pop(entity_id, None)
        if ent is not None:
            self._notify("world.entity.removed", {"entity_id": entity_id, "kind": ent.kind})
        return ent

    def get(self, entity_id: str) -> Optional[Entity]:
        """Look up an entity by ID."""
        with self._lock:
            return self._entities.get(entity_id)

    def __contains__(self, entity_id: str) -> bool:
        with self._lock:
            return entity_id in self._entities

    def __len__(self) -> int:
        with self._lock:
            return len(self._entities)

    # --- Mutation helpers (emit events) ---

    def move(self, entity_id: str, x: float, y: float) -> None:
        """Move an entity to an absolute position."""
        with self._lock:
            ent = self._entities.get(entity_id)
        if ent is None:
            return
        old_x, old_y = ent.move(x, y)
        self._notify(
            "world.entity.moved",
            {
                "entity_id": entity_id,
                "old_x": old_x,
                "old_y": old_y,
                "x": x,
                "y": y,
            },
        )

    def move_by(self, entity_id: str, dx: float, dy: float) -> None:
        """Move an entity by a relative offset."""
        with self._lock:
            ent = self._entities.get(entity_id)
        if ent is None:
            return
        old_x, old_y = ent.move_by(dx, dy)
        self._notify(
            "world.entity.moved",
            {
                "entity_id": entity_id,
                "old_x": old_x,
                "old_y": old_y,
                "x": ent.x,
                "y": ent.y,
            },
        )

    def set_prop(self, entity_id: str, key: str, value: Any) -> None:
        """Set a property on an entity."""
        with self._lock:
            ent = self._entities.get(entity_id)
        if ent is None:
            return
        old = ent.set_prop(key, value)
        self._notify(
            "world.entity.property",
            {"entity_id": entity_id, "key": key, "old": old, "new": value},
        )

    def relate(self, source_id: str, rel_name: str, target_id: str) -> None:
        """Add a relationship from source entity to target entity."""
        with self._lock:
            ent = self._entities.get(source_id)
        if ent is None:
            return
        ent.relate(rel_name, target_id)
        self._notify(
            "world.entity.related",
            {"source_id": source_id, "rel_name": rel_name, "target_id": target_id},
        )

    def unrelate(self, source_id: str, rel_name: str, target_id: str) -> None:
        """Remove a relationship from source entity to target entity."""
        with self._lock:
            ent = self._entities.get(source_id)
        if ent is None:
            return
        ent.unrelate(rel_name, target_id)
        self._notify(
            "world.entity.unrelated",
            {"source_id": source_id, "rel_name": rel_name, "target_id": target_id},
        )

    # --- Queries ---

    def entities(self) -> List[Entity]:
        """Return all entities as a list (snapshot)."""
        with self._lock:
            return list(self._entities.values())

    def entities_by_kind(self, kind: str) -> List[Entity]:
        """Return all entities of a given kind."""
        with self._lock:
            return [e for e in self._entities.values() if e.kind == kind]

    def entities_in_rect(
        self, x1: float, y1: float, x2: float, y2: float
    ) -> List[Entity]:
        """Return entities whose position is inside the rectangle (x1,y1)-(x2,y2)."""
        lo_x, hi_x = min(x1, x2), max(x1, x2)
        lo_y, hi_y = min(y1, y2), max(y1, y2)
        with self._lock:
            return [
                e
                for e in self._entities.values()
                if lo_x <= e.x <= hi_x and lo_y <= e.y <= hi_y
            ]

    def entities_near(
        self, x: float, y: float, radius: float
    ) -> List[Entity]:
        """Return entities within *radius* distance of (x, y)."""
        r2 = radius * radius
        with self._lock:
            return [
                e
                for e in self._entities.values()
                if (e.x - x) ** 2 + (e.y - y) ** 2 <= r2
            ]

    def entity_ids(self) -> List[str]:
        """Return all entity IDs."""
        with self._lock:
            return list(self._entities.keys())

    def clear(self) -> int:
        """Remove all entities; return count removed."""
        with self._lock:
            n = len(self._entities)
            self._entities.clear()
        if n > 0:
            self._notify("world.cleared", {"count": n})
        return n

    def snapshot(self) -> List[Dict[str, Any]]:
        """Return a serialisable snapshot of every entity."""
        with self._lock:
            return [e.to_dict() for e in self._entities.values()]
