import math
from datetime import timedelta

from memledger.core.service import LedgerService
from memledger.core.types import Claim, Labels, Session, SourceKind, Status, WriteProposal, now
from memledger.retrieval import HashEmbedder, Retriever
from memledger.store import InMemoryIndex

ALICE = Session("alice", "a", "r", 1)
BOB = Session("bob", "b", "r", 1)
SYS = Session("sys", "shared", "admin", 9)


def write(svc, text, ctx=(), session=ALICE):
    res = svc.propose_write(WriteProposal(text, list(ctx), session))
    return res.claim_ids[0]


def ids(res):
    return [m.claim.id for m in res]


def raw_claim(svc, cid, text, trust=0.5, valid_to=None, team="a"):
    t = now()
    svc.store.add_claim(Claim(cid, text, Labels(team), trust, Status.ACTIVE, t, valid_to, t, "h"))
    svc.index.add(team, cid, text)


def test_hash_embedder_deterministic_and_normalized():
    e = HashEmbedder(64)
    a, b = e(["Hello brave new world"]), e(["Hello brave new world"])
    assert a == b and len(a[0]) == 64
    assert math.isclose(sum(x * x for x in a[0]), 1.0)
    assert e([""])[0] == [0.0] * 64
    assert e(["hello"])[0] != e(["goodbye"])[0]


def test_embedding_index_cosine():
    ix = InMemoryIndex(embed=HashEmbedder())
    ix.add("a", "1", "cat sat mat")
    ix.add("a", "2", "dog barks")
    res = ix.query(["a"], "cat")
    assert res[0][0] == "1" and 0 < res[0][1] <= 1.0 and "2" not in [i for i, _ in res]


def test_team_isolation_with_shared():
    svc = LedgerService()
    mine = write(svc, "project alpha plan")
    shared = write(svc, "project alpha public", session=SYS)
    write(svc, "project alpha bob only", session=BOB)
    assert set(ids(Retriever(svc.store, svc.index).search("project alpha", ALICE))) == {mine, shared}


def test_keyword_route_finds_what_dense_misses():
    svc = LedgerService(index=InMemoryIndex(embed=HashEmbedder()))
    cid = write(svc, "the server restarts nightly")
    assert svc.index.query(["a"], "restart") == []  # different word form: no embedding overlap
    assert ids(Retriever(svc.store, svc.index).search("restart", ALICE)) == [cid]


def test_exact_triple_route():
    svc = LedgerService()
    cid = write(svc, "unrelated words entirely")
    svc.add_triple(cid, "Project X", "budget", "5M")
    res = Retriever(svc.store, svc.index).search("tell me about PROJECT X please", ALICE)
    assert ids(res) == [cid] and res[0].relevance == 1.0
    assert Retriever(svc.store, svc.index).search("tell me about project y", ALICE) == []


def test_one_hop_pulls_parent():
    svc = LedgerService()
    parent = write(svc, "orbital insertion burn schedule")
    child = write(svc, "zebra stripes", [parent])
    res = Retriever(svc.store, svc.index).search("zebra", ALICE)
    assert ids(res) == [child, parent]
    assert math.isclose(res[1].relevance, res[0].relevance * 0.5)
    # and the other direction: a child is found from its parent
    res = Retriever(svc.store, svc.index).search("orbital", ALICE)
    assert set(ids(res)) == {parent, child}


def test_newer_version_pulled_in():
    svc = LedgerService()
    old = write(svc, "launch date is monday")
    new = write(svc, "schedule moved to friday")
    svc.record_contradiction(new, old, is_update=True)
    assert ids(Retriever(svc.store, svc.index).search("launch monday", ALICE)) == [new]


def test_stage2_filters():
    svc = LedgerService()
    ok = write(svc, "widget fact ok")
    q = write(svc, "widget fact quarantined")
    sup = write(svc, "widget fact superseded")
    svc.store.set_status(q, "quarantined", "integrity: x")
    svc.store.set_status(sup, "superseded", "superseded by z")
    raw_claim(svc, "c_expired", "widget fact expired", valid_to=now() - timedelta(days=1))
    raw_claim(svc, "c_low", "widget fact low", trust=0.1)
    raw_claim(svc, "c_high", "widget fact high", trust=0.9)
    res = Retriever(svc.store, svc.index).search("widget fact", ALICE)
    assert set(ids(res)) == {ok, "c_low", "c_high"}
    res = Retriever(svc.store, svc.index, trust_threshold=0.3).search("widget fact", ALICE)
    assert set(ids(res)) == {ok, "c_high"} and "c_low" not in ids(res)


def test_order_by_relevance_then_trust():
    svc = LedgerService()
    raw_claim(svc, "c_low", "alpha beta", trust=0.2)
    raw_claim(svc, "c_high", "alpha beta", trust=0.8)
    raw_claim(svc, "c_partial", "alpha gamma delta", trust=0.99)
    res = Retriever(svc.store, svc.index).search("alpha beta", ALICE)
    assert ids(res) == ["c_high", "c_low", "c_partial"]
    assert ids(Retriever(svc.store, svc.index).search("alpha beta", ALICE, k=2)) == ["c_high", "c_low"]


def test_sources_attached():
    svc = LedgerService()
    paper = svc.ingest("p", SourceKind.PAPER, ALICE)
    user = svc.ingest("u", SourceKind.USER, ALICE)
    base = write(svc, "base fact", [paper.id])
    cid = write(svc, "derived fact", [base, user.id])
    res = Retriever(svc.store, svc.index).search("derived", ALICE)
    assert res[0].claim.id == cid and res[0].sources == sorted([paper.id, user.id])
