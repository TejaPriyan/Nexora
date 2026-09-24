"""CodeWorld demo: 2D entity visualisation driven by events.

Run with:
    pip install nexora[world]     # installs pygame
    python examples/codeworld_demo.py

Without pygame the demo still runs; it just skips the render window.
"""

from nexora import App

app = App(features=["ghost", "world"])


@app.task(name="setup_topology")
def setup_topology():
    """Create a simple network topology in the world."""
    w = app.world

    # Create nodes
    server = w.create(kind="server", entity_id="srv-01", label="Web Server",
                      x=0, y=0, color="#43aa8b", size=30, shape="rect")
    db = w.create(kind="database", entity_id="db-01", label="PostgreSQL",
                  x=200, y=0, color="#577590", size=30, shape="diamond")
    cache = w.create(kind="cache", entity_id="cache-01", label="Redis Cache",
                     x=100, y=-120, color="#f9844a", size=25, shape="circle")
    client1 = w.create(kind="client", entity_id="cli-01", label="Browser A",
                       x=-180, y=-80, color="#4ea8de", size=20)
    client2 = w.create(kind="client", entity_id="cli-02", label="Browser B",
                       x=-180, y=80, color="#4ea8de", size=20)

    # Relationships
    w.relate("cli-01", "connects_to", "srv-01")
    w.relate("cli-02", "connects_to", "srv-01")
    w.relate("srv-01", "queries", "db-01")
    w.relate("srv-01", "caches_via", "cache-01")
    w.relate("cache-01", "backed_by", "db-01")

    # Properties
    w.set_prop("srv-01", "port", 8080)
    w.set_prop("srv-01", "status", "healthy")
    w.set_prop("db-01", "connections", 4)
    w.set_prop("cache-01", "hit_rate", "94%")


@app.task(name="simulate_traffic")
def simulate_traffic():
    """Simulate some movements and state changes."""
    w = app.world

    # Move a client closer
    w.move("cli-01", -100, -40)

    # Update server properties
    w.set_prop("srv-01", "requests", 1234)
    w.set_prop("srv-01", "latency_ms", 12)

    # Create a new entity via event (external command pattern)
    app.bus.emit("world.create", payload={
        "entity_id": "lb-01",
        "kind": "load_balancer",
        "label": "HAProxy",
        "x": -80,
        "y": 0,
        "color": "#f3722c",
        "size": 28,
        "shape": "diamond",
    })

    # Wire it into the topology
    w.relate("cli-01", "connects_to", "lb-01")
    w.relate("cli-02", "connects_to", "lb-01")
    w.relate("lb-01", "forwards_to", "srv-01")


@app.task(name="inspect_world")
def inspect_world():
    """Print a snapshot of the world."""
    w = app.world
    print(f"\n  World snapshot: {len(w.world)} entities")
    for ent in w.entities():
        rels = ", ".join(f"--[{r}]-->{t}" for r, t in ent.relationships) or "none"
        props = ", ".join(f"{k}={v}" for k, v in ent.properties.items()) or "none"
        print(f"    {ent.display_label:20s} ({ent.kind:15s}) "
              f"pos=({ent.x:.0f},{ent.y:.0f})  rels=[{rels}]  props=[{props}]")


if __name__ == "__main__":
    app.run()
