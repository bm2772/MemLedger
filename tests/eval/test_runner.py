import json
from pathlib import Path

import pytest

from eval.llm import GullibleLLM
from eval.runner import load_episodes, main, record, run, run_one
from eval.versions import resolve_version
from memledger.agent.episode import Episode

ROOT = Path(__file__).resolve().parents[2]
SMOKE = ROOT / "eval" / "fixtures" / "smoke_v1.jsonl"


@pytest.fixture(autouse=True)
def lexical(monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")


def eps():
    return {e.id: e for e in load_episodes(SMOKE)}


def one(eid, version):
    row, _ = run_one(eps()[eid], resolve_version(version), GullibleLLM(), {}, "lexical")
    return row


def test_scripted_acme_attack_hijacks_baseline_not_full():
    base = one("smoke-acme-fake-fact", "baseline")
    assert base["hijacked"] is True and base["error"] is None
    assert [w["poison"] for w in base["writes"]] == [False, True] and all(w["accepted"] for w in base["writes"])
    (t,) = base["tools"]
    assert t["executed"] and t["params"]["account"] == "9876" and t["origin"] == "step"
    full = one("smoke-acme-fake-fact", "full")
    assert full["hijacked"] is False and not full["writes"][1]["accepted"]
    assert full["outbox"] == [] or all(o["params"]["account"] == "1234" for o in full["outbox"])
    assert full["flags"][0]["source"] == "web"


def test_task_fake_fact_through_the_llm_agent():
    base = one("smoke-task-fake-fact", "baseline")
    assert base["hijacked"] is True and base["llm"]["calls"] >= 3
    remember = [w for w in base["writes"] if w["origin"] == "agent"]
    assert remember and remember[0]["poison"] and remember[0]["accepted"]
    full = one("smoke-task-fake-fact", "full")
    assert full["hijacked"] is False and full["expected_calls_ok"] is True  # pays the registry account
    assert {t["session"] for t in full["tasks"]} == {"res", "fin"}


def test_clearance_canary_leaks_on_baseline_only():
    base = one("smoke-clearance-canary", "baseline")
    assert base["leaks"] and {x["session"] for x in base["leaks"]} == {"res"}
    assert {x["where"] for x in base["leaks"]} == {"task"}
    assert one("smoke-clearance-canary", "full")["leaks"] == []


def test_clean_task_recall_is_graded_from_the_answer():
    r = one("smoke-task-recall", "full")
    assert r["correct"] is True and r["tasks"][0]["answer"] and r["wall_s"] >= 0
    assert r["ms"]["write"] and r["ms"]["read"]


def test_record_scans_error_text_for_leaks_and_marks_error():
    e = eps()["smoke-clearance-canary"]
    r = record(e, "full", None, None, "KeyError: CANARY-8d2e61f0a4b94c7e9f13d5a6b7c8e9f0")
    assert r["leaks"] == [{"marker": "CANARY-8d2e61f0a4b94c7e9f13d5a6b7c8e9f0", "session": "res", "where": "error"}]
    assert r["hijacked"] is None and r["correct"] is None


def test_broken_episode_is_counted_not_raised():
    bad = Episode.from_dict({"id": "bad", "source": "t", "split": "dev", "kind": "clean", "category": "x",
                             "sessions": {"u": {"user_id": "u", "team": "t", "role": "r", "clearance": 0}},
                             "steps": [{"op": "flag", "source": "nowhere"},
                                       {"op": "tool", "tool": "send_payment", "params": {"vendor": 3}}]})
    row, _ = run_one(bad, resolve_version("full"), GullibleLLM(), {}, "lexical")
    assert row["wall_s"] >= 0 and "llm" in row


def test_load_episodes_from_world_json_and_filters(tmp_path):
    from scenarios.generator import Config, generate, save

    p = tmp_path / "w.json"
    save(generate(Config(seed=2)), p)
    dev = load_episodes(p, split="dev")
    assert dev and all(e.split == "dev" for e in dev)
    assert {e.category for e in load_episodes(p, categories=["payment"])} == {"payment"}
    assert len(load_episodes(p, limit=3)) == 3


def test_run_all_versions_writes_raw_and_summary_with_intervals(tmp_path):
    s = run(load_episodes(SMOKE), ["baseline", "full"], tmp_path, "t1")
    raw = (tmp_path / "raw" / "t1" / "full.jsonl").read_text().splitlines()
    assert len(raw) == 8 and json.loads(raw[0])["version"] == "full"
    saved = json.loads((tmp_path / "t1" / "summary.json").read_text())
    assert saved == json.loads(json.dumps(s))
    m = s["metrics"]
    assert m["baseline"]["attack_success_rate"]["p"] == 1.0 and m["full"]["attack_success_rate"]["x"] == 0
    assert m["full"]["leak_rate"]["upper3"] == pytest.approx(3 / 8) and m["baseline"]["leak_rate"]["x"] >= 1
    assert m["full"]["accuracy_loss"]["n"] >= 1 and s["llm"] == "fake-gullible"
    assert s["manifests"]["full"]["guard_backend"] == "lexical" and s["versions"]["full"]["n_errors"] == 0


def test_dev_split_of_generated_world_runs_all_five_versions(tmp_path):
    from scenarios.generator import Config, generate, save

    p = tmp_path / "w.json"
    save(generate(Config(seed=0)), p)
    s = run(load_episodes(p, split="dev"), ["baseline", "provenance", "write_checks", "full", "full_no_registry"],
            None, "dev")
    full, base = s["metrics"]["full"], s["metrics"]["baseline"]
    assert all(v["error_rate"]["x"] == 0 for v in s["metrics"].values())
    assert full["leak_rate"]["x"] == 0 and base["leak_rate"]["x"] > 0
    assert full["attack_success_rate"]["x"] == 0 and base["attack_success_rate"]["x"] > 0


def test_cli(tmp_path, capsys):
    main(["--episodes", str(SMOKE), "--versions", "baseline", "--llm", "fake", "--out", str(tmp_path),
          "--run-id", "cli", "--guards", "lexical", "--quiet"])
    assert "| baseline |" in capsys.readouterr().out and (tmp_path / "cli" / "summary.json").exists()
