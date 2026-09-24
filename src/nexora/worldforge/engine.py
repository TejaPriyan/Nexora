"""WorldForge engine: manages world entities, structures, roads, and procedural generation."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from .generator import ProceduralGenerator
from .models import Building, Character, Road, WorldMap


class WorldForgeEngine:
    """Thread-safe engine managing procedural and manual world structures."""

    def __init__(self, *, seed: int = 42) -> None:
        self._lock = threading.RLock()
        self.seed = seed
        self.generator = ProceduralGenerator(seed=seed)
        self.world_map: Optional[WorldMap] = None
        self.buildings: Dict[str, Building] = {}
        self.roads: Dict[str, Road] = {}
        self.characters: Dict[str, Character] = {}
        self.on_building_created: Optional[Callable[[Building], None]] = None
        self.on_character_created: Optional[Callable[[Character], None]] = None
        self.on_relationship_created: Optional[Callable[[str, str, str], None]] = None

    # --- Creation & Management ---

    def create_building(
        self,
        name: str,
        building_type: str = "residential",
        x: float = 0.0,
        y: float = 0.0,
        *,
        width: float = 40.0,
        height: float = 40.0,
        floors: int = 1,
        building_id: Optional[str] = None,
        **properties: Any,
    ) -> Building:
        """Create and place a building."""
        with self._lock:
            bldg = Building(
                id=building_id or Building().id,
                name=name,
                building_type=building_type,
                x=x,
                y=y,
                width=width,
                height=height,
                floors=floors,
                properties=properties,
            )
            self.buildings[bldg.id] = bldg
            if self.on_building_created:
                self.on_building_created(bldg)
            return bldg

    def create_road(
        self,
        name: str,
        start_pos: Tuple[float, float],
        end_pos: Tuple[float, float],
        *,
        road_type: str = "paved",
        lanes: int = 2,
        connected_nodes: Optional[List[str]] = None,
        road_id: Optional[str] = None,
        **properties: Any,
    ) -> Road:
        """Create a road segment."""
        with self._lock:
            road = Road(
                id=road_id or Road().id,
                name=name,
                start_pos=start_pos,
                end_pos=end_pos,
                road_type=road_type,
                lanes=lanes,
                connected_nodes=list(connected_nodes or []),
                properties=properties,
            )
            self.roads[road.id] = road
            return road

    def create_character(
        self,
        name: str,
        role: str = "citizen",
        x: float = 0.0,
        y: float = 0.0,
        *,
        home_id: Optional[str] = None,
        workplace_id: Optional[str] = None,
        inventory: Optional[List[str]] = None,
        char_id: Optional[str] = None,
        **properties: Any,
    ) -> Character:
        """Create and place an interactive character."""
        with self._lock:
            char = Character(
                id=char_id or Character().id,
                name=name,
                role=role,
                x=x,
                y=y,
                home_id=home_id,
                workplace_id=workplace_id,
                inventory=list(inventory or []),
                properties=properties,
            )
            self.characters[char.id] = char
            if home_id and home_id in self.buildings:
                self.buildings[home_id].occupants.append(char.id)
            if self.on_character_created:
                self.on_character_created(char)
            return char

    def add_relationship(self, char_a_id: str, rel_type: str, char_b_id: str) -> None:
        """Establish a relationship between world entities."""
        with self._lock:
            if char_a_id in self.characters:
                self.characters[char_a_id].relate(rel_type, char_b_id)
            if self.on_relationship_created:
                self.on_relationship_created(char_a_id, rel_type, char_b_id)

    # --- Procedural Generation ---

    def generate(
        self,
        *,
        seed: Optional[int] = None,
        width: int = 20,
        height: int = 15,
        num_buildings: int = 6,
        num_roads: int = 4,
        num_characters: int = 5,
    ) -> Tuple[WorldMap, List[Building], List[Road], List[Character]]:
        """Run deterministic procedural generation."""
        with self._lock:
            if seed is not None:
                self.seed = seed
                self.generator.set_seed(seed)

            world_map, buildings, roads, characters = self.generator.generate_complete_world(
                width=width,
                height=height,
                num_buildings=num_buildings,
                num_roads=num_roads,
                num_characters=num_characters,
            )

            self.world_map = world_map
            self.buildings = {b.id: b for b in buildings}
            self.roads = {r.id: r for r in roads}
            self.characters = {c.id: c for c in characters}

            if self.on_building_created:
                for bldg in buildings:
                    self.on_building_created(bldg)
            if self.on_character_created:
                for char in characters:
                    self.on_character_created(char)
            if self.on_relationship_created:
                for char in characters:
                    for rel_type, target_id in char.relationships:
                        self.on_relationship_created(char.id, rel_type, target_id)

            return world_map, buildings, roads, characters

    def clear(self) -> None:
        """Clear all world structures."""
        with self._lock:
            self.world_map = None
            self.buildings.clear()
            self.roads.clear()
            self.characters.clear()

    def export_dict(self) -> Dict[str, Any]:
        """Export serializable snapshot of the entire world."""
        with self._lock:
            return {
                "seed": self.seed,
                "map": self.world_map.to_dict() if self.world_map else None,
                "buildings": {k: v.to_dict() for k, v in self.buildings.items()},
                "roads": {k: v.to_dict() for k, v in self.roads.items()},
                "characters": {k: v.to_dict() for k, v in self.characters.items()},
            }
