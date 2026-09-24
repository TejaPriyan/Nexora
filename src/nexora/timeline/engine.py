"""TimeLoop state management engine: checkpoints, diffs, restores, and rewinds."""

from __future__ import annotations

import copy
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Union

from ..security import SecretRedactor
from .models import DiffResult, Snapshot


class TimeLoopEngine:
    """Thread-safe state timeline engine with automatic secret redaction.

    Every checkpoint is scrubbed through `SecretRedactor` to prevent storing
    passwords, tokens, or sensitive API keys. Never claims perfect secret detection.
    """

    def __init__(
        self,
        *,
        redactor: Optional[SecretRedactor] = None,
        ignore_keys: Sequence[str] = (),
    ) -> None:
        self._redactor = redactor or SecretRedactor()
        if ignore_keys:
            self._redactor.ignore(*ignore_keys)

        self._lock = threading.RLock()
        self._snapshots: List[Snapshot] = []
        self._current_index: int = -1
        self._counter: int = 0

    @property
    def redactor(self) -> SecretRedactor:
        return self._redactor

    def ignore(self, *keys: str) -> "TimeLoopEngine":
        """Add custom field names to the secret redaction exclusion list."""
        with self._lock:
            self._redactor.ignore(*keys)
        return self

    def checkpoint(
        self,
        label: str,
        data: Dict[str, Any],
        *,
        metadata: Optional[Dict[str, Any]] = None,
        now: Optional[float] = None,
    ) -> Snapshot:
        """Create and record a new state checkpoint with secret redaction."""
        with self._lock:
            t = now if now is not None else time.time()
            self._counter += 1
            snap_id = f"snap_{self._counter:04d}_{int(t * 1000)}"

            # Deep copy and redact data
            raw_copy = copy.deepcopy(data)
            clean_data = self._redactor.redact(raw_copy)
            clean_meta = self._redactor.redact(copy.deepcopy(metadata or {}))

            snapshot = Snapshot(
                id=snap_id,
                label=label,
                data=clean_data,
                timestamp=t,
                metadata=clean_meta,
            )

            self._snapshots.append(snapshot)
            self._current_index = len(self._snapshots) - 1
            return snapshot

    def snapshot(self) -> Optional[Snapshot]:
        """Return the current active snapshot."""
        with self._lock:
            if 0 <= self._current_index < len(self._snapshots):
                return self._snapshots[self._current_index]
            return None

    def get(self, snapshot_id: str) -> Optional[Snapshot]:
        """Retrieve a snapshot by ID."""
        with self._lock:
            for snap in self._snapshots:
                if snap.id == snapshot_id:
                    return snap
            return None

    def history(self) -> List[Snapshot]:
        """Return the complete chronological list of snapshots."""
        with self._lock:
            return list(self._snapshots)

    def restore(self, snapshot_id: str) -> Snapshot:
        """Move the timeline pointer to a specific snapshot ID."""
        with self._lock:
            for idx, snap in enumerate(self._snapshots):
                if snap.id == snapshot_id:
                    self._current_index = idx
                    return snap
            raise KeyError(f"Snapshot ID {snapshot_id!r} not found in timeline.")

    def rewind(self, steps: int = 1) -> Snapshot:
        """Rewind the timeline by `steps` checkpoints."""
        with self._lock:
            if not self._snapshots:
                raise IndexError("Cannot rewind: timeline contains no snapshots.")
            target_idx = max(0, self._current_index - steps)
            self._current_index = target_idx
            return self._snapshots[self._current_index]

    def forward(self, steps: int = 1) -> Snapshot:
        """Fast-forward the timeline by `steps` checkpoints."""
        with self._lock:
            if not self._snapshots:
                raise IndexError("Cannot forward: timeline contains no snapshots.")
            target_idx = min(len(self._snapshots) - 1, self._current_index + steps)
            self._current_index = target_idx
            return self._snapshots[self._current_index]

    def diff(
        self,
        source: Union[str, Snapshot, Dict[str, Any]],
        target: Union[str, Snapshot, Dict[str, Any]],
    ) -> DiffResult:
        """Compute the structural difference between two snapshots or state dictionaries."""
        with self._lock:
            src_data, src_id = self._resolve_data(source, default_id="source")
            tgt_data, tgt_id = self._resolve_data(target, default_id="target")

            added: Dict[str, Any] = {}
            removed: Dict[str, Any] = {}
            changed: Dict[str, Tuple[Any, Any]] = {}

            all_keys = set(src_data.keys()) | set(tgt_data.keys())

            for k in all_keys:
                if k not in src_data:
                    added[k] = tgt_data[k]
                elif k not in tgt_data:
                    removed[k] = src_data[k]
                elif src_data[k] != tgt_data[k]:
                    changed[k] = (src_data[k], tgt_data[k])

            return DiffResult(
                from_id=src_id,
                to_id=tgt_id,
                added=added,
                removed=removed,
                changed=changed,
            )

    def clear(self) -> None:
        """Reset timeline and snapshots."""
        with self._lock:
            self._snapshots.clear()
            self._current_index = -1
            self._counter = 0

    def _resolve_data(
        self,
        item: Union[str, Snapshot, Dict[str, Any]],
        default_id: str,
    ) -> Tuple[Dict[str, Any], str]:
        if isinstance(item, str):
            snap = self.get(item)
            if snap is None:
                raise KeyError(f"Snapshot ID {item!r} not found in timeline.")
            return snap.data, snap.id
        elif isinstance(item, Snapshot):
            return item.data, item.id
        elif isinstance(item, dict):
            return item, default_id
        else:
            raise TypeError(f"Invalid diff operand type: {type(item)}")
