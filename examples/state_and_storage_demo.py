"""Demonstrates the observable State container and the local, offline-only
LocalStore -- the two persistence/state primitives future modules
(Recall/Memory, TimeLoop/Timeline) will build on.

Run with:
    python examples/state_and_storage_demo.py
"""

import tempfile
from pathlib import Path

from nexora import App, LocalStore

app = App()
app.bus.on("state.changed", lambda e: print("state changed:", e.payload))

app.state.set("mode", "dark")
app.state.set("mode", "light")

with tempfile.TemporaryDirectory() as tmp:
    store = LocalStore("demo", base_dir=Path(tmp))
    store.set("preferences", {"mode": app.state.get("mode")})
    print("persisted:", store.get("preferences"))
    store.close()
