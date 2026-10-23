"""File backed cache of Claude responses.

Keyed by a hash of model, prompt and input, so a changed prompt or message is a
cache miss. Committed to the repo so the demo and the clips use real, recorded
outputs without paying for the same call twice.
"""

import hashlib
import json
import threading
from pathlib import Path
from typing import Any


def cache_key(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


class ResponseCache:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, Any]] = {}
        if path.exists():
            self._data = json.loads(path.read_text() or "{}")

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            return self._data.get(key)

    def put(self, key: str, entry: dict[str, Any]) -> None:
        with self._lock:
            self._data[key] = entry
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
            tmp.replace(self.path)

    def __len__(self) -> int:
        return len(self._data)
