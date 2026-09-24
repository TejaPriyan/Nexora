"""ScreenMind (screen perception) module for NEXORA.

Provides controlled, explicitly-permissioned visual understanding of the screen:
screenshot(), find(), find_text(), locate().
Local-first, privacy-by-default, zero telemetry, zero hidden capture.
Every capability is strictly gated behind nexora.security.PermissionManager.
"""

from .engine import VisionEngine
from .models import BBox, MatchResult, ScreenImage
from .plugin import ScreenMind, VisionPlugin

STATUS = "implemented"

__all__ = [
    "STATUS",
    "VisionPlugin",
    "ScreenMind",
    "VisionEngine",
    "BBox",
    "MatchResult",
    "ScreenImage",
]
