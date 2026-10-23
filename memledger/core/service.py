"""LedgerService: the real MemoryService. Implements slides 6 (provenance), 10 (service), 14 (hash chain)."""

from __future__ import annotations

import hashlib
import time
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from memledger.core.interfaces import ActionGate, Check, InputScreen
from memledger.core.merkle import merkle_proof, merkle_root, verify_proof
from memledger.core.mock import PRIORS
from memledger.core.trust import TrustEngine
from memledger.core.types import (
    Claim,
    Derivation,
    Labels,
    RetrievedMemory,
    Session,
    Source,
    SourceKind,
    Status,
    Verdict,
    WriteProposal,
    WriteResult,
    now,
)
from memledger.retrieval.retriever import Retriever
from memledger.store.index import InMemoryIndex, VectorIndex
from memledger.store.sqlite import SQLiteStore


def item_hash(content: str, recorded_at: datetime, parent_hashes: list[str]) -> str:
    """Slide 14: SHA-256(content | record time | sorted parent hashes)."""
    data = content.encode() + b"|" + recorded_at.isoformat().encode() + b"|" + "".join(sorted(parent_hashes)).encode()
    return hashlib.sha256(data).hexdigest()


def _new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex}"


class LedgerService:
    def __init__(
        self,
        store: SQLiteStore | None = None,
        index: VectorIndex | None = None,
        checks: list[Check] | None = None,
        signing_key: Ed25519PrivateKey | None = None,
        public_key: Ed25519PublicKey | None = None,
        input_screen: InputScreen | None = None,
        screen_threshold: float = 0.5,
        access: Any | None = None,
        gate: ActionGate | None = None,
        on_timing: Callable[[str, float], None] | None = None,
        version: str = "",
    ) -> None:
        self.store = store or SQLiteStore()
        self.index = index or InMemoryIndex()
        self.checks = list(checks or [])
        self.access = access  # policy.access.AccessControl: read filter (slide 15 step 6) and a write-path check
        if access is not None and access not in self.checks:
            self.checks.append(access)
        self.input_screen = input_screen
        self.screen_threshold = screen_threshold
        self.gate = gate
        self.on_timing = on_timing
        self.version = version
        self.timings: list[dict] = []  # {"op": ingest|write|read|gate, "ms": float, "version": str}
        self.signing_key = signing_key or Ed25519PrivateKey.generate()
        self.public_key = public_key or self.signing_key.public_key()
        self.trust = TrustEngine(self.store)

    # ---- timing (M4 "added delay": wall time of each service call, in ms)
    def _timed(self, op: str, t0: float) -> None:
        ms = (time.perf_counter() - t0) * 1000
        self.timings.append({"op": op, "ms": ms, "version": self.version})
        if self.on_timing is not None:
            self.on_timing(op, ms)

    # ---- writes
    def ingest(self, content: str, kind: SourceKind, session: Session) -> Source:
        t0 = time.perf_counter()
        try:
            return self._ingest(content, kind, session)
        finally:
            self._timed("ingest", t0)

    def _ingest(self, content: str, kind: SourceKind, session: Session) -> Source:
        t = now()
        # confidentiality = clearance of the session that brought it in (the access filter keys off it, slide 15 step 6)
        src = Source(_new_id("s_"), kind, content, Labels(session.team, session.clearance), PRIORS[kind],
                     item_hash(content, t, []), t)
        self.store.add_source(src)
        if self.input_screen is not None:  # step 1: a high score means the source never supports anything
            score = float(self.input_screen.score(content))
            if score >= self.screen_threshold:
                self.store.flag_source(src.id, f"input screen: score={score:.2f} >= {self.screen_threshold:.2f}")
                src = self.store.get_source(src.id) or src
        self._anchor()
        return src

    def propose_write(self, proposal: WriteProposal) -> WriteResult:
        t0 = time.perf_counter()
        try:
            return self._propose_write(proposal)
        finally:
            self._timed("write", t0)

    def _propose_write(self, proposal: WriteProposal) -> WriteResult:
        sources = [s for i in proposal.context_ids if (s := self.store.get_source(i)) is not None]
        verdicts = [c.check(proposal, sources) for c in self.checks]
        if any(not v.ok for v in verdicts):
            return WriteResult(False, [], verdicts)
        score = min((v.score for v in verdicts), default=1.0)
        team = proposal.session.team
        key = proposal.text.strip().lower()
        existing = next((c for c in self.store.list_claims(team=team)
                         if c.status != Status.QUARANTINED and c.text.strip().lower() == key), None)
        if existing is not None:  # same fact again: one more justification, not a new claim
            self.store.add_derivation(self._derivation(existing.id, proposal, score))
            self.trust.recompute([existing.id])
            self._anchor()
            return WriteResult(True, [existing.id], verdicts)
        claim = self._make_claim(proposal, score)
        self.store.add_claim(claim)
        self.store.add_derivation(self._derivation(claim.id, proposal, score))
        self.store.set_status(claim.id, Status.ACTIVE.value, "jtms: initial trust",
                              self.trust.claim_trust(claim.id) or 0.0)
        self.index.add(claim.labels.team, claim.id, claim.text)
        for c in self.checks:  # step 4: conflicts the contradiction check found are recorded as edges
            for conflict in getattr(c, "last_conflicts", []):
                self.record_contradiction(claim.id, conflict.claim_id, conflict.is_update)
        self._anchor()
        return WriteResult(True, [claim.id], verdicts)

    def _derivation(self, claim_id: str, p: WriteProposal, score: float) -> Derivation:
        return Derivation(_new_id("d_"), claim_id, list(p.context_ids),
                          {cid: score for cid in p.context_ids}, agent_id=p.agent_id)

    def add_triple(self, claim_id: str, subject: str, property: str, value: str) -> None:
        self.store.add_triple(claim_id, subject, property, value)

    def record_contradiction(self, claim_a: str, claim_b: str, is_update: bool = False) -> None:
        self.trust.contest(claim_a, claim_b, is_update)
        self._anchor()

    def _parent(self, pid: str) -> tuple[float, str] | None:
        if (s := self.store.get_source(pid)) is not None:
            return s.prior_trust, s.content_hash
        if (c := self.store.get_claim(pid)) is not None:
            return c.trust, c.content_hash
        return None

    def _make_claim(self, p: WriteProposal, score: float) -> Claim:
        parents = [x for pid in p.context_ids if (x := self._parent(pid)) is not None]
        base = min((t for t, _ in parents), default=PRIORS[SourceKind.AGENT])
        t = now()
        conf = max((x.labels.confidentiality for pid in p.context_ids
                    if (x := self.store.get_source(pid) or self.store.get_claim(pid)) is not None), default=0)
        return Claim(_new_id("c_"), p.text, Labels(p.session.team, conf), trust=score * base,
                     valid_from=t, valid_to=None, recorded_at=t,
                     content_hash=item_hash(p.text, t, [h for _, h in parents]))

    # ---- hash chain
    def _current_hashes(self) -> list[str]:
        hs = [s.content_hash for s in self.store.list_sources()]
        return hs + [c.content_hash for c in self.store.list_claims() if c.status != Status.QUARANTINED]

    def _anchor(self) -> None:
        hashes = self._current_hashes()
        root = merkle_root(hashes)
        self.store.append_hash_log(root, self.signing_key.sign(bytes.fromhex(root)), len(hashes))

    def _chain_ok(self) -> bool:
        log = self.store.hash_log()
        if not log or [r["seq"] for r in log] != list(range(1, len(log) + 1)):
            return False
        try:
            self.public_key.verify(log[-1]["signature"], bytes.fromhex(log[-1]["root"]))
        except InvalidSignature:
            return False
        return True

    def _item_ok(self, claim: Claim, seen: set[str]) -> bool:
        """Recompute the claim's hash (and its parents', recursively) from stored content."""
        seen.add(claim.id)
        first = self.store.derivations_for(claim.id)[:1]  # hash is based on the first derivation only
        parent_ids = [p for d in first for p in d.exposed_to]
        hashes = []
        for pid in dict.fromkeys(parent_ids):
            if (s := self.store.get_source(pid)) is not None:
                if item_hash(s.content, s.recorded_at, []) != s.content_hash:
                    return False
                hashes.append(s.content_hash)
            elif (pc := self.store.get_claim(pid)) is not None:
                if pid not in seen and not self._item_ok(pc, seen):
                    return False
                hashes.append(pc.content_hash)
            else:
                return False
        return item_hash(claim.text, claim.recorded_at, hashes) == claim.content_hash

    def verify_claim(self, claim_id: str) -> bool:
        claim = self.store.get_claim(claim_id)
        if claim is None:
            return False
        ok = self._item_ok(claim, set()) and self._chain_ok() and self._in_latest_root(claim)
        if not ok:
            self.store.set_status(claim_id, Status.QUARANTINED.value, "integrity: hash mismatch")
            self._anchor()
        return ok

    def _in_latest_root(self, claim: Claim) -> bool:
        if claim.status == Status.QUARANTINED:
            return True
        hashes = self._current_hashes()
        root = self.store.latest_root()["root"]
        if claim.content_hash not in hashes:
            return False
        return verify_proof(claim.content_hash, merkle_proof(hashes, claim.content_hash), root)

    # ---- reads
    def retrieve(self, query: str, session: Session, k: int = 8) -> list[RetrievedMemory]:
        t0 = time.perf_counter()
        try:
            out = []
            for m in Retriever(self.store, self.index).search(query, session, k * 2):
                if self.verify_claim(m.claim.id):
                    out.append(m)
            if self.access is not None:  # step 6: read filter, identity from the Session only
                out = self.access.filter(session, out)
            return out[:k]
        finally:
            self._timed("read", t0)

    def authorize(self, tool: str, params: dict, context_claim_ids: list[str], session: Session) -> Verdict:
        """Step 8 passthrough to the ActionGate; without a gate every call is allowed (baseline)."""
        if self.gate is None:
            return Verdict(True, 1.0, "no gate", "action_gate")
        t0 = time.perf_counter()
        try:
            return self.gate.allow(tool, params, context_claim_ids, session)
        finally:
            self._timed("gate", t0)

    def flag_source(self, source_id: str, reason: str) -> dict[str, list[str]]:
        self.store.flag_source(source_id, reason)
        res = self.trust.recompute()
        self._anchor()
        return {"quarantined": res["quarantined"], "restored": res["restored"]}

    def explain(self, claim_id: str) -> dict:
        return self._explain(claim_id, set())

    def _explain(self, claim_id: str, visited: set[str]) -> dict:
        claim = self.store.get_claim(claim_id)
        visited.add(claim_id)
        lineage = [
            {"derivation": d.id, "agent_id": d.agent_id,
             "exposed_to": [self._node(p, visited) for p in d.exposed_to],
             "supported_by": dict(d.supported_by)}
            for d in self.store.derivations_for(claim_id)
        ]
        return {"claim": claim_id, "text": claim.text, "status": claim.status.value, "trust": claim.trust,
                "content_hash": claim.content_hash, "lineage": lineage}

    def _node(self, pid: str, visited: set[str]) -> dict:
        s = self.store.get_source(pid)
        if s is not None:
            return {"id": s.id, "kind": s.kind.value, "type": "source",
                    "content_hash": s.content_hash, "flagged": s.flagged}
        if pid in visited or self.store.get_claim(pid) is None:
            return {"id": pid, "type": "claim", "claim": pid}
        return self._explain(pid, visited)
