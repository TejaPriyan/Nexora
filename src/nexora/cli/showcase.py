"""Packaged capability showcase runner for `nexora demo showcase`."""

from __future__ import annotations

import sys
import time

from ..app import App
from ..agentbox import DisallowedToolError, Sandbox
from ..security import PermissionDenied


def _separator(title: str) -> None:
    sys.stdout.flush()
    print("\n" + "=" * 75)
    print(f"  >>> {title}")
    print("=" * 75)
    sys.stdout.flush()


def run_showcase() -> None:
    """Demonstrate NEXORA's core modules and plugins in a self-contained run."""
    print("\n" + "#" * 75)
    print("       NEXORA -- FULL PLATFORM CAPABILITY SHOWCASE")
    print("#" * 75)

    _separator("MODULE 1: GhostUI (Zero-Config Terminal UI)")
    app_ghost = App(features=["ghost"])
    app_ghost.ghost.log("GhostUI initialized cleanly.", level="INFO")
    app_ghost.ghost.metric("cpu_usage_pct", 14.2, unit="%")
    app_ghost.ghost.table(
        title="Service Status",
        columns=["Service", "Health"],
        rows=[["auth-service", "Healthy"], ["billing-api", "Healthy"]],
    )

    _separator("MODULE 2: CodeWorld (2D Spatial Entity Graph)")
    app_world = App(features=["world"])
    app_world.world.create(kind="server", entity_id="srv-01", label="Gateway", x=0, y=0)
    app_world.world.create(kind="database", entity_id="db-01", label="Primary DB", x=150, y=50)
    app_world.world.relate("srv-01", "replicates_to", "db-01")
    for ent in app_world.world.entities():
        print(f"  * Entity [{ent.id}] '{ent.display_label}' at ({ent.x:.0f}, {ent.y:.0f})")

    _separator("MODULE 3: MoodUI (Adaptive Interaction Telemetry)")
    app_mood = App(features=["adaptive"])
    app_mood.adaptive.opt_in(reason="Showcase demo")
    for _ in range(4):
        app_mood.bus.emit("action", payload={"action": "power_command", "success": True})
    print(f"  * Interaction state: {app_mood.adaptive.current_state.value}")

    _separator("MODULE 4: Recall (Structured Memory with Secret Scrubbing)")
    app_recall = App(features=["memory"])
    mem = app_recall.memory.remember(
        "cloud_credentials",
        value={"provider": "AWS", "region": "us-west-2", "api_key": "sk-demo-secret"},
        tags=["cloud"],
    )
    print(f"  * Sanitized memory [{mem.id}]: {mem.value}")

    _separator("MODULE 5: TimeLoop (State Time-Travel & Checkpointing)")
    app_tl = App(features=["timeline"])
    app_tl.state.set("release_version", "1.0.0-rc1")
    s1 = app_tl.timeline.checkpoint("canary")
    app_tl.state.set("release_version", "1.0.0-prod")
    s2 = app_tl.timeline.checkpoint("prod")
    diff = app_tl.timeline.diff(s1.id, s2.id)
    print(f"  * Checkpoint diff: {diff.changed}")

    _separator("MODULE 6: Shadow (Observability Profiler)")
    app_shadow = App(features=["shadow"])

    @app_shadow.shadow.trace
    def sample_work() -> str:
        return "ok"

    sample_work()
    for name, stat in app_shadow.shadow.function_stats().items():
        print(f"  * [Profile] {name}: calls={stat.call_count}")

    _separator("MODULE 7: ScreenMind (Explicitly-Permissioned Vision)")
    app_vision = App(features=["vision"])
    try:
        app_vision.vision.screenshot()
    except PermissionDenied as err:
        print(f"  * Default Denied: {err}")
    app_vision.vision.grant_all("Showcase permission")
    try:
        from PIL import Image
        from ..vision import ScreenImage

        app_vision.vision.engine.set_capture_backend(
            lambda _reg: ScreenImage(Image.new("RGB", (64, 64), (240, 240, 240)))
        )
        img = app_vision.vision.screenshot()
        print(f"  * Permissioned capture: {img.width}x{img.height} pixels")
    except ImportError:
        print("  * Pillow extra not installed; vision permission gate verified")

    _separator("MODULE 8: WorldForge (Procedural World Generation)")
    app_forge = App(features=["worldforge"])
    wmap, buildings, _roads, chars = app_forge.worldforge.generate(
        seed=77, width=8, height=6, num_buildings=2, num_roads=1, num_characters=2
    )
    print(f"  * Procedural map {wmap.width}x{wmap.height}: {len(buildings)} buildings, {len(chars)} chars")

    _separator("MODULE 9: AgentBox (Sandboxed Autonomous Execution)")
    app_box = App(features=["agentbox"])
    app_box.agentbox.register_tool("ping", lambda host: f"pong:{host}", allow_by_default=True)
    app_box.agentbox.register_tool("wipe", lambda: "wiped", dangerous=True)
    app_box.permissions.grant("agentbox.tool.ping")
    print(f"  * Allowed tool output: {app_box.agentbox.execute_tool('ping', host='local')}")
    try:
        app_box.agentbox.execute_tool("wipe")
    except DisallowedToolError as err:
        print(f"  * Blocked dangerous tool: {err}")

    def routine(sb: Sandbox) -> str:
        sb.step()
        return sb.execute_tool("ping", host="sandbox")

    res = app_box.agentbox.run_agent(routine, allowed_tools={"ping"})
    print(f"  * Agent success={res.success}, steps={res.steps_taken}")

    _separator("MODULE 10: Cross-Module Interoperability")
    app_interop = App(features=["adaptive", "world", "worldforge"])
    app_interop.adaptive.opt_in(reason="Showcase interop")
    app_interop.worldforge.create_building("Central Command", "hq", 50, 50)
    print(f"  * Interop World entities: {len(app_interop.world.entities())}")
    print("\n  >>> SHOWCASE COMPLETE <<<\n")
