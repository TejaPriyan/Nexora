"""Shadow observability engine: genuine measurement of execution, timing, and errors."""

from __future__ import annotations

import contextlib
import functools
import threading
import time
import traceback
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

from .models import (
    DependencyLink,
    FunctionProfile,
    ObservabilitySnapshot,
    ObservedError,
    ObservedEvent,
)


class ShadowEngine:
    """Thread-safe observational telemetry engine for running Python applications."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._functions: Dict[str, FunctionProfile] = {}
        self._events: Dict[str, ObservedEvent] = {}
        self._errors: List[ObservedError] = []
        self._dependencies: Dict[Tuple[str, str], int] = {}
        self._active_callers: threading.local = threading.local()

    def _get_current_caller(self) -> Optional[str]:
        return getattr(self._active_callers, "current", None)

    def _set_current_caller(self, caller: Optional[str]) -> None:
        self._active_callers.current = caller

    def track_function_call(
        self,
        name: str,
        duration: float,
        *,
        success: bool = True,
        error_msg: Optional[str] = None,
        now: Optional[float] = None,
    ) -> FunctionProfile:
        """Record an observed function execution with genuine timing measurement."""
        with self._lock:
            t = now if now is not None else time.time()
            if name not in self._functions:
                self._functions[name] = FunctionProfile(name=name)

            prof = self._functions[name]
            prof.call_count += 1
            prof.total_duration += duration
            prof.last_called = t
            if duration < prof.min_duration:
                prof.min_duration = duration
            if duration > prof.max_duration:
                prof.max_duration = duration
            if not success:
                prof.error_count += 1

            return prof

    def track_event(self, event_type: str, source: str, *, timestamp: Optional[float] = None) -> None:
        """Record an event observation flowing on the system bus."""
        with self._lock:
            t = timestamp if timestamp is not None else time.time()
            if event_type not in self._events:
                self._events[event_type] = ObservedEvent(
                    event_type=event_type,
                    first_seen=t,
                    last_seen=t,
                )

            ev = self._events[event_type]
            ev.count += 1
            ev.last_seen = t
            if source:
                ev.sources.add(source)

    def track_dependency(self, caller: str, callee: str) -> None:
        """Record a measured invocation dependency link between components."""
        with self._lock:
            key = (caller, callee)
            self._dependencies[key] = self._dependencies.get(key, 0) + 1

    def record_error(
        self,
        error_type: str,
        message: str,
        source: str,
        *,
        traceback_str: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> ObservedError:
        """Record a genuinely measured application error."""
        with self._lock:
            t = timestamp if timestamp is not None else time.time()
            err = ObservedError(
                error_type=error_type,
                message=message,
                source=source,
                timestamp=t,
                traceback=traceback_str,
            )
            self._errors.append(err)
            return err

    def trace(
        self,
        func_or_name: Optional[Union[Callable[..., Any], str]] = None,
    ) -> Any:
        """Decorator to genuinely measure function execution time and capture errors."""
        def decorator(f: Callable[..., Any], explicit_name: Optional[str] = None) -> Callable[..., Any]:
            name = explicit_name or getattr(f, "__name__", getattr(f, "__qualname__", str(f)))

            @functools.wraps(f)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                parent_caller = self._get_current_caller()
                if parent_caller and parent_caller != name:
                    self.track_dependency(parent_caller, name)

                self._set_current_caller(name)
                start_t = time.perf_counter()
                success = True
                err_msg = None
                try:
                    return f(*args, **kwargs)
                except Exception as exc:
                    success = False
                    err_msg = str(exc)
                    tb = traceback.format_exc()
                    self.record_error(type(exc).__name__, err_msg, name, traceback_str=tb)
                    raise
                finally:
                    duration = time.perf_counter() - start_t
                    self.track_function_call(name, duration, success=success, error_msg=err_msg)
                    self._set_current_caller(parent_caller)

            return wrapper

        if callable(func_or_name):
            return decorator(func_or_name)
        elif isinstance(func_or_name, str):
            return lambda fn: decorator(fn, explicit_name=func_or_name)
        return decorator

    @contextlib.contextmanager
    def span(self, name: str) -> Iterator[None]:
        """Context manager to measure a named block execution."""
        parent_caller = self._get_current_caller()
        if parent_caller and parent_caller != name:
            self.track_dependency(parent_caller, name)

        self._set_current_caller(name)
        start_t = time.perf_counter()
        success = True
        err_msg = None
        try:
            yield
        except Exception as exc:
            success = False
            err_msg = str(exc)
            tb = traceback.format_exc()
            self.record_error(type(exc).__name__, err_msg, name, traceback_str=tb)
            raise
        finally:
            duration = time.perf_counter() - start_t
            self.track_function_call(name, duration, success=success, error_msg=err_msg)
            self._set_current_caller(parent_caller)

    # --- Inspection & Queries ---

    def function_stats(self, name: Optional[str] = None) -> Union[Optional[FunctionProfile], Dict[str, FunctionProfile]]:
        with self._lock:
            if name is not None:
                if name in self._functions:
                    return self._functions[name]
                for k, v in self._functions.items():
                    if k.endswith(f".{name}") or k.endswith(f":{name}"):
                        return v
                return None
            return dict(self._functions)

    def event_stats(self) -> Dict[str, ObservedEvent]:
        with self._lock:
            return dict(self._events)

    def error_log(self) -> List[ObservedError]:
        with self._lock:
            return list(self._errors)

    def dependencies(self) -> List[DependencyLink]:
        with self._lock:
            return [
                DependencyLink(caller=k[0], callee=k[1], call_count=count)
                for k, count in self._dependencies.items()
            ]

    def snapshot(self) -> ObservabilitySnapshot:
        with self._lock:
            return ObservabilitySnapshot(
                timestamp=time.time(),
                total_events=sum(e.count for e in self._events.values()),
                total_function_calls=sum(f.call_count for f in self._functions.values()),
                total_errors=len(self._errors),
                functions={k: v.to_dict() for k, v in self._functions.items()},
                event_counts={k: v.count for k, v in self._events.items()},
                errors=[e.to_dict() for e in self._errors],
                dependencies=[d.to_dict() for d in self.dependencies()],
            )

    def reset(self) -> None:
        with self._lock:
            self._functions.clear()
            self._events.clear()
            self._errors.clear()
            self._dependencies.clear()
