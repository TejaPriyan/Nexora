"""Data structures and policy models for AgentBox sandboxed execution."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set


class AgentBoxError(Exception):
    """Base exception for all AgentBox operations."""


class DisallowedToolError(AgentBoxError):
    """Raised when an agent attempts to execute a tool not in the allowlist."""


class ExecutionLimitExceeded(AgentBoxError):
    """Raised when an agent exceeds execution steps or tool call quotas."""


class AgentTimeoutError(AgentBoxError):
    """Raised when an agent tool or step execution times out."""


class ConfirmationDenied(AgentBoxError):
    """Raised when a dangerous action is rejected by confirmation prompt/handler."""


@dataclass
class ToolDefinition:
    """Registered tool available for agent execution."""

    name: str
    func: Callable[..., Any]
    description: str = ""
    dangerous: bool = False
    permission_scope: Optional[str] = None


@dataclass
class ToolCallRecord:
    """Audit record for a tool call attempt."""

    call_id: str = field(default_factory=lambda: f"call_{uuid.uuid4().hex[:8]}")
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"  # "success", "blocked", "confirmed", "denied", "error", "timeout"
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "arguments": dict(self.arguments),
            "timestamp": self.timestamp,
            "status": self.status,
            "result": str(self.result) if self.result is not None else None,
            "error": self.error,
            "duration": self.duration,
        }


@dataclass
class AgentExecutionLimits:
    """Resource constraints for an agent execution session."""

    max_steps: int = 50
    max_tool_calls: int = 100
    timeout_seconds: float = 10.0


@dataclass
class AgentPolicy:
    """Permission and capability configuration for sandboxed execution."""

    allowed_tools: Set[str] = field(default_factory=set)
    dangerous_tools: Set[str] = field(default_factory=set)
    auto_confirm_dangerous: bool = False
    require_permissions: bool = True


@dataclass
class AgentResult:
    """Outcome of a sandboxed agent execution run."""

    agent_id: str
    success: bool
    steps_taken: int
    tool_calls: List[ToolCallRecord]
    final_output: Any = None
    error: Optional[str] = None
