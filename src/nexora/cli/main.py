"""NEXORA command-line interface.

Deliberately stdlib-only (argparse) so `nexora doctor`/`nexora version`
always work even in the lightweight base install.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from .. import __version__
from ..plugins import available_features

# feature -> the import name of the module its pip extra installs
OPTIONAL_EXTRAS = {
    "ghost": "rich",
    "world": "pygame",
    "vision": "PIL",
}


def _is_installed(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"nexora {__version__}")
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    print(f"nexora {__version__} -- environment check\n")
    print("Core:        OK (stdlib only)")
    for feature, module_name in OPTIONAL_EXTRAS.items():
        status = "installed" if _is_installed(module_name) else "not installed"
        print(f"[{feature:<10}] extra -> {module_name:<8} : {status}")
    ai_status = "installed" if _is_installed("numpy") else "not installed"
    print(f"[{'ai':<10}] extra -> numpy    : {ai_status}\n")
    print("Planned features / status (see docs/ROADMAP.md):")
    for name, plugin_cls in sorted(available_features().items()):
        is_planned = "Planned" in getattr(plugin_cls, "__name__", "")
        status = "planned" if is_planned else "ready"
        print(f"  [{status:<7}] {name}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    feature = getattr(args, "feature", None) or getattr(args, "command", "showcase")
    feature = str(feature).lower()

    if feature == "ghost":
        from ..app import App
        app = App(features=["ghost"])

        @app.task(name="system_metrics_collector")
        def run_metrics():
            app.ghost.log("GhostUI is actively monitoring tasks and metrics.", level="INFO")
            for i in range(1, 4):
                app.ghost.progress("batch_indexing", completed=i * 33, total=100, unit="%")
            app.ghost.metric("active_threads", 8, unit="workers")
            app.ghost.metric("cluster_health", 99.8, unit="%")
            app.ghost.table(
                title="GhostUI Node Fleet",
                columns=["Node", "Region", "Health"],
                rows=[["node-primary", "us-east-1", "Optimal"], ["node-replica", "us-west-2", "Optimal"]],
            )

        app.run()
        return 0

    elif feature == "world":
        from ..app import App
        app = App(features=["world"])
        app.world.create(kind="server", entity_id="srv-1", label="Gateway Server", x=0, y=0)
        app.world.create(kind="database", entity_id="db-1", label="Postgres DB", x=150, y=50)
        app.world.relate("srv-1", "connects_to", "db-1")
        print("\n=== NEXORA CodeWorld 2D Entity Graph ===")
        for ent in app.world.entities():
            rels = ", ".join(f"--[{r}]-->{t}" for r, t in ent.relationships) or "none"
            print(f"  * Entity [{ent.id}] '{ent.display_label}' at ({ent.x:.0f}, {ent.y:.0f}) | rels: {rels}")
        return 0

    elif feature == "agentbox":
        from ..app import App
        app = App(features=["agentbox"])
        app.agentbox.register_tool("search_docs", lambda q: f"Found doc: {q}", allow_by_default=True)
        app.permissions.grant("agentbox.tool.search_docs")
        print("\n=== NEXORA AgentBox Sandboxed Execution ===")
        res = app.agentbox.execute_tool("search_docs", q="getting started")
        print(f"  * Safe tool execution output: {res}")
        print(f"  * Audit trail length: {len(app.agentbox.audit_trail())}")
        return 0

    elif feature == "memory":
        from ..app import App
        app = App(features=["memory"])
        app.memory.remember("api_endpoint", "https://api.internal.net", tags=["network"])
        print("\n=== NEXORA Recall Memory ===")
        for item in app.memory.timeline():
            print(f"  * Memory [{item.id}] -> {item.value} (tags: {item.tags})")
        return 0

    elif feature == "timeline":
        from ..app import App
        app = App(features=["timeline"])
        app.state.set("tier", "silver")
        s1 = app.timeline.checkpoint("v1")
        app.state.set("tier", "platinum")
        s2 = app.timeline.checkpoint("v2")
        diff = app.timeline.diff(s1.id, s2.id)
        print("\n=== NEXORA TimeLoop State Rewind ===")
        print(f"  * Checkpoint diff: {diff.changed}")
        return 0

    elif feature == "shadow":
        import time
        from ..app import App
        app = App(features=["shadow"])

        @app.shadow.trace
        def compute_analytics():
            time.sleep(0.01)
            return "done"

        compute_analytics()
        print("\n=== NEXORA Shadow Observability Profiler ===")
        for name, stat in app.shadow.function_stats().items():
            print(f"  * Profile [{name}]: avg={stat.avg_duration * 1000:.2f}ms, calls={stat.call_count}")
        return 0

    elif feature == "vision":
        from PIL import Image
        from ..app import App
        from ..vision import ScreenImage
        app = App(features=["vision"])
        app.vision.grant_all("CLI demo")
        app.vision.engine.set_capture_backend(lambda r: ScreenImage(Image.new("RGB", (100, 100), (255, 255, 255))))
        img = app.vision.screenshot()
        print("\n=== NEXORA ScreenMind Vision ===")
        print(f"  * Permissioned capture: {img.width}x{img.height} pixels")
        return 0

    elif feature == "worldforge":
        from ..app import App
        app = App(features=["worldforge"])
        wmap, buildings, roads, chars = app.worldforge.generate(seed=12, width=8, height=6, num_buildings=2, num_roads=1, num_characters=2)
        print("\n=== NEXORA WorldForge Procedural Generation ===")
        print(f"  * Map: {wmap.width}x{wmap.height} grid")
        for b in buildings:
            print(f"  * Building: [{b.building_type}] {b.name}")
        for c in chars:
            print(f"  * Character: {c.name} ({c.role})")
        return 0

    elif feature in ("adaptive", "mood"):
        from ..app import App
        app = App(features=["adaptive"])
        app.adaptive.opt_in(reason="CLI demo")
        for _ in range(4):
            app.bus.emit("action", payload={"action": "click", "success": True})
        print("\n=== NEXORA MoodUI Adaptive Interfaces ===")
        print(f"  * Interaction state: {app.adaptive.current_state.value}")
        return 0

    else:
        print("\nRunning NEXORA Showcase...")
        from ...examples.showcase_all import run_showcase
        run_showcase()
        return 0


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.path)
    target.mkdir(parents=True, exist_ok=True)
    app_file = target / "app.py"
    if app_file.exists() and not args.force:
        print(f"{app_file} already exists (use --force to overwrite)")
        return 1
    app_file.write_text(
        '"""A new NEXORA application, scaffolded by `nexora init`."""\n\n'
        "from nexora import App\n\n"
        "app = App()\n\n\n"
        "@app.task\n"
        "def hello():\n"
        '    print("Hello from NEXORA!")\n\n\n'
        'if __name__ == "__main__":\n'
        "    app.run()\n"
    )
    print(f"Created {app_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nexora", description="NEXORA runtime CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version", help="Print the installed nexora version").set_defaults(
        func=cmd_version
    )

    sub.add_parser(
        "doctor", help="Check which optional extras are installed"
    ).set_defaults(func=cmd_doctor)

    init_parser = sub.add_parser("init", help="Scaffold a new NEXORA app")
    init_parser.add_argument("path", nargs="?", default=".", help="Target directory")
    init_parser.add_argument(
        "--force", action="store_true", help="Overwrite an existing app.py"
    )
    init_parser.set_defaults(func=cmd_init)

    demo_parser = sub.add_parser("demo", help="Run a live feature demo")
    demo_parser.add_argument(
        "feature",
        nargs="?",
        default="showcase",
        choices=["ghost", "world", "adaptive", "memory", "timeline", "shadow", "vision", "worldforge", "agentbox", "showcase"],
        help="Feature to demonstrate",
    )
    demo_parser.set_defaults(func=cmd_demo)

    # Feature shortcuts so `nexora ghost`, `nexora world`, etc. work directly
    for feat in ["ghost", "world", "adaptive", "memory", "timeline", "shadow", "vision", "worldforge", "agentbox"]:
        feat_parser = sub.add_parser(feat, help=f"Run live {feat} demo")
        feat_parser.set_defaults(func=cmd_demo, feature=feat)

    return parser


def main(argv: "list[str] | None" = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
