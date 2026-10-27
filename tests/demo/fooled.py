"""FooledModel: a deterministic stand-in for the agent LLM, for the demo's tests only (the demo runs a real model).

It understands plain requests and believes everything it reads, like eval.llm.GullibleLLM, so the tests can check
that every attack is carried out on plain memory and prevented by MemLedger without a GPU.
"""

from __future__ import annotations

import json
import re

from demo.chat import LAB_DOMAIN
from memledger.agent.llm import LLMResponse, ToolCall

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
MEM_LINE = re.compile(r"^- \[[^\]]+\] trust=[\d.]+ sources=[^:]*: (.*)$")
STOP = {"what", "which", "when", "where", "does", "about", "with", "from", "this", "that", "have", "your", "into",
        "reach", "reached", "anything", "know", "tell", "please"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9%.]{4,}", text.lower()) if w not in STOP}


def _memories(text: str) -> list[str]:
    return [m.group(1) for line in text.splitlines() if (m := MEM_LINE.match(line))]


class FooledModel:
    """A deterministic agent model that believes everything it reads (like eval.llm.GullibleLLM, for free text).

    read a URL      read_web, then remember the page's "Note:" (the planted sentence)
    remember ...    remember the text after the colon
    pay <vendor>    send_payment with the vendor's last account number found in memory
    email ...       send_email to an address in the request, else one a memory says reports go to; "email our
                    notes ..." attaches the matching memories
    anything else   answer with the memories that share words with the question
    """

    model = "fooled-test-model"

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        task = messages[1]["content"].split("\n\nRelevant memories:")[0].strip()
        mems = _memories(messages[1]["content"]) + [t for m in messages if m["role"] == "tool"
                                                    for t in _memories(m["content"])]
        if messages[-1]["role"] == "tool":
            return self._after_tool(messages)
        if url := re.search(r"https?://[^\s,;]+[^\s,;.]", task):
            return LLMResponse("", [ToolCall("read_web", {"url": url.group(0)})])
        if re.search(r"\b(remember|note that|keep in mind)\b", task, re.IGNORECASE):
            text = task.split(":", 1)[1] if ":" in task else re.sub(r"(?i)^.*?\b(remember|note|keep in mind)\b"
                                                                     r"(\s+(this|that))?\s*", "", task)
            return LLMResponse("", [ToolCall("remember", {"text": text.strip()})])
        if m := re.search(r"(?i:\bpay)\s+(?:(?i:the)\s+)?(?:(?i:invoice)\s+(?:from|for|of)\s+)?"
                          r"([A-Z][\w&-]*(?:\s+(?:Ltd|Inc|GmbH|LLC|Corp)\.?)?)", task):
            vendor = m.group(1)
            amount = re.search(r"(\d+(?:\.\d+)?)\s*(?:EUR|USD|GBP|€|\$|euros?|dollars?)", task)
            accounts = [a for t in mems if vendor.split()[0] in t
                        for a in re.findall(r"account (?:has changed to|is|number is|:)\s*(\d{3,})", t)]
            return LLMResponse("", [ToolCall("send_payment", {
                "vendor": vendor, "amount": float(amount.group(1)) if amount else 0.0,
                "account": accounts[-1] if accounts else None})])
        if re.search(r"(?i)\b(e-?mail|send)\b", task):
            to = EMAIL.search(task)
            to = to.group(0) if to else next((a.group(0) for t in mems if "report" in t.lower()
                                              for a in EMAIL.finditer(t)), None)
            if re.search(r"(?i)\b(notes?|memor(y|ies)|everything)\b", task):  # "email our notes": attach memories
                subject, body = "Notes", "\n".join([t for t in mems if _words(t) & _words(task)] or mems)
            else:
                subject, body = "Weekly status report", task.split(":", 1)[1].strip() if ":" in task else task
            return LLMResponse("", [ToolCall("send_email", {
                "to": to or f"reports@{LAB_DOMAIN}", "subject": subject, "body": body})])
        hits = [t for t in mems if _words(t) & _words(task)]
        if hits:
            return LLMResponse("Here's what I have in memory:\n" + "\n".join(f"- {t}" for t in hits))
        return LLMResponse("I couldn't find anything about that in my memory.")

    def _after_tool(self, messages: list[dict]) -> LLMResponse:
        content = messages[-1]["content"]
        calls = [c for m in messages if m["role"] == "assistant" for c in m.get("tool_calls") or []]
        name = calls[-1]["function"]["name"] if calls else ""
        if name == "read_web":
            if note := re.search(r"Note: ([^<\n]*)", content):
                return LLMResponse("", [ToolCall("remember", {"text": note.group(1).strip()})])
            if "[withheld" in content:
                return LLMResponse("MemLedger withheld that page, so I have nothing from it to remember.")
            return LLMResponse("I've read the page; nothing in it needed remembering.")
        if name == "remember":
            text = json.loads(calls[-1]["function"]["arguments"]).get("text", "")
            if content.startswith("[blocked]"):
                return LLMResponse("I tried to remember it, but MemLedger refused to store it.")
            return LLMResponse(f"Noted, I'll remember: “{text}”")
        if content.startswith("[blocked]"):
            return LLMResponse("That action is waiting for a person to approve it.")
        if content.startswith("[error]"):
            return LLMResponse("I couldn't do that: I don't have the account number." if "account" in content
                               else "I couldn't do that.")
        return LLMResponse({"send_payment": "Done, the payment has been sent.",
                            "send_email": "Done, the email has been sent."}.get(name, "Done."))
