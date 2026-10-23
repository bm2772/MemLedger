"""End to end: scenario episodes through the agent on the plain-RAG mock (the baseline version)."""

import re

from memledger.agent import FakeLLM, LLMResponse, ToolCall
from memledger.agent.runner import leaks, run_episode, tool_call_matches
from memledger.core.mock import MockMemoryService
from scenarios.generator import Config, generate

W = generate(Config(seed=3))


def first(cat):
    return next(e for e in W.episodes if e.category == cat)


def gullible_agent(messages, tools):
    """Does what a fooled model would: remembers what it reads, pays the last account number it saw, and repeats
    every memory it was shown."""
    last = messages[-1]
    task = messages[1]["content"]
    if last["role"] == "tool":
        if "<data" in last["content"]:
            sentence = re.search(r"Note: [^<]*", last["content"]).group(0).strip()
            return LLMResponse("", [ToolCall("remember", {"text": sentence})])
        return LLMResponse("done")
    if task.startswith("Read "):
        return LLMResponse("", [ToolCall("read_web", {"url": re.search(r"https://\S+", task).group(0)})])
    if "pay" in task.lower():
        vendor = re.search(r"pay (.+?)'s", task).group(1)
        accounts = re.findall(r"account has changed to (\d+)", task)
        return LLMResponse("", [ToolCall("send_payment", {"vendor": vendor, "amount": 1, "account": accounts[-1]
                                                          if accounts else "unknown"})])
    return LLMResponse(task)  # echo the prompt, including all retrieved memories


def registry(world):
    return lambda vendor, f: world.registry["vendors"].get(vendor, {}).get(f)


def test_fake_fact_hijacks_baseline_payment():
    e = first("fake_fact")
    res = run_episode(e, MockMemoryService(), FakeLLM(gullible_agent))
    assert any(tool_call_matches(x, e.expect.forbidden_tool_calls[0]) for x in res.outbox)


def test_registry_binding_defeats_fake_fact():
    e = first("fake_fact")
    res = run_episode(e, MockMemoryService(), FakeLLM(gullible_agent), registry_lookup=registry(W))
    assert res.outbox and all(tool_call_matches(x, e.expect.tool_calls[0]) for x in res.outbox)
    assert not any(tool_call_matches(x, e.expect.forbidden_tool_calls[0]) for x in res.outbox)


def test_clean_recall_and_payment_succeed():
    e = first("recall")
    res = run_episode(e, MockMemoryService(), FakeLLM(gullible_agent))
    assert e.expect.answer in res.runs["t0"].answer
    e = first("payment")
    res = run_episode(e, MockMemoryService(), FakeLLM(gullible_agent), registry_lookup=registry(W))
    assert tool_call_matches(res.outbox[0], e.expect.tool_calls[0])


def test_cross_team_isolation_holds_on_mock():
    """Team scoping holds on the mock; the only leaks are the user's own team's confidential memories."""
    owner = {s: m for m in W.memories for s in (m.canary, m.meta["value"])}
    for e in (x for x in W.episodes if x.category == "cross_team"):
        res = run_episode(e, MockMemoryService(), FakeLLM(gullible_agent))
        for marker in leaks(res.visible_text(), e.expect.forbidden):
            m = owner[marker]
            assert m.team == e.user.team and m.confidentiality > e.user.clearance, e.id


def test_leak_oracle_catches_clearance_leak_on_mock():
    """The mock ignores confidentiality, so the clearance attack must be detected as a leak (baseline finding)."""
    e = first("clearance")
    res = run_episode(e, MockMemoryService(), FakeLLM(gullible_agent))
    target = next(m for m in W.memories if m.id == e.meta["target"])
    assert target.canary in leaks(res.visible_text(), e.expect.forbidden)
