"""Deterministic procedural generator for WorldForge."""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from .models import Building, Character, Road, WorldMap


class ProceduralGenerator:
    """Generates deterministic worlds from Python parameters given a seed."""

    TERRAIN_TYPES = ["plains", "forest", "mountain", "water"]
    BUILDING_TYPES = ["residential", "commercial", "shop", "town_hall", "workshop"]
    FIRST_NAMES = ["Alden", "Bria", "Cyrus", "Daphne", "Elian", "Fiona", "Gareth", "Halia", "Iris", "Jarek"]
    LAST_NAMES = ["Vance", "Thorne", "Sterling", "Mercer", "Blackwood", "Rivers", "Ashford", "Stone", "Waverly"]
    ROLES = ["mayor", "merchant", "builder", "citizen", "explorer"]

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self._rng = random.Random(seed)

    def set_seed(self, seed: int) -> None:
        self.seed = seed
        self._rng = random.Random(seed)

    def generate_map(
        self,
        width: int = 20,
        height: int = 15,
        *,
        water_ratio: float = 0.1,
        forest_ratio: float = 0.2,
        mountain_ratio: float = 0.1,
    ) -> WorldMap:
        """Deterministically generate terrain grid."""
        grid: List[List[str]] = []
        for _y in range(height):
            row: List[str] = []
            for _x in range(width):
                roll = self._rng.random()
                if roll < water_ratio:
                    row.append("water")
                elif roll < water_ratio + forest_ratio:
                    row.append("forest")
                elif roll < water_ratio + forest_ratio + mountain_ratio:
                    row.append("mountain")
                else:
                    row.append("plains")
            grid.append(row)

        return WorldMap(width=width, height=height, seed=self.seed, terrain_grid=grid)

    def generate_buildings(
        self,
        world_map: WorldMap,
        count: int = 6,
    ) -> List[Building]:
        """Deterministically generate and position buildings on valid terrain."""
        buildings: List[Building] = []
        cell_size = 40.0
        used_cells = set()

        # Always generate one town hall first
        b_types = ["town_hall"] + [
            self._rng.choice(["residential", "commercial", "shop", "workshop"])
            for _ in range(count - 1)
        ]

        for idx, b_type in enumerate(b_types):
            # Find a non-water cell
            placed = False
            for _ in range(100):
                cx = self._rng.randint(1, max(1, world_map.width - 2))
                cy = self._rng.randint(1, max(1, world_map.height - 2))
                if (cx, cy) not in used_cells and world_map.get_terrain(cx, cy) != "water":
                    used_cells.add((cx, cy))
                    bldg = Building(
                        id=f"bldg_{self.seed}_{idx + 1}",
                        name=f"{b_type.replace('_', ' ').title()} {idx + 1}",
                        building_type=b_type,
                        x=cx * cell_size,
                        y=cy * cell_size,
                        width=32.0,
                        height=32.0,
                        floors=self._rng.randint(1, 3),
                    )
                    buildings.append(bldg)
                    placed = True
                    break

            if not placed:
                # Fallback placement
                buildings.append(
                    Building(
                        id=f"bldg_{self.seed}_{idx + 1}",
                        name=f"{b_type.title()} {idx + 1}",
                        building_type=b_type,
                        x=float((idx + 1) * 45),
                        y=float((idx + 1) * 35),
                    )
                )

        return buildings

    def generate_roads(
        self,
        buildings: List[Building],
        count: int = 4,
    ) -> List[Road]:
        """Deterministically generate connecting road segments between buildings."""
        roads: List[Road] = []
        if len(buildings) < 2:
            return roads

        connected_pairs = set()
        for idx in range(min(count, len(buildings) * (len(buildings) - 1) // 2)):
            # Pick two distinct buildings
            b1 = self._rng.choice(buildings)
            b2 = self._rng.choice([b for b in buildings if b.id != b1.id])
            pair = tuple(sorted([b1.id, b2.id]))
            if pair in connected_pairs:
                continue
            connected_pairs.add(pair)

            road = Road(
                id=f"road_{self.seed}_{idx + 1}",
                name=f"Road {b1.name} - {b2.name}",
                start_pos=(b1.x, b1.y),
                end_pos=(b2.x, b2.y),
                road_type=self._rng.choice(["paved", "dirt", "cobble"]),
                lanes=self._rng.choice([1, 2]),
                connected_nodes=[b1.id, b2.id],
            )
            roads.append(road)

        return roads

    def generate_characters(
        self,
        buildings: List[Building],
        count: int = 5,
    ) -> List[Character]:
        """Deterministically generate characters, assign homes, and create social bonds."""
        characters: List[Character] = []
        residential_bldgs = [b for b in buildings if b.building_type in ("residential", "town_hall")]
        work_bldgs = [b for b in buildings if b.building_type in ("commercial", "shop", "workshop", "town_hall")]

        for idx in range(count):
            first = self._rng.choice(self.FIRST_NAMES)
            last = self._rng.choice(self.LAST_NAMES)
            role = self.ROLES[idx % len(self.ROLES)]

            home = self._rng.choice(residential_bldgs) if residential_bldgs else (buildings[0] if buildings else None)
            work = self._rng.choice(work_bldgs) if work_bldgs else (buildings[-1] if buildings else None)

            char_id = f"char_{self.seed}_{idx + 1}"
            x = home.x + self._rng.uniform(-10, 10) if home else float(idx * 20)
            y = home.y + self._rng.uniform(-10, 10) if home else float(idx * 20)

            char = Character(
                id=char_id,
                name=f"{first} {last}",
                role=role,
                x=x,
                y=y,
                home_id=home.id if home else None,
                workplace_id=work.id if work else None,
                inventory=[self._rng.choice(["map", "compass", "gold", "tools", "potion", "key"])],
            )
            if home:
                home.occupants.append(char_id)
            characters.append(char)

        # Generate relationships deterministically
        rel_types = ["friend", "coworker", "rival", "trade_partner", "neighbor"]
        for char in characters:
            possible_others = [c for c in characters if c.id != char.id]
            if possible_others and self._rng.random() < 0.7:
                target = self._rng.choice(possible_others)
                rel = self._rng.choice(rel_types)
                char.relate(rel, target.id)

        return characters

    def generate_complete_world(
        self,
        width: int = 20,
        height: int = 15,
        num_buildings: int = 6,
        num_roads: int = 4,
        num_characters: int = 5,
    ) -> Tuple[WorldMap, List[Building], List[Road], List[Character]]:
        """Generate all world elements deterministically in one cohesive pass."""
        world_map = self.generate_map(width, height)
        buildings = self.generate_buildings(world_map, count=num_buildings)
        roads = self.generate_roads(buildings, count=num_roads)
        characters = self.generate_characters(buildings, count=num_characters)
        return world_map, buildings, roads, characters
