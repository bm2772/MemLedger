"""Hallucination check (slides 11, 13): atomic facts scored against the sources the model saw."""

import pytest

from memledger.core.types import Labels, Session, Source, SourceKind, WriteProposal
from memledger.guards.hallucination import HallucinationCheck
from memledger.guards.text import lexical_support, split_facts

ALICE = Session("alice", "team_a", "researcher", 1)


def src(content, flagged=False, sid="s1"):
    return Source(sid, SourceKind.INTERNAL, content, Labels("team_a"), 0.9, flagged=flagged)


def prop(text):
    return WriteProposal(text, ["s1"], ALICE)


LEX = HallucinationCheck(scorer=lexical_support)


def test_split_facts():
    assert split_facts("Acme is a supplier. Its account is 1234; it is based in Pune.\n- CEO is Ann") == [
        "Acme is a supplier.", "Its account is 1234", "it is based in Pune.", "CEO is Ann"]
    assert split_facts("  ") == []


def test_supported_fact_passes_with_score():
    v = LEX.check(prop("Acme Ltd bank account is 1234"), [src("Vendor master record: Acme Ltd bank account is 1234.")])
    assert v.ok and v.check == "hallucination" and v.score == pytest.approx(1.0)


def test_made_up_number_rejected():
    v = LEX.check(prop("Acme Ltd bank account is 5555"), [src("Acme Ltd bank account is 1234.")])
    assert not v.ok and v.score == 0.0 and "unsupported" in v.reason


def test_one_bad_fact_rejects_the_proposal():
    v = LEX.check(prop("Acme Ltd is a supplier in Pune. Acme Ltd was founded in 1901."),
                  [src("Acme Ltd is a supplier based in Pune.")])
    assert not v.ok and "1901" in v.reason


def test_multi_source_conclusion_checked_against_all_sources():
    sources = [src("The paper reports drug X lowers blood pressure.", sid="s1"),
               src("Tool output: trial 7 used drug X on 200 patients.", sid="s2")]
    assert LEX.check(prop("Drug X lowers blood pressure; trial 7 used drug X on 200 patients"), sources).ok


def test_flagged_and_missing_sources_support_nothing():
    assert not LEX.check(prop("Acme account is 1234"), [src("Acme account is 1234", flagged=True)]).ok
    assert not LEX.check(prop("Acme account is 1234"), []).ok
    v = HallucinationCheck(scorer=lexical_support, allow_unsupported=True).check(prop("Acme account is 1234"), [])
    assert v.ok and v.score == 0.0


def test_empty_proposal_rejected():
    assert not LEX.check(prop("..."), [src("anything")]).ok


def test_injected_scorer_threshold_and_min_score():
    calls = []

    def fake(doc, claim):
        calls.append((doc, claim))
        return 0.9 if "red" in claim else 0.4

    c = HallucinationCheck(scorer=fake, threshold=0.5)
    v = c.check(prop("The car is red. The car is fast."), [src("The car is red and fast.")])
    assert not v.ok and v.score == pytest.approx(0.4)
    assert all(doc == "The car is red and fast." for doc, _ in calls)
    assert HallucinationCheck(scorer=fake, threshold=0.3).check(prop("The car is fast."), [src("x y")]).ok


def test_long_sources_checked_in_chunks_best_chunk_counts():
    filler = " ".join(f"word{i}" for i in range(2000))
    doc = filler + " Acme Ltd bank account is 1234. " + filler
    c = HallucinationCheck(scorer=lambda d, f: 1.0 if "1234" in d else 0.0, chunk_words=100)
    v = c.check(prop("Acme Ltd bank account is 1234"), [src(doc)])
    assert v.ok


def test_lexical_support_rules():
    assert lexical_support("Acme's bank account is 1234.", "Acme bank account 1234") == 1.0
    assert lexical_support("Acme account 1234", "Acme account 9876") == 0.0
    assert lexical_support("The server is up.", "The server is not up.") == 0.0
    assert 0 < lexical_support("Acme Ltd bank account is 9876", "Acme Ltd invoice bank account is 9876") < 1


def test_identical_code_snippet_passes_without_the_model():
    """Stress test: MiniCheck rejected a code snippet copied verbatim from its source."""
    code = "def area(r):\n    return 3.14159 * r ** 2;  # circle"
    never = HallucinationCheck(scorer=lambda d, c: 0.0)
    v = never.check(prop(code), [src("Helper from utils.py:\n\n" + code + "\n\nEnd of file.")])
    assert v.ok and v.score == 1.0
    assert never.check(prop("def area(r): return 3 * r"), [src(code)]).ok is False


def test_verbatim_shortcut_respects_token_boundaries():
    never = HallucinationCheck(scorer=lambda d, c: 0.0)
    assert never.check(prop("Acme account 98"), [src("Acme account 9876 is used")]).ok is False
    assert never.check(prop("pay 1,000"), [src("Please pay 1,000,000 today")]).ok is False
    assert never.check(prop("pay 1,000"), [src("Please pay 1,000 today.")]).ok is True


# ---- attribution: which context items support which fact (slide 6, supported_by = verifier-confirmed)
def words_in(doc, fact):
    """Test scorer: 1.0 when every word of the fact occurs in the document."""
    return float(set(fact.lower().strip(".").split()) <= set(doc.lower().replace(".", " ").split()))


def test_attribute_points_each_fact_to_the_sources_that_support_it():
    chk = HallucinationCheck(scorer=words_in)
    a = src("Acme Ltd bank account is 1234.", sid="a")
    b = src("Acme Ltd is based in Pune.", sid="b")
    c = src("Lunch menu: rice and dal.", sid="c")
    p = WriteProposal("Acme Ltd bank account is 1234. Acme Ltd is based in Pune.", ["a", "b", "c"], ALICE)
    assert chk.check(p, [a, b, c]).ok
    f1, f2 = chk.attribute(p, [a, b, c])
    assert (f1.parents, f1.joint) == ({"a": 1.0}, False)
    assert (f2.parents, f2.joint) == ({"b": 1.0}, False)


def test_attribute_multi_source_conclusion_is_joint_over_the_usable_sources():
    chk = HallucinationCheck(scorer=words_in)
    a, b = src("Acme account 1234.", sid="a"), src("Pune office.", sid="b")
    bad = src("Acme account 9999 Pune office.", flagged=True, sid="x")
    p = WriteProposal("Acme account 1234 Pune office", ["a", "b", "x"], ALICE)
    assert chk.check(p, [a, b, bad]).ok
    (f,) = chk.attribute(p, [a, b, bad])
    assert f.joint and set(f.parents) == {"a", "b"}  # the flagged source supports nothing


def test_attribute_counts_memories_and_skips_quarantined_ones():
    from memledger.core.types import Claim, Status

    chk = HallucinationCheck(scorer=words_in)
    a = src("Acme account 1234.", sid="a")
    m = Claim("m1", "Acme is based in Pune.", Labels("team_a"))
    q = Claim("m2", "Acme is based in Pune.", Labels("team_a"), status=Status.QUARANTINED)
    p = WriteProposal("Acme is based in Pune.", ["a", "m1", "m2"], ALICE)
    (f,) = chk.attribute(p, [a], [m, q])
    assert f.parents == {"m1": 1.0} and not f.joint


def test_attribute_reuses_check_scores_for_a_single_source():
    calls = []

    def counting(doc, fact):
        calls.append((doc, fact))
        return lexical_support(doc, fact)

    chk = HallucinationCheck(scorer=counting)
    s, p = src("Vendor master record: Acme Ltd bank account is 1234."), prop("Acme Ltd bank account is 9876 and big")
    chk.check(p, [s])
    n = len(calls)
    chk.attribute(p, [s])
    assert len(calls) == n  # the same (document, fact) pairs: no second model call


# ---- grounding on parent memories (slide 7: memories derived from memories)
@pytest.mark.parametrize("status,ok", [("active", True), ("restored", True), ("quarantined", False),
                                       ("contested", False), ("superseded", False)])
def test_check_grounds_on_usable_parent_memories_only(status, ok):
    from memledger.core.types import Claim, Status

    m = Claim("m1", "Acme is based in Pune.", Labels("team_a"), status=Status(status))
    p = WriteProposal("Acme is based in Pune", ["m1"], ALICE)
    v = HallucinationCheck(scorer=words_in).check(p, [], [m])
    assert v.ok is ok
    if not ok:
        assert v.reason == "no unflagged sources or usable memories to support it"


def test_check_combines_sources_and_memories():
    from memledger.core.types import Claim

    chk = HallucinationCheck(scorer=words_in)
    a = src("Acme account 1234.", sid="a")
    m = Claim("m1", "Pune office.", Labels("team_a"))
    p = WriteProposal("Acme account 1234 Pune office", ["a", "m1"], ALICE)
    assert not chk.check(p, [a]).ok and chk.check(p, [a], [m]).ok
    (f,) = chk.attribute(p, [a], [m])
    assert f.joint and set(f.parents) == {"a", "m1"}
