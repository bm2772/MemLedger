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
