"""Example 2: CodeWorld ONLY (No GhostUI needed).

Demonstrates:
- Pure 2D entity modeling
- Complex network relationships
- Entity properties and dynamic movement
- Spatial queries (finding nearby nodes)
- World snapshot inspection
"""

from nexora import App

# 1. Initialize with ONLY the 'world' feature
app = App(features=["world"])


@app.task
def deploy_infrastructure():
    world = app.world
    print("\n--- [Step 1: Deploying Cloud Infrastructure] ---")

    # Create Gateway
    world.create("gateway", entity_id="api-gw", x=0, y=-150, color="#f72585", properties={"ip": "10.0.0.1"})

    # Create Microservices
    world.create("service", entity_id="auth-svc", x=-120, y=0, color="#4cc9f0", properties={"port": 5001})
    world.create("service", entity_id="order-svc", x=0, y=0, color="#4cc9f0", properties={"port": 5002})
    world.create("service", entity_id="payment-svc", x=120, y=0, color="#4cc9f0", properties={"port": 5003})

    # Create Databases & Caches
    world.create("cache", entity_id="redis-cache", x=-80, y=150, color="#7209b7")
    world.create("database", entity_id="postgres-db", x=80, y=150, color="#3a0ca3")

    # Wire up relationships
    world.relate("api-gw", "routes_to", "auth-svc")
    world.relate("api-gw", "routes_to", "order-svc")
    world.relate("api-gw", "routes_to", "payment-svc")
    world.relate("order-svc", "reads_cache", "redis-cache")
    world.relate("payment-svc", "persists_to", "postgres-db")

    print(f"Created {len(world.entities())} cloud infrastructure nodes.")


@app.task
def simulate_traffic_and_scaling():
    world = app.world
    print("\n--- [Step 2: Simulating Traffic & Auto-scaling] ---")

    # Simulate dynamic movement / rebalancing of order-svc
    world.move_by("order-svc", dx=10, dy=-10)

    # Update properties dynamically
    world.set_prop("order-svc", "cpu_percent", 78.4)
    world.set_prop("order-svc", "active_connections", 1420)
    world.set_prop("postgres-db", "disk_used_gb", 184)

    # Spatial query: What components are near the order service?
    nearby = world.entities_near(0, 0, radius=130)
    print(f"Nodes operating within 130px radius of cluster center: {[e.id for e in nearby]}")


@app.task
def inspect_world_state():
    world = app.world
    print("\n--- [Step 3: Complete World Snapshot] ---")
    for entity in world.entities():
        rels = [f"--[{r}]--> {t}" for r, t in entity.relationships] or ["none"]
        print(f"  • {entity.id:<14} ({entity.kind:<9}) pos=({entity.x:.0f}, {entity.y:.0f})")
        print(f"      Relationships : {', '.join(rels)}")
        print(f"      Properties    : {entity.properties}")


if __name__ == "__main__":
    app.run()
