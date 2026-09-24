"""Secret redaction helpers.

Used directly today, and (in the TimeLoop/Timeline milestone) before any
state snapshot is stored or diffed, per the "never blindly serialize
secrets" requirement. This is a best-effort denylist plus explicit opt-in
exclusion -- it does not claim perfect detection.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Set

DEFAULT_SENSITIVE_KEYS: Set[str] = {
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "access_key", "private_key", "auth", "credential", "credentials",
    "session_id", "ssn", "credit_card",
}

_SENSITIVE_PATTERN = re.compile(
    "|".join(re.escape(k) for k in DEFAULT_SENSITIVE_KEYS), re.IGNORECASE
)

REDACTED = "***REDACTED***"


class SecretRedactor:
    """Redacts dict values whose keys look sensitive.

    Best-effort heuristic, not a guarantee. Callers with known sensitive
    fields should always add them explicitly via ``.ignore()``.
    """

    def __init__(self, extra_keys: Iterable[str] = ()) -> None:
        self._extra = {k.lower() for k in extra_keys}

    def ignore(self, *keys: str) -> "SecretRedactor":
        self._extra.update(k.lower() for k in keys)
        return self

    def is_sensitive(self, key: str) -> bool:
        lowered = key.lower()
        return lowered in self._extra or bool(_SENSITIVE_PATTERN.search(lowered))

    def redact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in data.items():
            if self.is_sensitive(key):
                result[key] = REDACTED
            elif isinstance(value, dict):
                result[key] = self.redact(value)
            else:
                result[key] = value
        return result
