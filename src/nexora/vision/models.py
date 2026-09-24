"""Data models for ScreenMind (screen perception) module."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@dataclass(frozen=True)
class BBox:
    """Bounding box in screen coordinates."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True)
class MatchResult:
    """Visual detection match result."""

    bbox: BBox
    confidence: float
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": self.bbox.to_dict(),
            "confidence": self.confidence,
            "label": self.label,
            "metadata": dict(self.metadata),
        }


class ScreenImage:
    """In-memory screen capture container."""

    def __init__(
        self,
        image: Any,  # PIL.Image.Image or duck-typed
        *,
        region: Optional[BBox] = None,
        timestamp: Optional[float] = None,
    ) -> None:
        self._image = image
        self.region = region
        self.timestamp = timestamp if timestamp is not None else time.time()

    @property
    def width(self) -> int:
        return self._image.size[0] if hasattr(self._image, "size") else 0

    @property
    def height(self) -> int:
        return self._image.size[1] if hasattr(self._image, "size") else 0

    @property
    def size(self) -> Tuple[int, int]:
        return (self.width, self.height)

    def to_pil(self) -> Any:
        return self._image

    def save(self, path: Union[str, Path]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._image.save(p)

    def crop(self, bbox: BBox) -> "ScreenImage":
        box = (bbox.x, bbox.y, bbox.right, bbox.bottom)
        cropped = self._image.crop(box)
        return ScreenImage(cropped, region=bbox, timestamp=self.timestamp)
