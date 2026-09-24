"""NEXORA Runtime: wires together the event bus, state store, permission
manager, and the set of active plugins for a running App instance."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from ..config import Config
from ..events import EventBus
from ..plugins import Plugin, resolve
from ..security import PermissionManager
from ..state import State

if TYPE_CHECKING:
    from ..app import App


class Runtime:
    def __init__(self, *, config: Optional[Config] = None) -> None:
        self.config = config or Config.load()
        self.bus = EventBus()
        self.state = State(self.bus, source="runtime")
        self.permissions = PermissionManager()
        self.plugins: Dict[str, Plugin] = {}
        self._started = False

    def register(self, app: "App", feature: str) -> Plugin:
        plugin_cls = resolve(feature)
        plugin = plugin_cls(app)
        plugin.on_register()
        self.plugins[feature] = plugin
        self.bus.emit(
            "plugin.registered",
            source="runtime",
            payload={
                "feature": feature,
                "milestone": getattr(plugin, "milestone", "unknown"),
            },
        )
        return plugin

    def start(self) -> None:
        self._started = True
        self.bus.emit("runtime.started", source="runtime")
        for plugin in self.plugins.values():
            plugin.on_start()

    def stop(self) -> None:
        for plugin in self.plugins.values():
            plugin.on_stop()
        self.bus.emit("runtime.stopped", source="runtime")
        self._started = False

    @property
    def started(self) -> bool:
        return self._started
