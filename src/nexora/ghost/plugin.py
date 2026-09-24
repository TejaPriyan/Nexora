"""GhostUI: automatic rich terminal UI derived from App and EventBus activity."""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional, Sequence, Union

try:
    import rich  # pyright: ignore[reportMissingImports]  # type: ignore
    from rich import box  # pyright: ignore[reportMissingImports]  # type: ignore
    from rich.console import Console  # pyright: ignore[reportMissingImports]  # type: ignore
    from rich.markup import escape  # pyright: ignore[reportMissingImports]  # type: ignore
    from rich.panel import Panel  # pyright: ignore[reportMissingImports]  # type: ignore
    from rich.table import Table  # pyright: ignore[reportMissingImports]  # type: ignore
    from rich.text import Text  # pyright: ignore[reportMissingImports]  # type: ignore

    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    box = None  # type: ignore[assignment]
    Console = None  # type: ignore[assignment]
    escape = None  # type: ignore[assignment]
    Panel = None  # type: ignore[assignment]
    Table = None  # type: ignore[assignment]
    Text = None  # type: ignore[assignment]

from .. import __version__
from ..plugins.base import Plugin
from .records import LogRecord, MetricRecord, ProgressRecord, TaskRecord

if TYPE_CHECKING:
    from ..app import App
    from ..events import Event



class _Symbols:
    """Platform- and encoding-aware glyphs for console rendering."""

    def __init__(self, console: Any) -> None:
        enc = getattr(console, "encoding", None) or getattr(getattr(console, "file", None), "encoding", None) or "utf-8"
        can_utf8 = True
        try:
            "● ✔ ✖ ⏳ 📊 ⚡ ━ ╸ ─".encode(enc)
        except (UnicodeEncodeError, LookupError):
            can_utf8 = False

        if can_utf8:
            self.bullet = "●"
            self.check = "✔"
            self.cross = "✖"
            self.running = "⏳"
            self.chart = "📊"
            self.bolt = "⚡"
            self.bar_fill = "━"
            self.bar_tip = "╸"
            self.bar_empty = "─"
        else:
            self.bullet = "*"
            self.check = "+"
            self.cross = "x"
            self.running = "~"
            self.chart = "[#]"
            self.bolt = "[!]"
            self.bar_fill = "="
            self.bar_tip = ">"
            self.bar_empty = "-"


class GhostPlugin(Plugin):
    """GhostUI automatically renders interfaces purely from App/EventBus activity.

    Subscribes to events flowing on the app's EventBus:
    - task.started, task.completed, task.failed -> task life-cycle & timing
    - progress, progress.*, task.progress -> visual progress bars & indicators
    - status, status.* -> application status updates
    - log, log.* -> formatted, color-coded log lines
    - error, error.* -> styled error panels & tracebacks
    - metric, metric.* -> metric recording and summaries
    - table, table.* -> structured data tables
    - state.changed -> optional state change inspection

    At shutdown (on_stop), it generates an end-of-run dashboard with a Tasks
    summary table, metrics summary, and execution stats.
    """

    name: ClassVar[str] = "ghost"
    requires_extra: ClassVar[Optional[str]] = "ghost"
    milestone: ClassVar[str] = "M1"

    def __init__(
        self,
        app: "App",
        *,
        console: Optional[Console] = None,
        show_header: bool = True,
        show_summary: bool = True,
        show_tasks: bool = True,
        show_progress: bool = True,
        show_status: bool = True,
        show_logs: bool = True,
        show_errors: bool = True,
        show_metrics: bool = True,
        show_tables: bool = True,
        show_state: bool = False,
        quiet: bool = False,
    ) -> None:
        super().__init__(app)
        self._console = console
        self._symbols: Optional[_Symbols] = None
        self.show_header = show_header
        self.show_summary = show_summary
        self.show_tasks = show_tasks
        self.show_progress = show_progress
        self.show_status = show_status
        self.show_logs = show_logs
        self.show_errors = show_errors
        self.show_metrics = show_metrics
        self.show_tables = show_tables
        self.show_state = show_state
        self.quiet = quiet

        # In-memory tracking
        self.task_records: Dict[str, TaskRecord] = {}
        self.progress_records: Dict[str, ProgressRecord] = {}
        self.metrics: Dict[str, MetricRecord] = {}
        self.logs: List[LogRecord] = []
        self.tables_rendered: List[Dict[str, Any]] = []

        self._start_time: Optional[float] = None
        self._registered = False
        self._started = False
        self._unsubscribers: List[Callable[[], None]] = []

    def _ensure_rich(self) -> None:
        if not HAS_RICH:
            raise ImportError(
                "GhostUI requires the 'rich' package. "
                "Install it with: pip install nexora[ghost]"
            )

    @property
    def console(self) -> Console:
        if self._console is None:
            self._ensure_rich()
            if hasattr(sys.stdout, "reconfigure"):
                try:
                    sys.stdout.reconfigure(encoding="utf-8")
                except Exception:
                    pass
            self._console = Console(legacy_windows=False)
        return self._console

    @console.setter
    def console(self, console: Console) -> None:
        self._console = console
        self._symbols = None

    @property
    def symbols(self) -> _Symbols:
        if self._symbols is None:
            self._symbols = _Symbols(self.console)
        return self._symbols

    # --- Lifecycle hooks ---
    def on_register(self) -> None:
        if self._registered:
            return
        self._registered = True
        self._subscribe_events()

    def on_start(self) -> None:
        self._ensure_rich()
        self._started = True
        self._start_time = time.perf_counter()
        if self.show_header and not self.quiet:
            self.render_header()

    def on_stop(self) -> None:
        if not self._started:
            return
        if self.show_summary and not self.quiet and HAS_RICH:
            self.render_summary()
        self._started = False

    # --- Event Subscriptions ---
    def _subscribe_events(self) -> None:
        bus = self.app.bus

        # Tasks
        self._sub(bus, "task.started", self._on_task_started)
        self._sub(bus, "task.completed", self._on_task_completed)
        self._sub(bus, "task.failed", self._on_task_failed)

        # Progress
        self._sub(bus, "progress", self._on_progress)
        self._sub(bus, "progress.*", self._on_progress)
        self._sub(bus, "task.progress", self._on_progress)

        # Status
        self._sub(bus, "status", self._on_status)
        self._sub(bus, "status.*", self._on_status)

        # Logs
        self._sub(bus, "log", self._on_log)
        self._sub(bus, "log.*", self._on_log)

        # Errors
        self._sub(bus, "error", self._on_error)
        self._sub(bus, "error.*", self._on_error)

        # Metrics
        self._sub(bus, "metric", self._on_metric)
        self._sub(bus, "metric.*", self._on_metric)

        # Tables
        self._sub(bus, "table", self._on_table)
        self._sub(bus, "table.*", self._on_table)

        # State
        self._sub(bus, "state.changed", self._on_state_changed)

        # Timeline (TimeLoop interoperability)
        self._sub(bus, "timeline.checkpoint", self._on_timeline_checkpoint)
        self._sub(bus, "timeline.restored", self._on_timeline_restored)
        self._sub(bus, "timeline.rewound", self._on_timeline_restored)

    def _sub(self, bus: Any, event_type: str, handler: Callable[[Any], None]) -> None:
        h = bus.on(event_type, handler)
        self._unsubscribers.append(lambda: bus.off(event_type, h))

    # --- Event Handlers ---
    def _on_task_started(self, event: "Event") -> None:
        task_name = str(event.payload.get("task", event.source or "unknown"))
        self.task_records[task_name] = TaskRecord(
            name=task_name,
            status="running",
            start_time=time.perf_counter(),
        )
        if self.show_tasks and not self.quiet and HAS_RICH:
            glyph = self.symbols.bullet
            self.console.print(
                f"[bold cyan]{glyph} Starting task:[/bold cyan] [white]{escape(task_name)}[/white]"
            )

    def _on_task_completed(self, event: "Event") -> None:
        task_name = str(event.payload.get("task", event.source or "unknown"))
        duration = float(event.payload.get("duration_seconds", 0.0))
        record = self.task_records.get(task_name)
        if record:
            record.status = "completed"
            record.end_time = time.perf_counter()
            record.duration = duration
        else:
            self.task_records[task_name] = TaskRecord(
                name=task_name,
                status="completed",
                start_time=time.perf_counter() - duration,
                end_time=time.perf_counter(),
                duration=duration,
            )
        if self.show_tasks and not self.quiet and HAS_RICH:
            glyph = self.symbols.check
            self.console.print(
                f"[bold green]{glyph} Completed task:[/bold green] [white]{escape(task_name)}[/white] "
                f"[dim]({duration:.4f}s)[/dim]"
            )

    def _on_task_failed(self, event: "Event") -> None:
        task_name = str(event.payload.get("task", event.source or "unknown"))
        duration = float(event.payload.get("duration_seconds", 0.0))
        error = str(event.payload.get("error", "Unknown error"))
        tb = event.payload.get("traceback")
        record = self.task_records.get(task_name)
        if record:
            record.status = "failed"
            record.end_time = time.perf_counter()
            record.duration = duration
            record.error = error
            record.traceback = tb
        else:
            self.task_records[task_name] = TaskRecord(
                name=task_name,
                status="failed",
                start_time=time.perf_counter() - duration,
                end_time=time.perf_counter(),
                duration=duration,
                error=error,
                traceback=tb,
            )
        if self.show_tasks and not self.quiet and HAS_RICH:
            glyph = self.symbols.cross
            self.console.print(
                f"[bold red]{glyph} Failed task:[/bold red] [white]{escape(task_name)}[/white] "
                f"[dim]({duration:.4f}s)[/dim] - [red]{escape(error)}[/red]"
            )
        if self.show_errors and not self.quiet and HAS_RICH:
            self.render_error_panel(task=task_name, error=error, traceback_text=tb)

    def _on_progress(self, event: "Event") -> None:
        task = str(
            event.payload.get("task")
            or event.payload.get("name")
            or event.source
            or "progress"
        )
        completed = float(event.payload.get("completed", 0.0))
        total = float(event.payload.get("total", 100.0))
        unit = str(event.payload.get("unit", ""))
        desc = str(event.payload.get("description", ""))

        self.progress_records[task] = ProgressRecord(
            name=task,
            completed=completed,
            total=total,
            unit=unit,
            description=desc,
            updated_at=time.perf_counter(),
        )

        if self.show_progress and not self.quiet and HAS_RICH:
            pct = min(max((completed / total * 100.0) if total > 0 else 0.0, 0.0), 100.0)
            filled = int(20 * pct / 100.0)
            bar = (self.symbols.bar_fill * filled) + (self.symbols.bar_tip if (0 < filled < 20) else "") + (self.symbols.bar_empty * max(0, 19 - filled))
            if filled >= 20:
                bar = self.symbols.bar_fill * 20
            unit_str = f" {escape(unit)}" if unit else ""
            desc_str = f" [dim]({escape(desc)})[/dim]" if desc else ""
            escaped_task = escape(f"[{task}]")
            glyph = self.symbols.running
            self.console.print(
                f"[cyan]{glyph} Progress {escaped_task}:[/cyan] "
                f"[bold cyan]{bar}[/bold cyan] {completed:g}/{total:g}{unit_str} "
                f"[bold green]({pct:.1f}%)[/bold green]{desc_str}"
            )

    def _on_status(self, event: "Event") -> None:
        status = str(
            event.payload.get("status")
            or event.payload.get("message")
            or event.type
        )
        msg = str(event.payload.get("message", "")) if "status" in event.payload else ""
        if self.show_status and not self.quiet and HAS_RICH:
            msg_part = f" - {escape(msg)}" if msg else ""
            escaped_status = escape(f"[{status}]")
            glyph = self.symbols.bolt
            self.console.print(
                f"[bold magenta]{glyph} Status {escaped_status}:[/bold magenta]{msg_part}"
            )

    def _on_log(self, event: "Event") -> None:
        msg = str(event.payload.get("message", ""))
        if "level" in event.payload:
            level = str(event.payload["level"]).upper()
        elif event.type.startswith("log."):
            level = event.type.split(".", 1)[1].upper()
        else:
            level = "INFO"
        source = str(event.payload.get("source") or event.source or "app")

        rec = LogRecord(message=msg, level=level, source=source, timestamp=event.timestamp)
        self.logs.append(rec)

        if self.show_logs and not self.quiet and HAS_RICH:
            if isinstance(event.timestamp, str):
                time_str = event.timestamp[11:19] if len(event.timestamp) >= 19 else event.timestamp
            else:
                time_str = event.timestamp.strftime("%H:%M:%S")

            if level == "DEBUG":
                badge = "[dim cyan]DEBUG[/dim cyan]"
            elif level == "INFO":
                badge = "[bold blue]INFO [/bold blue]"
            elif level in ("WARNING", "WARN"):
                badge = "[bold yellow]WARN [/bold yellow]"
            elif level == "ERROR":
                badge = "[bold red]ERROR[/bold red]"
            elif level in ("CRITICAL", "FATAL"):
                badge = "[bold white on red]CRIT [/bold white on red]"
            else:
                badge = f"[cyan]{level:<5}[/cyan]"

            escaped_source = escape(f"[{source}]")
            self.console.print(
                f"[dim]{time_str}[/dim] {badge} [dim]{escaped_source}[/dim] {escape(msg)}"
            )

    def _on_error(self, event: "Event") -> None:
        # task.failed errors are handled in _on_task_failed
        if event.type == "task.failed":
            return
        err = str(event.payload.get("error", "Unknown error"))
        tb = event.payload.get("traceback")
        task = event.payload.get("task")
        source = str(event.source or "app")
        if self.show_errors and not self.quiet and HAS_RICH:
            self.render_error_panel(task=task or source, error=err, traceback_text=tb)

    def _on_metric(self, event: "Event") -> None:
        name = str(event.payload.get("name", event.source or "metric"))
        val = event.payload.get("value")
        unit = event.payload.get("unit")
        tags = event.payload.get("tags") or {}

        try:
            num_val = float(val)
        except (ValueError, TypeError):
            num_val = None

        if name in self.metrics:
            rec = self.metrics[name]
            rec.value = val
            rec.count += 1
            if unit:
                rec.unit = unit
            if num_val is not None:
                if rec.min_value is None or num_val < rec.min_value:
                    rec.min_value = num_val
                if rec.max_value is None or num_val > rec.max_value:
                    rec.max_value = num_val
        else:
            self.metrics[name] = MetricRecord(
                name=name,
                value=val,
                unit=unit,
                count=1,
                min_value=num_val,
                max_value=num_val,
                tags=tags,
            )

        if self.show_metrics and not self.quiet and HAS_RICH:
            unit_str = f" {escape(unit)}" if unit else ""
            escaped_name = escape(f"[{name}]")
            glyph = self.symbols.chart
            self.console.print(
                f"[bold cyan]{glyph} Metric {escaped_name}:[/bold cyan] "
                f"[bold white]{escape(str(val))}[/bold white]{unit_str}"
            )

    def _on_table(self, event: "Event") -> None:
        title = str(event.payload.get("title", "Data Table"))
        columns = list(event.payload.get("columns", []))
        rows = list(event.payload.get("rows", []))
        self.tables_rendered.append({"title": title, "columns": columns, "rows": rows})
        if self.show_tables and not self.quiet and HAS_RICH:
            self.render_table(title=title, columns=columns, rows=rows)

    def _on_state_changed(self, event: "Event") -> None:
        if self.show_state and not self.quiet and HAS_RICH:
            key = escape(str(event.payload.get("key", "")))
            old = escape(str(event.payload.get("old", "")))
            new = escape(str(event.payload.get("new", "")))
            self.console.print(
                f"[dim magenta]State changed:[/dim magenta] [cyan]{key}[/cyan] = "
                f"[white]{new}[/white] [dim](was {old})[/dim]"
            )

    def _on_timeline_checkpoint(self, event: "Event") -> None:
        label = str(event.payload.get("label", "unnamed"))
        snap_id = str(event.payload.get("id", ""))[:8]
        keys_count = event.payload.get("keys_count", 0)
        self.logs.append(
            LogRecord(
                level="INFO",
                message=f"[TimeLoop] Checkpoint '{label}' saved ({keys_count} keys, id={snap_id})",
                source="timeline",
                timestamp=time.time(),
            )
        )
        if self.show_tasks and not self.quiet and HAS_RICH:
            glyph = self.symbols.bullet
            self.console.print(
                f"[bold magenta]{glyph} TimeLoop Checkpoint:[/bold magenta] [white]{escape(label)}[/white] [dim]({snap_id})[/dim]"
            )

    def _on_timeline_restored(self, event: "Event") -> None:
        label = str(event.payload.get("label", "unnamed"))
        snap_id = str(event.payload.get("id", ""))[:8]
        self.logs.append(
            LogRecord(
                level="INFO",
                message=f"[TimeLoop] Restored state to checkpoint '{label}' (id={snap_id})",
                source="timeline",
                timestamp=time.time(),
            )
        )
        if self.show_tasks and not self.quiet and HAS_RICH:
            glyph = self.symbols.bolt
            self.console.print(
                f"[bold yellow]{glyph} TimeLoop Rewound:[/bold yellow] [white]{escape(label)}[/white] [dim]({snap_id})[/dim]"
            )

    # --- Render Methods ---
    def render_header(self) -> None:
        """Render the application header panel."""
        self._ensure_rich()
        task_names = ", ".join(self.app.tasks) if self.app.tasks else "none"
        features = ", ".join(self.app.runtime.plugins.keys())
        content = (
            f"[bold cyan]NEXORA GhostUI[/bold cyan] [dim]v{__version__}[/dim]\n"
            f"[dim]Features:[/dim] [yellow]{escape(features)}[/yellow]  •  "
            f"[dim]Registered Tasks ({len(self.app.tasks)}):[/dim] [green]{escape(task_names)}[/green]"
        )
        panel = Panel(
            content,
            border_style="cyan",
            title="[bold]NEXORA Runtime[/bold]",
            subtitle="[dim]Milestone 1 — GhostUI[/dim]",
        )
        self.console.print(panel)

    def render_table(
        self,
        title: str,
        columns: Sequence[str],
        rows: Sequence[Sequence[Any]],
    ) -> Table:
        """Render a styled table to console."""
        self._ensure_rich()
        table = Table(title=title, box=box.ROUNDED, header_style="bold magenta")
        for col in columns:
            table.add_column(str(col))
        for row in rows:
            table.add_row(*[str(cell) for cell in row])
        self.console.print(table)
        return table

    def render_error_panel(
        self,
        task: Optional[str] = None,
        error: Optional[str] = None,
        traceback_text: Optional[str] = None,
    ) -> None:
        """Render an error panel with details and traceback."""
        self._ensure_rich()
        lines: List[str] = []
        if task:
            lines.append(f"[bold red]Task / Source:[/bold red] [white]{escape(task)}[/white]")
        if error:
            lines.append(f"[bold red]Error:[/bold red] [red]{escape(error)}[/red]")
        if traceback_text:
            lines.append("\n[dim]Traceback:[/dim]")
            lines.append(f"[dim red]{escape(traceback_text.strip())}[/dim red]")

        glyph = self.symbols.cross
        panel = Panel(
            "\n".join(lines),
            title=f"[bold red]{glyph} Error Encountered[/bold red]",
            border_style="red",
        )
        self.console.print(panel)

    def render_summary(self) -> None:
        """Render the end-of-run execution dashboard."""
        self._ensure_rich()
        # Tasks Summary Table
        if self.task_records:
            table = Table(
                title="Tasks Summary",
                box=box.ROUNDED,
                header_style="bold cyan",
            )
            table.add_column("#", justify="right", style="dim")
            table.add_column("Task", style="bold")
            table.add_column("Status", justify="center")
            table.add_column("Duration", justify="right")
            table.add_column("Details")

            for idx, record in enumerate(self.task_records.values(), start=1):
                if record.status == "completed":
                    status_badge = f"[bold green]{self.symbols.check} COMPLETED[/bold green]"
                elif record.status == "failed":
                    status_badge = f"[bold red]{self.symbols.cross} FAILED[/bold red]"
                else:
                    status_badge = f"[bold yellow]{self.symbols.running} RUNNING[/bold yellow]"

                dur_str = f"{record.duration:.4f}s" if record.duration is not None else "-"
                details = f"[red]{escape(record.error)}[/red]" if record.error else ""
                table.add_row(str(idx), escape(record.name), status_badge, dur_str, details)

            self.console.print(table)

        # Metrics Summary Table
        if self.metrics:
            m_table = Table(
                title="Metrics Summary",
                box=box.ROUNDED,
                header_style="bold cyan",
            )
            m_table.add_column("Metric", style="bold")
            m_table.add_column("Latest Value", justify="right")
            m_table.add_column("Unit", justify="center", style="dim")
            m_table.add_column("Updates", justify="right")
            m_table.add_column("Min / Max", justify="right", style="dim")

            for rec in self.metrics.values():
                unit_str = rec.unit or "-"
                min_max_str = (
                    f"{rec.min_value:g} / {rec.max_value:g}"
                    if (rec.min_value is not None and rec.max_value is not None)
                    else "-"
                )
                m_table.add_row(
                    escape(rec.name),
                    escape(str(rec.value)),
                    escape(unit_str),
                    str(rec.count),
                    min_max_str,
                )
            self.console.print(m_table)

        # Overall Run Summary
        total_tasks = len(self.task_records)
        completed_tasks = sum(1 for r in self.task_records.values() if r.status == "completed")
        failed_tasks = sum(1 for r in self.task_records.values() if r.status == "failed")
        elapsed = (
            time.perf_counter() - self._start_time
            if self._start_time is not None
            else 0.0
        )

        status_text = (
            f"[bold]Total Tasks:[/bold] {total_tasks}  •  "
            f"[bold green]Completed:[/bold green] {completed_tasks}  •  "
            f"[bold red]Failed:[/bold red] {failed_tasks}  •  "
            f"[dim]Total Elapsed:[/dim] [cyan]{elapsed:.3f}s[/cyan]"
        )
        border = "green" if failed_tasks == 0 else "red"
        self.console.print(
            Panel(
                status_text,
                title="[bold]Run Summary[/bold]",
                border_style=border,
            )
        )

    # --- Programmatic Helper Methods ---
    def log(self, message: str, level: str = "INFO", source: str = "ghost") -> None:
        """Emit a structured log event on the App event bus."""
        self.app.bus.emit(
            f"log.{level.lower()}",
            source=source,
            payload={"message": message, "level": level},
        )

    def progress(
        self,
        name: str,
        completed: float,
        total: float = 100.0,
        unit: str = "",
        description: str = "",
    ) -> None:
        """Emit a progress update event on the App event bus."""
        self.app.bus.emit(
            "progress.updated",
            source="ghost",
            payload={
                "task": name,
                "completed": completed,
                "total": total,
                "unit": unit,
                "description": description,
            },
        )

    def metric(
        self,
        name: str,
        value: Any,
        unit: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a metric event on the App event bus."""
        self.app.bus.emit(
            "metric",
            source="ghost",
            payload={
                "name": name,
                "value": value,
                "unit": unit,
                "tags": tags or {},
            },
        )

    def table(
        self,
        title: str,
        columns: Sequence[str],
        rows: Sequence[Sequence[Any]],
    ) -> None:
        """Emit a table display event on the App event bus."""
        self.app.bus.emit(
            "table",
            source="ghost",
            payload={"title": title, "columns": list(columns), "rows": list(rows)},
        )

    def status(self, status: str, message: str = "") -> None:
        """Emit a status update event on the App event bus."""
        self.app.bus.emit(
            "status.updated",
            source="ghost",
            payload={"status": status, "message": message},
        )


# Alias
GhostUI = GhostPlugin
