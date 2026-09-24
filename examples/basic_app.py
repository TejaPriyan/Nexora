"""A minimal, fully working NEXORA app using only core functionality
(no optional feature modules required).

Run with:
    python examples/basic_app.py
"""

from nexora import App

app = App()


@app.task
def load():
    print("Loading data...")


@app.task
def process():
    print("Processing data...")


@app.bus.on("task.completed")
def _on_task_completed(event):
    print(f"  -> {event.payload['task']} finished in {event.payload['duration_seconds']:.6f}s")


if __name__ == "__main__":
    app.run()
