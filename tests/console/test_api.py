"""MemLedger console API (web/api.py): every operation through the service, identity from the token only."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from demo import scenario as sc
from memledger.core.types import Session
from web.api import create_app
from web.auth import Auth

RIA, FIN, BO, ADMIN = ({"X-MemLedger-User": u} for u in ("ria", "fin", "bo", "admin"))


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    return TestClient(create_app(tmp_path, Auth(None), models={}))


def new(client, sample="empty", version="full", name="ws"):
    r = client.post("/api/workspaces", json={"name": name, "version": version, "sample": sample}, headers=RIA)
    assert r.status_code == 201, r.text
    return f"/api/workspaces/{r.json()['id']}"


def test_acme_sample_end_to_end_blocks_the_attacker(client):
    ws = new(client, "acme")
    tasks = client.get(ws, headers=RIA).json()["tasks"]
    read = client.post(f"{ws}/agent/run", json={"task": tasks[0]["task"]}, headers=RIA).json()
    assert [t["tool"] for t in read["tool_calls"]] == ["read_web", "remember"]
    assert read["tool_calls"][1]["status"] == "blocked"  # registry match rejects the fake account
    pay = client.post(f"{ws}/agent/run", json={"task": tasks[1]["task"]}, headers=FIN).json()
    assert pay["outbox"] and all(o["params"]["account"] == sc.REAL for o in pay["outbox"])
    assert client.get(ws, headers=RIA).json()["flagged_sources"] == 1


def test_baseline_pays_the_attacker(client):
    ws = new(client, "acme", version="baseline")
    for headers, t in zip((RIA, FIN), client.get(ws, headers=RIA).json()["tasks"], strict=True):
        out = client.post(f"{ws}/agent/run", json={"task": t["task"]}, headers=headers).json()
    assert out["outbox"][0]["params"]["account"] == sc.ATTACKER


def test_figure1_flag_quarantines_only_dependents_and_evidence_restores(client):
    ws = new(client, "figure1", version="provenance")
    claims = {c["text"]: c for c in client.get(f"{ws}/claims", headers=RIA).json()}
    web = next(s for s in client.get(f"{ws}/sources", headers=RIA).json() if s["kind"] == "web")
    paper = next(s for s in client.get(f"{ws}/sources", headers=RIA).json() if s["kind"] == "paper")
    out = client.post(f"{ws}/sources/{web['id']}/flag", json={"reason": "poisoned"}, headers=RIA).json()
    d1, d2 = claims["Kestrel reaches 91% recall on Saltmarsh"], claims["Kestrel needs no safety review"]
    assert d2["id"] in out["quarantined"] and d1["id"] not in out["quarantined"] and len(out["quarantined"]) == 2
    back = client.post(f"{ws}/claims/{d2['id']}/evidence", json={"source_ids": [paper["id"]]}, headers=RIA).json()
    assert d2["id"] in back["restored"]
    detail = client.get(f"{ws}/claims/{d1['id']}", headers=RIA).json()
    assert detail["verified"] is True and len(detail["explain"]["lineage"]) == 2


def test_other_team_sees_nothing_and_cannot_touch_it(client):
    ws = new(client, "figure1", version="full")
    assert client.get(f"{ws}/claims", headers=RIA).json()
    assert client.get(f"{ws}/claims", headers=BO).json() == [] and client.get(f"{ws}/sources", headers=BO).json() == []
    cid = client.get(f"{ws}/claims", headers=RIA).json()[0]["id"]
    assert client.get(f"{ws}/claims/{cid}", headers=BO).status_code == 404
    assert client.post(f"{ws}/recall", json={"query": "Kestrel"}, headers=BO).json() == []


def test_write_returns_verdicts_and_ingest_reports_screen(client):
    ws = new(client)
    src = client.post(f"{ws}/sources", json={"content": "Paper: the Orion cluster has 64 nodes.", "kind": "paper"},
                      headers=RIA).json()
    res = client.post(f"{ws}/claims", json={"text": "The Orion cluster has 64 nodes", "context_ids": [src["id"]]},
                      headers=RIA).json()
    assert res["accepted"] and {v["check"] for v in res["verdicts"]} >= {"hallucination", "contradiction"}
    hits = client.post(f"{ws}/recall", json={"query": "Orion nodes"}, headers=RIA).json()
    assert hits[0]["id"] == res["claim_ids"][0]
    assert client.post(f"{ws}/verify", headers=RIA).json() == {"enabled": True, "checked": 1, "failed": [],
                                                                "chain_ok": True}


def test_registry_is_admin_only_and_signed(client):
    ws = new(client)
    body = {"subject": "Acme Ltd", "field": "account", "value": "1234"}
    assert client.post(f"{ws}/registry", json=body, headers=RIA).status_code == 403
    assert client.post(f"{ws}/registry", json=body, headers=ADMIN).status_code == 201
    reg = client.get(f"{ws}/registry", headers=RIA).json()
    assert reg["signed_by"] == "admin" and reg["signature"] and reg["entries"][0]["value"] == "1234"
    assert client.delete(ws, headers=RIA).status_code == 403


def test_workspace_survives_restart_and_still_verifies(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    c1 = TestClient(create_app(tmp_path, Auth(None), models={}))
    ws = new(c1, "figure1", version="provenance")
    c2 = TestClient(create_app(tmp_path, Auth(None), models={}))
    claims = c2.get(f"{ws}/claims", headers=RIA).json()
    assert len(claims) == 3
    assert c2.post(f"{ws}/verify", headers=RIA).json()["failed"] == []  # same ledger key: old roots still verify
    assert c2.post(f"{ws}/recall", json={"query": "Kestrel recall"}, headers=RIA).json()  # index rebuilt


def test_token_mode_takes_identity_from_the_token_only(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    auth = Auth({"t-bo": Session("bo", "team_b", "analyst", 1)})
    c = TestClient(create_app(tmp_path, auth, models={}))
    assert c.get("/api/me", headers=RIA).status_code == 401  # the demo header means nothing here
    me = c.get("/api/me", headers={"Authorization": "Bearer t-bo", "X-MemLedger-User": "admin"}).json()
    assert me["user_id"] == "bo" and not me["admin"]
    assert c.get("/api/config").json()["users"] == []


def test_lab_runs_on_fresh_services(client):
    acme = client.post("/api/lab/acme", headers=RIA).json()["runs"]
    assert acme["baseline"]["hijacked"] and not acme["full"]["hijacked"]
    assert client.post("/api/lab/tamper", json={"edit": "claim_text"}, headers=RIA).json()["detected"]
    assert client.get("/api/workspaces", headers=RIA).json() == []


# ---- PR #14 review fixes (web/)
def test_guest_sees_only_shared_material(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    auth = Auth({"t-ria": Session("ria", "team_a", "researcher", 1), "t-g": Session("g", "team_a", "guest", 1)})
    c = TestClient(create_app(tmp_path, auth, models={}))
    ria, guest = {"Authorization": "Bearer t-ria"}, {"Authorization": "Bearer t-g"}
    made = c.post("/api/workspaces", json={"name": "g", "version": "provenance", "sample": "figure1"}, headers=ria)
    ws = f"/api/workspaces/{made.json()['id']}"
    assert c.get(f"{ws}/claims", headers=ria).json()
    assert all(x["labels"]["team"] == "shared" for x in c.get(f"{ws}/claims", headers=guest).json())
    assert all(x["labels"]["team"] == "shared" for x in c.get(f"{ws}/sources", headers=guest).json())


def test_registry_change_keeps_session_taint_and_approvals(client):
    ws = new(client, "acme")
    app_ws = client.app.state.workspaces.get(ws.rsplit("/", 1)[-1])
    svc_before, gate_queue = app_ws.service, app_ws.service.gate.queue
    s = Session("fin", "team_a", "finance", 1)
    web = client.post(f"{ws}/sources", json={"content": "Supplier news page.", "kind": "web"}, headers=FIN).json()
    app_ws.service.access.observe(s, [app_ws.store.get_source(web["id"])])
    assert client.post(f"{ws}/registry", json={"subject": "Bolt Co", "field": "account", "value": "5555"},
                       headers=ADMIN).status_code == 201
    assert app_ws.service is svc_before and app_ws.service.gate.queue is gate_queue
    assert app_ws.service.access.tainted(s)
    assert app_ws.registry.get("Bolt Co", "account") == "5555"


def test_evidence_runs_the_write_checks(client):
    ws = new(client, "figure1", version="full")
    claims = client.get(f"{ws}/claims", headers=RIA).json()
    unrelated = client.post(f"{ws}/sources", json={"content": "The cafeteria opens at 8am.", "kind": "user"},
                            headers=RIA).json()
    r = client.post(f"{ws}/claims/{claims[0]['id']}/evidence", json={"source_ids": [unrelated["id"]]}, headers=RIA)
    assert r.status_code == 400 and "unsupported" in r.text
