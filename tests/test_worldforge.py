"""Tests for WorldForge (procedural worlds) module."""

import pytest
from nexora import App
from nexora.worldforge import (
    Building,
    Character,
    ProceduralGenerator,
    Road,
    WorldForge,
    WorldForgeEngine,
    WorldForgePlugin,
    WorldMap,
)


def test_worldforge_plugin_registration():
    app = App(features=["worldforge"])
    assert app.worldforge is not None
    assert isinstance(app.worldforge, WorldForgePlugin)
    assert app.worldforge.engine is not None
    app.run()


def test_building_creation_and_entity_conversion():
    engine = WorldForgeEngine()
    bldg = engine.create_building(
        name="Arcane Academy",
        building_type="town_hall",
        x=120.0,
        y=80.0,
        width=60.0,
        height=50.0,
        floors=3,
        secret_vault=True,
    )

    assert isinstance(bldg, Building)
    assert bldg.name == "Arcane Academy"
    assert bldg.building_type == "town_hall"
    assert bldg.floors == 3
    assert bldg.properties.get("secret_vault") is True

    # Test conversion to CodeWorld Entity
    entity = bldg.to_entity()
    assert entity.kind == "building"
    assert entity.x == 120.0
    assert entity.y == 80.0
    assert entity.properties["floors"] == 3


def test_road_creation():
    engine = WorldForgeEngine()
    road = engine.create_road(
        name="King's Highway",
        start_pos=(10.0, 20.0),
        end_pos=(150.0, 200.0),
        road_type="paved",
        lanes=4,
        connected_nodes=["bldg_1", "bldg_2"],
    )

    assert isinstance(road, Road)
    assert road.name == "King's Highway"
    assert road.start_pos == (10.0, 20.0)
    assert road.end_pos == (150.0, 200.0)
    assert road.lanes == 4
    assert "bldg_1" in road.connected_nodes


def test_character_creation_and_relationships():
    engine = WorldForgeEngine()
    bldg = engine.create_building(name="Town Hall", building_type="town_hall")

    c1 = engine.create_character("Eldrin", role="mayor", home_id=bldg.id, inventory=["Seal of Office"])
    c2 = engine.create_character("Mira", role="merchant", inventory=["Rare Spices"])

    assert c1.home_id == bldg.id
    assert c1.id in bldg.occupants
    assert "Seal of Office" in c1.inventory

    # Relationship
    engine.add_relationship(c1.id, "ally", c2.id)
    assert ("ally", c2.id) in c1.relationships

    entity = c1.to_entity()
    assert entity.kind == "character"
    assert entity.properties["role"] == "mayor"


def test_deterministic_procedural_generation_same_seed():
    """Verify that same seed produces the EXACT same map, buildings, roads, and characters."""
    gen1 = ProceduralGenerator(seed=777)
    map1, bldgs1, roads1, chars1 = gen1.generate_complete_world(
        width=18, height=12, num_buildings=5, num_roads=3, num_characters=4
    )

    gen2 = ProceduralGenerator(seed=777)
    map2, bldgs2, roads2, chars2 = gen2.generate_complete_world(
        width=18, height=12, num_buildings=5, num_roads=3, num_characters=4
    )

    # 1. Map matches exactly
    assert map1.width == map2.width == 18
    assert map1.height == map2.height == 12
    assert map1.terrain_grid == map2.terrain_grid

    # 2. Buildings match exactly
    assert len(bldgs1) == len(bldgs2) == 5
    for b1, b2 in zip(bldgs1, bldgs2):
        assert b1.id == b2.id
        assert b1.name == b2.name
        assert b1.building_type == b2.building_type
        assert b1.x == b2.x
        assert b1.y == b2.y
        assert b1.floors == b2.floors

    # 3. Roads match exactly
    assert len(roads1) == len(roads2) == 3
    for r1, r2 in zip(roads1, roads2):
        assert r1.id == r2.id
        assert r1.start_pos == r2.start_pos
        assert r1.end_pos == r2.end_pos
        assert r1.road_type == r2.road_type
        assert r1.lanes == r2.lanes

    # 4. Characters match exactly
    assert len(chars1) == len(chars2) == 4
    for c1, c2 in zip(chars1, chars2):
        assert c1.id == c2.id
        assert c1.name == c2.name
        assert c1.role == c2.role
        assert c1.inventory == c2.inventory
        assert c1.home_id == c2.home_id
        assert c1.relationships == c2.relationships


def test_different_seeds_produce_different_worlds():
    gen1 = ProceduralGenerator(seed=101)
    map1, bldgs1, _, _ = gen1.generate_complete_world(width=15, height=15)

    gen2 = ProceduralGenerator(seed=999)
    map2, bldgs2, _, _ = gen2.generate_complete_world(width=15, height=15)

    # Grids or building placements should differ
    grid_different = (map1.terrain_grid != map2.terrain_grid)
    positions_different = [(b1.x, b1.y) for b1 in bldgs1] != [(b2.x, b2.y) for b2 in bldgs2]
    assert grid_different or positions_different


def test_plugin_event_bus_emission():
    app = App(features=["worldforge"])
    events = []
    app.bus.on("worldforge.*", lambda ev: events.append(ev.type))

    bldg = app.worldforge.create_building("Windmill", "workshop", 50, 50)
    road = app.worldforge.create_road("Trail", (0, 0), (50, 50))
    c1 = app.worldforge.create_character("Miller", "builder")
    c2 = app.worldforge.create_character("Baker", "citizen")
    app.worldforge.relate(c1.id, "customer", c2.id)
    app.worldforge.generate(seed=42, num_buildings=3, num_roads=2, num_characters=3)

    assert "worldforge.building.created" in events
    assert "worldforge.road.created" in events
    assert "worldforge.character.created" in events
    assert "worldforge.character.related" in events
    assert "worldforge.generated" in events


def test_codeworld_integration_bridge():
    app = App(features=["world", "worldforge"])
    assert app.world is not None
    assert app.worldforge is not None

    bldg = app.worldforge.create_building("Central Bank", "commercial", 200, 150)
    char = app.worldforge.create_character("Banker", "merchant", 210, 155)

    # Verify entities appear automatically in CodeWorld World
    assert bldg.id in app.world.world
    assert char.id in app.world.world

    entity_bldg = app.world.world.get(bldg.id)
    assert entity_bldg.kind == "building"
    assert entity_bldg.x == 200


def test_export_world_and_clear():
    app = App(features=["worldforge"])
    app.worldforge.generate(seed=555, num_buildings=4, num_roads=2, num_characters=3)

    exported = app.worldforge.export_world()
    assert exported["seed"] == 555
    assert len(exported["buildings"]) == 4
    assert len(exported["roads"]) == 2
    assert len(exported["characters"]) == 3
    assert exported["map"] is not None

    app.worldforge.engine.clear()
    cleared = app.worldforge.export_world()
    assert len(cleared["buildings"]) == 0
    assert len(cleared["roads"]) == 0
    assert len(cleared["characters"]) == 0
