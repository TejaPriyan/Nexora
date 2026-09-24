"""AgentBox plugin for NEXORA: sandboxed autonomous agent execution."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional, Set

from ..plugins.base import Plugin
from .engine import AgentBoxEngine
from .models import (
    AgentExecutionLimits,
    AgentPolicy,
    AgentResult,
    ConfirmationDenied,
    DisallowedToolError,
    ExecutionLimitExceeded,
    ToolCallRecord,
    ToolDefinition,
)
from .sandbox import Sandbox

if TYPE_CHECKING:
    from ..app import App


class AgentBoxPlugin(Plugin):
    """AgentBox: sandboxed execution boundary for autonomous agents.

    Provides strict tool allowlists, permission enforcement via PermissionManager,
    resource limits, execution timeouts, full audit trails, and confirmation
    prompts for dangerous actions.

    NOTE: The sandbox does not claim to be mathematically impenetrable against
    low-level OS escapes; its limitations are clearly documented in docs/ARCHITECTURE.md.
    """

    name: ClassVar[str] = "agentbox"
    requires_extra: ClassVar[Optional[str]] = None
    milestone: ClassVar[str] = "M9"

    def __init__(
        self,
        app: "App",
        *,
        engine: Optional[AgentBoxEngine] = None,
    ) -> None:
        super().__init__(app)
        self.engine = engine or AgentBoxEngine(permissions=app.permissions)
        self._default_sandbox = self.engine.create_sandbox()
        self._started = False

    # --- Lifecycle ---

    def on_register(self) -> None:
        pass

    def on_start(self) -> None:
        self._started = True

    def on_stop(self) -> None:
        self._started = False

    # --- Tool & Sandbox Management ---

    def register_tool(
        self,
        name: str,
        func: Callable[..., Any],
        *,
        description: str = "",
        dangerous: bool = False,
        permission_scope: Optional[str] = None,
        allow_by_default: bool = False,
    ) -> ToolDefinition:
        """Register a tool available for agent execution."""
        t = self.engine.register_tool(
            name=name,
            func=func,
            description=description,
            dangerous=dangerous,
            permission_scope=permission_scope,
            allow_by_default=allow_by_default,
        )
        if allow_by_default:
            self._default_sandbox.allow_tool(name)
        return t

    def allow_tool(self, name: str) -> None:
        """Add a tool to the default sandbox allowlist."""
        self._default_sandbox.allow_tool(name)

    def disallow_tool(self, name: str) -> None:
        """Remove a tool from the default sandbox allowlist."""
        self._default_sandbox.disallow_tool(name)

    def set_confirmation_handler(
        self,
        handler: Optional[Callable[[str, Dict[str, Any]], bool]],
    ) -> None:
        """Register a confirmation handler prompt for dangerous tool actions."""
        self.engine.set_confirmation_handler(handler)
        self._default_sandbox.confirmation_handler = handler

    def create_sandbox(
        self,
        *,
        allowed_tools: Optional[Set[str]] = None,
        dangerous_tools: Optional[Set[str]] = None,
        limits: Optional[AgentExecutionLimits] = None,
        confirmation_handler: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        auto_confirm_dangerous: bool = False,
    ) -> Sandbox:
        """Create a dedicated isolated sandbox instance."""
        return self.engine.create_sandbox(
            allowed_tools=allowed_tools,
            dangerous_tools=dangerous_tools,
            limits=limits,
            confirmation_handler=confirmation_handler,
            auto_confirm_dangerous=auto_confirm_dangerous,
        )

    # --- Execution ---

    def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a tool through the default sandbox boundary."""
        try:
            res = self._default_sandbox.execute_tool(tool_name, **kwargs)
            self.app.bus.emit(
                "agentbox.tool.executed",
                source="agentbox",
                payload={"tool": tool_name, "status": "success"},
            )
            return res
        except DisallowedToolError as exc:
            self.app.bus.emit(
                "agentbox.tool.blocked",
                source="agentbox",
                payload={"tool": tool_name, "reason": str(exc)},
            )
            raise
        except ConfirmationDenied as exc:
            self.app.bus.emit(
                "agentbox.confirmation.denied",
                source="agentbox",
                payload={"tool": tool_name, "reason": str(exc)},
            )
            raise

    def run_agent(
        self,
        agent_func: Callable[[Sandbox], Any],
        *,
        limits: Optional[AgentExecutionLimits] = None,
        allowed_tools: Optional[Set[str]] = None,
        agent_id: str = "agent_default",
    ) -> AgentResult:
        """Execute an autonomous agent function in a controlled sandbox."""
        self.app.bus.emit("agentbox.agent.started", source="agentbox", payload={"agent_id": agent_id})
        sb = self.create_sandbox(allowed_tools=allowed_tools, limits=limits)
        res = sb.run(agent_func, agent_id=agent_id)
        self.app.bus.emit(
            "agentbox.agent.completed",
            source="agentbox",
            payload={"agent_id": agent_id, "success": res.success, "steps": res.steps_taken},
        )
        return res

    def audit_trail(self) -> List[ToolCallRecord]:
        """Return the complete audit trail of tool invocations."""
        return self.engine.audit_trail()


# Alias
AgentBox = AgentBoxPlugin
