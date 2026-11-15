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
        try:
            have = {canon(m) for m in self.installed()}
        except Exception:
            return False          # an Ollama outage reads as "not installed", never as a crash
        return canon(model) in have

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
    return shutil.disk_usage(os.path.expanduser(path) if path not in ("", ".") else os.path.expanduser("~")).free / 1e9


def canon(model: str) -> str:
    """One spelling per model: no registry prefix, always a tag. 'llama3.2' and 'llama3.2:latest' are the same model."""
    m = (model or "").strip().lower()
    for pre in ("registry.ollama.ai/library/", "registry.ollama.ai/", "library/"):
        if m.startswith(pre):
            m = m[len(pre):]
    return m if (":" in m or not m) else m + ":latest"


# ------------------------------------------------------------------------------- ledger --
class ModelLedger:
    """data/arena_models.json: {'protected': [...], 'owned': {model: {'installed_at': ts}}, 'wiped': [...]}"""

    def __init__(self, path: str = "data/arena_models.json"):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.data: Dict = {"protected": [], "owned": {}, "wiped": []}
        self.corrupt = False
        if self.path.exists():
            try:
                self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
            except Exception:
                # An unreadable ledger means we no longer know what is safe: keep the evidence, delete nothing.
                self.corrupt = True
                try:
                    shutil.copy2(self.path, self.path.with_suffix(".corrupt"))
                except OSError:
                    pass

    @property
    def initialised(self) -> bool:
        """True once the first-run snapshot of pre-existing models has really been taken."""
        return self.corrupt or bool(self.data.get("snapshot_taken")) or bool(self.data.get("protected"))

    def _save(self) -> None:
        if self.corrupt:
            return                # never overwrite a ledger we could not read
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
                mine = {canon(m) for m in self.data["owned"]} | {canon(m) for m in self.data["wiped"]}
                self.data["protected"] = sorted({canon(m) for m in installed} - mine)
                self.data["snapshot_taken"] = True
                self._save()

    def mark_owned(self, model: str) -> None:
        with self._lock:
            if canon(model) not in {canon(m) for m in self.data["protected"]}:
                self.data["owned"].setdefault(canon(model), {"installed_at": time.time()})
                self._save()

    def mark_wiped(self, model: str) -> None:
        with self._lock:
            for k in [k for k in self.data["owned"] if canon(k) == canon(model)]:
                self.data["owned"].pop(k, None)
            if canon(model) not in {canon(m) for m in self.data["wiped"]}:
                self.data["wiped"].append(canon(model))
            self._save()

    def is_protected(self, model: str) -> bool:
        if self.corrupt:
            return True
        return canon(model) in {canon(m) for m in self.data["protected"]}

    def is_owned(self, model: str) -> bool:
        if self.corrupt:
            return False
        return canon(model) in {canon(m) for m in self.data["owned"]}
