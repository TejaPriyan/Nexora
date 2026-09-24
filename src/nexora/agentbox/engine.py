"""AgentBox engine coordinating sandboxed agent environments."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set

from .models import AgentExecutionLimits, AgentPolicy, ToolCallRecord, ToolDefinition
from .sandbox import Sandbox

if TYPE_CHECKING:
    from ..security.permissions import PermissionManager


class AgentBoxEngine:
    """Thread-safe coordinator for agent sandboxing, tool registration, and audit inspection."""

    def __init__(self, *, permissions: Optional[PermissionManager] = None) -> None:
        self._lock = threading.RLock()
        self.permissions = permissions
        self._tools: Dict[str, ToolDefinition] = {}
        self._default_policy = AgentPolicy()
        self._default_limits = AgentExecutionLimits()
        self._sandboxes: List[Sandbox] = []
        self._confirmation_handler: Optional[Callable[[str, Dict[str, Any]], bool]] = None

    def set_confirmation_handler(
        self,
        handler: Optional[Callable[[str, Dict[str, Any]], bool]],
    ) -> None:
        with self._lock:
            self._confirmation_handler = handler

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
        """Register a tool available to sandboxes."""
        with self._lock:
            t = ToolDefinition(
                name=name,
                func=func,
                description=description,
                dangerous=dangerous,
                permission_scope=permission_scope,
            )
            self._tools[name] = t
            if allow_by_default:
                self._default_policy.allowed_tools.add(name)
            if dangerous:
                self._default_policy.dangerous_tools.add(name)
            return t

    def create_sandbox(
        self,
        *,
        allowed_tools: Optional[Set[str]] = None,
        dangerous_tools: Optional[Set[str]] = None,
        limits: Optional[AgentExecutionLimits] = None,
        confirmation_handler: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        auto_confirm_dangerous: bool = False,
    ) -> Sandbox:
        """Instantiate a new sandboxed execution boundary."""
        with self._lock:
            policy = AgentPolicy(
                allowed_tools=set(allowed_tools) if allowed_tools is not None else set(self._default_policy.allowed_tools),
                dangerous_tools=set(dangerous_tools) if dangerous_tools is not None else set(self._default_policy.dangerous_tools),
                auto_confirm_dangerous=auto_confirm_dangerous,
            )
            handler = confirmation_handler if confirmation_handler is not None else self._confirmation_handler
            sb = Sandbox(
                tools=self._tools,
                policy=policy,
                limits=limits or self._default_limits,
                permissions=self.permissions,
                confirmation_handler=handler,
            )
            self._sandboxes.append(sb)
            return sb

    def audit_trail(self) -> List[ToolCallRecord]:
        """Aggregate audit trail across all sandboxes."""
        with self._lock:
            records: List[ToolCallRecord] = []
            for sb in self._sandboxes:
                records.extend(sb.audit_trail)
            records.sort(key=lambda r: r.timestamp)
            return records

    def clear(self) -> None:
        with self._lock:
            self._tools.clear()
            self._sandboxes.clear()
            self._default_policy.allowed_tools.clear()
            self._default_policy.dangerous_tools.clear()
