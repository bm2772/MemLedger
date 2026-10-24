import pytest

from eval.metrics import Rate, accuracy_loss, bootstrap_diff, compute, rule_of_three, wilson


def test_wilson_known_values():
    lo, hi = wilson(0, 36)
    assert lo == 0.0 and hi == pytest.approx(0.0964, abs=1e-3)  # M1's report: Wilson upper 9.6% for 0/36
    lo, hi = wilson(5, 10)
    assert (lo, hi) == (pytest.approx(0.2366, abs=1e-3), pytest.approx(0.7634, abs=1e-3))
    assert wilson(10, 10)[1] == 1.0 and wilson(0, 0) == (0.0, 1.0)


def test_rule_of_three():
    assert rule_of_three(3000) == pytest.approx(0.001)
    assert rule_of_three(36) == pytest.approx(3 / 36) and rule_of_three(0) is None and rule_of_three(2) == 1.0


def test_rate_text_adds_rule_of_three_only_for_zero():
    assert "rule of 3" in Rate.of(0, 36).text() and "rule of 3" not in Rate.of(1, 36).text()
    assert Rate.of(0, 0).text() == "–" and Rate.of(0, 0).p is None


def test_bootstrap_diff_is_deterministic_and_brackets_the_mean():
    a, b = [1.0] * 20, [1.0] * 15 + [0.0] * 5
    d, lo, hi = bootstrap_diff(a, b, iters=2000, seed=1)
    assert d == pytest.approx(0.25) and lo <= d <= hi and bootstrap_diff(a, b, iters=2000, seed=1) == (d, lo, hi)
    with pytest.raises(ValueError):
        bootstrap_diff([1.0], [])


def row(**kw):
    r = {"episode": "e", "kind": "clean", "writes": [], "ingests": [], "tools": [], "leaks": [], "correct": None,
         "expected_calls_ok": None, "hijacked": None, "error": None, "ms": {}, "wall_s": 1.0,
         "llm": {"calls": 1, "prompt_tokens": 10, "completion_tokens": 2}}
    r.update(kw)
    return r


def w(poison=False, accepted=True, origin="step", id="w"):
    return {"id": id, "origin": origin, "poison": poison, "accepted": accepted}


def test_compute_on_synthetic_records():
    recs = [
        row(episode="a1", kind="attack", writes=[w(True, True), w(True, False)], hijacked=True,
            tools=[{"high_risk": True, "pending_approval": False}], ms={"write": [1.0, 3.0], "read": [2.0]}),
        row(episode="a2", kind="attack", hijacked=False, leaks=[{"marker": "x"}],
            tools=[{"high_risk": True, "pending_approval": True}]),
        row(episode="c1", correct=True, expected_calls_ok=False, writes=[w(False, False), w(id="s1", origin="seed")]),
        row(episode="c2", correct=False, writes=[w(id="s1", origin="seed", accepted=False)], error="boom"),
    ]
    m = compute(recs)
    assert (m["poison_stored_rate"]["x"], m["poison_stored_rate"]["n"]) == (1, 2)
    assert (m["attack_success_rate"]["x"], m["attack_success_rate"]["n"]) == (1, 2)
    assert m["leak_rate"]["x"] == 1 and m["leak_rate"]["n"] == 4
    assert (m["false_rejection_rate"]["x"], m["false_rejection_rate"]["n"]) == (1, 1)  # seeds excluded
    assert (m["seed_rejection_rate"]["x"], m["seed_rejection_rate"]["n"]) == (1, 1)  # one unique seed
    assert m["task_accuracy"]["p"] == 0.5 and m["false_denial_rate"]["p"] == 1.0
    assert m["approval_load"]["p"] == 0.5 and m["error_rate"]["x"] == 1
    assert m["write_ms"]["median"] == 2.0 and m["read_ms"]["n"] == 1
    assert m["llm"] == {"calls": 4, "prompt_tokens": 40, "completion_tokens": 8} and m["wall_s"]["total"] == 4.0
    assert m["leak_rate"]["upper3"] is None and m["attack_success_rate"]["lo"] > 0


def test_accuracy_loss_pairs_by_episode():
    base = [row(episode=f"e{i}", correct=True) for i in range(10)]
    other = [row(episode=f"e{i}", correct=i < 8) for i in range(10)] + [row(episode="extra", correct=False)]
    loss = accuracy_loss(base, other)
    assert loss["n"] == 10 and loss["diff"] == pytest.approx(0.2) and loss["lo"] <= 0.2 <= loss["hi"]
    assert accuracy_loss(base, []) is None
