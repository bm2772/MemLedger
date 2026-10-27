import pytest

from demo import scenario as s


@pytest.fixture(autouse=True)
def lexical(monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")


def test_slide5_plain_memory_pays_the_attacker():
    r = s.play_acme("baseline")
    assert r["writes"]["m_account"]["accepted"] and not r["web_flagged"]
    assert r["hijacked"] and r["payment"][0]["paid"] == s.ATTACKER
    assert any(s.ATTACKER in line for line in r["recalled"])


def test_slide5_memledger_rejects_flags_pays_registry_and_cleans_up():
    r = s.play_acme("full")
    acct = r["writes"]["m_account"]
    assert not acct["accepted"] and any("registry" in x for x in acct["reasons"])
    assert r["web_flagged"] and not r["hijacked"] and r["paid_correctly"]
    assert r["payment"][0]["paid"] == s.REAL
    ship = next(c for c in r["claims"] if "ships" in c["text"])
    assert ship["status"] == "quarantined"  # everything else derived from the page


def test_figure1_quarantine_and_restore():
    f = s.figure1()
    svc, c = f["service"], f["claims"]
    out = s.flag(svc, f["sources"]["web"])
    assert set(out["quarantined"]) == {c["D2"], c["D3"]}
    assert svc.store.get_claim(c["D1"]).status.value == "active"  # independent justification survives
    back = s.restore_with_evidence(svc, c["D2"], [f["sources"]["paper"]])
    assert c["D2"] in back["restored"]


def test_lineage_dot_marks_flagged_and_quarantined():
    f = s.figure1()
    svc = f["service"]
    s.flag(svc, f["sources"]["web"])
    dot = s.lineage_dot(svc.explain(f["claims"]["D3"]))
    assert dot.startswith("digraph") and dot.rstrip().endswith("}")
    assert "web (flagged)" in dot and "quarantined" in dot and dot.count("->") >= 3


@pytest.mark.parametrize("edit", ["claim_text", "source_content", "recorded_at"])
def test_tamper_is_detected(edit):
    r = s.tamper_demo(edit)
    assert r["before"] and r["after"] == [] and r["detected"] and "integrity: hash mismatch" in r["history"]


def test_isolation_leaks_on_plain_memory_and_is_withheld_by_memledger():
    plain, ml = s.play_isolation("baseline"), s.play_isolation("full")
    assert plain["leaked"] and plain["retrieved"] >= 1 and s.CANARY in plain["answer"]
    assert not ml["leaked"] and s.CANARY not in ml["answer"] and ml["error"] is None


def test_one_episode_per_family_and_memledger_stops_them():
    fams = s.family_samples(path="/nonexistent")  # offline: generated in memory
    assert {"agentpoison", "db_tamper", "fake_fact", "isolation", "minja", "repetition_flooding"} <= set(fams)
    for name in ("minja", "db_tamper", "fake_fact"):
        base, full = s.play_family(fams[name], "baseline"), s.play_family(fams[name], "full")
        assert base["succeeded"] is True and full["succeeded"] is False, name
        assert full["blocked_by"] and full["error"] is None, name


def test_family_samples_prefer_episodes_that_work_on_plain_memory():
    fams = s.family_samples(path="/nonexistent")
    assert s.play_family(fams["repetition_flooding"], "baseline")["succeeded"] is True
    first = s.family_samples(path="/nonexistent", working_on_plain=False)
    assert first["minja"].id == fams["minja"].id  # unchanged where the first one already works
