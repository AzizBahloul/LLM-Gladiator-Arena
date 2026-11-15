"""The model catalog: every model family in the public Ollama library, with its sizes.

catalog_data.json is a snapshot of https://ollama.com/library (names, descriptions,
capabilities, parameter sizes, pull counts). `refresh()` re-reads the live page. Download and
VRAM figures are estimates for the default 4-bit builds, good enough to decide what will fit.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

DATA_FILE = Path(__file__).with_name("catalog_data.json")
LIBRARY_URL = "https://ollama.com/library"
_CAPS = {"tools", "vision", "thinking", "embedding", "cloud", "audio"}


@dataclass(frozen=True)
class Variant:
    family: str
    size: str                # "3b", "270m", "latest"
    tag: str                 # what you give to `ollama pull`
    params_b: float          # billions of parameters (0 if unknown)
    est_gb: float            # approximate download and VRAM need at 4-bit
    capabilities: tuple
    description: str
    pulls: int

    @property
    def thinking(self) -> bool:
        return "thinking" in self.capabilities

    @property
    def vision(self) -> bool:
        return "vision" in self.capabilities

    @property
    def embedding_only(self) -> bool:
        return "embedding" in self.capabilities

    def fits(self, vram_gb: float, headroom: float = 0.85) -> bool:
        return self.est_gb <= vram_gb * headroom


@dataclass
class Entry:
    name: str
    description: str
    capabilities: List[str]
    sizes: List[str]
    pulls: int
    tags: int
    updated: str = ""

    @property
    def local(self) -> bool:
        """False for entries that exist only as hosted cloud models."""
        return bool(self.sizes) or "cloud" not in self.capabilities

    @property
    def chat_capable(self) -> bool:
        return "embedding" not in self.capabilities


def parse_size(size: str) -> float:
    """'3b' -> 3.0, '270m' -> 0.27, 'e4b' (effective 4b) -> 4.0, '30b-a3b' -> 30.0, unknown -> 0."""
    m = re.match(r"e?(\d+(?:\.\d+)?)([bm])", size.lower())
    if not m:
        return 0.0
    v = float(m.group(1))
    return v / 1000 if m.group(2) == "m" else v


def estimate_gb(params_b: float) -> float:
    if params_b <= 0:
        return 4.0  # unknown: assume a mid-size model
    return round(params_b * 0.6 + 0.35, 1)


_PICTOGRAPHS = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]")


def plain(text: str) -> str:
    """Upstream descriptions carry emoji. The arena shows none, so they are removed on the way in."""
    return re.sub(r"\s+", " ", _PICTOGRAPHS.sub("", text or "")).strip()


def _load() -> Dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


_cache: Optional[List[Entry]] = None
_meta: Dict = {}


def entries() -> List[Entry]:
    global _cache, _meta
    if _cache is None:
        data = _load()
        _meta = {k: v for k, v in data.items() if k != "models"}
        _cache = [Entry(**dict(m, description=plain(m.get("description", "")))) for m in data["models"]]
    return _cache


def meta() -> Dict:
    entries()
    return _meta


def get(family: str) -> Optional[Entry]:
    return next((e for e in entries() if e.name == family), None)


def variants(entry: Entry) -> List[Variant]:
    sizes = entry.sizes or ["latest"]
    out = []
    for s in sizes:
        p = parse_size(s)
        out.append(Variant(entry.name, s, f"{entry.name}:{s}", p, estimate_gb(p),
                           tuple(entry.capabilities), entry.description, entry.pulls))
    return out


def all_variants(local_only: bool = True, chat_only: bool = True) -> List[Variant]:
    out: List[Variant] = []
    for e in entries():
        if local_only and not e.local:
            continue
        if chat_only and not e.chat_capable:
            continue
        out.extend(variants(e))
    return out


def lookup(tag: str) -> Optional[Variant]:
    """Find the catalog variant for a tag such as 'qwen3:4b' (family names with no size match 'latest')."""
    fam, _, size = tag.partition(":")
    e = get(fam)
    if not e:
        return None
    for v in variants(e):
        if v.size == (size or "latest") or (not size and v.size == "latest"):
            return v
    # an installed tag like 'mistral:latest' or 'llama3.2:3b-instruct-q4' maps to the family
    return variants(e)[0] if size in ("latest", "") or size.startswith(tuple(v.size for v in variants(e))) else None


def is_thinking_model(tag: str) -> bool:
    fam = tag.split(":")[0]
    e = get(fam)
    return bool(e and "thinking" in e.capabilities)


def search(query: str = "", *, max_gb: Optional[float] = None, capability: str = "",
           local_only: bool = True, chat_only: bool = True) -> List[Variant]:
    q = query.lower().strip()
    out = []
    for v in all_variants(local_only, chat_only):
        if q and q not in v.tag.lower() and q not in v.description.lower():
            continue
        if max_gb is not None and v.est_gb > max_gb:
            continue
        if capability and capability not in v.capabilities:
            continue
        out.append(v)
    return sorted(out, key=lambda v: (-v.pulls, v.params_b))


def pool_for(vram_gb: float, *, avoid_thinking: bool = True, exclude: Iterable[str] = (),
             min_params_b: float = 0.5, max_gb: Optional[float] = None, limit: int = 60) -> List[Variant]:
    """Candidates for playing a mind: chat models that fit, one variant per family (the largest that fits),
    most popular families first. Vision and thinking variants are kept out of the default pool."""
    excluded = set(exclude)
    cap = max_gb if max_gb is not None else vram_gb * 0.85
    chosen: Dict[str, Variant] = {}
    for e in sorted(entries(), key=lambda e: -e.pulls):
        if not e.local or not e.chat_capable:
            continue
        if avoid_thinking and "thinking" in e.capabilities:
            continue
        fits = [v for v in variants(e) if v.est_gb <= cap and v.params_b >= min_params_b and v.tag not in excluded]
        if fits:
            chosen[e.name] = max(fits, key=lambda v: v.params_b)
        if len(chosen) >= limit:
            break
    return list(chosen.values())


# ------------------------------------------------------------------------------- refresh --
def _num(s: str) -> int:
    m = re.match(r"([\d.]+)([KMB]?)", s.strip().upper().replace(",", ""))
    if not m:
        return 0
    return int(float(m.group(1)) * {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}[m.group(2)])


def parse_library_html(page: str) -> List[Dict]:
    out = []
    for it in re.findall(r'<li\s+class="flex items-baseline.*?</li>', page, flags=re.S):
        name = re.search(r'href="/library/([^"]+)"', it)
        if not name:
            continue
        desc = re.search(r'<p class="max-w-lg[^>]*>(.*?)</p>', it, re.S)
        spans = [html.unescape(s.strip()) for s in re.findall(r'<span\s+class="inline-flex[^>]*>(.*?)</span>', it, re.S)]
        pulls = re.search(r'<span >([\d.,]+[KMB]?)</span>\s*<span class="hidden sm:flex">&nbsp;Pulls', it)
        tags = re.search(r'<span >(\d+)</span>\s*<span class="hidden sm:flex">&nbsp;Tags', it)
        upd = re.search(r'<span[^>]*>\s*(\d+ (?:day|week|month|year|hour)s? ago)\s*</span>', it)
        out.append({
            "name": name.group(1),
            "description": plain(html.unescape(re.sub(r"\s+", " ", desc.group(1)).strip())) if desc else "",
            "capabilities": [s.lower() for s in spans if s.lower() in _CAPS],
            "sizes": [s for s in spans if s.lower() not in _CAPS],
            "pulls": _num(pulls.group(1)) if pulls else 0,
            "tags": int(tags.group(1)) if tags else 0,
            "updated": upd.group(1) if upd else "",
        })
    return out


def refresh(timeout: int = 30) -> int:
    """Re-read the live Ollama library page and rewrite catalog_data.json. Returns the model count."""
    import datetime
    import requests
    r = requests.get(LIBRARY_URL, timeout=timeout, headers={"User-Agent": "undermind-catalog/1.0"})
    r.raise_for_status()
    models = parse_library_html(r.text)
    if len(models) < 50:
        raise RuntimeError(f"Parsed only {len(models)} models; the page layout may have changed. Catalog not overwritten.")
    DATA_FILE.write_text(json.dumps({"source": LIBRARY_URL, "fetched": datetime.date.today().isoformat(), "models": models},
                                    separators=(",", ":")), encoding="utf-8")
    global _cache
    _cache = None
    return len(models)


def to_markdown() -> str:
    es = [e for e in entries() if e.local and e.chat_capable]
    emb = [e for e in entries() if not e.chat_capable]
    nvar = sum(len(variants(e)) for e in es)
    L = ["# Model catalog", "",
         f"{len(es)} chat-capable local model families ({nvar} sized variants) from {meta().get('source')}, snapshot {meta().get('fetched')}.",
         "Sizes are approximate downloads for the default 4-bit builds. 'think' marks reasoning models (the arena turns their thinking off).",
         "Embedding-only models and hosted-cloud-only entries are excluded from the arena and listed at the bottom.", "",
         "| Model | Sizes (approx GB) | Capabilities | Pulls | What it is |", "|---|---|---|---|---|"]
    for e in sorted(es, key=lambda e: -e.pulls):
        sz = ", ".join(f"{v.size} ({v.est_gb:g})" for v in variants(e)) if e.sizes else "latest"
        caps = ", ".join("think" if c == "thinking" else c for c in e.capabilities if c != "cloud") or "chat"
        pulls = f"{e.pulls/1e6:.1f}M" if e.pulls >= 1e6 else (f"{e.pulls/1e3:.0f}K" if e.pulls >= 1e3 else str(e.pulls))
        desc = e.description.replace("|", "/")
        desc = desc if len(desc) <= 110 else desc[:107].rstrip() + "..."
        L.append(f"| `{e.name}` | {sz} | {caps} | {pulls} | {desc} |")
    L += ["", "## Excluded", "", "Embedding-only: " + ", ".join(f"`{e.name}`" for e in emb) + ".", ""]
    cloud = [e for e in entries() if not e.local]
    if cloud:
        L += ["Hosted cloud only: " + ", ".join(f"`{e.name}`" for e in cloud) + ".", ""]
    return "\n".join(L)
