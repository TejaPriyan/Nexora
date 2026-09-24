"""Demonstrates the NEXORA event bus directly, without App.

Run with:
    python examples/events_demo.py
"""

from nexora import EventBus

bus = EventBus()


@bus.on("greeting")
def handle_greeting(event):
    print(f"Got greeting from {event.source}: {event.payload}")


bus.emit("greeting", source="demo", payload={"message": "hello world"})
print("History:", [e.type for e in bus.history()])
