from pathlib import Path

import pytest

from eval.report import CLAIMS, main, render
from eval.runner import load_episodes, run

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("node", [ev[1] for _, _, ev in CLAIMS if ev[0] == "test"])
def test_every_claimed_test_exists(node):
    path, name = node.split("::")
    assert f"def {name}(" in (ROOT / path).read_text(), node


@pytest.fixture
def summary(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    return run(load_episodes(ROOT / "eval/fixtures/smoke_v1.jsonl"), ["baseline", "full"], tmp_path, "rep")


def test_render_has_intervals_rule_of_three_and_preliminary_banner(summary):
    md = render(summary)
    assert "PRELIMINARY" in md and "| full |" in md and "rule of 3" in md
    assert "| 18 | Leak rate 0 on the full system |" in md and "| met |" in md
    assert "Accuracy loss vs baseline" in md and "Not measured yet" in md


def test_cli_writes_file(summary, tmp_path):
    out = tmp_path / "results.md"
    main([str(tmp_path / "rep" / "summary.json"), "--out", str(out)])
    assert out.read_text().startswith("# MemLedger results")


def test_multi_worker_latency_is_omitted_or_taken_from_the_latency_run(summary):
    par = dict(summary, latency_valid=False, workers=16)
    md = render(par)
    assert "n/a, run `rep` played 16 episodes in parallel" in md and "| n/a | n/a |" in md
    lat = dict(summary, run_id="lat", workers=1)
    lat["metrics"] = {v: dict(x, write_ms={"median": 7.5, "p95": 9.0, "n": 3}) for v, x in summary["metrics"].items()}
    md = render(par, lat)
    assert "from run `lat` (1 worker" in md and "7.5 / 9.0" in md and "n/a" not in md.split("## Slide claims")[0]
