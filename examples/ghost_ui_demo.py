"""Demonstrates GhostUI (Milestone 1) in action:
Tasks, progress bars, logs, metrics, tables, and summary dashboard
automatically rendered via rich purely from App/EventBus activity.

Run with:
    python examples/ghost_ui_demo.py
"""

import time
from nexora import App


def main() -> None:
    app = App(features=["ghost"])

    @app.task
    def load_dataset():
        app.ghost.log("Connecting to data source...", level="INFO")
        time.sleep(0.05)
        for i in range(1, 4):
            app.ghost.progress("loading_records", completed=i * 250, total=1000, unit="rows")
            time.sleep(0.02)
        app.ghost.log("Dataset loaded: 1,000 records ready", level="INFO")

    @app.task
    def train_model():
        app.ghost.log("Initializing model parameters...", level="INFO")
        app.ghost.metric("learning_rate", 0.001)
        for epoch in range(1, 4):
            time.sleep(0.03)
            acc = 0.85 + (epoch * 0.04)
            loss = 0.45 - (epoch * 0.1)
            app.ghost.metric("accuracy", round(acc, 4), unit="score")
            app.ghost.metric("loss", round(loss, 4))
            app.ghost.progress("epoch_progress", completed=epoch, total=3, unit="epochs")
            app.ghost.log(f"Epoch {epoch}/3 complete - accuracy: {acc:.2%}", level="INFO")

    @app.task
    def generate_report():
        app.ghost.table(
            title="Evaluation Results",
            columns=["Model", "Accuracy", "F1 Score", "Status"],
            rows=[
                ["Nexora-Small", "89.2%", "0.88", "Benchmarked"],
                ["Nexora-Base", "93.4%", "0.92", "Selected"],
                ["Nexora-Large", "94.1%", "0.93", "Candidate"],
            ],
        )

    app.run()


if __name__ == "__main__":
    main()
