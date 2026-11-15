"""Installing, listing and deleting Ollama models, plus the ledger of who installed what.

The ledger is what makes permadeath safe: it records which models were already on the machine
before the arena touched anything (protected) and which the arena installed itself (owned).
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set

import requests

Progress = Callable[[str, float, str], None]  # (model, fraction 0..1, status text)


class OllamaAdmin:
    def __init__(self, url: str = "http://localhost:11434", timeout: int = 15):
        self.url = url.rstrip("/")
        self.timeout = timeout

    def up(self) -> bool:
        try:
            return requests.get(f"{self.url}/api/tags", timeout=3).status_code == 200
        except Exception:
            return False

    def installed(self) -> Dict[str, float]:
        """name -> size in GB."""
        r = requests.get(f"{self.url}/api/tags", timeout=self.timeout)
        r.raise_for_status()
        return {m["name"]: round(m.get("size", 0) / 1e9, 2) for m in r.json().get("models", [])}

    def has(self, model: str) -> bool:
        have = self.installed()
        return model in have or (":" not in model and f"{model}:latest" in have)

    def pull(self, model: str, on_progress: Optional[Progress] = None, timeout: int = 7200) -> bool:
        try:
            with requests.post(f"{self.url}/api/pull", json={"model": model, "stream": True}, stream=True, timeout=timeout) as r:
                if r.status_code != 200:
                    if on_progress:
                        on_progress(model, 0.0, f"pull failed: HTTP {r.status_code}")
                    return False
                ok = False
                for line in r.iter_lines():
                    if not line:
                        continue
                    d = json.loads(line)
                    if d.get("error"):
                        if on_progress:
                            on_progress(model, 0.0, f"pull failed: {d['error']}")
                        return False
                    total, done = d.get("total"), d.get("completed")
                    frac = (done / total) if total and done is not None else 0.0
                    if on_progress:
                        on_progress(model, frac, d.get("status", ""))
                    if d.get("status") == "success":
                        ok = True
                return ok
        except Exception as exc:
            if on_progress:
                on_progress(model, 0.0, f"pull failed: {type(exc).__name__}: {exc}")
            return False

    def remove(self, model: str) -> bool:
        try:
            r = requests.delete(f"{self.url}/api/delete", json={"model": model}, timeout=60)
            return r.status_code == 200
        except Exception:
            return False


def free_disk_gb(path: str = ".") -> float:
    return shutil.disk_usage(os.path.expanduser("~")).free / 1e9


# ------------------------------------------------------------------------------- ledger --
class ModelLedger:
    """data/arena_models.json: {'protected': [...], 'owned': {model: {'installed_at': ts}}, 'wiped': [...]}"""

    def __init__(self, path: str = "data/arena_models.json"):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.data: Dict = {"protected": [], "owned": {}, "wiped": []}
        if self.path.exists():
            try:
                self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
            except Exception:
                pass

    @property
    def initialised(self) -> bool:
        return self.path.exists()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    def snapshot_protected(self, installed: Iterable[str]) -> None:
        """First run only: everything already on the machine is protected."""
        with self._lock:
            if not self.initialised:
                self.data["protected"] = sorted(set(installed))
                self._save()

    def mark_owned(self, model: str) -> None:
        with self._lock:
            if model not in self.data["protected"]:
                self.data["owned"].setdefault(model, {"installed_at": time.time()})
                self._save()

    def mark_wiped(self, model: str) -> None:
        with self._lock:
            self.data["owned"].pop(model, None)
            if model not in self.data["wiped"]:
                self.data["wiped"].append(model)
            self._save()

    def is_protected(self, model: str) -> bool:
        return model in self.data["protected"] or (":" not in model and f"{model}:latest" in self.data["protected"])

    def is_owned(self, model: str) -> bool:
        return model in self.data["owned"]
