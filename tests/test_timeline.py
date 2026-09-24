"""Tests for TimeLoop (timeline/rewind) module (Milestone 5)."""

import pytest
from nexora import App
from nexora.timeline import DiffResult, Snapshot, TimeLoop, TimeLoopEngine, TimelinePlugin


class TestTimeLoopEngine:
    def test_checkpoint_and_snapshot(self):
        engine = TimeLoopEngine()
        snap = engine.checkpoint("init", {"count": 1, "status": "active"})
        assert snap.label == "init"
        assert snap.data["count"] == 1
        assert engine.snapshot() == snap
        assert len(engine.history()) == 1

    def test_secret_redaction_default_password(self):
        engine = TimeLoopEngine()
        data = {
            "user": "admin",
            "password": "unencrypted_secret_pass",
            "api_key": "sk-secret-987",
            "token": "bearer-token-111",
        }
        snap = engine.checkpoint("user_state", data)
        assert snap.data["user"] == "admin"
        assert snap.data["password"] == "***REDACTED***"
        assert snap.data["api_key"] == "***REDACTED***"
        assert snap.data["token"] == "***REDACTED***"

    def test_secret_redaction_custom_ignore(self):
        engine = TimeLoopEngine()
        # Custom sensitive field not in standard list
        data = {
            "session": "open",
            "proprietary_vault_code": "vault-xyz-456",
            "custom_signature": "sig-789",
        }
        snap1 = engine.checkpoint("step1", data)
        # Without ignore, custom field is unredacted
        assert snap1.data["proprietary_vault_code"] == "vault-xyz-456"

        # Explicitly ignore custom field names
        engine.ignore("proprietary_vault_code", "custom_signature")
        snap2 = engine.checkpoint("step2", data)
        assert snap2.data["proprietary_vault_code"] == "***REDACTED***"
        assert snap2.data["custom_signature"] == "***REDACTED***"

    def test_restore_and_rewind(self):
        engine = TimeLoopEngine()
        s1 = engine.checkpoint("v1", {"count": 10})
        s2 = engine.checkpoint("v2", {"count": 20})
        s3 = engine.checkpoint("v3", {"count": 30})

        assert engine.snapshot().data["count"] == 30

        # Rewind 1 step
        rewound = engine.rewind(1)
        assert rewound.id == s2.id
        assert rewound.data["count"] == 20

        # Rewind 2 steps (caps at beginning)
        rewound_start = engine.rewind(2)
        assert rewound_start.id == s1.id
        assert rewound_start.data["count"] == 10

        # Forward 1 step
        fwd = engine.forward(1)
        assert fwd.id == s2.id
        assert fwd.data["count"] == 20

        # Restore by ID
        restored = engine.restore(s3.id)
        assert restored.id == s3.id
        assert restored.data["count"] == 30

    def test_diff_snapshots(self):
        engine = TimeLoopEngine()
        s1 = engine.checkpoint("v1", {"a": 1, "b": "old", "c": True})
        s2 = engine.checkpoint("v2", {"b": "new", "c": True, "d": "added"})

        diff: DiffResult = engine.diff(s1, s2)
        assert not diff.identical
        assert diff.added == {"d": "added"}
        assert diff.removed == {"a": 1}
        assert diff.changed == {"b": ("old", "new")}

        # Diff identical
        diff_same = engine.diff(s1, s1)
        assert diff_same.identical

    def test_history_and_clear(self):
        engine = TimeLoopEngine()
        engine.checkpoint("a", {"x": 1})
        engine.checkpoint("b", {"x": 2})
        assert len(engine.history()) == 2
        engine.clear()
        assert len(engine.history()) == 0
        assert engine.snapshot() is None


class TestTimelinePlugin:
    def test_plugin_properties_and_alias(self):
        app = App(features=["timeline"])
        assert app.timeline is not None
        assert app.timeloop is not None
        assert isinstance(app.timeline, TimelinePlugin)
        assert isinstance(app.timeline, TimeLoop)
        assert app.timeline.name == "timeline"
        assert app.timeline.requires_extra is None
        assert app.timeline.milestone == "M5"

    def test_checkpoint_from_app_state_and_restore(self):
        app = App(features=["timeline"])
        app.state.set("theme", "light")
        app.state.set("user", "test_user")

        snap1 = app.timeline.checkpoint("initial_state")
        assert snap1.data["theme"] == "light"

        # Change state
        app.state.set("theme", "dark")
        snap2 = app.timeline.checkpoint("updated_state")
        assert snap2.data["theme"] == "dark"

        # Restore to initial snapshot -> syncs back to app.state
        app.timeline.restore(snap1.id)
        assert app.state.get("theme") == "light"

    def test_rewind_syncs_to_state(self):
        app = App(features=["timeline"])
        app.state.set("val", 100)
        s1 = app.timeline.checkpoint("c1")

        app.state.set("val", 200)
        s2 = app.timeline.checkpoint("c2")

        # Rewind
        app.timeline.rewind(1)
        assert app.state.get("val") == 100

    def test_custom_ignore_on_plugin(self):
        app = App(features=["timeline"])
        app.timeline.ignore("special_token")

        snap = app.timeline.checkpoint(
            "test_ignore",
            data={"special_token": "secret_xyz", "normal": 42},
        )
        assert snap.data["special_token"] == "***REDACTED***"
        assert snap.data["normal"] == 42

    def test_timeline_events_emitted(self):
        app = App(features=["timeline"])
        events = []
        app.bus.on("timeline.*", lambda e: events.append(e))

        snap = app.timeline.checkpoint("event_test", data={"x": 1})
        assert any(e.type == "timeline.checkpoint" and e.payload["id"] == snap.id for e in events)

        app.timeline.rewind(1)
        assert any(e.type == "timeline.rewound" for e in events)

        app.timeline.restore(snap.id)
        assert any(e.type == "timeline.restored" for e in events)

    def test_coexistence_all_five_features(self):
        """GhostUI, CodeWorld, MoodUI, Recall, and TimeLoop together."""
        app = App(features=["ghost", "world", "adaptive", "memory", "timeline"])
        assert app.ghost is not None
        assert app.world is not None
        assert app.adaptive is not None
        assert app.memory is not None
        assert app.timeline is not None

        app.adaptive.opt_in()

        @app.task
        def complex_pipeline():
            app.state.set("pipeline_status", "running")
            app.timeline.checkpoint("pipeline_started")
            app.memory.remember("last_status", "running")
            app.world.create("server", entity_id="srv_task", x=5, y=5)
            app.ghost.metric("pipeline_jobs", 1)

        app.run()

        assert app.state.get("pipeline_status") == "running"
        assert len(app.timeline.history()) >= 1
        assert app.memory.get("last_status") is not None
        assert app.world.get("srv_task") is not None
