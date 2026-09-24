"""NEXORA configuration.

Config is intentionally boring: environment variables (``NEXORA_*``), an
optional ``nexora.toml`` in the current directory, and explicit constructor
arguments, in increasing order of precedence. Privacy-affecting defaults
(telemetry, cloud sync) always default to off.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, Optional

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore


@dataclass
class Config:
    telemetry: bool = False
    cloud_sync: bool = False
    data_dir: str = str(Path.home() / ".nexora")
    log_level: str = "INFO"
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(
        cls,
        *,
        config_path: Optional[Path] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> "Config":
        values: Dict[str, Any] = {}

        path = config_path or Path.cwd() / "nexora.toml"
        if tomllib is not None and path.exists():
            with open(path, "rb") as fh:
                file_values = tomllib.load(fh).get("nexora", {})
            values.update(file_values)

        known = {f.name for f in fields(cls)}
        for key in known:
            env_key = f"NEXORA_{key.upper()}"
            if env_key in os.environ:
                values[key] = _coerce(os.environ[env_key])

        if overrides:
            values.update(overrides)

        known_values = {k: v for k, v in values.items() if k in known}
        extra_values = {k: v for k, v in values.items() if k not in known}
        known_values.setdefault("extra", {})
        known_values["extra"] = {**known_values["extra"], **extra_values}
        return cls(**known_values)


def _coerce(raw: str) -> Any:
    if raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw
