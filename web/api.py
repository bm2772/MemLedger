"""HTTP API of the MemLedger console. Every memory operation goes through the workspace's LedgerService.

Identity: web/auth.py turns the request's token into a Session; the browser never sends team, role or clearance.
Lists show only what the caller may read: team(m) in {team(p), 'shared'} and c(m) <= clr(p) (slide 21, I1).
"""

import json
import os
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from memledger.agent.loop import Agent
from memledger.agent.tools import ToolBox
from memledger.core.types import Labels, Session, SourceKind, Status, WriteProposal
from memledger.policy.access import AccessControl
from web import samples
from web.auth import DEMO_USERS, Auth, Unauthorized, session_dict
from web.workspace import VERSIONS, Workspace, Workspaces

ROOT = Path(__file__).resolve().parents[1]
UI_DIST = Path(__file__).resolve().parent / "ui" / "dist"
TEXT = Field(min_length=1, max_length=50_000)

# what each version turns on (eval/versions.py, slide 17), for the UI's protection chips
PROTECTIONS = {
    "baseline": [],
    "provenance": ["provenance", "hash_chain", "jtms", "team_scope"],
    "write_checks": ["provenance", "hash_chain", "jtms", "team_scope", "input_screen", "write_checks"],
    "full_no_registry": ["provenance", "hash_chain", "jtms", "team_scope", "input_screen", "write_checks",
                         "access_control", "action_gate"],
    "full": ["provenance", "hash_chain", "jtms", "team_scope", "input_screen", "write_checks", "access_control",
             "action_gate", "registry"],
}


# ------------------------------------------------------------------------------------------------ request bodies
class NewWorkspace(BaseModel):
    name: str = Field(max_length=80)
    version: str = "full"
    sample: str = "empty"


class Ingest(BaseModel):
    content: str = TEXT
    kind: SourceKind = SourceKind.USER


class Flag(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class Write(BaseModel):
    text: str = Field(min_length=1, max_length=2_000)
    context_ids: list[str] = Field(default_factory=list, max_length=64)


class Evidence(BaseModel):
    source_ids: list[str] = Field(min_length=1, max_length=64)


class Recall(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    k: int = Field(8, ge=1, le=50)


class Run(BaseModel):
    task: str = Field(min_length=1, max_length=4_000)
    llm: str = "fake"  # "fake" (GullibleLLM, deterministic) | "server" (the model configured on the server)


class RegistryValue(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    field: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)
    confidentiality: int = Field(0, ge=0, le=5)


class WebPage(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    content: str = TEXT


class Tamper(BaseModel):
    edit: str = "claim_text"


# ------------------------------------------------------------------------------------------------ serialisation
def _labels(lb: Labels) -> dict:
    return {"team": lb.team, "confidentiality": lb.confidentiality, "integrity": int(lb.integrity)}


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def source_dict(s) -> dict:
    return {"id": s.id, "kind": s.kind.value, "content": s.content, "labels": _labels(s.labels),
            "prior_trust": s.prior_trust, "content_hash": s.content_hash, "recorded_at": _iso(s.recorded_at),
            "flagged": s.flagged}


def claim_dict(c) -> dict:
    return {"id": c.id, "text": c.text, "status": c.status.value, "trust": round(c.trust, 4),
            "labels": _labels(c.labels), "recorded_at": _iso(c.recorded_at), "content_hash": c.content_hash}


def verdict_dict(v) -> dict:
    return {"check": v.check, "ok": v.ok, "score": round(float(v.score), 4), "reason": v.reason}


def _plain(row: dict) -> dict:
    return {k: (v.hex() if isinstance(v, bytes) else v) for k, v in row.items()}


_READ = AccessControl()  # the deck's read rule incl. role policies (e.g. guests see shared only), in every version


def visible(labels: Labels, s: Session) -> bool:
    return _READ.can_read(s, labels)


# ---------------------------------------------------------------------------------------------------------- app
def create_app(data_dir: str | Path | None = None, auth: Auth | None = None,
               models: dict[str, Any] | None = None) -> FastAPI:
    backend = os.environ.setdefault("MEMLEDGER_GUARD_BACKEND", "lexical")
    if models is None:
        from eval.versions import load_guard_models

        models = load_guard_models(backend)
    auth = auth or Auth.from_env()
    spaces = Workspaces(data_dir, models)
    llm_model = os.environ.get("MEMLEDGER_LLM_MODEL", "qwen3:8b")
    llm_url = os.environ.get("MEMLEDGER_LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")

    app = FastAPI(title="MemLedger", version="1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.workspaces = spaces

    @app.exception_handler(Unauthorized)
    def _401(_: Request, e: Unauthorized):
        return JSONResponse({"detail": str(e)}, 401)

    @app.exception_handler(PermissionError)
    def _403(_: Request, e: PermissionError):
        return JSONResponse({"detail": str(e)}, 403)

    @app.exception_handler(ValueError)
    def _400(_: Request, e: ValueError):
        return JSONResponse({"detail": str(e)}, 400)

    def me(authorization: Annotated[str | None, Header()] = None,
           x_memledger_user: Annotated[str | None, Header()] = None) -> Session:
        return auth.session(authorization, x_memledger_user)

    Me = Annotated[Session, Depends(me)]

    def workspace(ws_id: str) -> Workspace:
        try:
            return spaces.get(ws_id)
        except KeyError:
            raise HTTPException(404, f"no workspace {ws_id!r}") from None

    WS = Annotated[Workspace, Depends(workspace)]

    def claim_or_404(ws: Workspace, claim_id: str, s: Session):
        c = ws.store.get_claim(claim_id)
        if c is None or not visible(c.labels, s):
            raise HTTPException(404, f"no memory {claim_id!r}")
        return c

    def make_llm(kind: str):
        if kind == "fake":
            from eval.llm import GullibleLLM

            return GullibleLLM()
        if kind == "server":
            from eval.llm import MeteredLLM

            return MeteredLLM(model=llm_model, base_url=llm_url, timeout=180)
        raise ValueError("llm must be 'fake' or 'server'")

    # ---- server
    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/config")
    def config():
        return {"auth": "open" if auth.open else "token", "guard_backend": backend,
                "users": [session_dict(s) for s in DEMO_USERS.values()] if auth.open else [],
                "versions": VERSIONS, "protections": PROTECTIONS, "samples": samples.SAMPLES,
                "llm": {"model": llm_model, "base_url": llm_url}, "kinds": [k.value for k in SourceKind]}

    @app.get("/api/me")
    def whoami(s: Me):
        return session_dict(s)

    @app.get("/api/llm/status")
    def llm_status(_: Me):
        try:
            with urllib.request.urlopen(f"{llm_url}/models", timeout=2) as r:
                models_ = [m.get("id") for m in json.load(r).get("data", [])]
            return {"reachable": True, "model": llm_model, "available": llm_model in models_, "models": models_}
        except (OSError, ValueError) as e:
            return {"reachable": False, "model": llm_model, "error": str(e)[:200]}

    # ---- workspaces
    @app.get("/api/workspaces")
    def list_workspaces(_: Me):
        return [w.summary() for w in spaces.list()]

    @app.post("/api/workspaces", status_code=201)
    def create_workspace(body: NewWorkspace, s: Me):
        if body.sample not in samples.SAMPLES:
            raise ValueError(f"unknown sample {body.sample!r}")
        ws = spaces.create(body.name, body.version, samples.SAMPLES[body.sample]["description"])
        with ws.lock:
            samples.seed(ws, body.sample)
            ws.log(s, "create_workspace", version=body.version, sample=body.sample)
        return ws.summary()

    @app.delete("/api/workspaces/{ws_id}", status_code=204)
    def delete_workspace(ws: WS, s: Me):
        from memledger.registry import require_admin

        require_admin(s)
        spaces.delete(ws.id)

    @app.get("/api/workspaces/{ws_id}")
    def overview(ws: WS, s: Me):
        with ws.lock:
            svc = ws.service
            claims = [c for c in ws.store.list_claims() if visible(c.labels, s)]
            sources = [x for x in ws.store.list_sources() if visible(x.labels, s)]
            by_status = {st.value: 0 for st in Status}
            for c in claims:
                by_status[c.status.value] += 1
            root = ws.store.latest_root()
            trust = [0] * 5
            for c in claims:
                if c.status != Status.QUARANTINED:
                    trust[min(int(c.trust * 5), 4)] += 1
            return {**ws.summary(), "protections": PROTECTIONS[ws.version], "memories": len(claims),
                    "by_status": by_status, "sources": len(sources),
                    "flagged_sources": sum(x.flagged for x in sources), "trust_histogram": trust,
                    "chain": {"ok": svc._chain_ok() if root else None, "root": root and root["root"],
                              "anchors": root and root["seq"], "items": root and root["n_items"],
                              "at": root and root["at"]},
                    "registry_entries": len(ws.registry_entries()), "web_pages": len(ws.meta.get("web_pages", {})),
                    "tasks": ws.meta.get("tasks", []), "activity": ws.activity[-12:][::-1]}

    # ---- sources
    @app.get("/api/workspaces/{ws_id}/sources")
    def list_sources(ws: WS, s: Me):
        with ws.lock:
            return [source_dict(x) for x in ws.store.list_sources() if visible(x.labels, s)][::-1]

    @app.post("/api/workspaces/{ws_id}/sources", status_code=201)
    def ingest(ws: WS, body: Ingest, s: Me):
        with ws.lock:
            src = ws.service.ingest(body.content, body.kind, s)
            hist = ws.store.status_history(src.id)
            ws.log(s, "ingest", source=src.id, kind=body.kind.value, flagged=src.flagged)
            return {**source_dict(src), "screen": hist[-1]["reason"] if src.flagged and hist else None}

    @app.post("/api/workspaces/{ws_id}/sources/{source_id}/flag")
    def flag(ws: WS, source_id: str, body: Flag, s: Me):
        with ws.lock:
            src = ws.store.get_source(source_id)
            if src is None or not visible(src.labels, s):
                raise HTTPException(404, f"no source {source_id!r}")
            out = ws.service.flag_source(source_id, f"{s.user_id}: {body.reason}")
            ws.log(s, "flag_source", source=source_id, reason=body.reason, **out)
            return {"quarantined": list(out["quarantined"]), "restored": list(out["restored"])}

    # ---- memories
    @app.get("/api/workspaces/{ws_id}/claims")
    def list_claims(ws: WS, s: Me):
        with ws.lock:
            out = []
            for c in ws.store.list_claims():
                if visible(c.labels, s):
                    ds = ws.store.derivations_for(c.id)
                    out.append({**claim_dict(c), "derivations": len(ds),
                                "parents": sorted({p for d in ds for p in d.exposed_to})})
            return out[::-1]

    @app.post("/api/workspaces/{ws_id}/claims")
    def propose(ws: WS, body: Write, s: Me):
        with ws.lock:
            res = ws.service.propose_write(WriteProposal(body.text, body.context_ids, s, f"console:{s.user_id}"))
            ws.log(s, "write", text=body.text[:200], accepted=res.accepted, claims=res.claim_ids)
            return {"accepted": res.accepted, "claim_ids": res.claim_ids,
                    "verdicts": [verdict_dict(v) for v in res.verdicts]}

    @app.get("/api/workspaces/{ws_id}/claims/{claim_id}")
    def claim_detail(ws: WS, claim_id: str, s: Me):
        with ws.lock:
            claim_or_404(ws, claim_id, s)
            verified = ws.service.verify_claim(claim_id) if ws.service.verify_hashes else None  # quarantines on fail
            c = ws.store.get_claim(claim_id)
            return {**claim_dict(c), "verified": verified, "explain": ws.service.explain(claim_id),
                    "history": ws.store.status_history(claim_id),
                    "conflicts": [e for e in ws.store.edges(type="contradicts")
                                  if claim_id in (e["src"], e["dst"])]}

    @app.post("/api/workspaces/{ws_id}/claims/{claim_id}/evidence")
    def evidence(ws: WS, claim_id: str, body: Evidence, s: Me):
        with ws.lock:
            claim_or_404(ws, claim_id, s)
            for sid in body.source_ids:
                src = ws.store.get_source(sid)
                if src is None or not visible(src.labels, s):
                    raise HTTPException(404, f"no source {sid!r}")
            before = {c.id: c.status for c in ws.store.list_claims()}
            res = ws.service.propose_justification(
                claim_id, WriteProposal("", body.source_ids, s, f"console:{s.user_id}"))
            ws.log(s, "evidence", claim=claim_id, sources=body.source_ids, accepted=res.accepted)
            if not res.accepted:
                raise HTTPException(400, "; ".join(v.reason for v in res.verdicts if not v.ok) or "evidence refused")
            after = {c.id: c.status for c in ws.store.list_claims()}
            changed = [i for i in after if after[i] != before.get(i)]
            return {"quarantined": [i for i in changed if after[i] == Status.QUARANTINED],
                    "restored": [i for i in changed if after[i] == Status.RESTORED],
                    "verdicts": [verdict_dict(v) for v in res.verdicts]}

    @app.post("/api/workspaces/{ws_id}/recall")
    def recall(ws: WS, body: Recall, s: Me):
        with ws.lock:
            hits = ws.service.retrieve(body.query, s, body.k)
            return [{**claim_dict(h.claim), "sources": h.sources, "relevance": round(h.relevance, 4)} for h in hits]

    # ---- agent
    @app.post("/api/workspaces/{ws_id}/agent/run")
    def run_agent(ws: WS, body: Run, s: Me):
        llm = make_llm(body.llm)
        with ws.lock:
            svc, reg = ws.service, ws.registry if ws.version == "full" else None
            tools = ToolBox(svc, web=dict(ws.meta.get("web_pages", {})), registry_lookup=reg.get if reg else None,
                            gate=svc.gate)
            run = Agent(svc, llm, tools).run(body.task, s)
            ws.log(s, "agent_run", task=body.task[:200], llm=getattr(llm, "model", body.llm),
                    tools=[r.tool for r in run.tool_calls], outbox=len(tools.outbox))
            return {"answer": run.answer, "steps": run.steps, "model": getattr(llm, "model", body.llm),
                    "tool_calls": [asdict(r) for r in run.tool_calls], "context_ids": run.context_ids,
                    "written_claim_ids": run.written_claim_ids, "outbox": tools.outbox,
                    "tokens": {k: getattr(llm.meter, k) for k in ("calls", "prompt_tokens", "completion_tokens")}}

    @app.get("/api/workspaces/{ws_id}/web")
    def web_pages(ws: WS, _: Me):
        return [{"url": u, "content": c} for u, c in ws.meta.get("web_pages", {}).items()]

    @app.put("/api/workspaces/{ws_id}/web")
    def put_web_page(ws: WS, body: WebPage, s: Me):
        with ws.lock:
            ws.set_web_page(body.url, body.content)
            ws.log(s, "web_page", url=body.url)
            return {"url": body.url, "content": body.content}

    # ---- registry
    @app.get("/api/workspaces/{ws_id}/registry")
    def registry(ws: WS, s: Me):
        doc = ws.registry_doc or {}
        rows = [e.to_dict() for e in ws.registry_entries() if e.confidentiality <= s.clearance]
        return {"used": ws.version == "full", "signed_by": doc.get("signed_by"), "signed_at": doc.get("signed_at"),
                "signature": doc.get("signature"), "entries": rows}

    @app.post("/api/workspaces/{ws_id}/registry", status_code=201)
    def set_registry(ws: WS, body: RegistryValue, s: Me):
        with ws.lock:
            e = ws.set_registry_value(s, body.subject, body.field, body.value, body.confidentiality)
            ws.log(s, "registry", key=e.key)
            return e.to_dict()

    # ---- audit
    @app.get("/api/workspaces/{ws_id}/audit")
    def audit(ws: WS, s: Me):
        with ws.lock:
            ids = {c.id for c in ws.store.list_claims() if visible(c.labels, s)}
            ids |= {x.id for x in ws.store.list_sources() if visible(x.labels, s)}
            rows = ws.store.conn.execute("SELECT * FROM status_log ORDER BY seq DESC LIMIT 500").fetchall()
            return {"status_log": [dict(r) for r in rows if r["entity_id"] in ids],
                    "hash_log": [_plain(r) for r in ws.store.hash_log()[-200:][::-1]],
                    "activity": [a for a in ws.activity[::-1] if a.get("team") in (s.team, None)][:500]}

    @app.post("/api/workspaces/{ws_id}/verify")
    def verify_all(ws: WS, s: Me):
        with ws.lock:
            svc = ws.service
            if not svc.verify_hashes:
                return {"enabled": False, "checked": 0, "failed": []}
            active = [c for c in ws.store.list_claims() if c.status != Status.QUARANTINED and visible(c.labels, s)]
            failed = [c.id for c in active if not svc.verify_claim(c.id)]
            ws.log(s, "verify", checked=len(active), failed=failed)
            return {"enabled": True, "checked": len(active), "failed": failed, "chain_ok": svc._chain_ok()}

    @app.get("/api/workspaces/{ws_id}/export")
    def export(ws: WS, s: Me):
        with ws.lock:
            claims = [c for c in ws.store.list_claims() if visible(c.labels, s)]
            return {"workspace": ws.summary(), "exported_by": s.user_id,
                    "sources": [source_dict(x) for x in ws.store.list_sources() if visible(x.labels, s)],
                    "claims": [{**claim_dict(c), "derivations": [
                        {**asdict(d), "created_at": _iso(d.created_at)} for d in ws.store.derivations_for(c.id)]}
                        for c in claims],
                    "hash_log": [_plain(r) for r in ws.store.hash_log()], "registry": ws.registry_doc}

    # ---- attack lab (demo/scenario.py, run on fresh in-memory services; nothing touches the workspaces)
    @app.post("/api/lab/acme")
    def lab_acme(_: Me, llm: str = "fake"):
        from demo import scenario as sc

        model = make_llm(llm)
        out = {}
        for v in ("baseline", "full"):
            r = sc.play_acme(v, model if llm != "fake" else None)
            r.pop("service")
            out[v] = r
        return {"page": sc.PAGE, "vendor": sc.VENDOR, "real": sc.REAL, "attacker": sc.ATTACKER, "runs": out}

    @app.post("/api/lab/tamper")
    def lab_tamper(body: Tamper, _: Me):
        from demo import scenario as sc

        return sc.tamper_demo(body.edit)

    tour_cache: dict[str, dict] = {}

    @app.get("/api/tour")
    def tour(_: Me, fresh: bool = False):
        """The story on fresh in-memory services (web/tour.py); no workspace is touched. Cached per server (with the
        hf checkers a play is many model calls); ?fresh=true plays it again (the page's Replay)."""
        from web import tour as t

        if fresh or "play" not in tour_cache:
            tour_cache["play"] = {**t.play(models), "backend": backend}
        return tour_cache["play"]

    @app.get("/api/results")
    def results(_: Me):
        md = ROOT / "docs" / "results.md"
        manifest = ROOT / "docs" / "results" / "suite_manifest.json"
        return {"markdown": md.read_text() if md.exists() else None,
                "suite": json.loads(manifest.read_text()) if manifest.exists() else None}

    # ---- the built UI (npm run build in web/ui); any other path is the single-page app
    if UI_DIST.exists():
        @app.get("/{path:path}", include_in_schema=False)
        def ui(path: str):
            if path.startswith("api/"):
                raise HTTPException(404, "not found")
            f = (UI_DIST / path).resolve()
            if path and f.is_file() and UI_DIST.resolve() in f.parents:
                return FileResponse(f)
            return FileResponse(UI_DIST / "index.html")

    return app
