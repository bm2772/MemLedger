import pytest

from memledger.core.service import LedgerService
from memledger.core.types import Derivation, Session, SourceKind, Status, Verdict, WriteProposal

ALICE = Session("alice", "a", "researcher", 1)


class Check:
    name = "fake"

    def __init__(self, score=0.9):
        self.score = score

    def check(self, proposal, sources):
        return Verdict(True, self.score, "", self.name)


def write(svc, text, ctx):
    res = svc.propose_write(WriteProposal(text, ctx, ALICE, "ag"))
    assert res.accepted
    return res.claim_ids[0]


def trust(svc, cid):
    return svc.store.get_claim(cid).trust


def test_slide7_worked_example():
    chk = Check(0.9)
    svc = LedgerService(checks=[chk])
    paper = svc.ingest("paper", SourceKind.PAPER, ALICE)
    tool = svc.ingest("tool output", SourceKind.INTERNAL, ALICE)
    user = svc.ingest("user note", SourceKind.USER, ALICE)
    c1 = write(svc, "Drug X inhibits Y", [paper.id, tool.id])
    assert trust(svc, c1) == pytest.approx(0.81)
    chk.score = 0.8
    c2 = write(svc, "Drug X inhibits Y", [user.id])
    assert c2 == c1 and len(svc.store.derivations_for(c1)) == 2
    ders = svc.store.derivations_for(c1)
    assert svc.trust.derivation_trust(ders[1]) == pytest.approx(0.56)
    assert trust(svc, c1) == pytest.approx(1 - 0.19 * 0.44)
    assert round(trust(svc, c1), 2) == 0.92
    assert svc.verify_claim(c1)  # merging keeps the hash tied to the first derivation
    out = svc.flag_source(paper.id, "retracted")
    assert out == {"quarantined": [], "restored": []}
    assert trust(svc, c1) == pytest.approx(0.56)
    assert svc.store.get_claim(c1).status != Status.QUARANTINED
    out = svc.flag_source(user.id, "bad")
    assert out["quarantined"] == [c1]
    assert svc.store.get_claim(c1).status == Status.QUARANTINED


def test_web_repetition_is_not_amplified():
    svc = LedgerService(checks=[Check(0.9)])
    web = svc.ingest("blog", SourceKind.WEB, ALICE)
    ids = {write(svc, "Fact Z", [web.id]) for _ in range(10)}
    assert len(ids) == 1
    assert trust(svc, ids.pop()) == pytest.approx(0.27)


def test_merge_ignores_case_and_whitespace_but_not_teams():
    svc = LedgerService()
    s = svc.ingest("x", SourceKind.USER, ALICE)
    a = write(svc, "Some Fact", [s.id])
    assert write(svc, "  some fact ", [s.id]) == a
    other = Session("bob", "b", "r", 1)
    res = svc.propose_write(WriteProposal("some fact", [], other))
    assert res.claim_ids[0] != a


def test_shared_origin_groups_by_max():
    svc = LedgerService(checks=[Check(0.9)])
    paper = svc.ingest("p", SourceKind.PAPER, ALICE)
    user = svc.ingest("u", SourceKind.USER, ALICE)
    tool = svc.ingest("t", SourceKind.INTERNAL, ALICE)
    c = write(svc, "F", [paper.id, user.id])  # 0.9 * 0.7 = 0.63
    write(svc, "F", [paper.id, tool.id])  # 0.9 * 0.9 = 0.81, shares the paper origin
    assert trust(svc, c) == pytest.approx(0.81)  # max, not noisy-OR (which would give 0.93)


def test_downstream_retraction_and_reasons():
    svc = LedgerService()
    s = svc.ingest("bad", SourceKind.WEB, ALICE)
    a = write(svc, "claim a", [s.id])
    b = write(svc, "claim b", [a])
    out = svc.flag_source(s.id, "poison")
    assert out["quarantined"] == [a, b]
    for cid in (a, b):
        assert svc.store.status_history(cid)[-1]["reason"].startswith("jtms")
    assert svc.retrieve("claim", ALICE) == []


def test_restore_only_for_jtms_quarantine():
    svc = LedgerService()
    s1 = svc.ingest("bad", SourceKind.WEB, ALICE)
    s2 = svc.ingest("good", SourceKind.PAPER, ALICE)
    a = write(svc, "claim a", [s1.id])
    b = write(svc, "claim b", [s1.id])
    svc.flag_source(s1.id, "poison")
    svc.store.set_status(b, "active", "manual test setup")
    svc.store.set_status(b, "quarantined", "integrity: hash mismatch")
    for cid in (a, b):
        svc.store.add_derivation(Derivation(f"d_new_{cid}", cid, [s2.id], {s2.id: 0.9}))
    res = svc.trust.recompute()
    assert res["restored"] == [a]
    assert svc.store.get_claim(a).status == Status.RESTORED
    assert trust(svc, a) == pytest.approx(0.9 * 0.95)
    assert svc.store.get_claim(b).status == Status.QUARANTINED


def test_contradiction_lower_trust_contested():
    svc = LedgerService()
    hi = svc.ingest("p", SourceKind.PAPER, ALICE)
    lo = svc.ingest("w", SourceKind.WEB, ALICE)
    a = write(svc, "water boils at 100", [hi.id])
    b = write(svc, "water boils at 90", [lo.id])
    svc.record_contradiction(a, b)
    assert svc.store.get_claim(b).status == Status.CONTESTED
    assert svc.store.get_claim(a).status == Status.ACTIVE
    assert svc.store.edges(type="contradicts")
    assert svc.store.status_history(b)[-1]["reason"] == f"contradicted by higher-trust {a}"


def test_contradiction_equal_trust_no_change():
    svc = LedgerService()
    s = svc.ingest("p", SourceKind.PAPER, ALICE)
    a, b = write(svc, "x is 1", [s.id]), write(svc, "x is 2", [s.id])
    svc.record_contradiction(a, b)
    assert {svc.store.get_claim(a).status, svc.store.get_claim(b).status} == {Status.ACTIVE}


def test_update_supersedes_older():
    svc = LedgerService()
    s = svc.ingest("p", SourceKind.PAPER, ALICE)
    old = write(svc, "the budget is 5 million", [s.id])
    new = write(svc, "the budget is 6 million", [s.id])
    svc.record_contradiction(new, old, is_update=True)
    assert svc.store.get_claim(old).status == Status.SUPERSEDED
    assert svc.store.edges(src=new, dst=old, type="supersedes")
    assert [m.claim.id for m in svc.retrieve("budget million", ALICE)] == [new]
