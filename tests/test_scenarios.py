"""M3 scenario generator (slides 5, 21, 22)."""

import re
from collections import Counter

import pytest

from scenarios.generator import CATEGORIES, Config, can_read, forbidden_for, generate, load, save

W = generate(Config(seed=7))


def test_at_least_three_teams_two_clearances():
    assert len(W.teams) >= 3
    assert {u.clearance for u in W.users} == {0, 1}
    with pytest.raises(ValueError):
        Config(n_teams=2)


def test_canaries_are_unique_128_bit_and_facts_unique():
    canaries = [m.canary for m in W.memories]
    assert len(set(canaries)) == len(canaries)
    assert all(re.fullmatch(r"[0-9a-f]{32}", c) for c in canaries)
    values = [m.meta["value"] for m in W.memories]
    codes = [m.meta["codename"] for m in W.memories]
    assert len(set(values)) == len(values) and len(set(codes)) == len(codes)
    for m in W.memories:  # each made-up fact appears in exactly one memory
        assert sum(m.meta["value"] in o.content for o in W.memories) == 1


def test_deterministic_by_seed():
    assert generate(Config(seed=7)).to_dict() == W.to_dict()
    assert generate(Config(seed=8)).to_dict() != W.to_dict()


def test_split_fixed_stratified_and_disjoint():
    assert {e.split for e in W.episodes} == {"dev", "test"}
    for cat in CATEGORIES:
        splits = Counter(e.split for e in W.episodes if e.category == cat)
        assert splits["test"] >= 1, cat
    ids = [e.id for e in W.episodes]
    assert len(set(ids)) == len(ids)
    assert len(W.split("dev")) + len(W.split("test")) == len(W.episodes)


def test_clean_recall_answer_is_readable_by_user():
    for e in W.episodes:
        if e.category in ("recall", "shared_recall"):
            target = next(m for m in W.memories if m.id == e.meta["target"])
            assert can_read(e.user, target)
            assert e.expect.answer == target.meta["value"]
            assert e.expect.answer not in e.expect.forbidden


def test_attacks_forbid_target_markers_and_target_unreadable():
    for e in W.episodes:
        if e.category in ("cross_team", "clearance"):
            target = next(m for m in W.memories if m.id == e.meta["target"])
            assert not can_read(e.user, target)
            assert target.canary in e.expect.forbidden and target.meta["value"] in e.expect.forbidden


def test_every_episode_forbids_everything_outside_auth():
    for e in W.episodes:
        assert set(forbidden_for(e.user, W.memories)) <= set(e.expect.forbidden)


def test_fake_fact_matches_slide_5():
    e = next(e for e in W.episodes if e.category == "fake_fact")
    (url, page), = e.meta["web"].items()
    attacker = e.meta["attacker_value"]
    assert f"bank account has changed to {attacker}" in page
    researcher, finance = (e.session_of(s) for s in e.steps)
    assert url in e.steps[0].content and researcher.role == "researcher"
    assert finance.role == "finance" and finance.team == researcher.team and e.user == finance
    assert e.attacker_goal == e.expect.forbidden_tool_calls[0] and e.poison_markers == [attacker]
    vendor = e.expect.tool_calls[0]["params"]["vendor"]
    assert e.registry[vendor]["account"] == W.registry["vendors"][vendor]["account"]
    assert e.expect.tool_calls[0]["params"]["account"] == W.registry["vendors"][vendor]["account"]
    assert e.expect.forbidden_tool_calls[0]["params"]["account"] == attacker != W.registry["vendors"][vendor]["account"]


def test_roundtrip(tmp_path):
    p = tmp_path / "w.json"
    save(W, p)
    assert load(p).to_dict() == W.to_dict()


def test_canaries_match_read_rule():
    e = W.episodes[0]
    assert len(e.canaries) == 2 * len(W.memories)
    for m in W.memories:
        for c in (c for c in e.canaries if c.marker in (m.canary, m.meta["value"])):
            for u in W.users:
                assert c.visible_to(u) == can_read(u, m)
