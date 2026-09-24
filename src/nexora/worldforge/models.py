"""Data structures for WorldForge (procedural worlds)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class WorldEntity:
    """Lightweight 2D visual representation of a world structure or actor."""

    id: str
    kind: str
    x: float
    y: float
    label: str
    color: str
    size: float
    shape: str
    properties: Dict[str, Any] = field(default_factory=dict)
    relationships: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class Building:
    """A building structure placed in a world."""

    id: str = field(default_factory=lambda: f"bldg_{uuid.uuid4().hex[:8]}")
    name: str = "Building"
    building_type: str = "residential"  # residential, commercial, shop, town_hall, workshop
    x: float = 0.0
    y: float = 0.0
    width: float = 40.0
    height: float = 40.0
    floors: int = 1
    occupants: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_entity(self) -> WorldEntity:
        """Convert to a 2D entity representation."""
        color_map = {
            "residential": "#4ea8de",
            "commercial": "#56cfe1",
            "shop": "#72efdd",
            "town_hall": "#e76f51",
            "workshop": "#f4a261",
        }
        return WorldEntity(
            id=self.id,
            kind="building",
            x=self.x,
            y=self.y,
            label=f"{self.name} ({self.building_type})",
            color=color_map.get(self.building_type, "#90e0ef"),
            size=max(self.width, self.height) / 2,
            shape="rect",
            properties={
                "building_type": self.building_type,
                "floors": self.floors,
                "occupants": list(self.occupants),
                **self.properties,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "building_type": self.building_type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "floors": self.floors,
            "occupants": list(self.occupants),
            "properties": dict(self.properties),
        }


@dataclass
class Road:
    """A pathway or road connecting two nodes or coordinates."""

    id: str = field(default_factory=lambda: f"road_{uuid.uuid4().hex[:8]}")
    name: str = "Road"
    start_pos: Tuple[float, float] = (0.0, 0.0)
    end_pos: Tuple[float, float] = (100.0, 0.0)
    road_type: str = "paved"  # dirt, paved, highway, cobble
    lanes: int = 2
    connected_nodes: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "road_type": self.road_type,
            "lanes": self.lanes,
            "connected_nodes": list(self.connected_nodes),
            "properties": dict(self.properties),
        }


@dataclass
class Character:
    """An interactive character or NPC residing in a world."""

    id: str = field(default_factory=lambda: f"char_{uuid.uuid4().hex[:8]}")
    name: str = "Citizen"
    role: str = "citizen"  # mayor, merchant, builder, citizen, explorer
    x: float = 0.0
    y: float = 0.0
    home_id: Optional[str] = None
    workplace_id: Optional[str] = None
    inventory: List[str] = field(default_factory=list)
    relationships: List[Tuple[str, str]] = field(default_factory=list)  # (rel_type, target_char_id)
    properties: Dict[str, Any] = field(default_factory=dict)

    def relate(self, rel_type: str, target_id: str) -> None:
        rel = (rel_type, target_id)
        if rel not in self.relationships:
            self.relationships.append(rel)

    def unrelate(self, rel_type: str, target_id: str) -> None:
        rel = (rel_type, target_id)
        if rel in self.relationships:
            self.relationships.remove(rel)

    def to_entity(self) -> WorldEntity:
        """Convert to a 2D entity representation."""
        color_map = {
            "mayor": "#e63946",
            "merchant": "#f1faee",
            "builder": "#a8dadc",
            "citizen": "#457b9d",
            "explorer": "#1d3557",
        }
        return WorldEntity(
            id=self.id,
            kind="character",
            x=self.x,
            y=self.y,
            label=f"{self.name} [{self.role}]",
            color=color_map.get(self.role, "#ffd166"),
            size=14.0,
            shape="circle",
            properties={
                "role": self.role,
                "home_id": self.home_id,
                "workplace_id": self.workplace_id,
                "inventory": list(self.inventory),
                **self.properties,
            },
            relationships=list(self.relationships),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "x": self.x,
            "y": self.y,
            "home_id": self.home_id,
            "workplace_id": self.workplace_id,
            "inventory": list(self.inventory),
            "relationships": list(self.relationships),
            "properties": dict(self.properties),
        }


@dataclass
class WorldMap:
    """2D tile/region map representation."""

    width: int = 30
    height: int = 20
    seed: int = 42
    terrain_grid: List[List[str]] = field(default_factory=list)  # "plains", "forest", "water", "mountain"
    properties: Dict[str, Any] = field(default_factory=dict)

    def get_terrain(self, x: int, y: int) -> str:
        if 0 <= y < len(self.terrain_grid) and 0 <= x < len(self.terrain_grid[0]):
            return self.terrain_grid[y][x]
        return "void"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "terrain_grid": [list(row) for row in self.terrain_grid],
            "properties": dict(self.properties),
        }
