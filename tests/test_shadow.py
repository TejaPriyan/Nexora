"""Tests for Shadow (live observability) module."""

import time
import pytest
from nexora import App
from nexora.shadow import (
    DependencyLink,
    FunctionProfile,
    ObservabilitySnapshot,
    ObservedError,
    ObservedEvent,
    ShadowEngine,
    ShadowPlugin,
)


def test_shadow_plugin_registration_and_lifecycle():
    app = App(features=["shadow"])
    assert app.shadow is not None
    assert isinstance(app.shadow, ShadowPlugin)
    assert app.shadow.engine is not None

    app.run()


def test_function_tracking_and_genuine_timing():
    engine = ShadowEngine()

    @engine.trace
    def compute(val: int) -> int:
        time.sleep(0.02)  # Real delay to ensure non-zero genuine measurement
        return val * 2

    res = compute(10)
    assert res == 20

    stats = engine.function_stats()
    assert "compute" in stats
    prof = stats["compute"]
    assert prof.call_count == 1
    assert prof.error_count == 0
    # Genuine timing: must be at least ~0.015s and less than 1.0s
    assert 0.015 <= prof.total_duration <= 1.0
    assert 0.015 <= prof.min_duration <= 1.0
    assert 0.015 <= prof.max_duration <= 1.0
    assert 0.015 <= prof.avg_duration <= 1.0

    # Second call
    compute(5)
    prof = engine.function_stats("compute")
    assert prof.call_count == 2
    assert prof.total_duration >= 0.03


def test_named_trace_decorator():
    engine = ShadowEngine()

    @engine.trace("custom_operation")
    def my_func():
        time.sleep(0.01)
        return "done"

    res = my_func()
    assert res == "done"
    prof = engine.function_stats("custom_operation")
    assert prof is not None
    assert prof.call_count == 1
    assert prof.avg_duration >= 0.008


def test_span_context_manager():
    engine = ShadowEngine()

    with engine.span("database_query"):
        time.sleep(0.015)

    prof = engine.function_stats("database_query")
    assert prof is not None
    assert prof.call_count == 1
    assert prof.avg_duration >= 0.01


def test_error_capture_and_traceback():
    engine = ShadowEngine()

    @engine.trace
    def failing_op():
        raise ValueError("Invalid operation encountered")

    with pytest.raises(ValueError, match="Invalid operation encountered"):
        failing_op()

    prof = engine.function_stats("failing_op")
    assert prof.call_count == 1
    assert prof.error_count == 1

    errors = engine.error_log()
    assert len(errors) == 1
    err = errors[0]
    assert err.error_type == "ValueError"
    assert "Invalid operation encountered" in err.message
    assert err.source == "failing_op"
    assert err.traceback is not None
    assert "ValueError" in err.traceback


def test_span_error_capture():
    engine = ShadowEngine()

    with pytest.raises(KeyError):
        with engine.span("failing_span"):
            raise KeyError("missing_key")

    prof = engine.function_stats("failing_span")
    assert prof.error_count == 1
    errors = engine.error_log()
    assert len(errors) == 1
    assert errors[0].error_type == "KeyError"


def test_dependency_tracking():
    engine = ShadowEngine()

    @engine.trace
    def inner_step():
        time.sleep(0.005)
        return 42

    @engine.trace
    def outer_step():
        return inner_step() + 1

    val = outer_step()
    assert val == 43

    deps = engine.dependencies()
    assert len(deps) == 1
    assert deps[0].caller == "outer_step"
    assert deps[0].callee == "inner_step"
    assert deps[0].call_count == 1

    # Call again
    outer_step()
    deps = engine.dependencies()
    assert deps[0].call_count == 2


def test_event_tracking_via_plugin():
    app = App(features=["shadow"])
    app.bus.emit("user.login", source="auth_svc", payload={"user": "alice"})
    app.bus.emit("user.login", source="auth_svc", payload={"user": "bob"})
    app.bus.emit("data.sync", source="sync_worker")

    ev_stats = app.shadow.event_stats()
    assert "user.login" in ev_stats
    assert ev_stats["user.login"].count == 2
    assert "auth_svc" in ev_stats["user.login"].sources

    assert "data.sync" in ev_stats
    assert ev_stats["data.sync"].count == 1
    assert "sync_worker" in ev_stats["data.sync"].sources


def test_app_task_timing_and_failure_observation():
    app = App(features=["shadow"])

    @app.task
    def good_task():
        time.sleep(0.01)
        return "success"

    @app.task
    def bad_task():
        raise RuntimeError("boom")

    res = good_task()
    assert res == "success"

    with pytest.raises(RuntimeError):
        bad_task()

    prof_good = app.shadow.function_stats("task:good_task")
    assert prof_good is not None
    assert prof_good.call_count == 1
    assert prof_good.error_count == 0
    assert prof_good.avg_duration >= 0.008

    prof_bad = app.shadow.function_stats("task:bad_task")
    assert prof_bad is not None
    assert prof_bad.call_count == 1
    assert prof_bad.error_count == 1

    errors = app.shadow.errors()
    assert any("boom" in e.message for e in errors)


def test_observability_snapshot_and_reset():
    app = App(features=["shadow"])

    @app.shadow.trace
    def test_func():
        return 1

    test_func()
    app.bus.emit("custom.metric", source="test")

    snap = app.shadow.snapshot()
    assert isinstance(snap, ObservabilitySnapshot)
    assert snap.total_function_calls >= 1
    assert snap.total_events >= 1
    assert "test_func" in snap.functions
    assert "custom.metric" in snap.event_counts

    app.shadow.reset()
    clean_snap = app.shadow.snapshot()
    assert clean_snap.total_function_calls == 0
    assert clean_snap.total_events == 0
    assert len(clean_snap.functions) == 0


def test_coexistence_with_other_modules():
    app = App(features=["memory", "timeline", "shadow"])

    @app.shadow.trace
    def do_workflow():
        app.recall.remember("test workflow execution", tags=["workflow"])
        app.timeloop.checkpoint("wf_ckpt")
        return True

    assert do_workflow() is True

    # Memory has item
    items = app.recall.search("workflow")
    assert len(items) == 1

    # TimeLoop has snapshot
    assert len(app.timeloop.history()) == 1

    # Shadow has traced function
    prof = app.shadow.function_stats("do_workflow")
    assert prof is not None
    assert prof.call_count == 1
