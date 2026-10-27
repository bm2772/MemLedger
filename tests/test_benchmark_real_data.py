"""Adapters on the real downloaded benchmarks (skipped where the data is absent: CI has none, see bench/download.py)."""

import json

import pytest

from bench import load
from bench.download import data_dir
from memledger.agent.episode import Episode

CASES = [("memshield", "dev"), ("memshield", "test"), ("memevobench", "dev"), ("memevobench", "test"),
         ("bipia", "dev"), ("bipia", "test"), ("injecagent", "test")]


@pytest.mark.parametrize(("name", "split"), CASES)
def test_real_records_adapt_to_valid_episodes(name, split):
    if not data_dir(name).exists():
        pytest.skip(f"{name} not downloaded")
    eps = load(name, split=split, limit=6)
    assert {e.kind for e in eps} == {"attack", "clean"}
    for e in eps:
        assert Episode.from_dict(json.loads(json.dumps(e.to_dict()))) == e
        assert any(s.op == "task" for s in e.steps) and e.meta["oracle"]["type"] in ("goal", "none")
        if e.kind == "attack":
            assert e.meta["oracle"]["type"] == "goal"
