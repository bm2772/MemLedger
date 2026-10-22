"""LedgerService: the real MemoryService. Implements slides 6 (provenance), 10 (service), 14 (hash chain)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from memledger.core.interfaces import Check
from memledger.core.merkle import merkle_proof, merkle_root, verify_proof
from memledger.core.mock import PRIORS
from memledger.core.types import (
    Claim,
    Derivation,
    Labels,
    RetrievedMemory,
    Session,
    Source,
    SourceKind,
    Status,
    WriteProposal,
    WriteResult,
    now,
)
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
    ) -> None:
        self.store = store or SQLiteStore()
        self.index = index or InMemoryIndex()
        self.checks = checks or []
        self.signing_key = signing_key or Ed25519PrivateKey.generate()
        self.public_key = public_key or self.signing_key.public_key()

    # ---- writes
    def ingest(self, content: str, kind: SourceKind, session: Session) -> Source:
        t = now()
        src = Source(_new_id("s_"), kind, content, Labels(session.team), PRIORS[kind],
                     item_hash(content, t, []), t)
        self.store.add_source(src)
        self._anchor()
        return src

    def propose_write(self, proposal: WriteProposal) -> WriteResult:
        sources = [s for i in proposal.context_ids if (s := self.store.get_source(i)) is not None]
        verdicts = [c.check(proposal, sources) for c in self.checks]
        if any(not v.ok for v in verdicts):
            return WriteResult(False, [], verdicts)
        score = min((v.score for v in verdicts), default=1.0)
        claim = self._make_claim(proposal, score)
        self.store.add_claim(claim)
        self.store.add_derivation(Derivation(
            _new_id("d_"), claim.id, list(proposal.context_ids),
            {cid: score for cid in proposal.context_ids}, agent_id=proposal.agent_id,
        ))
        self.index.add(claim.labels.team, claim.id, claim.text)
        self._anchor()
        return WriteResult(True, [claim.id], verdicts)

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
        return Claim(_new_id("c_"), p.text, Labels(p.session.team), trust=score * base,
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
        parent_ids = [p for d in self.store.derivations_for(claim.id) for p in d.exposed_to]
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
        teams = [session.team, "shared"]
        out = []
        for cid, score in self.index.query(teams, query, k * 3):
            claim = self.store.get_claim(cid)
            if claim is None or claim.labels.team not in teams or claim.status == Status.QUARANTINED:
                continue
            if not self.verify_claim(cid):
                continue
            exposed = [p for d in self.store.derivations_for(cid) for p in d.exposed_to]
            out.append(RetrievedMemory(claim, exposed, score))
        return out[:k]

    def flag_source(self, source_id: str, reason: str) -> dict[str, list[str]]:
        self.store.flag_source(source_id, reason)
        # TODO Day 3: JTMS recompute (slide 7)
        quarantined = []
        for c in self.store.list_claims():
            ders = self.store.derivations_for(c.id)
            if c.status != Status.QUARANTINED and ders and all(source_id in d.exposed_to for d in ders):
                self.store.set_status(c.id, Status.QUARANTINED.value, f"source {source_id} flagged: {reason}")
                quarantined.append(c.id)
        self._anchor()
        return {"quarantined": quarantined, "restored": []}

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
