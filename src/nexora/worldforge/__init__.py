"""WorldForge (procedural worlds) module for NEXORA.

Generate and manage interactive worlds from Python structures:
entities, maps, buildings, roads, characters, relationships, and basic procedural generation.
Shares the 'world' extra with CodeWorld, reusing its 2D entity and rendering primitives.
"""

from .engine import WorldForgeEngine
from .generator import ProceduralGenerator
from .models import Building, Character, Road, WorldMap
from .plugin import WorldForge, WorldForgePlugin

STATUS = "implemented"

__all__ = [
    "STATUS",
    "WorldForgePlugin",
    "WorldForge",
    "WorldForgeEngine",
    "ProceduralGenerator",
    "Building",
    "Road",
    "Character",
    "WorldMap",
]
