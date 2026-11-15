"""Installing models for new minds: a failed download is replaced, never fatal unless the user pinned it."""
import pytest

import main as M
from tests.helpers import make_hub


class Flaky:
    def __init__(self, admin, bad):
        self.admin, self.bad = admin, set(bad)
        self._orig = admin.pull

    def install(self):
        def pull(model, on_progress=None, timeout=0):
            if model in self.bad:
                return False
            return self._orig(model, on_progress, timeout)
        self.admin.pull = pull


def test_failed_download_is_replaced_by_the_next_candidate():
    hub, admin, ledger = make_hub({"mistral:latest": 4.4}, protected=["mistral:latest"])
    plan = hub.plan(3, exclude={"mistral:latest"})
    Flaky(admin, [plan[1]]).install()
    cfg = {"models": list(plan), "narrator_model": "mistral:latest", "god_model": "mistral:latest", "roster": []}
    M.install_missing(cfg, hub)
    assert plan[1] not in cfg["models"] and len(cfg["models"]) == 3 and len(set(cfg["models"])) == 3
    assert all(admin.has(m) for m in cfg["models"])


def test_a_pinned_model_that_fails_stops_the_run_with_a_clear_message():
    hub, admin, ledger = make_hub({"mistral:latest": 4.4}, protected=["mistral:latest"])
    Flaky(admin, ["pinned-model"]).install()
    cfg = {"models": ["pinned-model"], "_pinned_models": True, "narrator_model": "mistral:latest", "god_model": "mistral:latest", "roster": []}
    with pytest.raises(SystemExit) as e:
        M.install_missing(cfg, hub)
    assert "pinned-model" in str(e.value)


def test_resolve_models_never_puts_the_narrator_in_the_cast():
    hub, admin, ledger = make_hub({"mistral:latest": 4.4, "qwen3:4b": 2.5}, protected=["mistral:latest", "qwen3:4b"])
    cfg = {"models": "auto", "narrator_model": None, "god_model": None, "roster": ["a"] * 6}
    M.resolve_models(cfg, hub)
    assert cfg["narrator_model"] == "mistral:latest" and "mistral:latest" not in cfg["models"]
    assert hub.permadeath.status("mistral:latest") == "protected"
    assert len(cfg["models"]) == 6
