"""Injectable LLM backends for the agent (slide 16: local 8-12B model via Ollama, larger one via vLLM on Brev).

`OpenAICompatLLM` talks to any OpenAI-compatible /v1/chat/completions endpoint (Ollama, vLLM) using only the standard
library. `FakeLLM` is deterministic and is what the tests use.
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ToolCall:
    name: str
    args: dict
    id: str = ""


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLM(Protocol):
    model: str

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


class FakeLLM:
    """Deterministic LLM for tests.

    `script` is either a list of responses returned in order (the last one repeats), or a function
    `(messages, tools) -> LLMResponse` for responses that depend on what the agent was shown.
    Every call's messages are kept in `self.calls` so tests can assert on the prompt.
    """

    model = "fake"

    def __init__(self, script: Sequence[LLMResponse] | Callable[[list[dict], list[dict]], LLMResponse]):
        self.script = script
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        self.calls.append([dict(m) for m in messages])
        if callable(self.script):
            return self.script(messages, tools)
        i = min(len(self.calls) - 1, len(self.script) - 1)
        return self.script[i]


class OpenAICompatLLM:
    """Client for OpenAI-compatible chat endpoints.

    Defaults point at local Ollama; set MEMLEDGER_LLM_URL / MEMLEDGER_LLM_MODEL / MEMLEDGER_LLM_KEY for vLLM on Brev.
    Temperature 0 and a fixed seed so runs are repeatable (needed for the I7 two-store comparison, slide 22).
    """

    def __init__(self, model: str | None = None, base_url: str | None = None, api_key: str | None = None,
                 temperature: float = 0.0, seed: int = 0, timeout: float = 120.0):
        self.model = model or os.environ.get("MEMLEDGER_LLM_MODEL", "llama3.1:8b")
        self.base_url = (base_url or os.environ.get("MEMLEDGER_LLM_URL", "http://localhost:11434/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("MEMLEDGER_LLM_KEY", "ollama")
        self.temperature = temperature
        self.seed = seed
        self.timeout = timeout

    def build_request(self, messages: list[dict], tools: list[dict]) -> dict:
        body: dict = {"model": self.model, "messages": messages, "temperature": self.temperature, "seed": self.seed}
        if tools:
            body["tools"] = tools
        return body

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(self.build_request(messages, tools)).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return parse_response(json.load(resp))


def parse_response(data: dict) -> LLMResponse:
    msg = data["choices"][0]["message"]
    calls = []
    for tc in msg.get("tool_calls") or []:
        fn = tc["function"]
        args = fn.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args) if args.strip() else {}
            except json.JSONDecodeError:
                args = {"_raw": args}
        calls.append(ToolCall(fn["name"], args, tc.get("id", "")))
    return LLMResponse(msg.get("content") or "", calls)
