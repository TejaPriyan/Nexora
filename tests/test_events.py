from nexora import EventBus


def test_emit_and_history():
    bus = EventBus()
    received = []
    bus.on("task.started", received.append)
    event = bus.emit("task.started", source="t", payload={"a": 1})
    assert received == [event]
    assert event.type == "task.started"
    assert event.payload == {"a": 1}
    assert bus.history("task.started") == [event]


def test_wildcard_subscription():
    bus = EventBus()
    received = []
    bus.on("task.*", received.append)
    bus.emit("task.started", source="t")
    bus.emit("task.completed", source="t")
    bus.emit("other.event", source="t")
    assert len(received) == 2


def test_global_wildcard():
    bus = EventBus()
    received = []
    bus.on("*", received.append)
    bus.emit("anything.here", source="t")
    assert len(received) == 1


def test_off_removes_handler():
    bus = EventBus()
    received = []
    handler = bus.on("x", received.append)
    bus.off("x", handler)
    bus.emit("x", source="t")
    assert received == []


def test_decorator_style_subscription():
    bus = EventBus()
    received = []

    @bus.on("greeting")
    def handle(event):
        received.append(event)

    bus.emit("greeting", source="demo", payload={"msg": "hi"})
    assert len(received) == 1
    assert received[0].payload == {"msg": "hi"}


def test_history_limit_is_enforced():
    bus = EventBus(history_limit=3)
    for i in range(10):
        bus.emit("tick", source="t", payload={"i": i})
    assert len(bus.history()) == 3
    assert [e.payload["i"] for e in bus.history()] == [7, 8, 9]
