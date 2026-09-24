"""Shows what happens if you ask for a planned future plugin.
NEXORA raises a clear, honest error instead of pretending the feature works.

Run with:
    python examples/unbuilt_feature_demo.py
"""

from nexora import App
from nexora.plugins.registry import _REGISTRY, _planned

# Register a planned placeholder for demonstration
_REGISTRY["future_quantum"] = _planned("future_quantum", "quantum", "Distributed quantum mesh")

try:
    app = App(features=["future_quantum"])
    app.run()
except NotImplementedError as exc:
    print("Expected, honest failure instead of fake functionality:\n")
    print(exc)
