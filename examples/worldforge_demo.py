"""Demonstration of WorldForge (interactive procedural world generation) in NEXORA."""

from nexora import App


def main() -> None:
    app = App(features=["worldforge"])
    worldforge = app.worldforge
    assert worldforge is not None

    print("=== NEXORA WorldForge Procedural Generation Demo ===")

    # 1. Deterministic generation with seed 42
    print("\n1. Generating complete interactive world (seed=42)...")
    world_map, buildings, roads, characters = worldforge.generate(
        seed=42,
        width=16,
        height=10,
        num_buildings=5,
        num_roads=3,
        num_characters=4,
    )

    print(f" - Generated map: {world_map.width}x{world_map.height} tiles")
    print(f" - Generated {len(buildings)} buildings:")
    for b in buildings:
        print(f"   * [{b.building_type}] {b.name} at ({b.x:.1f}, {b.y:.1f}) with {b.floors} floors")

    print(f" - Generated {len(roads)} road networks:")
    for r in roads:
        print(f"   * {r.name} ({r.road_type}, {r.lanes} lanes)")

    print(f" - Generated {len(characters)} characters:")
    for c in characters:
        rels = ", ".join(f"{r}->{tid}" for r, tid in c.relationships) or "none"
        print(f"   * {c.name} ({c.role}) | Home: {c.home_id} | Relationships: {rels}")

    # 2. Manual World Extensions
    print("\n2. Manually creating a custom outpost and NPC...")
    outpost = worldforge.create_building("Frontier Outpost", "workshop", 450, 300, floors=2)
    guard = worldforge.create_character("Captain Thorne", "explorer", 455, 305, home_id=outpost.id)
    worldforge.relate(guard.id, "protects", outpost.id)
    print(f" - Created {outpost.name} and {guard.name}")

    # 3. Export snapshot
    world_data = worldforge.export_world()
    print(f"\n3. Exported world snapshot containing {len(world_data['buildings'])} total buildings.")

    print("\nWorldForge procedural generation completed successfully!")


if __name__ == "__main__":
    main()
