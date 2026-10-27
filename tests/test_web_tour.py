"""web/tour.py: the "How it works" story, on the real services with the lexical checkers."""

from web.tour import STEPS, play


def test_tour_shows_each_mechanism_acting():
    out = play()
    steps = {s["id"]: s["sides"] for s in out["steps"]}
    assert [s["id"] for s in out["steps"]] == [s["id"] for s in STEPS]
    status = lambda side: {c["label"]: c["status"] for c in side["claims"]}

    assert any(s["flagged"] for s in steps["sources"]["full"]["sources"])           # input screen
    assert not any(s["flagged"] for s in steps["sources"]["baseline"]["sources"])
    assert all(w["accepted"] for w in steps["poison"]["baseline"]["writes"])         # write checks
    assert not any(w["accepted"] for w in steps["poison"]["full"]["writes"])
    full = status(steps["flag"]["full"])                                             # JTMS retraction + exposure
    assert full["M1"] == "active" and full["M2"] == "contested"
    assert {full[k] for k in ("M3", "M4", "M5")} == {"quarantined"}
    assert set(status(steps["flag"]["baseline"]).values()) == {"active"}
    assert status(steps["evidence"]["full"])["M4"] == "restored"                     # new evidence
    assert steps["tamper"]["full"]["read"]["after"] == []                            # hash check fails closed
    assert steps["tamper"]["baseline"]["read"]["after"]
    assert steps["action"]["baseline"]["acme"]["hijacked"]                           # registry binding / gate
    assert not steps["action"]["full"]["acme"]["hijacked"]
    assert steps["write"]["full"]["explain"]["claim"]


def test_tour_endpoint():
    from fastapi.testclient import TestClient

    from web.api import create_app

    r = TestClient(create_app()).get("/api/tour", headers={"X-MemLedger-User": "ria"})
    assert r.status_code == 200 and len(r.json()["steps"]) == len(STEPS)


def test_tour_with_the_real_checkers():
    """Ahan's #26 review: with the hf models the story's memories were refused as contradictions and step 6 crashed.
    Skipped where the checker models are not installed (CI); run locally with MEMLEDGER_GUARD_BACKEND=hf."""
    import os

    import pytest

    if os.environ.get("MEMLEDGER_GUARD_BACKEND") != "hf":
        pytest.skip("set MEMLEDGER_GUARD_BACKEND=hf (and the model env vars) to run the tour on the real checkers")
    from eval.versions import load_guard_models

    out = play(load_guard_models("hf"))
    steps = {s["id"]: s["sides"]["full"] for s in out["steps"]}
    assert all(w["accepted"] for w in steps["chain"]["writes"]), steps["chain"]["writes"]
    assert not any(w["accepted"] for w in steps["poison"]["writes"])
    status = {c["label"]: c["status"] for c in steps["flag"]["claims"]}
    assert status["M1"] == "active" and {status[k] for k in ("M3", "M4", "M5")} == {"quarantined"}
    assert steps["tamper"]["read"]["after"] == [] and not steps["action"]["acme"]["hijacked"]


def test_tour_steps_survive_refused_memories(monkeypatch):
    """A memory refused at write time must give a warning, not a crash, in the later steps."""
    import web.tour as t

    monkeypatch.setattr(t, "WRITES", [w for w in t.WRITES if w[0] not in ("M1", "M4")])
    steps = {s["id"]: s["sides"]["full"] for s in t.play()["steps"]}
    assert steps["evidence"]["events"][0]["tone"] == "warn" and steps["tamper"]["events"][0]["tone"] == "warn"
