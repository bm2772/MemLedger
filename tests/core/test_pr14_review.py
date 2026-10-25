"""Regression tests for the PR #14 review (integration/v1 -> main): integrity and write-path findings."""

import pytest

from memledger.core.factory import build_service
from memledger.core.service import item_hash
from memledger.core.types import Session, SourceKind, Status, WriteProposal
from memledger.registry.registry import Registry

A = Session("a", "team_a", "researcher", 1)
B = Session("b", "team_b", "researcher", 1)


@pytest.fixture
def full(monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    return build_service("full", registry=Registry.from_mapping({}))


def remember(svc, text, session=A, kind=SourceKind.INTERNAL):
    s = svc.ingest(text, kind, session)
    res = svc.propose_write(WriteProposal(text, [s.id], session))
    assert res.accepted, res.verdicts
    return s, res.claim_ids[0]


def unlock(svc):
    conn = svc.store.conn
    for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall():
        conn.execute(f"DROP TRIGGER {name}")
    return conn


def test_forged_row_with_recomputed_hash_is_never_served_and_innocent_claims_survive(full):
    """Finding 1: a failed check used to re-anchor over the tampered state, so the forgery became 'verified'."""
    s1, x = remember(full, "The pump runs at 40 rpm.")
    _, y = remember(full, "The valve opens at 3 bar.")
    c = full.store.get_claim(x)
    forged = "The pump runs at 90 rpm."
    unlock(full).execute("UPDATE claims SET text=?, content_hash=? WHERE id=?",
                         (forged, item_hash(forged, c.recorded_at, [s1.content_hash], c.labels), x))
    assert full.verify_claim(y) and full.store.get_claim(y).status == Status.ACTIVE
    assert not full.verify_claim(x) and full.store.get_claim(x).status == Status.QUARANTINED
    assert forged not in [m.claim.text for m in full.retrieve("pump rpm", A)]
    # a later write re-signs, but only over items the service wrote: the forgery stays out
    remember(full, "The fan runs at 12 rpm.")
    assert not full.verify_claim(x)


def test_copied_row_under_a_new_id_is_not_anchored(full):
    _, x = remember(full, "The pump runs at 40 rpm.")
    conn = unlock(full)
    conn.execute("INSERT INTO claims SELECT 'c_copy', text, team, confidentiality, integrity, valid_from, valid_to, "
                 "recorded_at, content_hash FROM claims WHERE id=?", (x,))
    conn.execute("INSERT INTO derivations SELECT 'd_copy', 'c_copy', model, prompt_hash, agent_id, created_at "
                 "FROM derivations WHERE claim_id=?", (x,))
    assert not full.verify_claim("c_copy")


def test_parent_memory_from_another_team_is_refused(full):
    """Finding 2: claim parents bypassed the access check (only sources were checked)."""
    _, secret = remember(full, "Project Zorb secret: BLEU 41.7, marker 9f3a.")
    own = full.ingest("Weekly note: the team met on Monday.", SourceKind.INTERNAL, B)
    res = full.propose_write(WriteProposal("Weekly note: the team met on Monday.", [own.id, secret], B))
    assert not res.accepted and any(v.check == "access" for v in res.verdicts if not v.ok)


def test_parent_memory_from_another_team_is_refused_without_access_control(monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    svc = build_service("provenance")
    _, secret = remember(svc, "Project Zorb secret: BLEU 41.7.")
    own = svc.ingest("Weekly note.", SourceKind.INTERNAL, B)
    res = svc.propose_write(WriteProposal("Weekly note.", [own.id, secret], B))
    assert not res.accepted and res.verdicts[0].check == "team_scope"


def test_duplicate_context_ids_do_not_cause_a_false_tamper_alarm(full):
    """Finding 3: duplicates were hashed twice at write time but once on read."""
    s = full.ingest("The pump runs at 40 rpm.", SourceKind.INTERNAL, A)
    res = full.propose_write(WriteProposal("The pump runs at 40 rpm.", [s.id, s.id], A))
    assert res.accepted and full.verify_claim(res.claim_ids[0])


def test_unknown_context_ids_are_refused(full):
    s = full.ingest("The pump runs at 40 rpm.", SourceKind.INTERNAL, A)
    res = full.propose_write(WriteProposal("The pump runs at 40 rpm.", [s.id, "s_nope"], A))
    assert not res.accepted and "unknown context ids" in res.verdicts[0].reason


def test_claim_with_no_valid_justification_is_not_active(monkeypatch):
    """Finding 4: a claim derived only from a flagged source was ACTIVE with trust 0 and still retrieved."""
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    svc = build_service("provenance")
    s = svc.ingest("The pump runs at 40 rpm.", SourceKind.WEB, A)
    svc.flag_source(s.id, "bad")
    res = svc.propose_write(WriteProposal("The pump runs at 40 rpm.", [s.id], A))
    assert not res.accepted and svc.retrieve("pump", A) == []


def test_store_written_before_leaf_records_is_migrated(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    from memledger.store.sqlite import SQLiteStore
    path = str(tmp_path / "old.sqlite")
    svc = build_service("provenance", store=SQLiteStore(path))
    _, x = remember(svc, "The pump runs at 40 rpm.")
    unlock(svc).execute("DELETE FROM anchored")  # what a pre-fix database looks like
    svc.store.conn.commit()
    again = build_service("provenance", store=SQLiteStore(path))
    again.signing_key, again.public_key = svc.signing_key, svc.public_key
    assert again.verify_claim(x)


def test_leaf_inserted_into_anchored_is_never_signed_by_a_later_write():
    """PR #15 review (M1): a forged claim plus a matching `anchored` row must not be absorbed by the next root."""
    from memledger.core.service import IntegrityError, LedgerService, leaf_of
    from memledger.core.types import Claim, Derivation, Labels, now

    svc = LedgerService()
    s = svc.ingest("Acme account is 1234.", SourceKind.INTERNAL, A)
    svc.propose_write(WriteProposal("Acme account is 1234.", [s.id], A))
    t, lab = now(), Labels("team_a")
    forged = Claim("c_forged", "Acme account is 9999.", lab, trust=0.9, valid_from=t, recorded_at=t,
                   content_hash=item_hash("Acme account is 9999.", t, [s.content_hash], lab))
    svc.store.add_claim(forged)
    svc.store.add_derivation(Derivation("d_f", forged.id, [s.id], {s.id: 1.0}, created_at=t))
    svc.store.conn.execute("INSERT INTO anchored(item_id,leaf,seq) VALUES (?,?,1)",
                           (forged.id, leaf_of(forged.id, forged.content_hash)))
    svc.store.conn.commit()
    assert svc.verify_claim(forged.id) is False
    n = len(svc.store.hash_log())
    with pytest.raises(IntegrityError):
        svc.ingest("unrelated later page", SourceKind.WEB, A)
    assert len(svc.store.hash_log()) == n and svc.verify_claim(forged.id) is False
