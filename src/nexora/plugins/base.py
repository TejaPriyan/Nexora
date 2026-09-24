"""Base classes for NEXORA plugins (feature modules).

A "feature" string (e.g. "ghost", "world") maps to a Plugin subclass via
the PluginRegistry. Plugins are the extension point every optional NEXORA
module -- Ghost, World, Adaptive, Memory, Timeline, Vision, Shadow,
WorldForge, AgentBox -- will hook into as each is built, one milestone at a
time (see docs/ROADMAP.md).
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, ClassVar, Optional

if TYPE_CHECKING:
    from ..app import App


class Plugin(ABC):
    """Base class every NEXORA feature module implements."""

    name: ClassVar[str]
    requires_extra: ClassVar[Optional[str]] = None
    milestone: ClassVar[str] = "unscheduled"

    def __init__(self, app: "App") -> None:
        self.app = app

    def on_register(self) -> None:
        """Called once when the plugin is attached to an App."""

    def on_start(self) -> None:
        """Called when app.run() starts."""

    def on_stop(self) -> None:
        """Called when the app stops."""


class PlannedPlugin(Plugin):
    """Placeholder for a feature that is designed but not yet implemented.

    NEXORA is built incrementally: core first, then one module at a time,
    each landing in a runnable state. Requesting a planned feature does not
    crash App construction (so you can see it listed, inspect its
    docstring, etc.), but actually starting it raises a clear, honest error
    instead of silently no-op'ing or faking behavior.
    """

    milestone: ClassVar[str] = "planned"
    summary: ClassVar[str] = ""

    def on_start(self) -> None:
        raise NotImplementedError(
            f"NEXORA feature '{self.name}' is designed (see docs/ROADMAP.md) "
            f"but not implemented yet in this version of nexora-core. "
            f"{self.summary} "
            f"It will not silently no-op: remove '{self.name}' from "
            f"features=[...] until it ships, or track progress in the "
            f"project roadmap."
        )
