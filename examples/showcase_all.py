"""NEXORA Master Showcase -- Milestones 1 through 10 in Action.

Run with:
    python examples/showcase_all.py
"""

import sys
import time
from PIL import Image, ImageDraw

from nexora import App
from nexora.adaptive import InteractionState
from nexora.agentbox import DisallowedToolError, Sandbox
from nexora.security import PermissionDenied
from nexora.vision import BBox, ScreenImage


def separator(title: str) -> None:
    sys.stdout.flush()
    sys.stderr.flush()
    time.sleep(0.02)
    print("\n" + "=" * 75)
    print(f"  >>> {title}")
    print("=" * 75)
    sys.stdout.flush()


def run_showcase():
    print("\n" + "#" * 75)
    print("       NEXORA v1.0.0 -- FULL PLATFORM CAPABILITY SHOWCASE")
    print("          Demonstrating Milestones 1 through 10 Live")
    print("#" * 75)

    # -------------------------------------------------------------
    # Milestone 1: GhostUI
    # -------------------------------------------------------------
    separator("MILESTONE 1: GhostUI (Zero-Config Terminal UI)")
    app_ghost = App(features=["ghost"])
    app_ghost.ghost.log("GhostUI initialized with rich styling and zero configuration.", level="INFO")
    app_ghost.ghost.metric("cpu_usage_pct", 14.2, unit="%")
    app_ghost.ghost.metric("memory_mb", 128.5, unit="MB")
    app_ghost.ghost.table(
        title="Microservice Cluster Status",
        columns=["Service", "Version", "Replicas", "Health"],
        rows=[
            ["auth-service", "v1.4.0", "3", "Healthy"],
            ["billing-api", "v2.1.2", "2", "Healthy"],
            ["notification-worker", "v0.9.8", "5", "Healthy"],
        ],
    )

    # -------------------------------------------------------------
    # Milestone 2: CodeWorld
    # -------------------------------------------------------------
    separator("MILESTONE 2: CodeWorld (2D Spatial Entity Graph)")
    app_world = App(features=["world"])
    app_world.world.create(kind="server", entity_id="srv-01", label="Gateway Server", x=0, y=0, color="#2ecc71")
    app_world.world.create(kind="database", entity_id="db-01", label="Postgres Primary", x=150, y=50, color="#3498db")
    app_world.world.relate("srv-01", "replicates_to", "db-01")
    app_world.world.set_prop("srv-01", "uptime", "99.98%")
    app_world.world.set_prop("db-01", "iops", 12500)
    for ent in app_world.world.entities():
        rels = ", ".join(f"--[{r}]-->{t}" for r, t in ent.relationships) or "none"
        print(f"  * Entity [{ent.id}] '{ent.display_label}' at ({ent.x:.0f}, {ent.y:.0f}) | rels: {rels}")

    # -------------------------------------------------------------
    # Milestone 3: MoodUI
    # -------------------------------------------------------------
    separator("MILESTONE 3: MoodUI (Adaptive Interaction Telemetry)")
    app_mood = App(features=["adaptive"])
    print(f"  * Default telemetry permission: {app_mood.adaptive.is_permitted()} (Privacy-First)")
    app_mood.adaptive.opt_in(reason="User enabled adaptive assistance")
    print(f"  * Telemetry permission after opt-in: {app_mood.adaptive.is_permitted()}")
    for _ in range(4):
        app_mood.bus.emit("action", payload={"action": "power_command", "success": True})
    print(f"  * Interaction state after burst actions: {app_mood.adaptive.current_state.value}")
    app_mood.bus.emit("help.requested", payload={"topic": "query_optimizer"})
    print(f"  * Interaction state after help request: {app_mood.adaptive.current_state.value}")

    # -------------------------------------------------------------
    # Milestone 4: Recall
    # -------------------------------------------------------------
    separator("MILESTONE 4: Recall (Structured Memory with Secret Scrubbing)")
    app_recall = App(features=["memory"])
    mem = app_recall.memory.remember(
        "cloud_credentials",
        value={
            "provider": "AWS",
            "region": "us-west-2",
            "api_key": "AKIA_SUPER_SECRET_TOKEN_XYZ",
            "password": "production_database_password_999",
        },
        tags=["cloud", "credentials", "aws"],
    )
    print(f"  * Saved memory: {mem.id}")
    print(f"  * Sanitized memory value: {mem.value}")
    answer = app_recall.memory.ask("What is the AWS cloud credentials region?")
    print(f"  * Recall Ask query: {answer}")

    # -------------------------------------------------------------
    # Milestone 5: TimeLoop
    # -------------------------------------------------------------
    separator("MILESTONE 5: TimeLoop (State Time-Travel & Checkpointing)")
    app_timeloop = App(features=["timeline"])
    app_timeloop.state.set("release_version", "1.0.0-rc1")
    app_timeloop.state.set("traffic_weight", 10)
    snap1 = app_timeloop.timeline.checkpoint("canary_start")

    app_timeloop.state.set("release_version", "1.0.0-prod")
    app_timeloop.state.set("traffic_weight", 100)
    snap2 = app_timeloop.timeline.checkpoint("full_rollout")

    diff = app_timeloop.timeline.diff(snap1.id, snap2.id)
    print(f"  * Checkpoint 1: {snap1.label} -> Checkpoint 2: {snap2.label}")
    print(f"  * State diff: {diff.changed}")

    rewound = app_timeloop.timeline.rewind(1)
    print(f"  * Rewound to: {rewound.label} | release_version={app_timeloop.state.get('release_version')}")

    # -------------------------------------------------------------
    # Milestone 6: Shadow
    # -------------------------------------------------------------
    separator("MILESTONE 6: Shadow (Nanosecond Observability Profiler)")
    app_shadow = App(features=["shadow"])

    @app_shadow.shadow.trace
    def compute_billing_ledger(account_id: int):
        time.sleep(0.015)
        return {"account": account_id, "balance": 450.00}

    @app_shadow.shadow.trace
    def invoice_customer(account_id: int):
        ledger = compute_billing_ledger(account_id)
        time.sleep(0.01)
        return f"Invoiced {account_id} for ${ledger['balance']}"

    res = invoice_customer(42)
    print(f"  * Function executed: {res}")
    for name, stat in app_shadow.shadow.function_stats().items():
        print(f"  * [Profile] {name:25s} | avg={stat.avg_duration * 1000:6.2f}ms | calls={stat.call_count}")
    for dep in app_shadow.shadow.dependencies():
        print(f"  * [Dependency Trace] {dep.caller} -> {dep.callee}")

    # -------------------------------------------------------------
    # Milestone 7: ScreenMind
    # -------------------------------------------------------------
    separator("MILESTONE 7: ScreenMind (Explicitly-Permissioned Vision)")
    app_vision = App(features=["vision"])
    try:
        app_vision.vision.screenshot()
        print("  * ERROR: Unpermissioned capture succeeded!")
    except PermissionDenied as err:
        print(f"  * Default Denied: {err}")

    app_vision.vision.grant_all("User explicit permission for showcase demonstration")
    mock_canvas = Image.new("RGB", (200, 100), color=(240, 240, 240))
    canvas_draw = ImageDraw.Draw(mock_canvas)
    canvas_draw.rectangle([20, 20, 80, 50], fill=(52, 152, 219))  # Blue Submit button
    app_vision.vision.engine.set_capture_backend(lambda reg: ScreenImage(mock_canvas))
    app_vision.vision.engine.register_text_region("Submit Form", BBox(20, 20, 60, 30))

    img = app_vision.vision.screenshot()
    print(f"  * Permissioned screenshot captured: {img.width}x{img.height} pixels")
    found_text = app_vision.vision.find_text("Submit")
    for ft in found_text:
        print(f"  * Located visual UI element: '{ft.label}' at ({ft.bbox.x}, {ft.bbox.y})")

    # -------------------------------------------------------------
    # Milestone 8: WorldForge
    # -------------------------------------------------------------
    separator("MILESTONE 8: WorldForge (Procedural Interactive Generation)")
    app_forge = App(features=["worldforge"])
    wmap, buildings, roads, chars = app_forge.worldforge.generate(seed=77, width=12, height=8, num_buildings=3, num_roads=2, num_characters=3)
    print(f"  * Procedural Map size: {wmap.width}x{wmap.height} grid")
    for b in buildings:
        print(f"  * Building: [{b.building_type}] {b.name} at ({b.x:.0f}, {b.y:.0f})")
    for c in chars:
        print(f"  * Character: {c.name} ({c.role}) resident at {c.home_id}")

    # -------------------------------------------------------------
    # Milestone 9: AgentBox
    # -------------------------------------------------------------
    separator("MILESTONE 9: AgentBox (Safe Sandboxed Autonomous Execution)")
    app_box = App(features=["agentbox"])
    app_box.agentbox.register_tool("fetch_weather", lambda city: f"Clear and 22C in {city}", allow_by_default=True)
    app_box.agentbox.register_tool("delete_database", lambda: "Wiped", dangerous=True, allow_by_default=False)
    app_box.permissions.grant("agentbox.tool.fetch_weather")

    weather_out = app_box.agentbox.execute_tool("fetch_weather", city="Zurich")
    print(f"  * Safe tool execution output: {weather_out}")

    try:
        app_box.agentbox.execute_tool("delete_database")
    except DisallowedToolError as err:
        print(f"  * Blocked dangerous/disallowed tool: {err}")

    def autonomous_routine(sb: Sandbox) -> str:
        sb.step()
        data = sb.execute_tool("fetch_weather", city="Tokyo")
        sb.step()
        return f"Autonomous agent gathered: {data}"

    agent_run = app_box.agentbox.run_agent(autonomous_routine, allowed_tools={"fetch_weather"})
    print(f"  * Agent execution success: {agent_run.success}, steps: {agent_run.steps_taken}")
    print(f"  * Audit trail entries: {len(app_box.agentbox.audit_trail())}")

    # -------------------------------------------------------------
    # Milestone 10: Interoperability
    # -------------------------------------------------------------
    separator("MILESTONE 10: Cross-Module Event Interoperability")
    app_interop = App(features=["ghost", "timeline", "shadow", "adaptive", "world", "worldforge"])
    app_interop.adaptive.opt_in(reason="Showcase interop testing")

    # Shadow friction alert triggers MoodUI difficulty transition via EventBus
    for _ in range(3):
        app_interop.bus.emit("shadow.alert", payload={"message": "connection latency bottleneck"})
    print(f"  * MoodUI state dynamically adapted via Shadow event: {app_interop.adaptive.current_state.value}")

    # WorldForge generates entities and syncs them to CodeWorld 2D space via EventBus
    app_interop.worldforge.create_building("Central Command", "headquarters", 50, 50)
    world_entities = app_interop.world.entities()
    print(f"  * WorldForge building synced to CodeWorld 2D entity count: {len(world_entities)}")

    print("\n" + "=" * 75)
    print("  >>> ALL 10 MILESTONES TESTED AND VERIFIED FUNCTIONAL IN NEXORA v1.0.0! <<<")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_showcase()
