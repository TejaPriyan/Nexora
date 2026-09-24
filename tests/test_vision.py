"""Tests for ScreenMind (screen perception) module."""

import socket
import pytest
from PIL import Image, ImageDraw

from nexora import App
from nexora.security import PermissionDenied
from nexora.vision import (
    BBox,
    MatchResult,
    ScreenImage,
    ScreenMind,
    VisionEngine,
    VisionPlugin,
)


def _create_synthetic_screen(width=200, height=150) -> Image.Image:
    """Create a deterministic synthetic screen image for headless testing."""
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    # Draw a blue rectangle at x=40, y=50, w=30, h=20
    draw.rectangle([40, 50, 70, 70], fill=(0, 100, 255))
    # Draw a red rectangle at x=120, y=80, w=20, h=20
    draw.rectangle([120, 80, 140, 100], fill=(255, 0, 0))
    return img


@pytest.fixture
def mock_vision_app():
    """Create an App with vision plugin and a mocked screen backend."""
    app = App(features=["vision"])
    synth_img = _create_synthetic_screen()

    def mock_backend(region=None):
        if region:
            x, y, w, h = region
            cropped = synth_img.crop((x, y, x + w, y + h))
            return ScreenImage(cropped, region=BBox(x, y, w, h))
        return ScreenImage(synth_img, region=BBox(0, 0, synth_img.width, synth_img.height))

    app.vision.engine.set_capture_backend(mock_backend)
    return app


def test_vision_plugin_registration(mock_vision_app):
    app = mock_vision_app
    assert app.vision is not None
    assert isinstance(app.vision, VisionPlugin)
    assert app.screenmind is app.vision


def test_permission_gate_raises_permission_denied(mock_vision_app):
    app = mock_vision_app

    # Zero permissions granted by default
    with pytest.raises(PermissionDenied, match="vision.screenshot"):
        app.vision.screenshot()

    dummy_img = ScreenImage(_create_synthetic_screen())

    with pytest.raises(PermissionDenied, match="vision.find"):
        app.vision.find(dummy_img, dummy_img)

    with pytest.raises(PermissionDenied, match="vision.ocr"):
        app.vision.find_text("test", dummy_img)

    with pytest.raises(PermissionDenied, match="vision.locate"):
        app.vision.locate("red", dummy_img)


def test_permission_grant_and_revoke(mock_vision_app):
    app = mock_vision_app

    # Explicit grant
    app.permissions.grant("vision.screenshot")
    img = app.vision.screenshot()
    assert isinstance(img, ScreenImage)
    assert img.width == 200
    assert img.height == 150

    # Revoke
    app.permissions.revoke("vision.screenshot")
    with pytest.raises(PermissionDenied, match="vision.screenshot"):
        app.vision.screenshot()

    # Grant all helper
    app.vision.grant_all()
    img2 = app.vision.screenshot()
    assert img2 is not None

    # Revoke all helper
    app.vision.revoke_all()
    with pytest.raises(PermissionDenied, match="vision.screenshot"):
        app.vision.screenshot()


def test_template_finding_success(mock_vision_app):
    app = mock_vision_app
    app.vision.grant_all()

    # Blue template matching the rectangle drawn at (40, 50, w=30, h=20)
    blue_template = Image.new("RGB", (30, 20), color=(0, 100, 255))

    match = app.vision.find(blue_template)
    assert match is not None
    assert isinstance(match, MatchResult)
    assert match.bbox.x == 40
    assert match.bbox.y == 50
    assert match.bbox.width == 30
    assert match.bbox.height == 20
    assert match.confidence >= 0.95


def test_template_finding_no_match(mock_vision_app):
    app = mock_vision_app
    app.vision.grant_all()

    # Purple template that does not exist
    purple_template = Image.new("RGB", (25, 25), color=(180, 0, 180))

    match = app.vision.find(purple_template, threshold=0.9)
    assert match is None


def test_text_finding_and_registration(mock_vision_app):
    app = mock_vision_app
    app.vision.grant_all()

    app.vision.engine.register_text_region("Submit Button", BBox(10, 10, 60, 25))
    app.vision.engine.register_text_region("Cancel", BBox(80, 10, 50, 25))

    matches = app.vision.find_text("Submit")
    assert len(matches) == 1
    assert matches[0].bbox.x == 10
    assert matches[0].bbox.y == 10
    assert matches[0].label == "Submit Button"

    matches_cancel = app.vision.find_text("Cancel")
    assert len(matches_cancel) == 1
    assert matches_cancel[0].bbox.x == 80


def test_locate_colored_regions(mock_vision_app):
    app = mock_vision_app
    app.vision.grant_all()

    # Locate the red rectangle drawn at (120, 80)
    matches = app.vision.locate("red")
    assert len(matches) >= 1
    # Match should be in the red rectangle area
    red_match = any(115 <= m.bbox.x <= 140 and 75 <= m.bbox.y <= 100 for m in matches)
    assert red_match is True


def test_events_emitted_on_actions(mock_vision_app):
    app = mock_vision_app
    app.vision.grant_all()

    events = []
    app.bus.on("vision.*", lambda ev: events.append(ev))

    app.vision.screenshot()
    blue_template = Image.new("RGB", (30, 20), color=(0, 100, 255))
    app.vision.find(blue_template)

    event_types = [e.type for e in events]
    assert "vision.screenshot.captured" in event_types
    assert "vision.pattern.found" in event_types


def test_click_and_type_strictly_out_of_scope(mock_vision_app):
    app = mock_vision_app
    # Hard rule: click() and type() must NOT be implemented
    assert not hasattr(app.vision, "click")
    assert not hasattr(app.vision, "type")
    assert not hasattr(app.vision.engine, "click")
    assert not hasattr(app.vision.engine, "type")


def test_no_network_calls_during_vision(mock_vision_app, monkeypatch):
    app = mock_vision_app
    app.vision.grant_all()

    def forbidden_socket(*args, **kwargs):
        raise RuntimeError("Network calls are forbidden in Vision module!")

    monkeypatch.setattr(socket, "socket", forbidden_socket)

    img = app.vision.screenshot()
    assert img is not None
    blue_template = Image.new("RGB", (30, 20), color=(0, 100, 255))
    match = app.vision.find(blue_template)
    assert match is not None


def test_coexistence_with_other_modules():
    app = App(features=["vision", "memory", "timeline", "shadow"])
    assert app.vision is not None
    assert app.recall is not None
    assert app.timeloop is not None
    assert app.shadow is not None
    app.run()
