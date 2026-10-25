import hashlib

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from memledger.core.merkle import merkle_proof, merkle_root, verify_proof
from memledger.core.mock import PRIORS
from memledger.core.service import LedgerService, item_hash
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
    hashes = [s.content_hash, svc.store.get_claim(cid).content_hash]
    root = svc.store.latest_root()["root"]
    assert root == merkle_root(hashes)
    assert verify_proof(hashes[1], merkle_proof(hashes, hashes[1]), root)


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
    assert out == {"quarantined": [dep], "restored": []}
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


def test_flagging_an_unrelated_context_source_no_longer_retracts():
    svc = attributing_service()
    acct = svc.ingest("Acme account is 1234.", SourceKind.INTERNAL, ALICE)
    menu = svc.ingest("Lunch menu: rice and dal.", SourceKind.WEB, ALICE)
    cid = write(svc, "Acme account is 1234.", [acct.id, menu.id])
    assert svc.flag_source(menu.id, "poisoned")["quarantined"] == []
    assert svc.store.get_claim(cid).status == Status.ACTIVE
    assert svc.flag_source(acct.id, "poisoned")["quarantined"] == [cid]


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
