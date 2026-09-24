"""AgentBox (sandboxed agent execution) module for NEXORA.

Safely executes autonomous agents inside controlled environments:
permission policies, tool allowlists, execution limits, timeouts, logs,
an audit trail, and confirmation prompts for dangerous actions.
Built on nexora.security.PermissionManager.
"""

from .engine import AgentBoxEngine
from .models import (
    AgentBoxError,
    AgentExecutionLimits,
    AgentPolicy,
    AgentResult,
    AgentTimeoutError,
    ConfirmationDenied,
    DisallowedToolError,
    ExecutionLimitExceeded,
    ToolCallRecord,
    ToolDefinition,
)
from .plugin import AgentBox, AgentBoxPlugin
from .sandbox import Sandbox

STATUS = "implemented"

__all__ = [
    "STATUS",
    "AgentBoxPlugin",
    "AgentBox",
    "AgentBoxEngine",
    "Sandbox",
    "AgentPolicy",
    "AgentExecutionLimits",
    "AgentResult",
    "ToolDefinition",
    "ToolCallRecord",
    "AgentBoxError",
    "DisallowedToolError",
    "ExecutionLimitExceeded",
    "AgentTimeoutError",
    "ConfirmationDenied",
]
