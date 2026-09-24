"""Sandbox execution environment for autonomous agents."""

from __future__ import annotations

import concurrent.futures
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set

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

if TYPE_CHECKING:
    from ..security.permissions import PermissionManager


class Sandbox:
    """Sandboxed execution boundary for an autonomous agent."""

    def __init__(
        self,
        *,
        tools: Optional[Dict[str, ToolDefinition]] = None,
        policy: Optional[AgentPolicy] = None,
        limits: Optional[AgentExecutionLimits] = None,
        permissions: Optional[PermissionManager] = None,
        confirmation_handler: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._tools = tools if tools is not None else {}
        self.policy = policy or AgentPolicy()
        self.limits = limits or AgentExecutionLimits()
        self.permissions = permissions
        self.confirmation_handler = confirmation_handler
        self._audit_trail: List[ToolCallRecord] = []
        self._call_count = 0
        self._step_count = 0

    @property
    def audit_trail(self) -> List[ToolCallRecord]:
        with self._lock:
            return list(self._audit_trail)

    def register_tool(
        self,
        name: str,
        func: Callable[..., Any],
        *,
        description: str = "",
        dangerous: bool = False,
        permission_scope: Optional[str] = None,
    ) -> None:
        """Register a callable tool into the sandbox."""
        with self._lock:
            self._tools[name] = ToolDefinition(
                name=name,
                func=func,
                description=description,
                dangerous=dangerous,
                permission_scope=permission_scope,
            )

    def allow_tool(self, name: str) -> None:
        with self._lock:
            self.policy.allowed_tools.add(name)

    def disallow_tool(self, name: str) -> None:
        with self._lock:
            self.policy.allowed_tools.discard(name)

    def is_tool_allowed(self, name: str) -> bool:
        with self._lock:
            return name in self._tools and name in self.policy.allowed_tools

    def step(self) -> None:
        """Increment agent step count and assert within limits."""
        with self._lock:
            self._step_count += 1
            if self._step_count > self.limits.max_steps:
                raise ExecutionLimitExceeded(
                    f"Agent exceeded maximum step limit ({self.limits.max_steps})"
                )

    def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a tool with full policy, permission, timeout, and audit checking."""
        record = ToolCallRecord(tool_name=tool_name, arguments=kwargs)
        start_t = time.perf_counter()

        with self._lock:
            self._call_count += 1
            if self._call_count > self.limits.max_tool_calls:
                record.status = "error"
                record.error = f"Exceeded maximum tool call quota ({self.limits.max_tool_calls})"
                record.duration = time.perf_counter() - start_t
                self._audit_trail.append(record)
                raise ExecutionLimitExceeded(record.error)

            # 1. Tool registration & Allowlist check
            if tool_name not in self._tools or tool_name not in self.policy.allowed_tools:
                record.status = "blocked"
                record.error = f"Tool {tool_name!r} is not in the allowed tool list"
                record.duration = time.perf_counter() - start_t
                self._audit_trail.append(record)
                raise DisallowedToolError(record.error)

            tool = self._tools[tool_name]

            # 2. Permission check
            if self.policy.require_permissions and self.permissions is not None:
                scope = tool.permission_scope or f"agentbox.tool.{tool_name}"
                try:
                    self.permissions.require(scope)
                except Exception as exc:
                    record.status = "blocked"
                    record.error = str(exc)
                    record.duration = time.perf_counter() - start_t
                    self._audit_trail.append(record)
                    raise

            # 3. Confirmation for dangerous actions
            is_dangerous = tool.dangerous or (tool_name in self.policy.dangerous_tools)
            if is_dangerous and not self.policy.auto_confirm_dangerous:
                if self.confirmation_handler is None:
                    record.status = "denied"
                    record.error = f"Tool {tool_name!r} is marked dangerous but no confirmation handler is registered"
                    record.duration = time.perf_counter() - start_t
                    self._audit_trail.append(record)
                    raise ConfirmationDenied(record.error)

                confirmed = self.confirmation_handler(tool_name, kwargs)
                if not confirmed:
                    record.status = "denied"
                    record.error = f"Confirmation denied for dangerous tool {tool_name!r}"
                    record.duration = time.perf_counter() - start_t
                    self._audit_trail.append(record)
                    raise ConfirmationDenied(record.error)

        # 4. Timed execution
        timeout = self.limits.timeout_seconds
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(tool.func, **kwargs)
                result = future.result(timeout=timeout)

            duration = time.perf_counter() - start_t
            with self._lock:
                record.status = "success"
                record.result = result
                record.duration = duration
                self._audit_trail.append(record)
            return result
        except concurrent.futures.TimeoutError:
            duration = time.perf_counter() - start_t
            with self._lock:
                record.status = "timeout"
                record.error = f"Execution timed out after {timeout} seconds"
                record.duration = duration
                self._audit_trail.append(record)
            raise AgentTimeoutError(record.error)
        except Exception as exc:
            duration = time.perf_counter() - start_t
            with self._lock:
                record.status = "error"
                record.error = str(exc)
                record.duration = duration
                self._audit_trail.append(record)
            raise

    def run(
        self,
        agent_func: Callable[[Sandbox], Any],
        *,
        agent_id: str = "agent_default",
    ) -> AgentResult:
        """Run an autonomous agent function inside this sandbox."""
        self._step_count = 0
        self._call_count = 0
        try:
            output = agent_func(self)
            return AgentResult(
                agent_id=agent_id,
                success=True,
                steps_taken=self._step_count,
                tool_calls=self.audit_trail,
                final_output=output,
            )
        except Exception as exc:
            return AgentResult(
                agent_id=agent_id,
                success=False,
                steps_taken=self._step_count,
                tool_calls=self.audit_trail,
                error=str(exc),
            )
