"""Model backends. A backend turns (system, user) into text, or reports failure.

There is deliberately no fallback text here. If a model cannot answer, the caller gets
ok=False and the mind stalls for that turn: the engine never invents a reply for it.
"""
from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


@dataclass
class Completion:
    text: str = ""
    ok: bool = True
    error: str = ""


def clean(text: str) -> str:
    """Strip reasoning blocks some models emit."""
    from arena.llm.parsing import scrub
    text = _THINK.sub("", scrub(text or ""))
    if "<think>" in text.lower():  # unterminated: model ran out of tokens while thinking
        text = text[: text.lower().index("<think>")]
    return text.strip()


class Backend:
    name = "base"

    def complete(self, system: str, user: str, *, kind: str = "", model: str = "",
                 max_tokens: int = 300, temperature: float = 0.9) -> Completion:
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - optional
        pass


def _thinks(model: str) -> bool:
    try:
        from arena.llm import catalog
        return catalog.is_thinking_model(model)
    except Exception:
        return False


class OllamaBackend(Backend):
    name = "ollama"

    def __init__(self, url: str = "http://localhost:11434", timeout: int = 180,
                 keep_alive: str = "10m", retries: int = 1, num_ctx: int = 4096):
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.keep_alive = keep_alive
        self.retries = retries
        self.num_ctx = num_ctx
        self._local = threading.local()

    def _session(self) -> requests.Session:
        if not hasattr(self._local, "s"):
            self._local.s = requests.Session()
        return self._local.s

    def complete(self, system, user, *, kind="", model="", max_tokens=300, temperature=0.9):
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"num_predict": max_tokens, "temperature": temperature, "num_ctx": self.num_ctx},
        }
        if _thinks(model):
            payload["think"] = False   # thinking models otherwise spend the whole budget before answering
        err = ""
        for _ in range(self.retries + 1):
            try:
                r = self._session().post(f"{self.url}/api/chat", json=payload, timeout=self.timeout)
                if r.status_code == 400 and "think" in r.text.lower() and "think" in payload:
                    payload.pop("think")   # this model does not know the flag; ask without it
                    continue
                if r.status_code != 200:
                    err = f"HTTP {r.status_code}: {r.text[:120]}"
                    continue
                text = clean(r.json().get("message", {}).get("content", ""))
                if text:
                    return Completion(text)
                err = "empty reply"
            except Exception as exc:  # network, timeout, bad JSON
                err = f"{type(exc).__name__}: {exc}"
        return Completion("", False, err)


class AnthropicBackend(Backend):
    name = "anthropic"

    def __init__(self, api_key_env: str = "ANTHROPIC_API_KEY", timeout: int = 120):
        key = os.getenv(api_key_env)
        if not key:
            raise ValueError(f"Missing API key: set {api_key_env}")
        from anthropic import Anthropic  # imported lazily so ollama users do not need it
        self.client = Anthropic(api_key=key, timeout=timeout)

    def complete(self, system, user, *, kind="", model="", max_tokens=300, temperature=0.9):
        try:
            msg = self.client.messages.create(
                model=model, max_tokens=max_tokens, temperature=min(temperature, 1.0),
                system=system, messages=[{"role": "user", "content": user}])
            text = clean("".join(b.text for b in msg.content if getattr(b, "type", "") == "text"))
            return Completion(text) if text else Completion("", False, "empty reply")
        except Exception as exc:
            return Completion("", False, f"{type(exc).__name__}: {exc}")


def make_backend(config: Dict[str, Any]) -> Backend:
    api = config.get("api", {})
    provider = api.get("provider", "ollama")
    if provider == "ollama":
        return OllamaBackend(api.get("ollama_url", "http://localhost:11434"),
                             timeout=int(api.get("timeout", 180)),
                             keep_alive=str(api.get("keep_alive", "10m")),
                             num_ctx=int(api.get("num_ctx", 4096)))
    if provider == "anthropic":
        return AnthropicBackend(api.get("api_key_env", "ANTHROPIC_API_KEY"))
    if provider == "mock":
        from arena.llm.mock import MockBackend
        return MockBackend(seed=int(config.get("seed", 0) or 0))
    raise ValueError(f"Unsupported provider: {provider}")
