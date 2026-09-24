"""Example 1: GhostUI ONLY (No CodeWorld needed).

Demonstrates:
- Live terminal dashboards
- Multiple progress bars
- Real-time metrics tracking
- Color-coded logs
- Rich formatted data tables
- Automatic summary report
"""

from nexora import App

# 1. Initialize with ONLY the 'ghost' feature
app = App(features=["ghost"])


@app.task
def prepare_environment():
    app.ghost.log("Initializing AI training environment...", level="INFO")
    app.ghost.log("CUDA device detected: GPU 0 (NVIDIA RTX 4090)", level="INFO")
    app.ghost.metric("gpu_memory_used_mb", 1024, unit="MB")


@app.task
def download_data():
    app.ghost.log("Streaming dataset from cloud storage...", level="INFO")
    # Simulate downloading batches
    for percent in [25, 50, 75, 100]:
        app.ghost.progress("dataset_download", percent, 100, unit="%")


@app.task
def train_model():
    app.ghost.log("Starting model fine-tuning...", level="INFO")
    for epoch in range(1, 4):
        # Update metrics dynamically
        app.ghost.metric("learning_rate", 0.0003)
        app.ghost.metric("loss", 0.45 - (epoch * 0.12))
        app.ghost.metric("accuracy", 0.82 + (epoch * 0.05), unit="score")
        app.ghost.progress("training_epochs", epoch, 3, unit="epochs")
        app.ghost.log(f"Epoch {epoch}/3 completed successfully", level="INFO")


@app.task
def generate_benchmark_table():
    # Render a structured table comparing models
    app.ghost.table(
        title="Model Benchmark Results",
        columns=["Model Architecture", "Accuracy", "Latency (ms)", "Status"],
        rows=[
            ["Nexora-Small-7B", "87.4%", "14.2 ms", "Passed"],
            ["Nexora-Medium-13B", "92.1%", "28.6 ms", "Passed"],
            ["Nexora-Large-70B", "96.8%", "82.1 ms", "Candidate (Optimal)"],
        ],
    )


if __name__ == "__main__":
    app.run()
