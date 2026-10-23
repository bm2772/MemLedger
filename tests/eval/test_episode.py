import json
from pathlib import Path

import pytest

from eval.episode import Episode, load_episodes
from memledger.core.types import Session


def ep(**kw):
    d = {"id": "e1", "kind": "clean",
         "sessions": {"alice": {"user_id": "alice", "team": "team_a", "role": "researcher", "clearance": 1}},
         "steps": [{"op": "ingest", "session": "alice", "kind": "paper", "content": "x", "as": "s1"}]}
    d.update(kw)
    return d


def test_from_dict_builds_sessions_and_defaults():
    e = Episode.from_dict(ep())
    assert e.sessions["alice"] == Session("alice", "team_a", "researcher", 1)
    assert e.split == "dev" and e.attacker_goal is None and e.poison_markers == []


def test_unknown_op_and_session_rejected():
    with pytest.raises(ValueError, match="op"):
        Episode.from_dict(ep(steps=[{"op": "teleport", "session": "alice"}]))
    with pytest.raises(ValueError, match="session"):
        Episode.from_dict(ep(steps=[{"op": "retrieve", "session": "mallory", "query": "q"}]))
    with pytest.raises(ValueError, match="kind"):
        Episode.from_dict(ep(kind="maybe"))


def test_is_poison_uses_label_then_markers():
    e = Episode.from_dict(ep(kind="attack", poison_markers=["9876"]))
    assert e.is_poison({"poison": True}, "anything")
    assert not e.is_poison({"poison": False}, "account 9876")
    assert e.is_poison({}, "Acme account is 9876")
    assert not e.is_poison({}, "Acme account is 1234")


def test_load_jsonl_json_list_and_filters(tmp_path):
    rows = [ep(id="a", split="dev"), ep(id="b", split="test"), ep(id="c", split="dev")]
    p1 = tmp_path / "e.jsonl"
    p1.write_text("\n".join(json.dumps(r) for r in rows) + "\n\n")
    p2 = tmp_path / "e.json"
    p2.write_text(json.dumps(rows))
    assert [e.id for e in load_episodes(p1)] == ["a", "b", "c"]
    assert [e.id for e in load_episodes(p2, split="dev")] == ["a", "c"]
    assert [e.id for e in load_episodes(p1, split="dev", limit=1)] == ["a"]


def test_smoke_fixture_loads():
    eps = load_episodes(Path(__file__).resolve().parents[2] / "eval" / "fixtures" / "smoke.jsonl")
    assert {e.kind for e in eps} == {"attack", "clean"}
