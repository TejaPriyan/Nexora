"""Example 3: Combined GhostUI + CodeWorld (Multi-Agent AI Collaboration).

Demonstrates:
- Autonomous AI agent pipeline
- GhostUI rendering progress, logs, metrics, and summary tables
- CodeWorld tracking the agents and drawing their relationships live
"""

from nexora import App

# 1. Initialize with BOTH 'ghost' and 'world'
app = App(features=["ghost", "world"])


@app.task
def initialize_ai_swarm():
    app.ghost.log("Spawning Autonomous Agent Swarm...", level="INFO")

    # Create agent entities in CodeWorld
    app.world.create("agent", entity_id="agent:planner", x=0, y=-100, color="#4cc9f0", properties={"role": "Lead Planner"})
    app.world.create("agent", entity_id="agent:coder", x=-100, y=50, color="#f72585", properties={"role": "Code Generator"})
    app.world.create("agent", entity_id="agent:reviewer", x=100, y=50, color="#7209b7", properties={"role": "Security Reviewer"})

    # Connect them with collaborative relationships
    app.world.relate("agent:planner", "assigns_task", "agent:coder")
    app.world.relate("agent:coder", "submits_pr", "agent:reviewer")

    app.ghost.log("Agent Swarm initialized and connected in 2D mesh.", level="INFO")


@app.task
def execute_coding_phase():
    app.ghost.log("Planner assigned 'Auth Service Refactor' to Coder Agent", level="INFO")

    for i in range(1, 5):
        app.ghost.progress("code_generation", i * 25, 100, unit="%")
        app.ghost.metric("tokens_generated", i * 850, unit="tokens")
        app.ghost.metric("generation_speed", 78.4, unit="tok/s")

    app.world.set_prop("agent:coder", "status", "pr_created")
    app.ghost.log("Pull Request #42 opened by Coder Agent", level="INFO")


@app.task
def execute_review_phase():
    app.ghost.log("Security Reviewer analyzing AST and vulnerability patterns...", level="INFO")

    app.ghost.metric("vulnerabilities_found", 0, unit="issues")
    app.ghost.metric("test_coverage", 94.6, unit="%")

    app.world.set_prop("agent:reviewer", "status", "approved")
    app.world.move_by("agent:reviewer", dx=10, dy=-10)

    # Output executive audit table
    app.ghost.table(
        title="Agent Swarm Audit Summary",
        columns=["Agent ID", "Role", "Status", "Review Verdict"],
        rows=[
            ["agent:planner", "Lead Planner", "Idle", "Task Distributed"],
            ["agent:coder", "Code Generator", "Complete", "Code Built & Tested"],
            ["agent:reviewer", "Security Reviewer", "Approved", "Passed Security Gate"],
        ],
    )


if __name__ == "__main__":
    app.run()
