"""2D renderer for CodeWorld using pygame.

Handles window creation, entity drawing, relationship lines,
label rendering, camera pan/zoom, and entity selection/inspection.
The renderer is fully separated from the World model — it only reads
entity state at render time, making it safe to run the renderer on
a separate thread (or not at all, for headless/test use).
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

try:
    import pygame  # pyright: ignore[reportMissingImports]  # type: ignore
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
    pygame: Any = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from .models import Entity, World


# --- Colour helpers ---

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert '#rrggbb' or '#rgb' to (r, g, b)."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except (ValueError, IndexError):
        return (120, 120, 120)


# --- Default theme ---

_BG_COLOR = (18, 18, 24)
_GRID_COLOR = (30, 30, 42)
_LABEL_COLOR = (200, 200, 210)
_REL_COLOR = (80, 80, 110)
_SELECTED_COLOR = (255, 220, 80)
_INSPECTOR_BG = (24, 24, 36, 210)
_INSPECTOR_TEXT = (220, 220, 230)
_FONT_SIZE = 14
_TITLE_FONT_SIZE = 16


class Renderer:
    """A pygame-based 2D renderer for a CodeWorld ``World``.

    Call ``open()`` to create the window, ``draw()`` to render one frame,
    and ``close()`` to tear it down.  The ``run_loop()`` convenience runs
    a standard event-loop until the user closes the window.
    """

    def __init__(
        self,
        world: "World",
        *,
        width: int = 960,
        height: int = 640,
        title: str = "NEXORA CodeWorld",
        fps: int = 30,
        show_grid: bool = True,
        show_labels: bool = True,
        show_relationships: bool = True,
    ) -> None:
        self.world = world
        self.width = width
        self.height = height
        self.title = title
        self.fps = fps
        self.show_grid = show_grid
        self.show_labels = show_labels
        self.show_relationships = show_relationships

        # Camera state
        self.cam_x: float = 0.0
        self.cam_y: float = 0.0
        self.zoom: float = 1.0

        # Selection / inspection
        self.selected_id: Optional[str] = None

        # Pygame objects (set in open())
        self._screen: Any = None
        self._clock: Any = None
        self._font: Any = None
        self._title_font: Any = None
        self._running = False
        self._opened = False

    @staticmethod
    def available() -> bool:
        return HAS_PYGAME

    def _ensure_pygame(self) -> None:
        if not HAS_PYGAME:
            raise ImportError(
                "CodeWorld renderer requires 'pygame'. "
                "Install it with: pip install nexora[world]"
            )

    # --- Coordinate transforms ---

    def world_to_screen(self, wx: float, wy: float) -> Tuple[int, int]:
        sx = int((wx - self.cam_x) * self.zoom + self.width / 2)
        sy = int((wy - self.cam_y) * self.zoom + self.height / 2)
        return sx, sy

    def screen_to_world(self, sx: int, sy: int) -> Tuple[float, float]:
        wx = (sx - self.width / 2) / self.zoom + self.cam_x
        wy = (sy - self.height / 2) / self.zoom + self.cam_y
        return wx, wy

    # --- Window lifecycle ---

    def open(self) -> None:
        """Create the pygame window."""
        self._ensure_pygame()
        pygame.init()
        self._screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(self.title)
        self._clock = pygame.time.Clock()
        self._font = pygame.font.SysFont("consolas,monospace", _FONT_SIZE)
        self._title_font = pygame.font.SysFont("consolas,monospace", _TITLE_FONT_SIZE, bold=True)
        self._opened = True
        self._running = True

    def close(self) -> None:
        """Destroy the window."""
        self._running = False
        if self._opened:
            pygame.quit()
            self._opened = False

    @property
    def is_open(self) -> bool:
        return self._opened and self._running

    # --- Drawing ---

    def draw(self) -> None:
        """Render one frame of the current world state."""
        if not self._opened or self._screen is None:
            return

        self._screen.fill(_BG_COLOR)

        if self.show_grid:
            self._draw_grid()

        entities = self.world.entities()
        entity_map = {e.id: e for e in entities}

        # Relationships (drawn first, under entities)
        if self.show_relationships:
            for ent in entities:
                for rel_name, target_id in ent.relationships:
                    target = entity_map.get(target_id)
                    if target is not None:
                        self._draw_relationship(ent, target, rel_name)

        # Entities
        for ent in entities:
            if ent.visible:
                self._draw_entity(ent)

        # Inspector for selected entity
        if self.selected_id and self.selected_id in entity_map:
            self._draw_inspector(entity_map[self.selected_id])

        pygame.display.flip()

    def _draw_grid(self) -> None:
        step = max(40, int(60 * self.zoom))
        # Vertical lines
        start_wx = self.cam_x - self.width / (2 * self.zoom)
        offset = start_wx % step
        wx = start_wx - offset
        while True:
            sx, _ = self.world_to_screen(wx, 0)
            if sx > self.width:
                break
            pygame.draw.line(self._screen, _GRID_COLOR, (sx, 0), (sx, self.height))
            wx += step
        # Horizontal lines
        start_wy = self.cam_y - self.height / (2 * self.zoom)
        offset = start_wy % step
        wy = start_wy - offset
        while True:
            _, sy = self.world_to_screen(0, wy)
            if sy > self.height:
                break
            pygame.draw.line(self._screen, _GRID_COLOR, (0, sy), (self.width, sy))
            wy += step

    def _draw_entity(self, ent: "Entity") -> None:
        sx, sy = self.world_to_screen(ent.x, ent.y)
        r = max(4, int(ent.size * self.zoom / 2))
        rgb = _hex_to_rgb(ent.color)

        is_selected = ent.id == self.selected_id

        if ent.shape == "rect":
            rect = pygame.Rect(sx - r, sy - r, r * 2, r * 2)
            pygame.draw.rect(self._screen, rgb, rect)
            if is_selected:
                pygame.draw.rect(self._screen, _SELECTED_COLOR, rect, 2)
        elif ent.shape == "diamond":
            points = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
            pygame.draw.polygon(self._screen, rgb, points)
            if is_selected:
                pygame.draw.polygon(self._screen, _SELECTED_COLOR, points, 2)
        else:  # circle
            pygame.draw.circle(self._screen, rgb, (sx, sy), r)
            if is_selected:
                pygame.draw.circle(self._screen, _SELECTED_COLOR, (sx, sy), r + 2, 2)

        if self.show_labels:
            label_surf = self._font.render(ent.display_label, True, _LABEL_COLOR)
            lx = sx - label_surf.get_width() // 2
            ly = sy + r + 4
            self._screen.blit(label_surf, (lx, ly))

    def _draw_relationship(self, source: "Entity", target: "Entity", name: str) -> None:
        sx1, sy1 = self.world_to_screen(source.x, source.y)
        sx2, sy2 = self.world_to_screen(target.x, target.y)
        pygame.draw.line(self._screen, _REL_COLOR, (sx1, sy1), (sx2, sy2), 1)

        # Label at midpoint
        if self.show_labels and name:
            mx, my = (sx1 + sx2) // 2, (sy1 + sy2) // 2
            label_surf = self._font.render(name, True, _REL_COLOR)
            self._screen.blit(label_surf, (mx + 4, my - 8))

    def _draw_inspector(self, ent: "Entity") -> None:
        """Draw a semi-transparent inspector panel for the selected entity."""
        pad = 10
        line_h = 18
        lines: List[str] = [
            f"ID: {ent.id}",
            f"Kind: {ent.kind}",
            f"Position: ({ent.x:.1f}, {ent.y:.1f})",
            f"Color: {ent.color}  Shape: {ent.shape}",
        ]
        if ent.properties:
            lines.append("Properties:")
            for k, v in ent.properties.items():
                lines.append(f"  {k}: {v}")
        if ent.relationships:
            lines.append("Relationships:")
            for rn, tid in ent.relationships:
                lines.append(f"  --[{rn}]--> {tid}")

        panel_w = 280
        panel_h = pad * 2 + len(lines) * line_h + line_h  # extra line for title
        panel_x = self.width - panel_w - 12
        panel_y = 12

        # Semi-transparent background
        surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        surf.fill(_INSPECTOR_BG)
        self._screen.blit(surf, (panel_x, panel_y))

        # Title
        title_text = self._title_font.render(ent.display_label, True, _SELECTED_COLOR)
        self._screen.blit(title_text, (panel_x + pad, panel_y + pad))

        # Lines
        ty = panel_y + pad + line_h
        for line in lines:
            txt = self._font.render(line, True, _INSPECTOR_TEXT)
            self._screen.blit(txt, (panel_x + pad, ty))
            ty += line_h

    # --- Hit-testing ---

    def entity_at_screen(self, sx: int, sy: int) -> Optional[str]:
        """Return the ID of the entity under screen coords (sx, sy), or None."""
        wx, wy = self.screen_to_world(sx, sy)
        best: Optional["Entity"] = None
        best_dist = float("inf")
        for ent in self.world.entities():
            if not ent.visible:
                continue
            d2 = (ent.x - wx) ** 2 + (ent.y - wy) ** 2
            hit_r = (ent.size / 2) ** 2
            if d2 <= hit_r and d2 < best_dist:
                best = ent
                best_dist = d2
        return best.id if best is not None else None

    # --- Input handling ---

    def handle_events(self) -> bool:
        """Process pygame events. Return False if the window was closed."""
        if not HAS_PYGAME:
            return False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # left click → select
                    self.selected_id = self.entity_at_screen(*event.pos)
            elif event.type == pygame.KEYDOWN:
                self._handle_key(event.key)
        return True

    def _handle_key(self, key: int) -> None:
        pan_speed = 20 / self.zoom
        if key == pygame.K_LEFT or key == pygame.K_a:
            self.cam_x -= pan_speed
        elif key == pygame.K_RIGHT or key == pygame.K_d:
            self.cam_x += pan_speed
        elif key == pygame.K_UP or key == pygame.K_w:
            self.cam_y -= pan_speed
        elif key == pygame.K_DOWN or key == pygame.K_s:
            self.cam_y += pan_speed
        elif key == pygame.K_EQUALS or key == pygame.K_PLUS:
            self.zoom = min(self.zoom * 1.2, 5.0)
        elif key == pygame.K_MINUS:
            self.zoom = max(self.zoom / 1.2, 0.2)
        elif key == pygame.K_ESCAPE:
            self.selected_id = None
        elif key == pygame.K_r:
            self.cam_x, self.cam_y, self.zoom = 0.0, 0.0, 1.0

    # --- Main loop ---

    def run_loop(self) -> None:
        """Open the window and run until the user closes it."""
        self.open()
        try:
            while self._running:
                if not self.handle_events():
                    break
                self.draw()
                self._clock.tick(self.fps)
        finally:
            self.close()

    def run_loop_in_thread(self) -> threading.Thread:
        """Start the render loop in a daemon thread (non-blocking)."""
        t = threading.Thread(target=self.run_loop, daemon=True)
        t.start()
        return t
