from nexora import App

# Start an app with both GhostUI and CodeWorld enabled
app = App(features=["ghost", "world"])

@app.task
def step_one():
    app.ghost.log("Connecting to core network...", level="INFO")
    # Add visual entities to the 2D world
    app.world.create("server", entity_id="server-1", x=0, y=0)
    app.world.create("database", entity_id="db-1", x=150, y=0)
    app.world.relate("server-1", "queries", "db-1")
    app.ghost.log("Connected server-1 to db-1", level="INFO")

@app.task
def step_two():
    app.ghost.metric("cpu_usage", 42.5, unit="%")
    app.ghost.metric("memory_mb", 512, unit="MB")
    app.ghost.progress("data_sync", 100, 100, unit="MB")
    app.ghost.log("Data sync complete!", level="INFO")

if __name__ == "__main__":
    app.run()
