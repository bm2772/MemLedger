import hashlib

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from memledger.core.merkle import merkle_proof, merkle_root, verify_proof
from memledger.core.mock import PRIORS
from memledger.core.service import LedgerService, item_hash, leaf_of
from memledger.core.types import Session, SourceKind, Status, Verdict, WriteProposal

ALICE = Session("alice", "a", "researcher", 1)
BOB = Session("bob", "b", "researcher", 1)


class FakeCheck:
    name = "fake"

    def __init__(self, ok=True, score=0.8):
        self.ok, self.score, self.seen = ok, score, []

    def check(self, proposal, sources):
        self.seen.append(sources)
        return Verdict(self.ok, self.score, "r", self.name)


@pytest.fixture
def svc():
    return LedgerService()


def write(svc, text, ctx, session=ALICE):
    res = svc.propose_write(WriteProposal(text, ctx, session, "ag"))
    assert res.accepted
    return res.claim_ids[0]


def test_ingest_hash_and_prior(svc):
    for kind in SourceKind:
        s = svc.ingest(f"x {kind}", kind, ALICE)
        assert s.prior_trust == PRIORS[kind] and s.id.startswith("s_")
        assert s.content_hash == item_hash(s.content, s.recorded_at, [], s.labels)
        assert svc.store.get_source(s.id).content_hash == s.content_hash


def test_hash_rule_deterministic_and_parent_sensitive(svc):
    s = svc.ingest("a", SourceKind.USER, ALICE)
    h1 = item_hash("t", s.recorded_at, ["aa", "bb"])
    assert h1 == item_hash("t", s.recorded_at, ["bb", "aa"])
    assert h1 != item_hash("t", s.recorded_at, ["aa", "cc"])
    expect = hashlib.sha256(b"t|" + s.recorded_at.isoformat().encode() + b"|aabb").hexdigest()
    assert h1 == expect


def test_exposed_to_equals_context_even_with_passing_check():
    chk = FakeCheck(ok=True, score=0.9)
    svc = LedgerService(checks=[chk])
    s1 = svc.ingest("one", SourceKind.USER, ALICE)
    s2 = svc.ingest("two", SourceKind.WEB, ALICE)
    cid = write(svc, "claim", [s1.id, s2.id])
    d = svc.store.derivations_for(cid)[0]
    assert d.exposed_to == [s1.id, s2.id]
    assert d.supported_by == {s1.id: 0.9, s2.id: 0.9}
    assert chk.seen[0][0].id == s1.id and chk.seen[0][1].id == s2.id


def test_failing_check_rejects_and_writes_nothing():
    svc = LedgerService(checks=[FakeCheck(ok=False)])
    s = svc.ingest("one", SourceKind.USER, ALICE)
    n = len(svc.store.hash_log())
    res = svc.propose_write(WriteProposal("c", [s.id], ALICE))
    assert not res.accepted and res.claim_ids == [] and not res.verdicts[0].ok
    assert svc.store.list_claims() == [] and len(svc.store.hash_log()) == n


def test_baseline_accepts_and_sets_times_and_trust(svc):
    s = svc.ingest("one", SourceKind.WEB, ALICE)
    cid = write(svc, "claim", [s.id])
    c = svc.store.get_claim(cid)
    assert c.valid_from is not None and c.valid_to is None and c.recorded_at
    assert c.trust == pytest.approx(0.3) and c.labels.team == "a" and cid.startswith("c_")
    assert svc.store.derivations_for(cid)[0].id.startswith("d_")
    c2 = svc.store.get_claim(write(svc, "no parents", []))
    assert c2.trust == PRIORS[SourceKind.AGENT]


def test_claim_hash_depends_on_parent_hash(svc):
    s = svc.ingest("one", SourceKind.USER, ALICE)
    c = svc.store.get_claim(write(svc, "claim", [s.id]))
    assert c.content_hash == item_hash(c.text, c.recorded_at, [s.content_hash], c.labels)
    assert c.content_hash != item_hash(c.text, c.recorded_at, ["00"])


def test_hash_log_grows_and_signatures_verify():
    key = Ed25519PrivateKey.generate()
    svc = LedgerService(signing_key=key)
    s = svc.ingest("one", SourceKind.USER, ALICE)
    assert len(svc.store.hash_log()) == 1
    write(svc, "claim", [s.id])
    log = svc.store.hash_log()
    assert [r["seq"] for r in log] == [1, 2] and log[1]["n_items"] == 2
    for r in log:
        key.public_key().verify(r["signature"], bytes.fromhex(r["root"]))


def test_anchor_root_matches_merkle(svc):
    s = svc.ingest("one", SourceKind.USER, ALICE)
    cid = write(svc, "claim", [s.id])
    leaves = [leaf_of(s.id, s.content_hash), leaf_of(cid, svc.store.get_claim(cid).content_hash)]
    root = svc.store.latest_root()["root"]
    assert root == merkle_root(leaves)
    assert verify_proof(leaves[1], merkle_proof(leaves, leaves[1]), root)


def test_explain_nested_lineage(svc):
    s = svc.ingest("one", SourceKind.USER, ALICE)
    c1 = write(svc, "first", [s.id])
    c2 = write(svc, "second", [c1])
    e = svc.explain(c2)
    assert e["claim"] == c2 and e["status"] == "active"
    node = e["lineage"][0]["exposed_to"][0]
    assert node["claim"] == c1
    src = node["lineage"][0]["exposed_to"][0]
    assert src["type"] == "source" and src["id"] == s.id and src["flagged"] is False


def test_flag_source_quarantines_dependents(svc):
    s1 = svc.ingest("bad", SourceKind.WEB, ALICE)
    s2 = svc.ingest("good", SourceKind.USER, ALICE)
    dep = write(svc, "dependent fact", [s1.id])
    other = write(svc, "other fact", [s2.id])
    out = svc.flag_source(s1.id, "poisoned")
    assert out == {"quarantined": [dep], "restored": [], "contested": []}
    assert svc.store.get_claim(dep).status.value == "quarantined"
    assert svc.store.get_source(s1.id).flagged
    assert svc.retrieve("dependent", ALICE) == []
    assert [m.claim.id for m in svc.retrieve("other fact", ALICE)] == [other]


def test_retrieve_team_scoping_and_shared(svc):
    write(svc, "alpha secret project", [], ALICE)
    write(svc, "shared project notes", [], Session("sys", "shared", "admin", 9))
    assert svc.retrieve("project", BOB)[0].claim.text == "shared project notes"
    assert len(svc.retrieve("project", BOB)) == 1
    assert len(svc.retrieve("project", ALICE)) == 2
    assert svc.retrieve("project", ALICE, k=1)[0].relevance > 0


def test_tamper_claim_text(svc):
    s = svc.ingest("one", SourceKind.USER, ALICE)
    cid = write(svc, "honest fact", [s.id])
    svc.store.conn.execute("DROP TRIGGER claims_no_update")
    svc.store.conn.execute("UPDATE claims SET text='evil' WHERE id=?", (cid,))
    assert svc.retrieve("honest fact evil", ALICE) == []
    assert svc.store.get_claim(cid).status.value == "quarantined"
    assert "integrity" in svc.store.status_history(cid)[-1]["reason"]


def test_tamper_parent_source(svc):
    s = svc.ingest("original", SourceKind.USER, ALICE)
    cid = write(svc, "derived fact", [s.id])
    svc.store.conn.execute("DROP TRIGGER sources_no_update")
    svc.store.conn.execute("UPDATE sources SET content='changed' WHERE id=?", (s.id,))
    assert svc.retrieve("derived fact", ALICE) == []
    assert svc.store.get_claim(cid).status.value == "quarantined"


def test_tamper_hash_log_gap(svc):
    s = svc.ingest("one", SourceKind.USER, ALICE)
    cid = write(svc, "fact", [s.id])
    assert svc.verify_claim(cid)
    svc.store.conn.execute("DROP TRIGGER hash_log_no_delete")
    svc.store.conn.execute("DELETE FROM hash_log WHERE seq=1")
    assert svc.verify_claim(cid) is False


def test_bad_signature_fails(svc):
    s = svc.ingest("one", SourceKind.USER, ALICE)
    cid = write(svc, "fact", [s.id])
    svc.public_key = Ed25519PrivateKey.generate().public_key()
    assert svc.verify_claim(cid) is False


def test_restored_claim_is_reanchored_and_retrievable(svc):
    """A claim the JTMS restores must be back in the latest signed root (else verify quarantines it for integrity)."""
    bad = svc.ingest("shared fact", SourceKind.WEB, ALICE)
    good = svc.ingest("shared fact", SourceKind.PAPER, ALICE)
    cid = write(svc, "shared fact", [bad.id])
    svc.flag_source(bad.id, "retracted")
    assert svc.retrieve("shared fact", ALICE) == []
    res = svc.add_justification(cid, [good.id], 0.9, "ag")
    assert res["restored"] == [cid]
    assert [m.claim.id for m in svc.retrieve("shared fact", ALICE)] == [cid]
    assert svc.store.get_claim(cid).status.value == "restored"


# ---- supported_by = the parents of the facts (attribution by the hallucination check), not the whole context
def attributing_service():
    from memledger.guards.hallucination import HallucinationCheck

    def words_in(doc, fact):
        return float(set(fact.lower().strip(".").split()) <= set(doc.lower().replace(".", " ").split()))

    return LedgerService(checks=[HallucinationCheck(scorer=words_in)])


def test_supported_by_holds_only_the_sources_of_the_facts():
    svc = attributing_service()
    acct = svc.ingest("Acme account is 1234.", SourceKind.INTERNAL, ALICE)
    menu = svc.ingest("Lunch menu: rice and dal.", SourceKind.WEB, ALICE)
    cid = write(svc, "Acme account is 1234.", [acct.id, menu.id])
    (d,) = svc.store.derivations_for(cid)
    assert d.exposed_to == [acct.id, menu.id] and list(d.supported_by) == [acct.id]
    assert [(f.fact, f.parents, f.joint) for f in d.facts] == [("Acme account is 1234.", {acct.id: 1.0}, False)]
    assert svc.explain(cid)["lineage"][0]["facts"] == [
        {"fact": "Acme account is 1234.", "parents": {acct.id: 1.0}, "joint": False}]


def contested_by_exposure(svc, cid):
    c = svc.store.get_claim(cid)
    return c.status == Status.CONTESTED and svc.store.status_history(cid)[-1]["reason"].startswith("exposure: ")


def test_exposed_only_memory_is_contested_with_trust_unchanged():
    svc = attributing_service()
    acct = svc.ingest("Acme account is 1234.", SourceKind.INTERNAL, ALICE)
    menu = svc.ingest("Lunch menu: rice and dal.", SourceKind.WEB, ALICE)
    cid = write(svc, "Acme account is 1234.", [acct.id, menu.id])
    before = svc.store.get_claim(cid).trust
    assert svc.flag_source(menu.id, "poisoned") == {"quarantined": [], "restored": [], "contested": [cid]}
    assert contested_by_exposure(svc, cid) and svc.store.get_claim(cid).trust == before
    assert svc.store.status_history(cid)[-1]["reason"] == f"exposure: flagged source {menu.id}"


def test_source_in_supported_by_still_quarantines():
    svc = attributing_service()
    acct = svc.ingest("Acme account is 1234.", SourceKind.INTERNAL, ALICE)
    menu = svc.ingest("Lunch menu: rice and dal.", SourceKind.WEB, ALICE)
    cid = write(svc, "Acme account is 1234.", [acct.id, menu.id])
    assert svc.flag_source(acct.id, "poisoned") == {"quarantined": [cid], "restored": [], "contested": []}
    assert svc.store.get_claim(cid).status == Status.QUARANTINED


def test_unflagging_restores_contested_and_quarantined_memories():
    svc = attributing_service()
    acct = svc.ingest("Acme account is 1234.", SourceKind.INTERNAL, ALICE)
    menu = svc.ingest("Lunch menu: rice and dal.", SourceKind.WEB, ALICE)
    cid = write(svc, "Acme account is 1234.", [acct.id, menu.id])
    svc.flag_source(menu.id, "poisoned")
    assert svc.unflag_source(menu.id, "false alarm") == {"quarantined": [], "restored": [cid], "contested": []}
    assert svc.store.get_claim(cid).status == Status.RESTORED
    svc.flag_source(acct.id, "poisoned")
    assert svc.unflag_source(acct.id, "false alarm")["restored"] == [cid]


def test_contradiction_contested_memory_is_not_restored_by_unflagging():
    svc = attributing_service()
    acct = svc.ingest("Acme account is 1234.", SourceKind.INTERNAL, ALICE)
    menu = svc.ingest("Lunch menu: rice and dal.", SourceKind.WEB, ALICE)
    cid = write(svc, "Acme account is 1234.", [acct.id, menu.id])
    svc.store.set_status(cid, Status.CONTESTED.value, "contradicted by higher-trust c_x")
    assert svc.flag_source(menu.id, "poisoned")["contested"] == []  # already contested, reason kept
    assert svc.unflag_source(menu.id, "false alarm")["restored"] == []
    assert svc.store.get_claim(cid).status == Status.CONTESTED


def test_memory_written_next_to_an_already_flagged_source_is_contested_at_birth():
    svc = attributing_service()
    acct = svc.ingest("Acme account is 1234.", SourceKind.INTERNAL, ALICE)
    menu = svc.ingest("Lunch menu: rice and dal.", SourceKind.WEB, ALICE)
    svc.flag_source(menu.id, "screened")
    cid = write(svc, "Acme account is 1234.", [acct.id, menu.id])
    assert contested_by_exposure(svc, cid)


def test_contest_spreads_down_the_chain_only_when_it_is_the_only_support():
    svc = attributing_service()
    pune = svc.ingest("Acme is based in Pune.", SourceKind.INTERNAL, ALICE)
    pune2 = svc.ingest("Acme is based in Pune and Mumbai.", SourceKind.INTERNAL, ALICE)
    menu = svc.ingest("Lunch menu: rice and dal.", SourceKind.WEB, ALICE)
    parent = write(svc, "Acme is based in Pune.", [pune.id, menu.id])
    only_via_parent = write(svc, "Acme is based in Pune", [parent])  # grounded on the memory alone
    also_clean = write(svc, "Acme is in Pune", [parent])
    write(svc, "Acme is in Pune", [pune2.id])  # a second, clean justification
    out = svc.flag_source(menu.id, "poisoned")
    assert out["contested"] == [parent, only_via_parent] and out["quarantined"] == []
    assert contested_by_exposure(svc, only_via_parent)
    assert svc.store.get_claim(also_clean).status == Status.ACTIVE
    assert svc.store.status_history(only_via_parent)[-1]["reason"] == f"exposure: rests on contested memory {parent}"
    assert set(svc.unflag_source(menu.id, "false alarm")["restored"]) == {parent, only_via_parent}


def test_gate_does_not_count_a_contested_memory_as_trusted_context():
    from memledger.core.factory import build_service

    svc = build_service("full_no_registry")
    reg = svc.ingest("Vendor master: Acme account is 1234.", SourceKind.REGISTRY, ALICE)
    menu = svc.ingest("Lunch menu: rice and dal.", SourceKind.INTERNAL, ALICE)
    cid = write(svc, "Acme account is 1234.", [reg.id, menu.id])
    pay = {"vendor": "Acme", "account": "1234", "amount": 10}
    assert svc.authorize("pay_invoice", pay, [cid], ALICE).ok
    svc.flag_source(menu.id, "poisoned")
    assert svc.store.get_claim(cid).status == Status.CONTESTED
    v = svc.authorize("pay_invoice", pay, [cid], ALICE)
    assert not v.ok and "contested" in v.reason


def test_memory_parents_are_attributed_and_retraction_follows_only_them():
    svc = attributing_service()
    pune = svc.ingest("Acme is based in Pune.", SourceKind.INTERNAL, ALICE)
    acct = svc.ingest("Acme account is 1234.", SourceKind.INTERNAL, ALICE)
    m_pune, m_acct = write(svc, "Acme is based in Pune.", [pune.id]), write(svc, "Acme account is 1234.", [acct.id])
    new = write(svc, "Acme is based in Pune", [pune.id, m_pune, m_acct])  # retrieved memories in the context
    (d,) = svc.store.derivations_for(new)
    assert list(d.supported_by) == [pune.id, m_pune]  # not the unrelated memory m_acct
    assert svc.flag_source(acct.id, "poisoned")["quarantined"] == [m_acct]
    assert svc.store.get_claim(new).status == Status.ACTIVE
    assert set(svc.flag_source(pune.id, "poisoned")["quarantined"]) == {m_pune, new}


def test_without_a_verifier_every_context_item_is_a_parent(svc):
    s1, s2 = svc.ingest("one", SourceKind.USER, ALICE), svc.ingest("two", SourceKind.WEB, ALICE)
    (d,) = svc.store.derivations_for(write(svc, "claim", [s1.id, s2.id]))
    assert list(d.supported_by) == [s1.id, s2.id] and d.facts == []


def test_memory_grounded_only_on_a_memory_is_accepted_and_retracted_with_it():
    svc = attributing_service()
    pune = svc.ingest("Acme is based in Pune.", SourceKind.INTERNAL, ALICE)
    parent = write(svc, "Acme is based in Pune.", [pune.id])
    child = write(svc, "Acme is based in Pune", [parent])  # no source in the context: grounded on the memory
    assert list(svc.store.derivations_for(child)[0].supported_by) == [parent]
    assert set(svc.flag_source(pune.id, "poisoned")["quarantined"]) == {parent, child}
    res = svc.propose_write(WriteProposal("Acme is in Pune", [parent], ALICE, "ag"))  # quarantined: grounds nothing
    assert not res.accepted


def test_checks_without_a_claims_parameter_still_work():
    chk = FakeCheck(ok=True, score=0.9)
    svc = LedgerService(checks=[chk])
    s1 = svc.ingest("one", SourceKind.USER, ALICE)
    c1 = write(svc, "claim", [s1.id])
    write(svc, "claim two", [s1.id, c1])
    assert [x.id for x in chk.seen[-1]] == [s1.id]  # sources only, as before


# ---- alternative supporters are OR (slide 6 D1; review of #17): one derivation per independent supporter
def test_d1_paper_and_web_copy_each_support_the_fact_flagging_the_copy_keeps_it():
    from memledger.core.factory import build_service

    svc = build_service("full_no_registry")
    paper = svc.ingest("Drug X lowers blood pressure in adults.", SourceKind.PAPER, ALICE)
    web = svc.ingest("Drug X lowers blood pressure in adults!", SourceKind.WEB, ALICE)
    cid = write(svc, "Drug X lowers blood pressure in adults", [paper.id, web.id])
    ders = svc.store.derivations_for(cid)
    assert sorted(list(d.supported_by) for d in ders) == sorted([[paper.id], [web.id]])
    t = {next(iter(d.supported_by)): svc.trust.derivation_trust(d) for d in ders}
    # independent origins: noisy-OR (was one AND-derivation: min parent trust 0.3 x s = 0.15)
    assert svc.store.get_claim(cid).trust == pytest.approx(1 - (1 - t[paper.id]) * (1 - t[web.id]))
    assert svc.store.get_claim(cid).trust > 0.5
    out = svc.flag_source(web.id, "planted copy")
    assert out == {"quarantined": [], "restored": [], "contested": []}  # supported by the paper alone: kept
    assert svc.store.get_claim(cid).status == Status.ACTIVE
    assert svc.store.get_claim(cid).trust == pytest.approx(t[paper.id])
    assert svc.flag_source(paper.id, "retracted")["quarantined"] == [cid]


def test_copies_of_one_page_count_as_one_supporter():
    svc = attributing_service()
    copies = [svc.ingest("Acme account is 1234.", SourceKind.WEB, ALICE) for _ in range(5)]
    cid = write(svc, "Acme account is 1234.", [c.id for c in copies])
    (d,) = svc.store.derivations_for(cid)
    assert set(d.supported_by) == {c.id for c in copies}
    one = attributing_service()
    s1 = one.ingest("Acme account is 1234.", SourceKind.WEB, ALICE)
    assert svc.store.get_claim(cid).trust == pytest.approx(one.store.get_claim(write(one, "Acme account is 1234.",
                                                                                     [s1.id])).trust)


def test_two_facts_with_alternative_supporters_hold_while_each_fact_keeps_one():
    svc = attributing_service()
    a1 = svc.ingest("Acme account is 1234.", SourceKind.INTERNAL, ALICE)
    a2 = svc.ingest("Note: Acme account is 1234 per finance.", SourceKind.USER, ALICE)
    b1 = svc.ingest("Acme is based in Pune.", SourceKind.INTERNAL, ALICE)
    cid = write(svc, "Acme account is 1234. Acme is based in Pune.", [a1.id, a2.id, b1.id])
    ders = svc.store.derivations_for(cid)
    assert sorted(sorted(d.supported_by) for d in ders) == sorted([sorted([a1.id, b1.id]), sorted([a2.id, b1.id])])
    assert len(ders[0].facts) == 2 and all(d.facts == [] for d in ders[1:])  # per-fact support stored once
    assert svc.flag_source(a1.id, "x")["quarantined"] == []  # fact 1 still has a2
    assert svc.flag_source(b1.id, "x")["quarantined"] == [cid]  # fact 2 had only b1


def test_joint_fact_still_needs_all_its_sources():
    svc = attributing_service()
    a = svc.ingest("Acme account 1234.", SourceKind.INTERNAL, ALICE)
    b = svc.ingest("Pune office.", SourceKind.INTERNAL, ALICE)
    cid = write(svc, "Acme account 1234 Pune office", [a.id, b.id])
    (d,) = svc.store.derivations_for(cid)
    assert set(d.supported_by) == {a.id, b.id} and d.facts[0].joint
    assert svc.flag_source(b.id, "x")["quarantined"] == [cid]


# ---- support must be well-founded (review of #17): a memory cannot hold itself up through a loop
def loop_service():
    from memledger.core.factory import build_service

    return build_service("full_no_registry")


def test_memory_restated_from_itself_is_still_retracted_with_its_source():
    svc = loop_service()
    web = svc.ingest("Vendor Globex ships within 2 days.", SourceKind.WEB, ALICE)
    m1 = write(svc, "Globex ships within 2 days", [web.id])
    assert write(svc, "Globex ships within 2 days", [m1]) == m1  # recall-then-remember: m1 now cites itself
    m2 = write(svc, "Globex delivers within 2 days", [m1])
    assert set(svc.flag_source(web.id, "poisoned")["quarantined"]) == {m1, m2}


def test_two_step_loop_is_still_retracted_with_its_source():
    svc = loop_service()
    web = svc.ingest("Vendor Globex ships within 2 days.", SourceKind.WEB, ALICE)
    m1 = write(svc, "Globex ships within 2 days", [web.id])
    m2 = write(svc, "Globex delivers within 2 days", [m1])
    assert write(svc, "Globex ships within 2 days", [m2]) == m1  # m1 re-stated from m2: m1 -> m2 -> m1
    assert set(svc.flag_source(web.id, "poisoned")["quarantined"]) == {m1, m2}


def test_a_loop_does_not_hide_an_independent_source():
    svc = loop_service()
    web = svc.ingest("Vendor Globex ships within 2 days.", SourceKind.WEB, ALICE)
    paper = svc.ingest("Audit: Globex ships within 2 days.", SourceKind.PAPER, ALICE)
    m1 = write(svc, "Globex ships within 2 days", [web.id])
    m2 = write(svc, "Globex delivers within 2 days", [m1])
    write(svc, "Globex ships within 2 days", [m2])  # loop m1 -> m2 -> m1
    write(svc, "Globex ships within 2 days", [paper.id])  # and a real second source for m1
    assert svc.flag_source(web.id, "poisoned")["quarantined"] == []
    assert svc.store.get_claim(m1).status == Status.ACTIVE and svc.store.get_claim(m2).status == Status.ACTIVE
    assert set(svc.flag_source(paper.id, "retracted")["quarantined"]) == {m1, m2}
