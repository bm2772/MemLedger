"""eval/mechanisms.py: clean-up recall / false quarantine on random graphs, conflict pairs (lexical checkers)."""

from eval.mechanisms import FREE_TEXT, _graph, _oracle, cleanup, conflict_pairs, conflicts


def test_cleanup_matches_the_independent_recomputation():
    c = cleanup(n_graphs=15, seed=1)
    assert c["recall"][0] == c["recall"][1] > 0 and c["false_quarantine"][0] == 0 < c["false_quarantine"][1]


def test_oracle_needs_one_clean_justification():
    import random

    g = {"sources": {"c0": False, "p0": True}, "mems": {"m0": [["p0"], ["c0"]], "m1": [["m0", "p0"]], "m2": [["p0"]]}}
    assert _oracle(g) == {"m0": True, "m1": False, "m2": False}
    assert set(_graph(random.Random(0), 2, 1, 5)["mems"]) == {f"m{i}" for i in range(5)}


def test_conflict_pairs_and_scoring():
    pairs = conflict_pairs(40, 0)
    assert len(pairs) == 40 + len(FREE_TEXT) and {k for *_, k in pairs} >= {"conflict", "restatement"}
    k = conflicts(40, 0)
    assert k["recall"][1] == 10 and 0 <= k["f1"] <= 1
