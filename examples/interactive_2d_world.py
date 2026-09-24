"""Interactive 2D CodeWorld Visualizer Window.

This script opens the real 2D Pygame window on your screen so you can
interact with the visual graph!

Controls:
  - Mouse Click : Select & inspect any node
  - W / A / S / D or Arrows : Pan the 2D camera
  - + / - : Zoom in and out
  - R : Reset camera view
  - ESC or Close (X) : Exit the window
"""

import time
from nexora import App

# 1. Start App with CodeWorld enabled
app = App(features=["world"])

# 2. Build the visual topology
world = app.world

# Gateway
world.create("gateway", entity_id="api-gw", label="API Gateway",
             x=0, y=-150, color="#f72585", size=32, shape="diamond",
             properties={"ip": "10.0.0.1", "status": "active"})

# Microservices
world.create("service", entity_id="auth-svc", label="Auth Service",
             x=-140, y=0, color="#4cc9f0", size=26, shape="rect",
             properties={"port": 5001, "auth_type": "JWT"})

world.create("service", entity_id="order-svc", label="Order Service",
             x=0, y=0, color="#4895ef", size=28, shape="rect",
             properties={"port": 5002, "load": "normal"})

world.create("service", entity_id="payment-svc", label="Payment Service",
             x=140, y=0, color="#4361ee", size=26, shape="rect",
             properties={"port": 5003, "gateway": "Stripe"})

# Cache & Databases
world.create("cache", entity_id="redis-cache", label="Redis Cache",
             x=-90, y=140, color="#7209b7", size=24, shape="circle",
             properties={"hit_rate": "96.4%"})

world.create("database", entity_id="postgres-db", label="PostgreSQL DB",
             x=90, y=140, color="#3a0ca3", size=30, shape="diamond",
             properties={"connections": 18, "disk_gb": 240})

# Connecting Relationships
world.relate("api-gw", "routes_to", "auth-svc")
world.relate("api-gw", "routes_to", "order-svc")
world.relate("api-gw", "routes_to", "payment-svc")
world.relate("order-svc", "reads_cache", "redis-cache")
world.relate("payment-svc", "persists_to", "postgres-db")
world.relate("auth-svc", "queries", "postgres-db")

print("\n" + "=" * 60)
print("  🚀 OPENING 2D CODEWORLD PYGAME WINDOW...")
print("=" * 60)
print("  Controls inside the 2D window:")
print("    • Click any node to inspect properties")
print("    • W / A / S / D or Arrow Keys to Pan camera")
print("    • + / - to Zoom in and out")
print("    • Press ESC or close the window (X) when done")
print("=" * 60 + "\n")

# Open and run the interactive 2D window loop directly on the main thread
from nexora.world.renderer import Renderer

renderer = Renderer(
    world.world,
    width=900,
    height=650,
    title="NEXORA CodeWorld -- 2D Interactive Execution Map",
)
renderer.run_loop()

print("Window closed. CodeWorld run complete!")
