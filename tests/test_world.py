"""Tests for CodeWorld (Milestone 2): models, plugin, EventBus integration."""

import pytest
from unittest.mock import patch

from nexora import App
from nexora.world import Entity, World, WorldPlugin, CodeWorld, Renderer


# ── Entity unit tests ──────────────────────────────────────────────────

class TestEntity:

    def test_default_creation(self):
        e = Entity()
        assert e.kind == "entity"
        assert e.x == 0.0 and e.y == 0.0
        assert e.color == "#4ea8de"
        assert e.shape == "circle"
        assert e.visible is True
        assert e.properties == {}
        assert e.relationships == []

    def test_display_label_falls_back_to_kind(self):
        e = Entity(kind="sensor")
        assert e.display_label == "sensor"
        e.label = "Temperature Probe"
        assert e.display_label == "Temperature Probe"

    def test_move_and_move_by(self):
        e = Entity(x=10, y=20)
        old = e.move(50, 60)
        assert old == (10, 20)
        assert e.x == 50 and e.y == 60

        old = e.move_by(-10, 5)
        assert old == (50, 60)
        assert e.x == 40 and e.y == 65

    def test_relate_and_unrelate(self):
        e = Entity()
        e.relate("follows", "abc")
        assert ("follows", "abc") in e.relationships
        # Duplicate is a no-op
        e.relate("follows", "abc")
        assert len(e.relationships) == 1

        e.unrelate("follows", "abc")
        assert e.relationships == []
        # Unrelating non-existent is safe
        e.unrelate("follows", "xyz")

    def test_set_prop_and_get_prop(self):
        e = Entity()
        old = e.set_prop("temp", 22.5)
        assert old is None
        assert e.get_prop("temp") == 22.5
        old = e.set_prop("temp", 25.0)
        assert old == 22.5
        assert e.get_prop("missing", "default") == "default"

    def test_to_dict(self):
        e = Entity(id="e1", kind="node", x=1, y=2, color="#fff", shape="rect")
        d = e.to_dict()
        assert d["id"] == "e1"
        assert d["kind"] == "node"
        assert d["x"] == 1
        assert d["shape"] == "rect"
        assert isinstance(d["properties"], dict)
        assert isinstance(d["relationships"], list)


# ── World unit tests ───────────────────────────────────────────────────

class TestWorld:

    def test_create_and_get(self):
        w = World()
        ent = w.create(kind="server", x=10, y=20, label="web-01")
        assert ent.kind == "server"
        assert w.get(ent.id) is ent
        assert ent.id in w
        assert len(w) == 1

    def test_add_and_remove(self):
        w = World()
        e = Entity(id="e1", kind="sensor")
        w.add(e)
        assert "e1" in w
        removed = w.remove("e1")
        assert removed is e
        assert "e1" not in w
        assert w.remove("nonexistent") is None

    def test_move_and_move_by(self):
        w = World()
        ent = w.create(entity_id="m1", x=0, y=0)
        w.move("m1", 100, 200)
        assert ent.x == 100 and ent.y == 200
        w.move_by("m1", -50, 10)
        assert ent.x == 50 and ent.y == 210
        # Move non-existent is safe
        w.move("no_such", 0, 0)
        w.move_by("no_such", 1, 1)

    def test_set_prop(self):
        w = World()
        ent = w.create(entity_id="p1")
        w.set_prop("p1", "temperature", 42)
        assert ent.get_prop("temperature") == 42
        # Set on non-existent is safe
        w.set_prop("no_such", "key", "val")

    def test_relate_and_unrelate(self):
        w = World()
        a = w.create(entity_id="a")
        b = w.create(entity_id="b")
        w.relate("a", "depends_on", "b")
        assert ("depends_on", "b") in a.relationships
        w.unrelate("a", "depends_on", "b")
        assert ("depends_on", "b") not in a.relationships
        # On non-existent entity is safe
        w.relate("no_such", "x", "b")
        w.unrelate("no_such", "x", "b")

    def test_entities_by_kind(self):
        w = World()
        w.create(kind="task", entity_id="t1")
        w.create(kind="task", entity_id="t2")
        w.create(kind="sensor", entity_id="s1")
        assert len(w.entities_by_kind("task")) == 2
        assert len(w.entities_by_kind("sensor")) == 1
        assert len(w.entities_by_kind("other")) == 0

    def test_entities_in_rect(self):
        w = World()
        w.create(entity_id="in1", x=5, y=5)
        w.create(entity_id="in2", x=15, y=15)
        w.create(entity_id="out", x=50, y=50)
        result = w.entities_in_rect(0, 0, 20, 20)
        ids = {e.id for e in result}
        assert ids == {"in1", "in2"}

    def test_entities_near(self):
        w = World()
        w.create(entity_id="close", x=3, y=4)   # dist=5
        w.create(entity_id="far", x=100, y=100)
        result = w.entities_near(0, 0, 6)
        assert len(result) == 1
        assert result[0].id == "close"

    def test_entity_ids(self):
        w = World()
        w.create(entity_id="a")
        w.create(entity_id="b")
        assert set(w.entity_ids()) == {"a", "b"}

    def test_clear(self):
        w = World()
        w.create(entity_id="a")
        w.create(entity_id="b")
        n = w.clear()
        assert n == 2
        assert len(w) == 0
        assert w.clear() == 0  # Clearing empty world

    def test_snapshot(self):
        w = World()
        w.create(entity_id="s1", kind="node")
        snap = w.snapshot()
        assert len(snap) == 1
        assert snap[0]["id"] == "s1"

    def test_on_change_callback(self):
        events = []
        w = World()
        w._on_change = lambda t, p: events.append((t, p))
        w.create(entity_id="cb1", kind="node")
        assert len(events) == 1
        assert events[0][0] == "world.entity.added"
        assert events[0][1]["entity_id"] == "cb1"


# ── WorldPlugin / CodeWorld tests ──────────────────────────────────────

class TestWorldPlugin:

    def test_plugin_initialization(self):
        app = App(features=["world"])
        assert app.world is not None
        assert isinstance(app.world, WorldPlugin)
        assert isinstance(app.world, CodeWorld)
        assert app.world.name == "world"
        assert app.world.requires_extra == "world"
        assert app.world.milestone == "M2"

    def test_optional_and_absent_by_default(self):
        app = App()
        assert app.world is None
        assert "world" not in app.runtime.plugins

    def test_world_runs_without_crash(self):
        app = App(features=["world"])

        @app.task
        def hello():
            return "world"

        app.run()
        assert app.world.world.get("task:hello") is not None
        assert app.world.world.get("task:hello").get_prop("status") == "completed"

    def test_auto_task_entities(self):
        app = App(features=["world"])
        events = []
        app.bus.on("world.entity.added", lambda e: events.append(e))

        @app.task
        def step_one():
            pass

        @app.task
        def step_two():
            pass

        app.run()

        # Two task entities created
        ents = app.world.world.entities_by_kind("task")
        assert len(ents) == 2
        labels = {e.label for e in ents}
        assert labels == {"step_one", "step_two"}
        # Both completed
        for ent in ents:
            assert ent.get_prop("status") == "completed"
            assert ent.color == "#43aa8b"

    def test_task_failure_entity(self):
        app = App(features=["world"])

        @app.task
        def crashing():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            app.run()

        ent = app.world.world.get("task:crashing")
        assert ent is not None
        assert ent.get_prop("status") == "failed"
        assert ent.color == "#e63946"
        assert "boom" in ent.get_prop("error")

    def test_convenience_helpers(self):
        app = App(features=["world"])
        wp = app.world

        e = wp.create(kind="sensor", entity_id="s1", x=10, y=20, label="Temp Sensor")
        assert e.id == "s1"
        assert wp.get("s1") is e

        wp.move("s1", 50, 60)
        assert e.x == 50

        wp.move_by("s1", 5, -10)
        assert e.x == 55 and e.y == 50

        wp.set_prop("s1", "reading", 42)
        assert e.get_prop("reading") == 42

        e2 = wp.create(entity_id="s2")
        wp.relate("s1", "monitors", "s2")
        assert ("monitors", "s2") in e.relationships

        wp.unrelate("s1", "monitors", "s2")
        assert ("monitors", "s2") not in e.relationships

        removed = wp.remove("s2")
        assert removed is not None

        ents = wp.entities()
        assert len(ents) == 1

        snap = wp.snapshot()
        assert snap[0]["id"] == "s1"

    def test_event_driven_world_commands(self):
        app = App(features=["world"])

        # Create via event
        app.bus.emit("world.create", payload={
            "entity_id": "ev1",
            "kind": "remote",
            "x": 100,
            "y": 200,
            "label": "Remote Node",
        })
        assert app.world.get("ev1") is not None
        assert app.world.get("ev1").kind == "remote"

        # Move via event
        app.bus.emit("world.move", payload={"entity_id": "ev1", "x": 300, "y": 400})
        assert app.world.get("ev1").x == 300

        # Set prop via event
        app.bus.emit("world.set_prop", payload={
            "entity_id": "ev1",
            "key": "load",
            "value": 0.85,
        })
        assert app.world.get("ev1").get_prop("load") == 0.85

        # Relate via event
        app.bus.emit("world.create", payload={"entity_id": "ev2"})
        app.bus.emit("world.relate", payload={
            "source_id": "ev1",
            "target_id": "ev2",
            "rel_name": "talks_to",
        })
        assert ("talks_to", "ev2") in app.world.get("ev1").relationships

        # Remove via event
        app.bus.emit("world.remove", payload={"entity_id": "ev2"})
        assert app.world.get("ev2") is None

    def test_world_events_on_bus(self):
        app = App(features=["world"])
        events = []
        app.bus.on("world.*", lambda e: events.append(e.type))

        app.world.create(entity_id="x1")
        app.world.move("x1", 5, 5)
        app.world.set_prop("x1", "color", "red")
        app.world.remove("x1")

        assert "world.entity.added" in events
        assert "world.entity.moved" in events
        assert "world.entity.property" in events
        assert "world.entity.removed" in events

    def test_world_coexists_with_ghost(self):
        app = App(features=["ghost", "world"])
        assert app.ghost is not None
        assert app.world is not None

        @app.task
        def hello():
            app.world.create(entity_id="from_task", kind="artifact")

        app.run()
        # Ghost tracked the task
        assert "hello" in app.ghost.task_records
        # World has the auto-task entity AND the manual one
        assert app.world.get("task:hello") is not None
        assert app.world.get("from_task") is not None

    def test_world_started_stopped_events(self):
        app = App(features=["world"])
        events = []
        app.bus.on("world.started", lambda e: events.append("started"))
        app.bus.on("world.stopped", lambda e: events.append("stopped"))

        @app.task
        def noop():
            pass

        app.run()
        assert "started" in events
        assert "stopped" in events

    def test_on_stop_idempotent(self):
        app = App(features=["world"])
        app.world.on_stop()  # Should not error when not started

    def test_on_register_idempotent(self):
        app = App(features=["world"])
        app.world.on_register()  # Should be a no-op second time

    def test_world_clear_emits_event(self):
        app = App(features=["world"])
        events = []
        app.bus.on("world.cleared", lambda e: events.append(e))
        app.world.create(entity_id="c1")
        app.world.create(entity_id="c2")
        n = app.world.world.clear()
        assert n == 2
        assert len(events) == 1
        assert events[0].payload["count"] == 2


# ── Renderer tests (without actually opening a pygame window) ──────────

class TestRenderer:

    def test_renderer_available_reflects_pygame(self):
        from nexora.world.renderer import HAS_PYGAME
        assert Renderer.available() == HAS_PYGAME

    def test_hex_to_rgb(self):
        from nexora.world.renderer import _hex_to_rgb
        assert _hex_to_rgb("#ff0000") == (255, 0, 0)
        assert _hex_to_rgb("#0f0") == (0, 255, 0)
        assert _hex_to_rgb("invalid") == (120, 120, 120)

    def test_coordinate_transforms(self):
        w = World()
        r = Renderer(w, width=800, height=600)
        r.cam_x = 0
        r.cam_y = 0
        r.zoom = 1.0
        # Origin should map to center of screen
        sx, sy = r.world_to_screen(0, 0)
        assert sx == 400 and sy == 300
        # Round-trip
        wx, wy = r.screen_to_world(sx, sy)
        assert abs(wx) < 0.01 and abs(wy) < 0.01

    def test_zoom_affects_transform(self):
        w = World()
        r = Renderer(w, width=800, height=600)
        r.zoom = 2.0
        sx, sy = r.world_to_screen(10, 10)
        # At zoom=2, 10 world units = 20 screen pixels from center
        assert sx == 420 and sy == 320

    def test_entity_at_screen_no_entities(self):
        w = World()
        r = Renderer(w, width=800, height=600)
        assert r.entity_at_screen(400, 300) is None

    def test_entity_at_screen_hit(self):
        w = World()
        w.create(entity_id="hit1", x=0, y=0, size=40)
        r = Renderer(w, width=800, height=600)
        r.cam_x = 0
        r.cam_y = 0
        r.zoom = 1.0
        # Center of screen is (0,0) in world
        result = r.entity_at_screen(400, 300)
        assert result == "hit1"

    def test_entity_at_screen_miss(self):
        w = World()
        w.create(entity_id="far", x=500, y=500, size=20)
        r = Renderer(w, width=800, height=600)
        # Screen center is world (0,0) → miss
        assert r.entity_at_screen(400, 300) is None

    def test_renderer_not_available_without_pygame(self):
        with patch("nexora.world.renderer.HAS_PYGAME", False):
            assert Renderer.available() is False

    def test_renderer_import_error_without_pygame(self):
        w = World()
        r = Renderer(w)
        with patch("nexora.world.renderer.HAS_PYGAME", False):
            with pytest.raises(ImportError, match="pygame"):
                r._ensure_pygame()

    def test_plugin_open_renderer_import_error(self):
        app = App(features=["world"])
        with patch("nexora.world.plugin.HAS_PYGAME", False):
            with pytest.raises(ImportError, match="pygame"):
                app.world.open_renderer()
