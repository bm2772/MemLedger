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
