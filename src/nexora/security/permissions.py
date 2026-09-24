"""NEXORA permission system.

Privacy-sensitive modules (ScreenMind, AgentBox, Vision, etc., in later
milestones) must request explicit permission through this manager before
they may act. Nothing in NEXORA core grants permissions automatically, and
every grant/revoke is recorded in an audit trail.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class PermissionRecord:
    scope: str
    granted: bool
    reason: str
    timestamp: float = field(default_factory=time.time)


class PermissionDenied(PermissionError):
    pass


class PermissionManager:
    """Tracks explicit, per-scope permission grants.

    Nothing is granted by default. A scope such as ``"vision.screenshot"``
    or ``"agentbox.write_project"`` must be explicitly granted with
    ``.grant()`` before ``.require()`` will pass.
    """

    def __init__(self) -> None:
        self._grants: Dict[str, bool] = {}
        self._audit: List[PermissionRecord] = []
        self._lock = threading.RLock()

    def grant(self, scope: str, *, reason: str = "granted by caller") -> None:
        with self._lock:
            self._grants[scope] = True
            self._audit.append(PermissionRecord(scope, True, reason))

    def revoke(self, scope: str, *, reason: str = "revoked by caller") -> None:
        with self._lock:
            self._grants[scope] = False
            self._audit.append(PermissionRecord(scope, False, reason))

    def is_granted(self, scope: str) -> bool:
        with self._lock:
            return self._grants.get(scope, False)

    def require(self, scope: str) -> None:
        if not self.is_granted(scope):
            raise PermissionDenied(
                f"Scope {scope!r} was not explicitly granted. NEXORA never "
                f"assumes consent -- call permissions.grant({scope!r}) first."
            )

    def audit_trail(self) -> List[PermissionRecord]:
        with self._lock:
            return list(self._audit)
