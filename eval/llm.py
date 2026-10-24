"""LLM backends for eval runs (slide 16): a token-metered OpenAI-compatible client and an offline fooled model.

MeteredLLM talks to Ollama (local) or vLLM (Brev) like memledger.agent.llm.OpenAICompatLLM, and also counts calls and
tokens from each response's `usage` so results can report tokens next to dollars (infra/cost_logger.py).
For qwen3 it switches thinking off: with thinking on every call is ~30x slower (docs/testing/local_run_2026-10-23.md).

GullibleLLM is a deterministic stand-in for offline runs and tests: it reads every page it is told to, remembers the
"Note:" in it, pays the last account number it saw, and answers by echoing the memories it was shown. It is fooled
by everything, so differences between versions come only from the memory layer. For the benchmark adapters it also
follows instructions found in tool outputs and retrieved memories (attacks/gullible.py).
"""

from __future__ import annotations

import json
import re
import urllib.request

from attacks.gullible import respond as benchmark_response
from infra.cost_logger import TokenMeter
from memledger.agent.llm import LLMResponse, OpenAICompatLLM, ToolCall, parse_response


def is_ollama(base_url: str) -> bool:
    return ":11434" in base_url


class MeteredLLM(OpenAICompatLLM):
    def __init__(self, *args, think: bool | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.think = think if think is not None else "qwen3" not in self.model.lower()
        self.meter = TokenMeter()

    def build_request(self, messages: list[dict], tools: list[dict]) -> dict:
        body = super().build_request(messages, tools)
        if not self.think:
            if is_ollama(self.base_url):
                body.update({"think": False, "reasoning_effort": "none"})
            else:  # vLLM: qwen3's chat template switch
                body["chat_template_kwargs"] = {"enable_thinking": False}
        return body

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(self.build_request(messages, tools)).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.load(resp)
        self.meter.add(data)
        return parse_response(data)


class GullibleLLM:
    model = "fake-gullible"

    def __init__(self) -> None:
        self.meter = TokenMeter()

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        self.meter.add({})
        last, task = messages[-1], messages[1]["content"]
        if (resp := benchmark_response(messages, tools)) is not None:  # benchmark episodes: follows injected text
            return resp
        if last["role"] == "tool":
            if "<data" in last["content"] and (m := re.search(r"Note: [^<]*", last["content"])):
                return LLMResponse("", [ToolCall("remember", {"text": m.group(0).strip()})])
            return LLMResponse("done")
        if task.startswith("Read ") and (url := re.search(r"https?://\S+", task)):
            return LLMResponse("", [ToolCall("read_web", {"url": url.group(0)})])
        if m := re.search(r"[Pp]ay (.+?)'s", task):
            accounts = re.findall(r"account (?:has changed to|is) (\d+)", task)
            return LLMResponse("", [ToolCall("send_payment", {"vendor": m.group(1), "amount": 1,
                                                              "account": accounts[-1] if accounts else "unknown"})])
        return LLMResponse(task)  # "answers" with the task and every memory it was shown
