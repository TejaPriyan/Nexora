"""WorldForge plugin for NEXORA: generate and manage interactive worlds."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple

from ..plugins.base import Plugin
from .engine import WorldForgeEngine
from .models import Building, Character, Road, WorldMap

if TYPE_CHECKING:
    from ..app import App
    from ..events import Event


class WorldForgePlugin(Plugin):
    """WorldForge: interactive world generation and management.

    Creates maps, buildings, roads, characters, and relationships.
    Supports deterministic procedural generation with reproducible seeds.
    Emits events (worldforge.*, world.create, world.relate) for cross-module observability.
    Zero direct cross-module imports: interoperates purely through the shared EventBus.
    """

    name: ClassVar[str] = "worldforge"
    requires_extra: ClassVar[Optional[str]] = "world"
    milestone: ClassVar[str] = "M8"

    def __init__(
        self,
        app: "App",
        *,
        seed: int = 42,
        engine: Optional[WorldForgeEngine] = None,
    ) -> None:
        super().__init__(app)
        self.engine = engine or WorldForgeEngine(seed=seed)
        self._started = False

    # --- Lifecycle ---

    def on_register(self) -> None:
        self.engine.on_building_created = self._emit_world_building
        self.engine.on_character_created = self._emit_world_character
        self.engine.on_relationship_created = self._emit_world_relation
        self.app.bus.on("worldforge.generate", self._on_generate_event)

    def on_start(self) -> None:
        self._started = True

    def on_stop(self) -> None:
        self._started = False

    def _on_generate_event(self, event: "Event") -> None:
        seed = int(event.payload.get("seed", self.engine.seed))
        self.generate(seed=seed)

    def _emit_world_building(self, bldg: Building) -> None:
        color_map = {
            "residential": "#4ea8de",
            "commercial": "#56cfe1",
            "shop": "#72efdd",
            "town_hall": "#e76f51",
            "workshop": "#f4a261",
        }
        self.app.bus.emit(
            "world.create",
            source="worldforge",
            payload={
                "entity_id": bldg.id,
                "kind": "building",
                "x": bldg.x,
                "y": bldg.y,
                "label": f"{bldg.name} ({bldg.building_type})",
                "color": color_map.get(bldg.building_type, "#90e0ef"),
                "size": max(bldg.width, bldg.height) / 2,
                "shape": "rect",
                "properties": bldg.to_dict(),
            },
        )

    def _emit_world_character(self, char: Character) -> None:
        color_map = {
            "mayor": "#e63946",
            "merchant": "#f1faee",
            "builder": "#a8dadc",
            "citizen": "#457b9d",
            "explorer": "#1d3557",
        }
        self.app.bus.emit(
            "world.create",
            source="worldforge",
            payload={
                "entity_id": char.id,
                "kind": "character",
                "x": char.x,
                "y": char.y,
                "label": f"{char.name} [{char.role}]",
                "color": color_map.get(char.role, "#ffd166"),
                "size": 14.0,
                "shape": "circle",
                "properties": char.to_dict(),
            },
        )

    def _emit_world_relation(self, source_id: str, rel_type: str, target_id: str) -> None:
        self.app.bus.emit(
            "world.relate",
            source="worldforge",
            payload={
                "source_id": source_id,
                "rel_name": rel_type,
                "target_id": target_id,
            },
        )

    # --- Public API ---

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
        """Create a new building in the world."""
        bldg = self.engine.create_building(
            name=name,
            building_type=building_type,
            x=x,
            y=y,
            width=width,
            height=height,
            floors=floors,
            building_id=building_id,
            **properties,
        )
        self.app.bus.emit(
            "worldforge.building.created",
            source="worldforge",
            payload={"id": bldg.id, "name": bldg.name, "type": bldg.building_type, "x": bldg.x, "y": bldg.y},
        )
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
        """Create a road connecting two locations."""
        road = self.engine.create_road(
            name=name,
            start_pos=start_pos,
            end_pos=end_pos,
            road_type=road_type,
            lanes=lanes,
            connected_nodes=connected_nodes,
            road_id=road_id,
            **properties,
        )
        self.app.bus.emit(
            "worldforge.road.created",
            source="worldforge",
            payload={"id": road.id, "name": road.name, "start": start_pos, "end": end_pos},
        )
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
        """Create a character and place them in the world."""
        char = self.engine.create_character(
            name=name,
            role=role,
            x=x,
            y=y,
            home_id=home_id,
            workplace_id=workplace_id,
            inventory=inventory,
            char_id=char_id,
            **properties,
        )
        self.app.bus.emit(
            "worldforge.character.created",
            source="worldforge",
            payload={"id": char.id, "name": char.name, "role": char.role, "x": char.x, "y": char.y},
        )
        return char

    def relate(self, char_a_id: str, rel_type: str, char_b_id: str) -> None:
        """Create a social relationship between characters."""
        self.engine.add_relationship(char_a_id, rel_type, char_b_id)
        self.app.bus.emit(
            "worldforge.character.related",
            source="worldforge",
            payload={"source": char_a_id, "relation": rel_type, "target": char_b_id},
        )

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
        """Procedurally generate a complete, deterministic world."""
        world_map, buildings, roads, characters = self.engine.generate(
            seed=seed,
            width=width,
            height=height,
            num_buildings=num_buildings,
            num_roads=num_roads,
            num_characters=num_characters,
        )
        self.app.bus.emit(
            "worldforge.generated",
            source="worldforge",
            payload={
                "seed": seed if seed is not None else self.engine.seed,
                "buildings_count": len(buildings),
                "roads_count": len(roads),
                "characters_count": len(characters),
            },
        )
        return world_map, buildings, roads, characters

    def export_world(self) -> Dict[str, Any]:
        """Export serializable world dictionary."""
        return self.engine.export_dict()


# Alias
WorldForge = WorldForgePlugin
