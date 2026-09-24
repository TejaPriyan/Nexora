import io
from unittest.mock import patch
import pytest

from rich.console import Console

from nexora import App
from nexora.ghost import GhostPlugin, GhostUI, LogRecord, MetricRecord, TaskRecord
from nexora.ghost.plugin import HAS_RICH


def _make_test_app(**kwargs) -> tuple[App, GhostPlugin, io.StringIO]:
    stream = io.StringIO()
    console = Console(file=stream, record=True, force_terminal=False, width=120)
    app = App(features=["ghost"])
    ghost: GhostPlugin = app.ghost
    ghost.console = console
    for k, v in kwargs.items():
        setattr(ghost, k, v)
    return app, ghost, stream


def test_ghost_initialization():
    app = App(features=["ghost"])
    assert app.ghost is not None
    assert isinstance(app.ghost, GhostPlugin)
    assert isinstance(app.ghost, GhostUI)
    assert app.ghost.name == "ghost"
    assert app.ghost.requires_extra == "ghost"
    assert app.ghost.milestone == "M1"


def test_ghost_optional_and_absent_by_default():
    app = App()
    assert app.ghost is None
    assert "ghost" not in app.runtime.plugins


def test_ghost_header_rendered_on_start():
    app, ghost, stream = _make_test_app()

    @app.task
    def sample():
        pass

    app.run()
    out = stream.getvalue()
    assert "NEXORA GhostUI" in out
    assert "sample" in out
    assert "Registered Tasks" in out


def test_task_lifecycle_rendering_and_history():
    app, ghost, stream = _make_test_app()

    @app.task
    def process_item():
        return 123

    res = process_item()
    assert res == 123

    rec = ghost.task_records.get("process_item")
    assert rec is not None
    assert rec.status == "completed"
    assert rec.duration is not None
    assert rec.duration >= 0

    out = stream.getvalue()
    assert "Starting task: process_item" in out
    assert "Completed task: process_item" in out


def test_task_failure_rendering():
    app, ghost, stream = _make_test_app()

    @app.task
    def bad_task():
        raise RuntimeError("Something went wrong!")

    with pytest.raises(RuntimeError):
        bad_task()

    rec = ghost.task_records.get("bad_task")
    assert rec is not None
    assert rec.status == "failed"
    assert "Something went wrong!" in rec.error

    out = stream.getvalue()
    assert "Failed task: bad_task" in out
    assert "Something went wrong!" in out
    assert "Error Encountered" in out


def test_progress_events():
    app, ghost, stream = _make_test_app()

    app.bus.emit(
        "progress.updated",
        payload={
            "task": "download_weights",
            "completed": 50,
            "total": 100,
            "unit": "MB",
            "description": "halfway",
        },
    )

    assert "download_weights" in ghost.progress_records
    prog = ghost.progress_records["download_weights"]
    assert prog.completed == 50
    assert prog.total == 100
    assert prog.unit == "MB"

    out = stream.getvalue()
    assert "download_weights" in out
    assert "50/100 MB" in out
    assert "50.0%" in out
    assert "halfway" in out


def test_status_events():
    app, ghost, stream = _make_test_app()

    app.bus.emit(
        "status.updated",
        payload={"status": "Optimizing", "message": "Applying gradient step"},
    )

    out = stream.getvalue()
    assert "Status [Optimizing]" in out
    assert "Applying gradient step" in out


def test_log_events():
    app, ghost, stream = _make_test_app()

    app.bus.emit("log.info", source="worker-1", payload={"message": "System healthy"})
    app.bus.emit("log.warning", source="worker-1", payload={"message": "Disk space low"})
    app.bus.emit("log.error", source="worker-2", payload={"message": "Network timeout"})
    app.bus.emit("log.debug", source="core", payload={"message": "Cache hit"})

    assert len(ghost.logs) == 4
    assert ghost.logs[0].level == "INFO"
    assert ghost.logs[0].message == "System healthy"
    assert ghost.logs[1].level == "WARNING"
    assert ghost.logs[2].level == "ERROR"
    assert ghost.logs[3].level == "DEBUG"

    out = stream.getvalue()
    assert "INFO" in out and "System healthy" in out
    assert "WARN" in out and "Disk space low" in out
    assert "ERROR" in out and "Network timeout" in out
    assert "DEBUG" in out and "Cache hit" in out


def test_error_events():
    app, ghost, stream = _make_test_app()

    app.bus.emit(
        "error",
        source="subsystem",
        payload={
            "error": "Database disconnected",
            "traceback": "Traceback...\n  File x.py",
        },
    )

    out = stream.getvalue()
    assert "Error Encountered" in out
    assert "Database disconnected" in out
    assert "Traceback" in out


def test_metric_tracking_and_events():
    app, ghost, stream = _make_test_app()

    app.bus.emit("metric", payload={"name": "cpu_pct", "value": 15.5, "unit": "%"})
    app.bus.emit("metric", payload={"name": "cpu_pct", "value": 45.0, "unit": "%"})
    app.bus.emit("metric", payload={"name": "cpu_pct", "value": 30.0, "unit": "%"})

    rec = ghost.metrics["cpu_pct"]
    assert rec.value == 30.0
    assert rec.count == 3
    assert rec.min_value == 15.5
    assert rec.max_value == 45.0
    assert rec.unit == "%"

    out = stream.getvalue()
    assert "cpu_pct" in out
    assert "30" in out


def test_table_events():
    app, ghost, stream = _make_test_app()

    app.bus.emit(
        "table",
        payload={
            "title": "Model Benchmarks",
            "columns": ["Model", "Accuracy", "Latency"],
            "rows": [["Model A", "94.5%", "12ms"], ["Model B", "97.1%", "28ms"]],
        },
    )

    assert len(ghost.tables_rendered) == 1
    out = stream.getvalue()
    assert "Model Benchmarks" in out
    assert "Model A" in out
    assert "97.1%" in out


def test_state_change_rendering():
    app, ghost, stream = _make_test_app(show_state=True)

    app.state.set("theme", "dracula")

    out = stream.getvalue()
    assert "State changed:" in out
    assert "theme" in out
    assert "dracula" in out


def test_summary_dashboard_on_stop():
    app, ghost, stream = _make_test_app()

    @app.task
    def task_one():
        pass

    @app.task
    def task_two():
        pass

    app.bus.emit("metric", payload={"name": "tokens", "value": 1500, "unit": "tok"})
    app.run()

    out = stream.getvalue()
    assert "Tasks Summary" in out
    assert "task_one" in out
    assert "task_two" in out
    assert "COMPLETED" in out
    assert "Metrics Summary" in out
    assert "tokens" in out
    assert "Run Summary" in out
    assert "Total Tasks: 2" in out


def test_quiet_mode_suppresses_printing():
    app, ghost, stream = _make_test_app(quiet=True)

    @app.task
    def t1():
        pass

    app.run()
    app.bus.emit("log.info", payload={"message": "hidden"})
    app.bus.emit("metric", payload={"name": "test_m", "value": 1})

    # In-memory structures still populated
    assert "t1" in ghost.task_records
    assert len(ghost.logs) == 1
    assert "test_m" in ghost.metrics
    # Console stream has zero printed output
    assert stream.getvalue() == ""


def test_programmatic_helpers():
    app, ghost, stream = _make_test_app()

    ghost.log("Helper log test", level="WARNING")
    ghost.progress("helper_prog", completed=25, total=50)
    ghost.metric("helper_metric", value=99, unit="pts")
    ghost.table("Helper Table", columns=["K", "V"], rows=[["x", "100"]])
    ghost.status("Ready", "All systems nominal")

    out = stream.getvalue()
    assert "Helper log test" in out
    assert "helper_prog" in out
    assert "helper_metric" in out
    assert "Helper" in out and "Table" in out
    assert "100" in out
    assert "Ready" in out


def test_ensure_rich_raises_when_missing():
    app = App(features=["ghost"])
    with patch("nexora.ghost.plugin.HAS_RICH", False):
        with pytest.raises(ImportError, match="rich"):
            app.ghost._ensure_rich()


def test_ghost_default_console_and_idempotent_lifecycle():
    app = App(features=["ghost"])
    # Default console creation
    assert app.ghost.console is not None
    # Idempotent registration
    app.ghost.on_register()
    # Stopping when not started
    app.ghost.on_stop()


def test_ghost_unseen_task_completion_and_failure():
    app, ghost, stream = _make_test_app()
    # Directly emit completed without started
    app.bus.emit("task.completed", payload={"task": "orphan_c", "duration_seconds": 0.5})
    assert ghost.task_records["orphan_c"].status == "completed"

    # Directly emit failed without started
    app.bus.emit("task.failed", payload={"task": "orphan_f", "duration_seconds": 0.2, "error": "err"})
    assert ghost.task_records["orphan_f"].status == "failed"


def test_ghost_progress_100_percent():
    app, ghost, stream = _make_test_app()
    app.bus.emit("progress.updated", payload={"task": "done_p", "completed": 100, "total": 100})
    out = stream.getvalue()
    assert "100.0%" in out


def test_ghost_logs_critical_custom_and_datetime_timestamp():
    from datetime import datetime, timezone
    from nexora.events import Event

    app, ghost, stream = _make_test_app()
    ev = Event(
        type="log.critical",
        source="system",
        payload={"message": "Kernal Panic"},
        timestamp=datetime.now(timezone.utc),
    )
    ghost._on_log(ev)

    ev_custom = Event(
        type="log.custom",
        source="audit",
        payload={"message": "Custom event", "level": "TRACE"},
    )
    ghost._on_log(ev_custom)

    out = stream.getvalue()
    assert "CRIT" in out and "Kernal Panic" in out
    assert "TRACE" in out and "Custom event" in out


def test_ghost_non_numeric_metric():
    app, ghost, stream = _make_test_app()
    app.bus.emit("metric", payload={"name": "deployment_env", "value": "production"})
    assert ghost.metrics["deployment_env"].value == "production"
    assert ghost.metrics["deployment_env"].min_value is None
    out = stream.getvalue()
    assert "deployment_env" in out
    assert "production" in out


def test_ghost_summary_with_failures():
    app, ghost, stream = _make_test_app()

    @app.task
    def will_fail():
        raise ValueError("Intentional crash")

    with pytest.raises(ValueError):
        app.run(raise_on_task_error=True)

    out = stream.getvalue()
    assert "Tasks Summary" in out
    assert "will_fail" in out
    assert "FAILED" in out
    assert "Failed: 1" in out
