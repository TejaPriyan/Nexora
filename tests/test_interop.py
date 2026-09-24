"""Integration tests verifying event-based interoperability across all NEXORA modules."""

import ast
import os
from pathlib import Path
import pytest

from nexora import App
from nexora.adaptive import InteractionState


def test_ghostui_renders_timeloop_events():
    """Verify GhostUI subscribes to and renders TimeLoop checkpoint/restore events."""
    app = App(features=["ghost", "timeline"])
    app.state.set("user_count", 42)

    # Trigger TimeLoop checkpoint
    snap = app.timeloop.checkpoint("savepoint_alpha")
    assert snap is not None

    # Check that GhostUI received the checkpoint event and logged it
    checkpoint_logs = [log for log in app.ghost.logs if "[TimeLoop] Checkpoint 'savepoint_alpha'" in log.message]
    assert len(checkpoint_logs) >= 1
    assert checkpoint_logs[0].source == "timeline"

    # Trigger TimeLoop restore / rewind
    app.timeloop.rewind(steps=1)
    rewind_logs = [log for log in app.ghost.logs if "[TimeLoop] Restored state" in log.message]
    assert len(rewind_logs) >= 1


def test_shadow_alerts_consumed_by_moodui():
    """Verify Shadow's error and task alert observations are consumed by MoodUI via events."""
    app = App(features=["shadow", "adaptive"])
    app.adaptive.opt_in()

    assert app.adaptive.engine._consecutive_errors == 0
    assert len(app.adaptive.engine._recent_errors) == 0

    # Emit shadow alert (e.g. from shadow failure observation)
    app.bus.emit(
        "shadow.alert",
        source="shadow",
        payload={"error": "Database connection drop observed", "source": "task:db_sync"},
    )

    # MoodUI must have ingested the error signal via EventBus
    assert app.adaptive.engine._consecutive_errors >= 1
    recent = list(app.adaptive.engine._recent_errors)
    assert len(recent) >= 1
    assert any("shadow:Database connection drop" in err.name for err in recent)


def test_worldforge_populates_codeworld_via_eventbus():
    """Verify WorldForge generates entities that CodeWorld observes purely through events."""
    app = App(features=["world", "worldforge"])

    bldg = app.worldforge.create_building("Grand Fortress", "town_hall", 150.0, 220.0)
    char = app.worldforge.create_character("Commander", "explorer", 160.0, 230.0)
    app.worldforge.relate(char.id, "guards", bldg.id)

    # Verify CodeWorld captured the entities and relation from the EventBus
    assert bldg.id in app.world.world
    assert char.id in app.world.world

    ent_bldg = app.world.world.get(bldg.id)
    assert ent_bldg.kind == "building"
    assert ent_bldg.x == 150.0

    ent_char = app.world.world.get(char.id)
    assert ent_char.kind == "character"
    assert ("guards", bldg.id) in ent_char.relationships


def test_agentbox_memory_and_timeline_interop():
    """Verify AgentBox, Recall memory, and TimeLoop collaborate through the shared App context."""
    app = App(features=["agentbox", "memory", "timeline"])

    def record_finding(topic: str, notes: str) -> str:
        app.recall.remember(f"{topic}: {notes}", tags=["agent_finding"])
        app.state.set("last_topic", topic)
        app.timeloop.checkpoint(f"agent_{topic}")
        return "recorded"

    app.agentbox.register_tool("record", record_finding, allow_by_default=True)
    app.permissions.grant("agentbox.tool.record")

    # Agent executes tool
    res = app.agentbox.execute_tool("record", topic="security", notes="all ports clean")
    assert res == "recorded"

    # Memory has item
    memories = app.recall.search("security")
    assert len(memories) >= 1
    assert "all ports clean" in memories[0].content

    # TimeLoop has snapshot
    history = app.timeloop.history()
    assert any(snap.label == "agent_security" for snap in history)
    assert app.state.get("last_topic") == "security"


def test_zero_direct_cross_module_imports():
    """Enforce architectural purity: zero direct cross-module imports between feature packages."""
    src_dir = Path(__file__).resolve().parent.parent / "src" / "nexora"
    feature_modules = {
        "adaptive",
        "agentbox",
        "ghost",
        "memory",
        "shadow",
        "timeline",
        "vision",
        "world",
        "worldforge",
    }

    violations = []

    for mod_name in feature_modules:
        mod_dir = src_dir / mod_name
        if not mod_dir.is_dir():
            continue

        for py_file in mod_dir.glob("**/*.py"):
            code = py_file.read_text(encoding="utf-8")
            tree = ast.parse(code, filename=str(py_file))

            for node in ast.walk(tree):
                # Check ImportFrom: e.g. from ..world import ... or from nexora.world import ...
                if isinstance(node, ast.ImportFrom):
                    target_module = node.module or ""
                    # Check relative imports: level == 2 means from ..something
                    if node.level == 2:
                        first_part = target_module.split(".")[0]
                        if first_part in feature_modules and first_part != mod_name:
                            violations.append(
                                f"{py_file.relative_to(src_dir)} imports from sibling feature module '{first_part}' (line {node.lineno})"
                            )
                    # Check absolute imports: from nexora.world import ...
                    elif target_module.startswith("nexora."):
                        parts = target_module.split(".")
                        if len(parts) >= 2 and parts[1] in feature_modules and parts[1] != mod_name:
                            violations.append(
                                f"{py_file.relative_to(src_dir)} imports from feature module '{parts[1]}' (line {node.lineno})"
                            )

    assert not violations, "Direct cross-module imports detected:\n" + "\n".join(violations)
