"""The model catalog: a snapshot of the public Ollama library, used to pick and swap models."""
from arena.llm import catalog
from arena.llm.hardware import Hardware
from tests.helpers import make_hub


def test_catalog_has_hundreds_of_models():
    chat = [e for e in catalog.entries() if e.local and e.chat_capable]
    assert len(chat) >= 200
    assert len(catalog.all_variants()) >= 400
    assert catalog.meta().get("fetched")


def test_sizes_and_estimates_are_sane():
    assert catalog.parse_size("3b") == 3 and abs(catalog.parse_size("270m") - 0.27) < 1e-6
    assert catalog.estimate_gb(3) < catalog.estimate_gb(8)
    for v in catalog.all_variants():
        assert v.est_gb >= 0 and v.tag.startswith(v.family)


def test_lookup_and_thinking_detection():
    assert catalog.lookup("llama3.2:3b") is not None
    assert catalog.is_thinking_model("deepseek-r1:1.5b")
    assert not catalog.is_thinking_model("llama3.2:3b")


def test_search_filters():
    small = catalog.search("llama", max_gb=3)
    assert small and all(v.est_gb <= 3 and "llama" in (v.tag + v.description).lower() for v in small)
    assert all("thinking" in v.capabilities for v in catalog.search(capability="thinking"))


def test_pool_for_a_small_machine_excludes_big_and_thinking_models():
    pool = catalog.pool_for(6, avoid_thinking=True, max_gb=2.5, limit=100)
    assert pool and all(v.est_gb <= 2.5 and not v.thinking for v in pool)
    assert len({v.family for v in pool}) == len(pool)       # one variant per family


def test_plan_prefers_new_models_and_avoids_unfit_ones():
    hub, admin, ledger = make_hub({"mistral:latest": 4.4, "qwen3:4b": 2.5}, protected=["mistral:latest", "qwen3:4b"])
    plan = hub.plan(6, exclude={"mistral:latest"})
    assert len(plan) == 6 and len(set(plan)) == 6
    assert "mistral:latest" not in plan
    assert sum(1 for m in plan if ledger.is_protected(m)) <= 2          # at most a third are pre-existing
    for m in plan:
        v = catalog.lookup(m)
        assert v is None or (v.est_gb <= hub.cap_gb() and not v.thinking)
    assert not any(w in m for m in plan for w in ("coder", "guard", "embed", "-vl"))


def test_newborn_model_choice_never_takes_an_unavailable_or_reserved_model():
    hub, admin, ledger = make_hub({"narr": 4.0}, protected=[])
    hub.permadeath.reserved.add("narr")
    m = hub.pick_newborn_model(in_use=set())
    assert m and m != "narr"


def test_models_markdown_lists_every_family():
    md = catalog.to_markdown()
    chat = [e for e in catalog.entries() if e.local and e.chat_capable]
    assert md.count("\n| `") >= len(chat)
