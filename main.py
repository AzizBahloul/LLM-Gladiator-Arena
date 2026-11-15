#!/usr/bin/env python3
"""THE UNDERMIND: command line.

    python main.py                       start a new season
    python main.py new --endless         start a run that never ends (God writes new seasons)
    python main.py resume [RUN_ID]       carry on exactly where a run was closed
    python main.py runs                  list saved runs
    python main.py models list|search|pull|status|refresh|markdown

Run `python main.py <command> --help` for the options of each.
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / "data" / "runs"
LEDGER = ROOT / "data" / "arena_models.json"
console = Console()


# ------------------------------------------------------------------------------ config -----
def load_config(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def apply_flags(cfg: Dict[str, Any], a: argparse.Namespace) -> None:
    g = cfg.setdefault("game", {})
    if getattr(a, "endless", False):
        g["endless"] = True
    if getattr(a, "once", False):
        g["endless"] = False
    if getattr(a, "cycles", None) is not None:
        g["cycles"] = a.cycles
    if getattr(a, "no_god", False):
        g["god"] = False
    if getattr(a, "no_permadeath", False):
        g["permadeath"] = False
    if getattr(a, "mock", False):
        cfg.setdefault("api", {})["provider"] = "mock"
    if getattr(a, "models", None):
        cfg["models"] = "auto" if a.models == "auto" else [m.strip() for m in a.models.split(",") if m.strip()]
    if getattr(a, "pace", None) is not None:
        cfg["pace"] = a.pace


# ------------------------------------------------------------------------------- models -----
def make_hub(cfg: Dict[str, Any], a: argparse.Namespace):
    """The ModelHub (installing, choosing, wiping) for an ollama run. None for mock and hosted runs."""
    from arena.engine.models import ModelHub
    from arena.engine.permadeath import Permadeath
    from arena.llm import hardware
    from arena.llm.ollama_tools import ModelLedger, OllamaAdmin

    api = cfg.get("api", {})
    admin = OllamaAdmin(api.get("ollama_url", "http://localhost:11434"))
    if not admin.up():
        sys.exit("Ollama is not running at " + api.get("ollama_url", "http://localhost:11434") +
                 ". Start it with `ollama serve`, or run with --mock for an offline dry run.")
    ledger = ModelLedger(str(LEDGER))
    if not ledger.initialised:
        # First run ever: everything already on this machine is protected from permadeath, forever.
        ledger.snapshot_protected(admin.installed())
    g = cfg.get("game", {})
    perm = Permadeath(admin, ledger, enabled=bool(g.get("permadeath", True)),
                      include_preexisting=bool(getattr(a, "include_preexisting", False)))
    return ModelHub(admin, ledger, perm, hardware.detect(), max_model_gb=float(cfg.get("max_model_gb", 2.5)),
                    auto_install=bool(cfg.get("auto_install", True)))


def resolve_models(cfg: Dict[str, Any], hub) -> None:
    """Fill in narrator/god models and, for `models: auto`, choose and install the models that will play."""
    installed = hub.installed()
    from arena.llm import catalog
    if not cfg.get("narrator_model"):
        # The Registrar needs a steady voice that is not at stake: prefer a protected, non-thinking model already installed.
        pre = [m for m in installed if hub.ledger.is_protected(m) and not catalog.is_thinking_model(m)]
        cfg["narrator_model"] = pre[0] if pre else None
    if not cfg.get("god_model"):
        cfg["god_model"] = cfg.get("narrator_model")
    reserved = {m for m in (cfg.get("narrator_model"), cfg.get("god_model")) if m}
    hub.permadeath.reserved |= reserved

    roster = cfg.get("roster") or []
    n = len(roster) or 6
    models = cfg.get("models")
    if models in (None, "auto"):
        models = hub.plan(n, exclude=reserved)
        if not models:
            sys.exit("No model in the catalog fits this machine. Set `models:` in config.yaml by hand.")
    cfg["_pinned_models"] = cfg.get("models") not in (None, "auto")
    cfg["models"] = list(models)
    if not cfg.get("narrator_model"):
        cfg["narrator_model"] = cfg["models"][0]
        cfg["god_model"] = cfg.get("god_model") or cfg["narrator_model"]


def install_missing(cfg: Dict[str, Any], hub) -> None:
    """Download whatever is not installed. A model that cannot be downloaded is replaced by the next candidate
    in the catalog instead of ending the run, unless the user pinned it by hand."""
    from arena.llm import catalog
    from arena.llm.ollama_tools import free_disk_gb

    pinned = cfg.get("_pinned_models", False)
    keep = [m for m in (cfg.get("narrator_model"), cfg.get("god_model")) if m]
    for e in cfg.get("roster") or []:
        if isinstance(e, dict) and e.get("model"):
            keep.append(e["model"])
    wanted = list(dict.fromkeys(cfg["models"] + keep))
    missing = [m for m in wanted if not hub.admin.has(m)]
    if not missing:
        return
    total = sum((catalog.lookup(m).est_gb if catalog.lookup(m) else 2.0) for m in missing)
    free = free_disk_gb(str(Path.home()))
    console.print(f"[bold]New minds need {len(missing)} model(s), about {total:.1f} GB:[/bold] {', '.join(missing)}  (free disk: {free:.0f} GB)")
    if total * 1.2 > free:
        sys.exit("Not enough free disk space for those models. Free some space, or set `max_model_gb` lower.")
    failed: List[str] = []
    for m in missing:
        current = m
        for _attempt in range(4):
            last = [-1.0]

            def prog(model: str, frac: float, status: str) -> None:
                if frac - last[0] >= 0.05 or frac >= 1.0:
                    last[0] = frac
                    console.print(f"  installing {model}: {frac * 100:3.0f}%  {status}", highlight=False, markup=False)

            if hub.ensure(current, prog):
                if current != m:
                    cfg["models"] = [current if x == m else x for x in cfg["models"]]
                break
            failed.append(current)
            console.print(f"  [yellow]could not install {current}.[/yellow]")
            if pinned or current in keep:
                sys.exit(f"Could not install {current}, which was named in the configuration. Check the connection and run again.")
            repl = [v.tag for v in hub.candidates(exclude=set(cfg["models"]) | set(failed)) if not hub.admin.has(v.tag)]
            if not repl:
                sys.exit("Could not install a model and found no replacement. Check the connection and run again.")
            current = repl[0]
            console.print(f"  trying {current} instead")
        else:
            sys.exit("Several downloads failed in a row. Check the connection and run again.")


def permadeath_notice(cfg: Dict[str, Any], hub) -> None:
    if not hub or not hub.permadeath.enabled:
        console.print("[dim]Permadeath is off: no model will be deleted.[/dim]")
        return
    at_stake = sorted({m for m in cfg["models"] if hub.permadeath.status(m) == "at stake"})
    safe = sorted({m for m in cfg["models"] + [cfg.get("narrator_model")] if m and hub.permadeath.status(m) != "at stake"})
    console.print("[bold]Permadeath is on.[/bold] When a mind is dissolved, the model that gave it a voice is deleted from this machine.")
    console.print(f"  at stake: {', '.join(at_stake) or 'none'}")
    console.print(f"  protected (installed before the arena first ran, or reserved for the Registrar and God): {', '.join(safe) or 'none'}")
    console.print("  use --no-permadeath to keep every model, or --include-preexisting to put protected models at stake too.\n")


# -------------------------------------------------------------------------------- runs ------
def build_game(cfg: Dict[str, Any], a: argparse.Namespace, store, state=None, seed: Optional[int] = None):
    from arena.engine.events import EventBus
    from arena.engine.game import Game
    from arena.llm.backends import make_backend

    provider = cfg.get("api", {}).get("provider", "ollama")
    hub = make_hub(cfg, a) if provider == "ollama" else None
    if hub:
        resolve_models(cfg, hub)
        install_missing(cfg, hub)
        permadeath_notice(cfg, hub)
    backend = make_backend(cfg)
    bus = EventBus()
    game = Game(cfg, backend, bus, state=state, seed=seed, pace=float(cfg.get("pace", 0.35)), store=store, hub=hub)
    return game, bus, provider


def save_run_config(store, cfg: Dict[str, Any]) -> None:
    import json
    (store.dir / "config.json").write_text(json.dumps(cfg, indent=1, default=str), encoding="utf-8")


def start(cfg: Dict[str, Any], a: argparse.Namespace, resume_id: Optional[str] = None) -> int:
    from arena.engine.store import RunStore
    from arena.ui.chronicle_file import ChronicleWriter

    state = None
    replay: List[Any] = []
    if resume_id is not None:
        store = RunStore.open(str(RUNS_DIR), resume_id)
        saved = store.dir / "config.json"
        if saved.exists():
            import json
            cfg = json.loads(saved.read_text(encoding="utf-8"))
            apply_flags(cfg, a)
        state, cut = store.load()
        replay = store.events()
        if cut:
            console.print(f"[dim]Resuming {store.run_id} at cycle {state.cycle}. {cut} unfinished journal line(s) set aside in partial/.[/dim]")
        else:
            console.print(f"[dim]Resuming {store.run_id} at cycle {state.cycle}.[/dim]")
        seed = state.seed
    else:
        seed = a.seed if a.seed is not None else (cfg.get("seed") or int.from_bytes(os.urandom(3), "big"))
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        store = RunStore.create(str(RUNS_DIR), int(seed))

    game, bus, provider = build_game(cfg, a, store, state=state, seed=int(seed))
    if resume_id is None:
        save_run_config(store, cfg)
    writer = ChronicleWriter(str(store.chronicle_path), {
        "seed": seed, "minds": [(w.name, w.model) for w in game.s.wicks.values()]})
    writer.replay(replay)
    bus.subscribe(writer)
    console.print(f"[dim]Run {store.run_id}. Story: {store.chronicle_path}[/dim]")

    if a.no_gui:
        return run_console(game, bus, replay)
    from arena.ui.tui import UndermindApp
    app = UndermindApp(game, bus, chronicle_path=str(store.chronicle_path), provider=provider, replay=replay)
    app.run()
    return 0


def run_console(game, bus, replay) -> int:
    from arena.ui.console import ConsoleRenderer
    r = ConsoleRenderer(console)
    r.banner([{"name": w.name, "color": game.s.persona(w.persona_id).color, "epithet": game.s.persona(w.persona_id).epithet,
               "model": w.model} for w in game.s.wicks.values()])
    for ev in replay:
        r(ev)
    bus.subscribe(r)
    signal.signal(signal.SIGINT, lambda *_: game.stop())
    t = threading.Thread(target=game.run, daemon=True)
    t.start()
    while t.is_alive():
        t.join(0.2)
    s = game.s
    console.print(f"\n[dim]Closed at cycle {s.cycle}. Resume with: python main.py resume[/dim]" if s.phase != "finished" or game.rules.endless
                  else f"\n[dim]Season over. Story saved.[/dim]")
    return 0


# ------------------------------------------------------------------------------ commands ----
def cmd_runs(a: argparse.Namespace) -> int:
    from arena.engine.store import RunStore
    runs = RunStore.list_runs(str(RUNS_DIR)) if RUNS_DIR.exists() else []
    if not runs:
        console.print("No saved runs yet. Start one with `python main.py`.")
        return 0
    t = Table(show_edge=False, header_style="bold")
    for c in ("Run", "Season", "Cycle", "State", "Minds"):
        t.add_column(c)
    for r in runs:
        state = "finished" if r.get("phase") == "finished" and not r.get("endless") else (r.get("ending") or r.get("phase") or "open")
        t.add_row(r.get("run_id", "?"), str(r.get("season", 1)), str(r.get("cycle", 0)), str(state),
                  ", ".join(m[0] for m in r.get("minds", [])))
    console.print(t)
    return 0


def cmd_models(a: argparse.Namespace) -> int:
    from arena.llm import catalog
    if a.what == "refresh":
        n = catalog.refresh()
        console.print(f"Catalog refreshed: {n} model families.")
        return 0
    if a.what == "markdown":
        Path(ROOT / "docs" / "MODELS.md").write_text(catalog.to_markdown(), encoding="utf-8")
        console.print("Wrote docs/MODELS.md")
        return 0
    if a.what in ("list", "search"):
        vs = catalog.search(a.query or "", max_gb=a.max_gb, capability=a.capability or "")
        t = Table(show_edge=False, header_style="bold")
        for c in ("Tag", "GB", "Capabilities", "What it is"):
            t.add_column(c)
        for v in vs[: a.limit]:
            t.add_row(v.tag, f"{v.est_gb:g}", ", ".join(v.capabilities) or "chat", v.description[:70])
        console.print(t)
        console.print(f"[dim]{len(vs)} matching variants, {len(catalog.entries())} families in the catalog.[/dim]")
        return 0
    from arena.llm.ollama_tools import ModelLedger, OllamaAdmin
    admin = OllamaAdmin()
    if not admin.up():
        sys.exit("Ollama is not running. Start it with `ollama serve`.")
    ledger = ModelLedger(str(LEDGER))
    if a.what == "status":
        inst = admin.installed()
        t = Table(show_edge=False, header_style="bold")
        t.add_column("Installed model")
        t.add_column("GB", justify="right")
        t.add_column("Permadeath")
        for m, gb in sorted(inst.items()):
            t.add_row(m, f"{gb:.1f}", "protected" if ledger.is_protected(m) else ("at stake" if ledger.is_owned(m) else "untracked"))
        console.print(t)
        return 0
    if a.what == "pull":
        if not a.query:
            sys.exit("Give a model tag, e.g. python main.py models pull gemma2:2b")
        if not admin.up():
            sys.exit("Ollama is not running. Start it with `ollama serve`.")
        if not ledger.initialised:      # record what is already here BEFORE adding anything of ours
            ledger.snapshot_protected(admin.installed())
        ok = admin.pull(a.query, lambda m, f, s: console.print(f"  {m}: {f * 100:3.0f}% {s}", highlight=False, markup=False) if int(f * 20) != int((f - 0.001) * 20) else None)
        if ok:
            ledger.mark_owned(a.query)
        return 0 if ok else 1
    return 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="main.py", description="THE UNDERMIND: language models that fight each other.")
    sub = p.add_subparsers(dest="cmd")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=str(ROOT / "config.yaml"), help="path to the configuration file")

    def run_flags(sp: argparse.ArgumentParser, new: bool) -> None:
        sp.add_argument("--no-gui", action="store_true", help="plain console output instead of the full-screen interface")
        sp.add_argument("--mock", action="store_true", help="offline dry run with a seeded test double instead of real models")
        sp.add_argument("--no-permadeath", action="store_true", help="never delete a model")
        sp.add_argument("--include-preexisting", action="store_true", help="models installed before the arena first ran may be deleted too")
        sp.add_argument("--pace", type=float, help="seconds between events")
        if new:
            sp.add_argument("--seed", type=int)
            sp.add_argument("--cycles", type=int, help="cycles per season (0 = until the story ends it)")
            sp.add_argument("--endless", action="store_true", help="after an ending, God begins a new season and the run continues (the default in config.yaml)")
            sp.add_argument("--once", action="store_true", help="stop after one season")
            sp.add_argument("--no-god", action="store_true", help="use the fixed deck of Notices instead of God")
            sp.add_argument("--models", help="'auto' (choose and install new models) or a comma list of ollama tags")

    run_flags(sub.add_parser("new", help="start a new run", parents=[common]), True)
    r = sub.add_parser("resume", help="resume a saved run", parents=[common])
    r.add_argument("run_id", nargs="?", default="latest")
    run_flags(r, False)
    sub.add_parser("runs", help="list saved runs")
    m = sub.add_parser("models", help="browse, install and inspect models")
    m.add_argument("what", choices=["list", "search", "pull", "status", "refresh", "markdown"])
    m.add_argument("query", nargs="?")
    m.add_argument("--max-gb", type=float)
    m.add_argument("--capability")
    m.add_argument("--limit", type=int, default=40)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0].startswith("-") and argv[0] not in ("-h", "--help")):
        argv.insert(0, "new")        # `python main.py --mock` is `python main.py new --mock`
    a = p.parse_args(argv)
    cmd = a.cmd
    if cmd == "runs":
        return cmd_runs(a)
    if cmd == "models":
        return cmd_models(a)
    cfg = load_config(a.config)
    apply_flags(cfg, a)
    try:
        return start(cfg, a, resume_id=a.run_id if cmd == "resume" else None)
    except FileNotFoundError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    sys.exit(main())
