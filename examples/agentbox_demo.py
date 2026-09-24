"""Demonstration of AgentBox (sandboxed autonomous agent execution) in NEXORA."""

from nexora import App
from nexora.agentbox import ConfirmationDenied, DisallowedToolError, Sandbox


def main() -> None:
    app = App(features=["agentbox"])
    agentbox = app.agentbox
    assert agentbox is not None

    print("=== NEXORA AgentBox Sandboxed Agent Execution Demo ===")

    # 1. Register tools
    agentbox.register_tool(
        "search_docs",
        lambda query: f"Docs result for: {query}",
        description="Search internal documentation",
        allow_by_default=True,
    )
    agentbox.register_tool(
        "deploy_service",
        lambda env: f"Deployed service to {env}",
        description="Deploy software to cluster",
        dangerous=True,
        allow_by_default=True,
    )
    agentbox.register_tool(
        "format_disk",
        lambda: "Drive formatted",
        description="Low level disk formatting",
        dangerous=True,
        allow_by_default=False,  # Disallowed
    )

    # 2. Grant permissions
    app.permissions.grant("agentbox.tool.search_docs")
    app.permissions.grant("agentbox.tool.deploy_service")

    # 3. Setup confirmation prompt
    def confirm_action(tool_name: str, args: dict) -> bool:
        print(f"\n[CONFIRMATION PROMPT] Agent requested dangerous action: {tool_name}({args})")
        # In a real CLI, we prompt the user. Here we simulate approving 'staging' and rejecting 'prod'
        target_env = args.get("env")
        if target_env == "production":
            print(" -> User DENIED execution on production!")
            return False
        print(" -> User APPROVED execution on staging.")
        return True

    agentbox.set_confirmation_handler(confirm_action)

    # 4. Safe tool execution
    print("\n1. Executing safe tool...")
    res = agentbox.execute_tool("search_docs", query="API setup")
    print(" - Tool output:", res)

    # 5. Blocked disallowed tool
    print("\n2. Executing disallowed tool (format_disk)...")
    try:
        agentbox.execute_tool("format_disk")
    except DisallowedToolError as err:
        print(" - Successfully blocked disallowed tool:")
        print("  ", err)

    # 6. Dangerous tool with confirmation approved
    print("\n3. Executing dangerous tool on staging...")
    res_deploy = agentbox.execute_tool("deploy_service", env="staging")
    print(" - Tool output:", res_deploy)

    # 7. Dangerous tool with confirmation rejected
    print("\n4. Executing dangerous tool on production...")
    try:
        agentbox.execute_tool("deploy_service", env="production")
    except ConfirmationDenied as err:
        print(" - Successfully blocked dangerous tool on rejection:")
        print("  ", err)

    # 8. Run an autonomous agent loop
    print("\n5. Running autonomous agent...")
    def autonomous_worker(sb: Sandbox) -> str:
        sb.step()
        doc = sb.execute_tool("search_docs", query="deployment guide")
        sb.step()
        return f"Worker completed workflow using: {doc}"

    agent_result = agentbox.run_agent(autonomous_worker, allowed_tools={"search_docs"}, agent_id="worker_42")
    print(f" - Agent Success: {agent_result.success}")
    print(f" - Steps Taken: {agent_result.steps_taken}")
    print(f" - Final Output: {agent_result.final_output}")

    # 9. Audit Trail
    print("\n6. Inspecting Sandbox Audit Trail...")
    for rec in agentbox.audit_trail():
        print(f" - [{rec.status.upper()}] {rec.tool_name}({rec.arguments}) in {rec.duration * 1000:.2f}ms")

    print("\nAgentBox sandboxed execution demo completed successfully!")


if __name__ == "__main__":
    main()
