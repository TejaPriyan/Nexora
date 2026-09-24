"""Demonstration of ScreenMind (explicitly-permissioned screen perception) in NEXORA."""

from PIL import Image, ImageDraw
from nexora import App
from nexora.security import PermissionDenied
from nexora.vision import BBox, ScreenImage


def main() -> None:
    app = App(features=["vision"])
    vision = app.vision
    assert vision is not None

    print("=== NEXORA ScreenMind Vision Demo ===")

    # 1. Privacy First: Trying without permission raises PermissionDenied
    print("\n1. Testing default privacy enforcement...")
    try:
        vision.screenshot()
        print("ERROR: Screenshot succeeded without permission!")
    except PermissionDenied as err:
        print(" - Successfully blocked unpermissioned capture:")
        print(f"   {err}")

    # 2. Explicitly granting permissions
    print("\n2. Granting explicit vision permissions...")
    vision.grant_all(reason="Demonstration script explicit user authorization")
    print(" - Permissions granted. Audit trail length:", len(app.permissions.audit_trail()))

    # 3. Inject synthetic screen for demonstration
    demo_screen = Image.new("RGB", (320, 240), color=(245, 245, 245))
    draw = ImageDraw.Draw(demo_screen)
    # Target 1: Green Save button at (50, 60, 80, 30)
    draw.rectangle([50, 60, 130, 90], fill=(46, 204, 113))
    # Target 2: Red Alert box at (180, 120, 60, 40)
    draw.rectangle([180, 120, 240, 160], fill=(231, 76, 60))

    vision.engine.set_capture_backend(lambda reg: ScreenImage(demo_screen))
    vision.engine.register_text_region("Save Document", BBox(50, 60, 80, 30))

    # 4. Capture screenshot
    print("\n3. Capturing permissioned screenshot...")
    img = vision.screenshot()
    print(f" - Captured screen image: {img.width}x{img.height} pixels")

    # 5. Visual Template Search
    print("\n4. Searching for visual template (Save button)...")
    save_button_template = Image.new("RGB", (80, 30), color=(46, 204, 113))
    match = vision.find(save_button_template)
    if match:
        print(f" - Found template at ({match.bbox.x}, {match.bbox.y}) with {match.confidence * 100:.1f}% confidence")

    # 6. Text Search
    print("\n5. Searching for text elements...")
    text_matches = vision.find_text("Save")
    for tm in text_matches:
        print(f" - Found text '{tm.label}' at ({tm.bbox.x}, {tm.bbox.y})")

    # 7. Locate color
    print("\n6. Locating red alert color...")
    color_matches = vision.locate((231, 76, 60), tolerance=10)
    for cm in color_matches:
        print(f" - Located color region at ({cm.bbox.x}, {cm.bbox.y})")

    print("\nScreenMind vision demo completed successfully!")


if __name__ == "__main__":
    main()
