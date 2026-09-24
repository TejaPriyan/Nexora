"""Vision plugin (ScreenMind): explicitly-permissioned screen perception."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, ClassVar, List, Optional, Tuple, Union

from ..plugins.base import Plugin
from .engine import VisionEngine
from .models import BBox, MatchResult, ScreenImage

if TYPE_CHECKING:
    from ..app import App


class VisionPlugin(Plugin):
    """ScreenMind: explicitly-permissioned visual screen understanding.

    Provides screenshot capture, visual template matching, text search, and color locating.
    Privacy-first:
    - Every action requires explicit permission via PermissionManager.
    - Zero cloud uploads, zero telemetry, zero background recording.
    - click() and type() are strictly prohibited and out of scope.
    """

    name: ClassVar[str] = "vision"
    requires_extra: ClassVar[Optional[str]] = "vision"
    milestone: ClassVar[str] = "M7"

    SCOPES: ClassVar[Tuple[str, ...]] = (
        "vision.screenshot",
        "vision.find",
        "vision.ocr",
        "vision.locate",
    )

    def __init__(
        self,
        app: "App",
        *,
        engine: Optional[VisionEngine] = None,
    ) -> None:
        super().__init__(app)
        self.engine = engine or VisionEngine()
        self._started = False

    # --- Lifecycle ---

    def on_register(self) -> None:
        pass

    def on_start(self) -> None:
        self._started = True

    def on_stop(self) -> None:
        self._started = False

    # --- Permissions Helpers ---

    def grant_all(self, reason: str = "granted by caller") -> None:
        """Grant all ScreenMind vision permissions to the current application."""
        for scope in self.SCOPES:
            self.app.permissions.grant(scope, reason=reason)

    def revoke_all(self, reason: str = "revoked by caller") -> None:
        """Revoke all ScreenMind vision permissions."""
        for scope in self.SCOPES:
            self.app.permissions.revoke(scope, reason=reason)

    # --- Public Perception API ---

    def screenshot(
        self,
        region: Optional[Union[BBox, Tuple[int, int, int, int]]] = None,
    ) -> ScreenImage:
        """Capture screen image. Requires 'vision.screenshot' permission."""
        self.app.permissions.require("vision.screenshot")
        img = self.engine.screenshot(region)
        self.app.bus.emit(
            "vision.screenshot.captured",
            source="vision",
            payload={
                "width": img.width,
                "height": img.height,
                "timestamp": img.timestamp,
                "region": img.region.to_dict() if img.region else None,
            },
        )
        return img

    def find(
        self,
        template: Union[str, Path, ScreenImage, Any],
        image: Optional[ScreenImage] = None,
        *,
        threshold: float = 0.8,
    ) -> Optional[MatchResult]:
        """Locate template on screen. Requires 'vision.find' (and 'vision.screenshot' if capturing)."""
        self.app.permissions.require("vision.find")
        if image is None:
            image = self.screenshot()
        match = self.engine.find(template, image, threshold=threshold)
        if match:
            self.app.bus.emit(
                "vision.pattern.found",
                source="vision",
                payload={
                    "bbox": match.bbox.to_dict(),
                    "confidence": match.confidence,
                    "label": match.label,
                },
            )
        return match

    def find_all(
        self,
        template: Union[str, Path, ScreenImage, Any],
        image: Optional[ScreenImage] = None,
        *,
        threshold: float = 0.8,
        max_matches: int = 10,
    ) -> List[MatchResult]:
        """Locate all occurrences of template. Requires 'vision.find'."""
        self.app.permissions.require("vision.find")
        if image is None:
            image = self.screenshot()
        return self.engine.find_all(template, image, threshold=threshold, max_matches=max_matches)

    def find_text(
        self,
        text: str,
        image: Optional[ScreenImage] = None,
        *,
        case_sensitive: bool = False,
    ) -> List[MatchResult]:
        """Find text in screen image. Requires 'vision.ocr'."""
        self.app.permissions.require("vision.ocr")
        if image is None:
            image = self.screenshot()
        return self.engine.find_text(text, image, case_sensitive=case_sensitive)

    def locate(
        self,
        color: Union[Tuple[int, int, int], str],
        image: Optional[ScreenImage] = None,
        *,
        tolerance: int = 15,
    ) -> List[MatchResult]:
        """Locate colored screen elements. Requires 'vision.locate'."""
        self.app.permissions.require("vision.locate")
        if image is None:
            image = self.screenshot()
        return self.engine.locate(color, image, tolerance=tolerance)


# Alias
ScreenMind = VisionPlugin
