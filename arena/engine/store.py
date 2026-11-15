"""Durable storage for a run: nothing lost on close, nothing duplicated on resume.

Layout (data/runs/<run_id>/):
  journal.jsonl   append-only record of every story event, each with a sequence number
  snapshot.json   the full game state at the last checkpoint, written atomically; it records the
                  journal sequence it covers
  meta.json       small summary for the run browser
  seasons.jsonl   one line per finished season, written once per season
  chronicle.md    the readable story, rebuilt from the journal on resume
  partial/        journal lines written after the last checkpoint when a run was interrupted

On resume the journal is cut back to the snapshot's sequence, so the half-finished stretch is not
replayed twice, and the cut-off lines are kept in partial/ so nothing is thrown away.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from arena.engine.events import Event
from arena.engine.state import GameState

SKIP = {"state", "think"}  # live UI signals, not story


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class RunStore:
    def __init__(self, root: str, run_id: str):
        self.root = Path(root)
        self.run_id = run_id
        self.dir = self.root / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.journal_path = self.dir / "journal.jsonl"
        self.snapshot_path = self.dir / "snapshot.json"
        self.meta_path = self.dir / "meta.json"
        self.seasons_path = self.dir / "seasons.jsonl"
        self.chronicle_path = self.dir / "chronicle.md"
        self.seq = 0
        self._lock = threading.Lock()
        self._fh = None

    # ------------------------------------------------------------------ creating / finding --
    @classmethod
    def create(cls, root: str, seed: int) -> "RunStore":
        run_id = time.strftime("%Y%m%d-%H%M%S") + f"-s{seed}"
        n, rid = 1, run_id
        while (Path(root) / rid).exists():
            n += 1
            rid = f"{run_id}-{n}"
        return cls(root, rid)

    @classmethod
    def list_runs(cls, root: str) -> List[Dict[str, Any]]:
        out = []
        for m in Path(root).glob("*/meta.json"):
            try:
                out.append(json.loads(m.read_text(encoding="utf-8")))
            except Exception:
                continue
        return sorted(out, key=lambda d: d.get("updated", 0), reverse=True)

    @classmethod
    def open(cls, root: str, run_id: str = "latest") -> "RunStore":
        if run_id == "latest":
            runs = cls.list_runs(root)
            if not runs:
                raise FileNotFoundError("There are no saved runs yet.")
            run_id = runs[0]["run_id"]
        if not (Path(root) / run_id / "snapshot.json").exists():
            raise FileNotFoundError(f"Run {run_id} has no snapshot to resume from.")
        return cls(root, run_id)

    # ------------------------------------------------------------------------- journal ------
    def _open(self):
        if self._fh is None:
            self._fh = open(self.journal_path, "a", encoding="utf-8")
        return self._fh

    def record(self, ev: Event) -> None:
        if ev.kind in SKIP:
            return
        with self._lock:
            self.seq += 1
            d = asdict(ev)
            d["seq"] = self.seq
            fh = self._open()
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
            fh.flush()

    def _read_journal(self) -> List[Dict[str, Any]]:
        rows = []
        if self.journal_path.exists():
            with open(self.journal_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue  # a torn final line from a hard kill
        return rows

    def events(self, limit: Optional[int] = None) -> List[Event]:
        rows = self._read_journal()
        if limit:
            rows = rows[-limit:]
        evs = []
        for r in rows:
            r.pop("seq", None)
            try:
                evs.append(Event(**r))
            except TypeError:
                continue
        return evs

    # ----------------------------------------------------------------------- checkpoints ----
    def checkpoint(self, state: GameState, meta: Dict[str, Any]) -> None:
        """Make everything so far durable. Journal first, then the snapshot that covers it."""
        with self._lock:
            if self._fh:
                self._fh.flush()
                os.fsync(self._fh.fileno())
            seq = self.seq
        payload = {"version": 2, "journal_seq": seq, "saved_at": time.time(), "state": state.to_dict()}
        _atomic_write(self.snapshot_path, json.dumps(payload))
        meta = dict(meta, run_id=self.run_id, updated=time.time(), journal_seq=seq)
        meta.setdefault("created", self._created())
        _atomic_write(self.meta_path, json.dumps(meta, indent=1))

    def _created(self) -> float:
        try:
            return json.loads(self.meta_path.read_text(encoding="utf-8")).get("created", time.time())
        except Exception:
            return time.time()

    def load(self) -> Tuple[GameState, int]:
        """Load the last checkpoint and cut the journal back to it. Returns (state, number of lines set aside)."""
        snap = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        covered = int(snap.get("journal_seq", 0))
        rows = self._read_journal()
        keep = [r for r in rows if r.get("seq", 0) <= covered]
        extra = [r for r in rows if r.get("seq", 0) > covered]
        if extra:
            part = self.dir / "partial"
            part.mkdir(exist_ok=True)
            _atomic_write(part / f"journal-{time.strftime('%Y%m%d-%H%M%S')}.jsonl",
                          "\n".join(json.dumps(r, ensure_ascii=False) for r in extra) + "\n")
        if self._fh:
            self._fh.close()
            self._fh = None
        _atomic_write(self.journal_path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep))
        self.seq = covered
        return GameState.from_dict(snap["state"]), len(extra)

    # ------------------------------------------------------------------------------ seasons --
    def append_season(self, summary: Dict[str, Any]) -> bool:
        """Write a finished season once. Returns False if that season was already recorded."""
        done = set()
        if self.seasons_path.exists():
            for line in self.seasons_path.read_text(encoding="utf-8").splitlines():
                try:
                    done.add(json.loads(line)["season"])
                except Exception:
                    pass
        if summary["season"] in done:
            return False
        with open(self.seasons_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return True

    def close(self) -> None:
        with self._lock:
            if self._fh:
                self._fh.flush()
                os.fsync(self._fh.fileno())
                self._fh.close()
                self._fh = None
