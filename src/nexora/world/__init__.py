"""CodeWorld: 2D visualization of NEXORA application execution and state.

Milestone 2 of NEXORA.  Provides an in-memory entity world model with
2D pygame rendering, driven by and integrated with the shared EventBus.
"""

from .models import Entity, World
from .plugin import CodeWorld, WorldPlugin
from .renderer import Renderer

STATUS = "implemented"

__all__ = [
    "Entity",
    "World",
    "WorldPlugin",
    "CodeWorld",
    "Renderer",
    "STATUS",
]
