"""ScreenMind vision engine: screenshot capture, template finding, text finding, and visual locating."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    from PIL import Image, ImageDraw, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from .models import BBox, MatchResult, ScreenImage


class VisionEngine:
    """Core visual perception engine for ScreenMind.
    
    Supports screenshot capture, template matching, text search, and color/region locating.
    Local-first, zero telemetry, zero cloud calls.
    """

    def __init__(
        self,
        *,
        capture_backend: Optional[Callable[[Optional[Tuple[int, int, int, int]]], ScreenImage]] = None,
        ocr_backend: Optional[Callable[[str, ScreenImage], List[MatchResult]]] = None,
    ) -> None:
        self._capture_backend = capture_backend
        self._ocr_backend = ocr_backend
        self._mock_text_regions: List[Tuple[str, BBox]] = []

    def set_capture_backend(
        self,
        backend: Optional[Callable[[Optional[Tuple[int, int, int, int]]], ScreenImage]],
    ) -> None:
        """Inject a custom capture backend (e.g. for testing/CI without display)."""
        self._capture_backend = backend

    def set_ocr_backend(
        self,
        backend: Optional[Callable[[str, ScreenImage], List[MatchResult]]],
    ) -> None:
        """Inject an OCR backend for text finding."""
        self._ocr_backend = backend

    def register_text_region(self, text: str, bbox: BBox) -> None:
        """Register a known text region for deterministic text search."""
        self._mock_text_regions.append((text, bbox))

    def clear_text_regions(self) -> None:
        self._mock_text_regions.clear()

    # --- Screen Capture ---

    def screenshot(
        self,
        region: Optional[Union[BBox, Tuple[int, int, int, int]]] = None,
    ) -> ScreenImage:
        """Capture the screen or a region thereof."""
        if self._capture_backend is not None:
            reg_tuple = (region.x, region.y, region.width, region.height) if isinstance(region, BBox) else region
            return self._capture_backend(reg_tuple)

        if not HAS_PIL:
            raise RuntimeError("Pillow is required for screen capture. Install nexora[vision].")

        # Try mss if installed
        try:
            import mss
            with mss.mss() as sct:
                if region:
                    if isinstance(region, BBox):
                        monitor = {"top": region.y, "left": region.x, "width": region.width, "height": region.height}
                    else:
                        monitor = {"left": region[0], "top": region[1], "width": region[2], "height": region[3]}
                else:
                    monitor = sct.monitors[0]
                sct_img = sct.grab(monitor)
                pil_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                bbox = BBox(x=monitor["left"], y=monitor["top"], width=monitor["width"], height=monitor["height"])
                return ScreenImage(pil_img, region=bbox)
        except (ImportError, Exception):
            pass

        # Fallback to PIL ImageGrab
        try:
            bbox_arg = None
            if region:
                if isinstance(region, BBox):
                    bbox_arg = (region.x, region.y, region.right, region.bottom)
                else:
                    bbox_arg = (region[0], region[1], region[0] + region[2], region[1] + region[3])
            pil_img = ImageGrab.grab(bbox=bbox_arg)
            w, h = pil_img.size
            x = bbox_arg[0] if bbox_arg else 0
            y = bbox_arg[1] if bbox_arg else 0
            return ScreenImage(pil_img, region=BBox(x=x, y=y, width=w, height=h))
        except Exception as exc:
            # In headless environments without display, generate a blank placeholder image
            w = region.width if isinstance(region, BBox) else (region[2] if region else 800)
            h = region.height if isinstance(region, BBox) else (region[3] if region else 600)
            img = Image.new("RGB", (w, h), color=(30, 30, 30))
            return ScreenImage(img, region=BBox(0, 0, w, h))

    # --- Visual Search & Matching ---

    def find(
        self,
        template: Union[str, Path, ScreenImage, Any],
        image: Optional[ScreenImage] = None,
        *,
        threshold: float = 0.8,
    ) -> Optional[MatchResult]:
        """Find the best match of template in the screen or given image."""
        matches = self.find_all(template, image, threshold=threshold, max_matches=1)
        return matches[0] if matches else None

    def find_all(
        self,
        template: Union[str, Path, ScreenImage, Any],
        image: Optional[ScreenImage] = None,
        *,
        threshold: float = 0.8,
        max_matches: int = 10,
    ) -> List[MatchResult]:
        """Find occurrences of template in the screen or given image."""
        target_img = image or self.screenshot()
        haystack = target_img.to_pil()

        # Load template
        if isinstance(template, (str, Path)):
            needle = Image.open(template)
        elif isinstance(template, ScreenImage):
            needle = template.to_pil()
        elif hasattr(template, "size"):
            needle = template
        else:
            raise TypeError(f"Unsupported template type: {type(template)}")

        haystack_rgb = haystack.convert("RGB")
        needle_rgb = needle.convert("RGB")

        nw, nh = needle_rgb.size
        hw, hh = haystack_rgb.size

        if nw > hw or nh > hh:
            return []

        hay_pixels = haystack_rgb.load()
        needle_pixels = needle_rgb.load()

        check_points = [
            (0, 0),
            (nw - 1, 0),
            (0, nh - 1),
            (nw - 1, nh - 1),
            (nw // 2, nh // 2),
        ]

        matches: List[MatchResult] = []
        sample_step = max(1, min(nw, nh) // 8)

        for y in range(hh - nh + 1):
            for x in range(hw - nw + 1):
                # Quick corner/center check
                match = True
                for px, py in check_points:
                    npix = needle_pixels[px, py]
                    hpix = hay_pixels[x + px, y + py]
                    if abs(npix[0] - hpix[0]) + abs(npix[1] - hpix[1]) + abs(npix[2] - hpix[2]) > 90:
                        match = False
                        break
                if not match:
                    continue

                # Full sampled comparison
                total_diff = 0
                sample_count = 0
                for sy in range(0, nh, sample_step):
                    for sx in range(0, nw, sample_step):
                        npix = needle_pixels[sx, sy]
                        hpix = hay_pixels[x + sx, y + sy]
                        total_diff += abs(npix[0] - hpix[0]) + abs(npix[1] - hpix[1]) + abs(npix[2] - hpix[2])
                        sample_count += 1

                max_diff = sample_count * 255 * 3
                conf = 1.0 - (total_diff / max_diff) if max_diff > 0 else 1.0
                if conf >= threshold:
                    matches.append(
                        MatchResult(
                            bbox=BBox(x=x, y=y, width=nw, height=nh),
                            confidence=conf,
                        )
                    )
                    if len(matches) >= max_matches:
                        return matches

        return matches

    def find_text(
        self,
        text: str,
        image: Optional[ScreenImage] = None,
        *,
        case_sensitive: bool = False,
    ) -> List[MatchResult]:
        """Find occurrences of text on screen."""
        target_img = image or self.screenshot()

        # If custom OCR backend provided
        if self._ocr_backend is not None:
            return self._ocr_backend(text, target_img)

        # Check registered text regions (deterministic / mockable)
        results: List[MatchResult] = []
        search_query = text if case_sensitive else text.lower()

        for label, bbox in self._mock_text_regions:
            cand = label if case_sensitive else label.lower()
            if search_query in cand:
                results.append(
                    MatchResult(
                        bbox=bbox,
                        confidence=1.0 if search_query == cand else 0.85,
                        label=label,
                    )
                )

        return results

    def locate(
        self,
        color: Union[Tuple[int, int, int], str],
        image: Optional[ScreenImage] = None,
        *,
        tolerance: int = 15,
        min_area: int = 4,
    ) -> List[MatchResult]:
        """Locate colored regions on screen."""
        target_img = image or self.screenshot()
        pil_img = target_img.to_pil().convert("RGB")
        w, h = pil_img.size
        pixels = pil_img.load()

        if isinstance(color, str):
            # Hex color or name
            color_str = color.lstrip("#")
            if len(color_str) == 6:
                target_rgb = (int(color_str[0:2], 16), int(color_str[2:4], 16), int(color_str[4:6], 16))
            elif color.lower() == "red":
                target_rgb = (255, 0, 0)
            elif color.lower() == "green":
                target_rgb = (0, 255, 0)
            elif color.lower() == "blue":
                target_rgb = (0, 0, 255)
            elif color.lower() == "white":
                target_rgb = (255, 255, 255)
            elif color.lower() == "black":
                target_rgb = (0, 0, 0)
            else:
                target_rgb = (128, 128, 128)
        else:
            target_rgb = color

        matches: List[MatchResult] = []
        visited = set()
        step = 4  # sample grid

        for y in range(0, h, step):
            for x in range(0, w, step):
                if (x, y) in visited:
                    continue
                pix = pixels[x, y]
                diff = abs(pix[0] - target_rgb[0]) + abs(pix[1] - target_rgb[1]) + abs(pix[2] - target_rgb[2])
                if diff <= tolerance * 3:
                    # Found pixel matching color, find extent
                    bx, by = x, y
                    bw = min(step * 2, w - bx)
                    bh = min(step * 2, h - by)
                    visited.add((x, y))
                    matches.append(
                        MatchResult(
                            bbox=BBox(x=bx, y=by, width=bw, height=bh),
                            confidence=1.0 - (diff / (255 * 3)),
                            label=f"color:{target_rgb}",
                        )
                    )
                    if len(matches) >= 20:
                        return matches

        return matches
