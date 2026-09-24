"""Tests for AgentBox (sandboxed autonomous agent execution) module."""

import time
import pytest
from nexora import App
from nexora.agentbox import (
    AgentBox,
    AgentBoxEngine,
    AgentBoxPlugin,
    AgentExecutionLimits,
    AgentPolicy,
    AgentResult,
    AgentTimeoutError,
    ConfirmationDenied,
    DisallowedToolError,
    ExecutionLimitExceeded,
    Sandbox,
    ToolCallRecord,
)
from nexora.security import PermissionDenied


def test_agentbox_plugin_registration():
    app = App(features=["agentbox"])
    assert app.agentbox is not None
    assert isinstance(app.agentbox, AgentBoxPlugin)
    assert app.agentbox.engine is not None
    app.run()


def test_allowed_tool_runs_successfully():
    app = App(features=["agentbox"])
    app.agentbox.register_tool("add", lambda a, b: a + b, allow_by_default=True)
    app.permissions.grant("agentbox.tool.add")

    res = app.agentbox.execute_tool("add", a=10, b=25)
    assert res == 35

    trail = app.agentbox.audit_trail()
    assert len(trail) == 1
    assert trail[0].tool_name == "add"
    assert trail[0].status == "success"
    assert trail[0].result == 35


def test_disallowed_tool_call_is_blocked():
    app = App(features=["agentbox"])
    app.agentbox.register_tool("dangerous_rm", lambda path: f"removed {path}")
    # Tool registered, but NOT in allowlist

    with pytest.raises(DisallowedToolError, match="not in the allowed tool list"):
        app.agentbox.execute_tool("dangerous_rm", path="/etc/hosts")

    trail = app.agentbox.audit_trail()
    assert len(trail) == 1
    assert trail[0].tool_name == "dangerous_rm"
    assert trail[0].status == "blocked"


def test_permission_gate_enforcement():
    app = App(features=["agentbox"])
    app.agentbox.register_tool("write_file", lambda f, data: True, allow_by_default=True)
    # Allowed in tool list, but permission not granted in PermissionManager

    with pytest.raises(PermissionDenied, match="agentbox.tool.write_file"):
        app.agentbox.execute_tool("write_file", f="test.txt", data="secret")

    trail = app.agentbox.audit_trail()
    assert len(trail) == 1
    assert trail[0].status == "blocked"


def test_dangerous_tool_confirmation_denial():
    app = App(features=["agentbox"])
    app.agentbox.register_tool("wipe_disk", lambda: "wiped", dangerous=True, allow_by_default=True)
    app.permissions.grant("agentbox.tool.wipe_disk")

    # Handler denies confirmation
    app.agentbox.set_confirmation_handler(lambda name, args: False)

    with pytest.raises(ConfirmationDenied, match="Confirmation denied"):
        app.agentbox.execute_tool("wipe_disk")

    trail = app.agentbox.audit_trail()
    assert len(trail) == 1
    assert trail[0].status == "denied"


def test_dangerous_tool_confirmation_approval():
    app = App(features=["agentbox"])
    app.agentbox.register_tool("wipe_disk", lambda: "wiped", dangerous=True, allow_by_default=True)
    app.permissions.grant("agentbox.tool.wipe_disk")

    # Handler approves confirmation
    app.agentbox.set_confirmation_handler(lambda name, args: True)

    res = app.agentbox.execute_tool("wipe_disk")
    assert res == "wiped"

    trail = app.agentbox.audit_trail()
    assert len(trail) == 1
    assert trail[0].status == "success"


def test_tool_call_limit_enforced():
    app = App(features=["agentbox"])
    app.agentbox.register_tool("ping", lambda: "pong", allow_by_default=True)
    app.permissions.grant("agentbox.tool.ping")

    limits = AgentExecutionLimits(max_tool_calls=2)
    sb = app.agentbox.create_sandbox(allowed_tools={"ping"}, limits=limits)

    assert sb.execute_tool("ping") == "pong"
    assert sb.execute_tool("ping") == "pong"

    with pytest.raises(ExecutionLimitExceeded, match="Exceeded maximum tool call quota"):
        sb.execute_tool("ping")


def test_step_limit_enforced():
    limits = AgentExecutionLimits(max_steps=2)
    sb = Sandbox(limits=limits)

    sb.step()
    sb.step()
    with pytest.raises(ExecutionLimitExceeded, match="maximum step limit"):
        sb.step()


def test_execution_timeout_enforced():
    app = App(features=["agentbox"])

    def slow_tool():
        time.sleep(0.3)
        return "finished"

    app.agentbox.register_tool("slow_tool", slow_tool, allow_by_default=True)
    app.permissions.grant("agentbox.tool.slow_tool")

    limits = AgentExecutionLimits(timeout_seconds=0.05)
    sb = app.agentbox.create_sandbox(allowed_tools={"slow_tool"}, limits=limits)

    with pytest.raises(AgentTimeoutError, match="timed out"):
        sb.execute_tool("slow_tool")

    trail = sb.audit_trail
    assert len(trail) == 1
    assert trail[0].status == "timeout"


def test_complete_audit_trail_tracking():
    app = App(features=["agentbox"])
    app.agentbox.register_tool("tool_a", lambda: "ok_a", allow_by_default=True)
    app.agentbox.register_tool("tool_b", lambda: "ok_b")  # Not allowed
    app.permissions.grant("agentbox.tool.tool_a")

    # Call 1: Success
    app.agentbox.execute_tool("tool_a")

    # Call 2: Blocked
    with pytest.raises(DisallowedToolError):
        app.agentbox.execute_tool("tool_b")

    trail = app.agentbox.audit_trail()
    assert len(trail) == 2
    assert trail[0].tool_name == "tool_a"
    assert trail[0].status == "success"
    assert trail[1].tool_name == "tool_b"
    assert trail[1].status == "blocked"


def test_autonomous_agent_runner():
    app = App(features=["agentbox"])
    app.agentbox.register_tool("fetch", lambda key: f"value_{key}", allow_by_default=True)
    app.permissions.grant("agentbox.tool.fetch")

    def agent_logic(sb: Sandbox) -> str:
        sb.step()
        val = sb.execute_tool("fetch", key="alpha")
        sb.step()
        return f"Agent output with {val}"

    result = app.agentbox.run_agent(agent_logic, allowed_tools={"fetch"}, agent_id="agent_007")
    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.agent_id == "agent_007"
    assert result.steps_taken == 2
    assert "value_alpha" in result.final_output
    assert len(result.tool_calls) == 1


def test_event_bus_emissions():
    app = App(features=["agentbox"])
    events = []
    app.bus.on("agentbox.*", lambda ev: events.append(ev.type))

    app.agentbox.register_tool("greet", lambda name: f"Hi {name}", allow_by_default=True)
    app.permissions.grant("agentbox.tool.greet")

    app.agentbox.execute_tool("greet", name="Dev")

    assert "agentbox.tool.executed" in events


def test_coexistence_with_all_prior_modules():
    app = App(
        features=[
            "ghost",
            "world",
            "adaptive",
            "memory",
            "timeline",
            "shadow",
            "vision",
            "worldforge",
            "agentbox",
        ]
    )
    assert app.ghost is not None
    assert app.world is not None
    assert app.adaptive is not None
    assert app.recall is not None
    assert app.timeloop is not None
    assert app.shadow is not None
    assert app.vision is not None
    assert app.worldforge is not None
    assert app.agentbox is not None

    app.run()
