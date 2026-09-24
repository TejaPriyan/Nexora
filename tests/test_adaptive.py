"""Tests for MoodUI / adaptive interfaces (Milestone 3)."""

import time
import pytest
from nexora import App
from nexora.adaptive import (
    AdaptiveConfig,
    AdaptiveEngine,
    AdaptivePlugin,
    InteractionSignal,
    InteractionState,
    MoodUI,
    StateTransition,
)
from nexora.security import PermissionDenied


class TestAdaptiveModelsAndEngine:
    def test_states_enum_values(self):
        assert InteractionState.NORMAL.value == "NORMAL"
        assert InteractionState.FAST.value == "FAST"
        assert InteractionState.DIFFICULTY_HIGH.value == "DIFFICULTY_HIGH"
        assert InteractionState.INACTIVE.value == "INACTIVE"
        assert InteractionState.ERROR_HEAVY.value == "ERROR_HEAVY"

    def test_engine_initial_state(self):
        engine = AdaptiveEngine()
        assert engine.current_state == InteractionState.NORMAL
        assert engine.transitions == []

    def test_engine_fast_cadence(self):
        config = AdaptiveConfig(fast_action_count=3, fast_window_seconds=2.0)
        engine = AdaptiveEngine(config=config)
        now = 1000.0

        engine.record_action("click_1", success=True, now=now)
        assert engine.current_state == InteractionState.NORMAL

        engine.record_action("click_2", success=True, now=now + 0.2)
        assert engine.current_state == InteractionState.NORMAL

        engine.record_action("click_3", success=True, now=now + 0.4)
        assert engine.current_state == InteractionState.FAST
        assert len(engine.transitions) == 1
        assert engine.transitions[0].from_state == InteractionState.NORMAL
        assert engine.transitions[0].to_state == InteractionState.FAST

    def test_engine_error_heavy(self):
        config = AdaptiveConfig(error_threshold=3)
        engine = AdaptiveEngine(config=config)
        now = 1000.0

        engine.record_error("err1", now=now)
        engine.record_error("err2", now=now + 1.0)
        assert engine.current_state == InteractionState.NORMAL

        engine.record_error("err3", now=now + 2.0)
        assert engine.current_state == InteractionState.ERROR_HEAVY
        assert engine.transitions[-1].to_state == InteractionState.ERROR_HEAVY

    def test_engine_repeated_action_difficulty(self):
        config = AdaptiveConfig(repeated_action_threshold=3, repeated_action_window_seconds=5.0)
        engine = AdaptiveEngine(config=config)
        now = 1000.0

        engine.record_action("submit_form", success=True, now=now)
        engine.record_action("submit_form", success=True, now=now + 1.0)
        assert engine.current_state == InteractionState.NORMAL

        engine.record_action("submit_form", success=True, now=now + 2.0)
        assert engine.current_state == InteractionState.DIFFICULTY_HIGH
        assert engine.transitions[-1].to_state == InteractionState.DIFFICULTY_HIGH

    def test_engine_navigation_loop(self):
        config = AdaptiveConfig()
        engine = AdaptiveEngine(config=config)
        now = 1000.0

        # Pattern: home -> settings -> home -> settings
        engine.record_navigation("home", now=now)
        engine.record_navigation("settings", now=now + 1.0)
        engine.record_navigation("home", now=now + 2.0)
        assert engine.current_state == InteractionState.NORMAL

        engine.record_navigation("settings", now=now + 3.0)
        assert engine.current_state == InteractionState.DIFFICULTY_HIGH
        assert "Navigation loop" in engine.transitions[-1].reason

    def test_engine_help_request(self):
        engine = AdaptiveEngine()
        now = 1000.0
        engine.record_help_request("billing_faq", now=now)
        assert engine.current_state == InteractionState.DIFFICULTY_HIGH
        assert engine.transitions[-1].to_state == InteractionState.DIFFICULTY_HIGH

    def test_engine_inactivity(self):
        config = AdaptiveConfig(inactivity_timeout_seconds=5.0)
        engine = AdaptiveEngine(config=config)
        now = 1000.0

        engine.record_action("view", now=now)
        # Check at 3s -> not inactive
        assert engine.check_inactivity(now=now + 3.0) == InteractionState.NORMAL
        # Check at 6s -> inactive
        assert engine.check_inactivity(now=now + 6.0) == InteractionState.INACTIVE
        assert engine.current_state == InteractionState.INACTIVE

    def test_engine_recovery_to_normal(self):
        config = AdaptiveConfig(error_threshold=2, recovery_action_count=2)
        engine = AdaptiveEngine(config=config)
        now = 1000.0

        engine.record_error("e1", now=now)
        engine.record_error("e2", now=now + 1.0)
        assert engine.current_state == InteractionState.ERROR_HEAVY

        # 1 successful action is not enough
        engine.record_action("good_1", success=True, now=now + 2.0)
        assert engine.current_state == InteractionState.ERROR_HEAVY

        # 2nd successful action restores NORMAL
        engine.record_action("good_2", success=True, now=now + 3.0)
        assert engine.current_state == InteractionState.NORMAL

    def test_engine_reset(self):
        engine = AdaptiveEngine()
        engine.record_error("e1")
        engine.record_error("e2")
        engine.record_error("e3")
        assert engine.current_state == InteractionState.ERROR_HEAVY
        engine.reset()
        assert engine.current_state == InteractionState.NORMAL
        assert engine.transitions == []


class TestAdaptivePluginAndPermissions:
    def test_plugin_properties_and_alias(self):
        app = App(features=["adaptive"])
        assert app.adaptive is not None
        assert app.mood is not None
        assert isinstance(app.adaptive, AdaptivePlugin)
        assert isinstance(app.adaptive, MoodUI)
        assert app.adaptive.name == "adaptive"
        assert app.adaptive.requires_extra is None
        assert app.adaptive.milestone == "M3"

    def test_permission_gate_blocks_observation_by_default(self):
        app = App(features=["adaptive"])
        adaptive: AdaptivePlugin = app.adaptive

        assert not adaptive.is_permitted()

        # Emit events on bus
        app.bus.emit("task.failed", payload={"task": "crash"})
        app.bus.emit("error", payload={"error": "db timeout"})
        app.bus.emit("help", payload={"topic": "setup"})
        app.bus.emit("action", payload={"action": "click"})

        # Zero observation occurred
        assert adaptive.current_state == InteractionState.NORMAL
        assert len(adaptive.history) == 0

        # Programmatic calls without permission raise PermissionDenied
        with pytest.raises(PermissionDenied):
            adaptive.record_action("click")

        with pytest.raises(PermissionDenied):
            adaptive.record_error("err")

        with pytest.raises(PermissionDenied):
            adaptive.record_navigation("dashboard")

        with pytest.raises(PermissionDenied):
            adaptive.record_help_request("faq")

    def test_opt_in_and_opt_out(self):
        app = App(features=["adaptive"])
        adaptive: AdaptivePlugin = app.adaptive

        assert not adaptive.is_permitted()
        adaptive.opt_in(reason="user consented in UI settings")
        assert adaptive.is_permitted()

        # Programmatic call now works
        adaptive.record_help_request("how_to_export")
        assert adaptive.current_state == InteractionState.DIFFICULTY_HIGH
        assert len(adaptive.history) == 1

        # Opt out revokes permission
        adaptive.opt_out(reason="user revoked consent")
        assert not adaptive.is_permitted()

        # Further events are ignored
        app.bus.emit("error", payload={"error": "unhandled"})
        assert len(adaptive.history) == 1

    def test_event_driven_state_transitions(self):
        app = App(features=["adaptive"])
        adaptive: AdaptivePlugin = app.adaptive
        adaptive.opt_in()

        transitions_received = []

        def on_transition(event):
            transitions_received.append(event.payload)

        app.bus.on("adaptive.state_changed", on_transition)

        # 1. Trigger ERROR_HEAVY via task.failed
        app.bus.emit("task.failed", payload={"task": "step1"})
        app.bus.emit("task.failed", payload={"task": "step2"})
        app.bus.emit("task.failed", payload={"task": "step3"})

        assert adaptive.current_state == InteractionState.ERROR_HEAVY
        assert len(transitions_received) == 1
        assert transitions_received[0]["current_state"] == "ERROR_HEAVY"
        assert transitions_received[0]["previous_state"] == "NORMAL"

        # 2. Recover back to NORMAL via task.completed
        app.bus.emit("task.completed", payload={"task": "step4", "duration_seconds": 0.1})
        app.bus.emit("task.completed", payload={"task": "step5", "duration_seconds": 0.1})

        assert adaptive.current_state == InteractionState.NORMAL
        assert len(transitions_received) == 2
        assert transitions_received[1]["current_state"] == "NORMAL"

    def test_navigation_loop_via_events(self):
        app = App(features=["adaptive"])
        adaptive: AdaptivePlugin = app.adaptive
        adaptive.opt_in()

        for route in ["viewA", "viewB", "viewA", "viewB"]:
            app.bus.emit("navigation", payload={"to": route})

        assert adaptive.current_state == InteractionState.DIFFICULTY_HIGH

    def test_repeated_action_via_events(self):
        app = App(features=["adaptive"])
        adaptive: AdaptivePlugin = app.adaptive
        adaptive.opt_in()

        for _ in range(3):
            app.bus.emit("action", payload={"action": "checkout_button", "success": True})

        assert adaptive.current_state == InteractionState.DIFFICULTY_HIGH

    def test_help_request_via_events(self):
        app = App(features=["adaptive"])
        adaptive: AdaptivePlugin = app.adaptive
        adaptive.opt_in()

        app.bus.emit("help.requested", payload={"topic": "api_keys"})
        assert adaptive.current_state == InteractionState.DIFFICULTY_HIGH

    def test_inactivity_check_via_event(self):
        app = App(features=["adaptive"])
        adaptive: AdaptivePlugin = app.adaptive
        adaptive.opt_in()

        # Send an interaction at t=100
        app.bus.emit("action", payload={"action": "init"})
        # Send inactivity check at t=1000
        app.bus.emit("adaptive.inactivity_check", payload={"now": time.time() + 100.0})
        assert adaptive.current_state == InteractionState.INACTIVE

    def test_on_state_change_callback_listener(self):
        app = App(features=["adaptive"])
        adaptive: AdaptivePlugin = app.adaptive
        adaptive.opt_in()

        captured = []
        unsub = adaptive.on_state_change(lambda t: captured.append(t))

        adaptive.record_help_request("support")
        assert len(captured) == 1
        assert captured[0].to_state == InteractionState.DIFFICULTY_HIGH

        # Unsubscribe
        unsub()
        adaptive.reset()
        adaptive.record_help_request("support2")
        assert len(captured) == 1  # Unsubscribed, no more calls

    def test_lifecycle_and_idempotence(self):
        app = App(features=["adaptive"])
        adaptive: AdaptivePlugin = app.adaptive

        adaptive.on_register()
        adaptive.on_register()  # Idempotent
        adaptive.on_start()
        adaptive.on_start()
        adaptive.on_stop()
        adaptive.on_stop()

    def test_coexistence_ghost_world_adaptive(self):
        """All 3 milestones running simultaneously in harmony."""
        app = App(features=["ghost", "world", "adaptive"])
        assert app.ghost is not None
        assert app.world is not None
        assert app.adaptive is not None

        app.adaptive.opt_in()

        @app.task
        def pipeline_step():
            app.world.create("node", entity_id="n1", x=0, y=0)
            app.ghost.metric("counter", 1)

        app.run()

        # CodeWorld created the entity
        assert app.world.get("n1") is not None
        # GhostUI tracked the task
        assert "pipeline_step" in app.ghost.task_records
        # Adaptive UI observed the task completion
        assert app.adaptive.current_state == InteractionState.NORMAL
