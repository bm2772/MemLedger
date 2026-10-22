import sqlite3
from datetime import UTC, datetime

import pytest

from memledger.core.types import Claim, Derivation, Integrity, Labels, Source, SourceKind, Status
from memledger.store import SQLiteStore
from memledger.store.sqlite import TABLES

T0 = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def mk_source(i="s1", team="a"):
    return Source(i, SourceKind.PAPER, "hello", Labels(team, 2, Integrity.TRUSTED), 0.95, "h", T0)


def mk_claim(i="c1", team="a"):
    return Claim(i, "fact", Labels(team, 1, Integrity.UNTRUSTED), 0.4, Status.ACTIVE, T0, None, T0, "ch")


@pytest.fixture
def st():
    return SQLiteStore()


def test_source_roundtrip(st):
    st.add_source(mk_source())
    got = st.get_source("s1")
    assert got == mk_source()
    assert got.recorded_at.tzinfo is not None
    assert st.get_source("nope") is None
    assert [s.id for s in st.list_sources()] == ["s1"]


def test_claim_roundtrip_and_status(st):
    st.add_claim(mk_claim())
    got = st.get_claim("c1")
    assert got == mk_claim()
    assert st.status_history("c1")[0]["reason"] == "created"
    st.set_status("c1", "quarantined", "bad", trust=0.1)
    got = st.get_claim("c1")
    assert got.status == Status.QUARANTINED and got.trust == 0.1
    st.set_status("c1", "restored", "ok")
    assert st.get_claim("c1").trust == 0.1  # carried forward
    hist = st.status_history("c1")
    assert [h["status"] for h in hist] == ["active", "quarantined", "restored"]
    assert hist[1]["reason"] == "bad" and hist[1]["at"]


def test_empty_reason_rejected(st):
    with pytest.raises(ValueError):
        st.set_status("c1", "quarantined", "")


def test_flag_source(st):
    st.add_source(mk_source())
    assert not st.get_source("s1").flagged
    st.flag_source("s1", "poisoned")
    assert st.get_source("s1").flagged


def test_derivation_roundtrip(st):
    st.add_derivation(Derivation("d1", "c1", ["s1", "s2"], {"s1": 0.9}, "m", "ph", "ag", T0))
    d = st.get_derivation("d1")
    assert d.claim_id == "c1" and sorted(d.exposed_to) == ["s1", "s2"]
    assert d.supported_by == {"s1": 0.9} and d.agent_id == "ag" and d.created_at == T0
    assert [x.id for x in st.derivations_for("c1")] == ["d1"]
    assert len(st.edges(dst="c1", type="exposed_to")) == 2
    assert st.edges(type="supported_by")[0]["score"] == 0.9


def test_invalid_edge_type(st):
    with pytest.raises(sqlite3.IntegrityError):
        st.add_edge("a", "b", "bogus")
    st.add_edge("a", "b", "contradicts")
    assert len(st.edges(src="a")) == 1


@pytest.mark.parametrize("table", TABLES)
def test_append_only(st, table):
    st.add_source(mk_source())
    st.add_claim(mk_claim())
    st.add_derivation(Derivation("d1", "c1", ["s1"], {}, created_at=T0))
    st.append_hash_log("r", b"sig", 1)
    st.add_triple("c1", "x", "p", "v")
    col = {"sources": "kind", "claims": "text", "derivations": "model", "edges": "type",
           "status_log": "reason", "hash_log": "root", "triples": "value"}[table]
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        st.conn.execute(f"UPDATE {table} SET {col}={col}")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        st.conn.execute(f"DELETE FROM {table}")


def test_hash_log(st):
    assert st.latest_root() is None
    assert st.append_hash_log("r1", b"s1", 3) == 1
    assert st.append_hash_log("r2", b"s2", 4) == 2
    log = st.hash_log()
    assert [r["seq"] for r in log] == [1, 2]
    assert st.latest_root()["root"] == "r2" and st.latest_root()["signature"] == b"s2"


def test_list_claims_filter(st):
    st.add_claim(mk_claim("c1", "a"))
    st.add_claim(mk_claim("c2", "b"))
    st.add_claim(mk_claim("c3", "shared"))
    assert len(st.list_claims()) == 3
    assert [c.id for c in st.list_claims(team="a")] == ["c1"]
    assert {c.id for c in st.list_claims(teams=["a", "shared"])} == {"c1", "c3"}


def test_keyword_search_bm25_team_scope_and_sanitizing(st):
    for cid, team, text in [("c1", "a", "the server restarts nightly"), ("c2", "a", "dogs bark"),
                            ("c3", "b", "server restarts hourly")]:
        c = mk_claim(cid, team)
        c.text = text
        st.add_claim(c)
    hits = st.keyword_search(["a"], "restart server!! (now)", 5)
    assert [i for i, _ in hits] == ["c1"] and hits[0][1] > 0
    assert {i for i, _ in st.keyword_search(["a", "b"], "server", 5)} == {"c1", "c3"}
    assert st.keyword_search(["a"], "?!  ", 5) == []
    assert st.keyword_search(["a"], 'x" OR NEAR(', 5) == []


def test_triples_lookup_case_insensitive(st):
    st.add_triple("c1", "Project X", "budget", "5")
    st.add_triple("c2", "project x", "owner", "bob")
    assert st.lookup_triples("PROJECT x") == ["c1", "c2"]
    assert st.lookup_triples("project x", "Owner") == ["c2"]
    assert st.lookup_triples("project") == []
    assert st.triple_subjects() == ["project x"]
