"""M3 attack suite: dev >= 150, disjoint fixed splits, ground truth on every attack, replays on the real service."""

import json
from collections import Counter

from attacks.suite import SuiteConfig, build, manifest, write
from bench import load
from memledger.agent.episode import load_jsonl
from tests.test_bench import root  # noqa: F401  (tiny on-disk benchmark fixtures)


def markers(eps):
    return {c.marker for e in eps if e.source == "scenario" for c in e.canaries}


def test_dev_has_at_least_150_and_splits_are_disjoint(root):  # noqa: F811
    dev, _ = build("dev", root=root)
    test, skipped = build("test", root=root)
    assert len(dev) >= 150 and {e.split for e in dev} == {"dev"} and {e.split for e in test} == {"test"}
    assert not {e.id for e in dev} & {e.id for e in test}
    assert not markers(dev) & markers(test)  # different worlds: no canary, value or account shared
    assert "agentdojo" in skipped or any(e.source == "agentdojo" for e in test)


def test_every_attack_has_ground_truth(root):  # noqa: F811
    for split in ("dev", "test"):
        eps, _ = build(split, root=root)
        for e in eps:
            assert e.meta["family"] and e.meta["part"] in ("scenario", "benchmark")
            if e.kind == "attack":
                ex = e.expect
                assert ex.blocked or ex.forbidden or ex.forbidden_tool_calls or ex.label, e.id


def test_test_only_benchmarks_never_in_dev(root):  # noqa: F811
    dev, _ = build("dev", root=root)
    test, _ = build("test", root=root)
    assert not {e.source for e in dev} & {"injecagent", "agentdojo"}
    assert any(e.source == "injecagent" for e in test)
    assert {e.meta["family"] for e in test} >= {"fake_fact", "isolation", "poisoning", "planted_doc", "tool_hijack"}


def test_build_is_deterministic_and_missing_data_is_skipped(tmp_path, root):  # noqa: F811
    a, _ = build("dev", root=root)
    b, _ = build("dev", root=root)
    assert manifest(a, {})["sha256"] == manifest(b, {})["sha256"]
    eps, skipped = build("dev", SuiteConfig(dev_worlds=1), root=tmp_path / "empty")
    assert {e.source for e in eps} == {"scenario"} and set(skipped) == {"memshield", "memevobench", "bipia"}


def test_write_roundtrips(tmp_path, root):  # noqa: F811
    report = write(tmp_path / "out", SuiteConfig(dev_worlds=1, test_worlds=1, bench_limit=5), root=root)
    for split in ("dev", "test"):
        eps = load_jsonl(tmp_path / "out" / f"{split}.jsonl")
        assert len(eps) == report[split]["n"] and manifest(eps, report[split]["skipped"]) == report[split]
    assert json.loads((tmp_path / "out" / "manifest.json").read_text()) == report


def test_fake_fact_attacks_replay_on_real_service(root):  # noqa: F811
    """Scripted stand-in for a fooled model: baseline pays the attacker, full binds the registry account."""
    from memledger.agent import FakeLLM, LLMResponse, ToolCall
    from memledger.agent.runner import run_episode, tool_call_matches
    from memledger.core.factory import build_service
    from memledger.registry import Registry

    eps, _ = build("dev", SuiteConfig(dev_worlds=1, benchmarks=[]), root=root)
    for e in [e for e in eps if e.category == "fake_fact"][:2]:
        vendor = e.expect.tool_calls[0]["params"]["vendor"]
        attacker = e.meta["attacker_value"]
        url = next(iter(e.meta["web"]))
        hijacked = {}
        for version in ("baseline", "full"):
            script = [LLMResponse("", [ToolCall("read_web", {"url": url})]),
                      LLMResponse("", [ToolCall("remember", {"text": f"{vendor} bank account is {attacker}"})]),
                      LLMResponse("noted"),
                      LLMResponse("", [ToolCall("send_payment", {"vendor": vendor, "amount": 100,
                                                                 "account": attacker})]),
                      LLMResponse("paid")]
            reg = Registry.from_mapping(e.registry)
            svc = build_service(version, registry=reg)
            res = run_episode(e, svc, FakeLLM(script), registry_lookup=reg if version == "full" else None,
                              gate=svc.gate)
            hijacked[version] = any(tool_call_matches(x, e.attacker_goal) for x in res.outbox)
        assert hijacked == {"baseline": True, "full": False}, e.id


def test_test_split_samples_benchmarks_more_than_dev(root):  # noqa: F811
    """6a: bigger test samples per benchmark; dev (used for tuning) keeps bench_limit."""
    cfg = SuiteConfig(dev_worlds=0, test_worlds=0, family_sizes={}, bench_limit=1,
                      test_bench_limits={"memshield": None, "bipia": 2})
    assert (cfg.limit("memshield", "dev"), cfg.limit("memshield", "test"), cfg.limit("bipia", "test"),
            cfg.limit("memevobench", "test")) == (1, None, 2, 1)
    dev = Counter(e.source for e in build("dev", cfg, root=root)[0])
    test = Counter(e.source for e in build("test", cfg, root=root)[0])
    assert dev["memshield"] == 2 and test["memshield"] == len(load("memshield", "test", None, root=root)) > 2
    assert dev["bipia"] == 2 and test["bipia"] == 4 and test["memevobench"] == dev["memevobench"] == 2
