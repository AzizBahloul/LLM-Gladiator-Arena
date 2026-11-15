"""The command line, end to end with the mock backend (no model, no ollama)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args, cwd=ROOT):
    return subprocess.run([sys.executable, "main.py", *args], cwd=cwd, capture_output=True, text=True, timeout=120)


def test_models_search_works_offline():
    r = run("models", "search", "llama", "--max-gb", "3", "--limit", "3")
    assert r.returncode == 0 and "llama" in r.stdout


def test_mock_run_saves_and_resumes(tmp_path):
    runs = ROOT / "data" / "runs"
    before = set(p.name for p in runs.glob("*")) if runs.exists() else set()
    r = run("--mock", "--no-gui", "--cycles", "2", "--pace", "0", "--seed", "21", "--once")
    assert r.returncode == 0, r.stderr
    new = [p for p in runs.glob("*") if p.name not in before]
    try:
        assert len(new) == 1
        d = new[0]
        for f in ("journal.jsonl", "snapshot.json", "meta.json", "chronicle.md", "config.json"):
            assert (d / f).exists(), f
        assert "Nothing below was scripted" in (d / "chronicle.md").read_text()
        r2 = run("resume", d.name, "--mock", "--no-gui", "--pace", "0")
        assert r2.returncode == 0, r2.stderr
        # a finished season resumes to a finished season, with the story intact and unduplicated
        text = (d / "chronicle.md").read_text()
        assert text.count("## Ending:") == 1
    finally:
        import shutil
        for p in new:
            shutil.rmtree(p, ignore_errors=True)


def test_runs_lists_without_error():
    assert run("runs").returncode == 0
