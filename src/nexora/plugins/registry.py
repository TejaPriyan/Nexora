"""Maps feature names (as passed to ``App(features=[...])``) to Plugin
classes.

As each module milestone lands, its entry here points at a real
implementation instead of ``PlannedPlugin`` -- callers do not need to
change their code.  Currently implemented: ``ghost`` (M1), ``world`` (M2).
"""

from __future__ import annotations

from typing import Dict, Optional, Type

from ..adaptive import AdaptivePlugin
from ..agentbox import AgentBoxPlugin
from ..ghost import GhostPlugin
from ..memory import MemoryPlugin
from ..shadow import ShadowPlugin
from ..timeline import TimelinePlugin
from ..vision import VisionPlugin
from ..world import WorldPlugin
from ..worldforge import WorldForgePlugin
from .base import PlannedPlugin, Plugin


def _planned(name: str, extra: Optional[str], summary: str) -> Type[Plugin]:
    return type(
        f"Planned_{name.capitalize()}",
        (PlannedPlugin,),
        {"name": name, "requires_extra": extra, "summary": summary},
    )


_REGISTRY: Dict[str, Type[Plugin]] = {
    "ghost": GhostPlugin,
    "world": WorldPlugin,
    "adaptive": AdaptivePlugin,
    "memory": MemoryPlugin,
    "timeline": TimelinePlugin,
    "shadow": ShadowPlugin,
    "vision": VisionPlugin,
    "worldforge": WorldForgePlugin,
    "agentbox": AgentBoxPlugin,
}


class UnknownFeatureError(ValueError):
    pass


def resolve(feature: str) -> Type[Plugin]:
    try:
        return _REGISTRY[feature]
    except KeyError as exc:
        known = ", ".join(sorted(_REGISTRY))
        raise UnknownFeatureError(
            f"Unknown NEXORA feature {feature!r}. Known features: {known}"
        ) from exc


def available_features() -> Dict[str, Type[Plugin]]:
    return dict(_REGISTRY)
