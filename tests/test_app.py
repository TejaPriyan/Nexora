import pytest

from nexora import App
from nexora.plugins import UnknownFeatureError


def test_task_emits_events():
    app = App()
    events = []
    app.bus.on("*", events.append)

    @app.task
    def do_thing():
        return 42

    result = do_thing()
    assert result == 42
    types = [e.type for e in events]
    assert "task.started" in types
    assert "task.completed" in types


def test_task_failure_emits_task_failed_and_reraises():
    app = App()
    events = []
    app.bus.on("task.failed", events.append)

    @app.task
    def boom():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        boom()
    assert len(events) == 1
    assert events[0].payload["task"] == "boom"
    assert "nope" in events[0].payload["error"]


def test_run_executes_registered_tasks_in_order():
    app = App()
    calls = []

    @app.task
    def a():
        calls.append("a")

    @app.task
    def b():
        calls.append("b")

    app.run()
    assert calls == ["a", "b"]


def test_run_emits_task_events_too():
    app = App()
    events = []
    app.bus.on("task.completed", events.append)

    @app.task
    def a():
        pass

    app.run()
    assert len(events) == 1
    assert events[0].payload["task"] == "a"


def test_state_is_observable_via_bus():
    app = App()
    events = []
    app.bus.on("state.changed", events.append)
    app.state.set("mode", "dark")
    assert app.state.get("mode") == "dark"
    assert len(events) == 1
    assert events[0].payload == {"key": "mode", "old": None, "new": "dark"}


def test_planned_feature_registers_but_raises_clear_error_on_start():
    from nexora.plugins.base import PlannedPlugin
    from nexora.plugins.registry import _REGISTRY
    _REGISTRY["future_feature"] = type(
        "Planned_Future",
        (PlannedPlugin,),
        {"name": "future_feature", "requires_extra": None, "summary": "A future feature."},
    )
    try:
        app = App(features=["future_feature"])
        assert "future_feature" in app.runtime.plugins
        with pytest.raises(NotImplementedError, match="future_feature"):
            app.run()
    finally:
        _REGISTRY.pop("future_feature", None)


def test_ghost_feature_registers_and_runs():
    app = App(features=["ghost"])
    assert app.ghost is not None
    assert "ghost" in app.runtime.plugins

    @app.task
    def hello():
        return "world"

    app.run()
    assert app.ghost.task_records["hello"].status == "completed"


def test_unknown_feature_raises_at_construction():
    with pytest.raises(UnknownFeatureError):
        App(features=["not-a-real-feature"])


def test_available_features_lists_all_planned_modules():
    features = App.available_features()
    for expected in (
        "ghost", "world", "adaptive", "memory", "timeline",
        "vision", "shadow", "worldforge", "agentbox",
    ):
        assert expected in features
