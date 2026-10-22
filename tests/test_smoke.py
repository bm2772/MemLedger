from memledger.core.mock import MockMemoryService
from memledger.core.types import Session, SourceKind, WriteProposal

ALICE = Session("alice", "team_a", "researcher", 1)
BOB = Session("bob", "team_b", "researcher", 1)


def test_write_then_retrieve_same_team():
    svc = MockMemoryService()
    src = svc.ingest("Acme bank account is 1234", SourceKind.INTERNAL, ALICE)
    res = svc.propose_write(WriteProposal("Acme account is 1234", [src.id], ALICE))
    assert res.accepted
    assert svc.retrieve("Acme account", ALICE)


def test_other_team_cannot_read():
    svc = MockMemoryService()
    svc.propose_write(WriteProposal("secret project codename falcon", [], ALICE))
    assert svc.retrieve("project codename", BOB) == []
