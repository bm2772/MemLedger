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
