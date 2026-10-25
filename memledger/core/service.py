"""LedgerService: the real MemoryService. Implements slides 6 (provenance), 10 (service), 14 (hash chain)."""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import replace
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
from memledger.store.sqlite import SQLiteStore, locked


def item_hash(content: str, recorded_at: datetime, parent_hashes: list[str], labels: Labels | None = None) -> str:
    """Slide 14: SHA-256(content | record time | sorted parent hashes | labels).

    Labels (team, confidentiality, integrity) go beyond the slide's formula: without them a direct edit of a
    claim's team or confidentiality would move it across the access boundary undetected.
    """
    data = content.encode() + b"|" + recorded_at.isoformat().encode() + b"|" + "".join(sorted(parent_hashes)).encode()
    if labels is not None:
        data += f"|{labels.team}|{labels.confidentiality}|{int(labels.integrity)}".encode()
    return hashlib.sha256(data).hexdigest()


def leaf_of(item_id: str, content_hash: str) -> str:
    """Merkle leaf of one stored item: binds the id to its hash, so a copied row under a new id is not anchored."""
    return hashlib.sha256(f"{item_id}|{content_hash}".encode()).hexdigest()


class IntegrityError(RuntimeError):
    """The stored ledger no longer matches its signed root; the service refuses to sign over it."""


def _new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex}"


@locked  # a write is several store calls plus a signed anchor: serialise whole operations (F4)
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
        verify_hashes: bool = True,
        scoped: bool = True,
        jtms: bool = True,
    ) -> None:
        self.lock = threading.RLock()
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
        # Plain-RAG switches (eval baseline): no hash-chain check on read, no team-scoped lookup, no JTMS retraction.
        self.verify_hashes, self.scoped, self.jtms = verify_hashes, scoped, jtms
        self.stats = {"read_filtered": 0}  # memories the access-control read filter dropped (eval attribution)
        self.timings: list[dict] = []  # {"op": ingest|write|read|gate, "ms": float, "version": str}
        self.signing_key = signing_key or Ed25519PrivateKey.generate()
        self.public_key = public_key or self.signing_key.public_key()
        self.trust = TrustEngine(self.store)
        self._anchor_cache: tuple[int, dict[str, str], bool] | None = None  # (log seq, signed leaves, root matches)
        self._migrated = False

    def _migrate_anchors(self) -> None:
        """A store written before leaves were recorded: anchor what is there now (trust on first use). Runs on first
        use, not in __init__, because callers may set signing_key after construction (web/workspace.py)."""
        if self._migrated:
            return
        self._migrated = True
        if self.store.anchored_leaves() or self.store.latest_root() is None:  # new store, or already recorded
            return
        self._anchor([(x.id, x.content_hash) for x in [*self.store.list_sources(), *self.store.list_claims()]],
                     migrate=True)

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
        labels = Labels(session.team, session.clearance)
        src = Source(_new_id("s_"), kind, content, labels, PRIORS[kind], item_hash(content, t, [], labels), t)
        self.store.add_source(src)
        if self.input_screen is not None:  # step 1: a high score means the source never supports anything
            score = float(self.input_screen.score(content))
            if score >= self.screen_threshold:
                self.store.flag_source(src.id, f"input screen: score={score:.2f} >= {self.screen_threshold:.2f}")
                src = self.store.get_source(src.id) or src
        self._anchor([(src.id, src.content_hash)])
        return src

    def propose_write(self, proposal: WriteProposal) -> WriteResult:
        t0 = time.perf_counter()
        try:
            return self._propose_write(proposal)
        finally:
            self._timed("write", t0)

    def _validate(self, proposal: WriteProposal) -> tuple[WriteProposal, list[Verdict]]:
        """Write-path checks shared by new claims and new evidence: context ids de-duplicated and all known (the hash
        is rebuilt from exactly these parents on read), parent claims within Auth(p) like parent sources (I1, I2),
        then the checks. Returns (normalised proposal, verdicts)."""
        ids = list(dict.fromkeys(proposal.context_ids))
        proposal = replace(proposal, context_ids=ids)
        unknown = [i for i in ids if self.store.get_source(i) is None and self.store.get_claim(i) is None]
        if unknown:
            return proposal, [Verdict(False, 0.0, f"unknown context ids: {', '.join(unknown[:5])}", "provenance")]
        sources = [s for i in ids if (s := self.store.get_source(i)) is not None]
        claims = [c for i in ids if (c := self.store.get_claim(i)) is not None]
        access = self.access or next((c for c in self.checks if hasattr(c, "derive_labels")), None)
        if access is not None:  # the access check only sees sources: apply the same rule to parent memories
            try:
                access.derive_labels(proposal.session, [c.labels for c in claims])
            except PermissionError as e:  # policy.access.AccessDenied
                return proposal, [Verdict(False, 0.0, f"parent memory: {e}", "access")]
            access.observe(proposal.session, [c.id for c in claims])  # an untrusted parent taints too (I3)
        elif self.scoped and any(c.labels.team not in (proposal.session.team, "shared") for c in claims):
            return proposal, [Verdict(False, 0.0, "parent memory from another team", "team_scope")]
        return proposal, [c.check(proposal, sources) for c in self.checks]

    def _propose_write(self, proposal: WriteProposal) -> WriteResult:
        proposal, verdicts = self._validate(proposal)
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
        t = self.trust.claim_trust(claim.id)
        if t is None and self.jtms:  # its only justification is already invalid (flagged source / quarantined parent)
            self.store.set_status(claim.id, Status.QUARANTINED.value, "jtms: no valid justification", 0.0)
            self._anchor([(claim.id, claim.content_hash)])
            return WriteResult(False, [], [*verdicts, Verdict(False, 0.0, "no valid justification (JTMS)", "jtms")])
        self.store.set_status(claim.id, Status.ACTIVE.value, "jtms: initial trust", t or 0.0)
        self.index.add(claim.labels.team, claim.id, claim.text)
        for c in self.checks:  # step 4: conflicts the contradiction check found are recorded as edges
            for conflict in getattr(c, "last_conflicts", []):
                self.record_contradiction(claim.id, conflict.claim_id, conflict.is_update)
        self._anchor([(claim.id, claim.content_hash)])
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
        labels = Labels(p.session.team, conf)
        return Claim(_new_id("c_"), p.text, labels, trust=score * base,
                     valid_from=t, valid_to=None, recorded_at=t,
                     content_hash=item_hash(p.text, t, [h for _, h in parents], labels))

    # ---- hash chain
    def _anchor(self, new: list[tuple[str, str]] = (), migrate: bool = False) -> None:
        """Sign a root over every item anchored so far plus `new` (item id, content hash) pairs, the items this write
        batch created. The leaf set only grows with items the service itself wrote, starting from the set the latest
        signed root covers; it is never rebuilt from the current rows, so neither a row edited in storage nor a row
        inserted into `anchored` can become part of a signed root."""
        if not self._migrated:
            self._migrate_anchors()
        leaves = self._verified_leaves(migrate)
        added = {i: leaf_of(i, h) for i, h in new if i not in leaves}
        leaves.update(added)
        root = merkle_root(list(leaves.values()))
        self.store.append_hash_log(root, self.signing_key.sign(bytes.fromhex(root)), len(leaves), added)

    def _verified_leaves(self, migrate: bool) -> dict[str, str]:
        """The leaf set to extend: empty for a new store or a migration, otherwise exactly the set the latest signed
        root covers. Refuses to sign if the stored leaves no longer reproduce that root (rows added or removed)."""
        if migrate or self.store.latest_root() is None:
            return {}
        leaves = self._signed_leaves()
        if leaves is None:
            raise IntegrityError("stored leaf set does not reproduce the latest signed root; refusing to sign")
        return dict(leaves)

    def _chain_ok(self) -> bool:
        log = self.store.hash_log()
        if not log or [r["seq"] for r in log] != list(range(1, len(log) + 1)):
            return False
        try:
            self.public_key.verify(log[-1]["signature"], bytes.fromhex(log[-1]["root"]))
        except InvalidSignature:
            return False
        return True

    def _signed_leaves(self) -> dict[str, str] | None:
        """The leaf set the latest signed root covers, or None if the stored leaves do not reproduce that root.
        Cached per log entry: one tree build per new root, not per verified claim."""
        self._migrate_anchors()
        latest = self.store.latest_root()
        if latest is None:
            return None
        if self._anchor_cache is None or self._anchor_cache[0] != latest["seq"]:
            leaves = self.store.anchored_leaves()
            self._anchor_cache = (latest["seq"], leaves, merkle_root(list(leaves.values())) == latest["root"])
        _, leaves, ok = self._anchor_cache
        return leaves if ok else None

    def _anchored(self, item_id: str, content_hash: str) -> bool:
        leaves = self._signed_leaves()
        return leaves is not None and leaves.get(item_id) == leaf_of(item_id, content_hash)

    def _item_ok(self, claim: Claim, seen: set[str]) -> bool:
        """Recompute the claim's hash (and its parents', recursively) from stored content; every parent must also be
        in the signed leaf set with that hash."""
        seen.add(claim.id)
        first = self.store.derivations_for(claim.id)[:1]  # hash is based on the first derivation only
        parent_ids = [p for d in first for p in d.exposed_to]
        hashes = []
        for pid in dict.fromkeys(parent_ids):
            if (s := self.store.get_source(pid)) is not None:
                if item_hash(s.content, s.recorded_at, [], s.labels) != s.content_hash:
                    return False
                if not self._anchored(s.id, s.content_hash):
                    return False
                hashes.append(s.content_hash)
            elif (pc := self.store.get_claim(pid)) is not None:
                if pid not in seen and not (self._item_ok(pc, seen) and self._anchored(pc.id, pc.content_hash)):
                    return False
                hashes.append(pc.content_hash)
            else:
                return False
        return item_hash(claim.text, claim.recorded_at, hashes, claim.labels) == claim.content_hash

    def verify_claim(self, claim_id: str) -> bool:
        claim = self.store.get_claim(claim_id)
        if claim is None:
            return False
        ok = self._chain_ok() and self._item_ok(claim, set()) and self._in_latest_root(claim)
        if not ok and claim.status != Status.QUARANTINED:
            # quarantine only; no re-anchor: the signed leaf set must never absorb the state that just failed
            self.store.set_status(claim_id, Status.QUARANTINED.value, "integrity: hash mismatch")
        return ok

    def _in_latest_root(self, claim: Claim) -> bool:
        leaves = self._signed_leaves()
        if leaves is None or not self._anchored(claim.id, claim.content_hash):
            return False
        leaf = leaf_of(claim.id, claim.content_hash)
        return verify_proof(leaf, merkle_proof(list(leaves.values()), leaf), self.store.latest_root()["root"])

    # ---- reads
    def retrieve(self, query: str, session: Session, k: int = 8) -> list[RetrievedMemory]:
        t0 = time.perf_counter()
        try:
            out = []
            for m in Retriever(self.store, self.index).search(query, session, k * 2, scoped=self.scoped):
                if not self.verify_hashes or self.verify_claim(m.claim.id):  # baseline: nothing is verified
                    out.append(m)
            if self.access is not None:  # step 6: read filter, identity from the Session only
                kept = self.access.filter(session, out)
                self.stats["read_filtered"] += len(out) - len(kept)
                out = kept
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
        if not self.jtms:  # plain memory has no dependency graph to retract through
            return {"quarantined": [], "restored": []}
        res = self.trust.recompute()
        self._anchor()
        return {"quarantined": res["quarantined"], "restored": res["restored"]}

    def propose_justification(self, claim_id: str, proposal: WriteProposal) -> WriteResult:
        """New evidence from a user or agent: the same write-path checks as a new memory (unknown ids, Auth(p),
        support for the claim's own text, taint cap), then add_justification with the checks' score as s. Use this,
        not add_justification, for anything a caller supplies: unchecked evidence could raise any claim's trust."""
        claim = self.store.get_claim(claim_id)
        if claim is None:
            raise KeyError(claim_id)
        proposal, verdicts = self._validate(replace(proposal, text=claim.text))
        if any(not v.ok for v in verdicts):
            return WriteResult(False, [], verdicts)
        score = min((v.score for v in verdicts), default=1.0)
        self.add_justification(claim_id, proposal.context_ids, score, agent_id=proposal.agent_id)
        return WriteResult(True, [claim_id], verdicts)

    def add_justification(self, claim_id: str, context_ids: list[str], score: float = 1.0,
                          agent_id: str = "") -> dict[str, list[str]]:
        """New evidence for an existing claim (slide 7): record the derivation, recompute trust, re-anchor.

        Re-anchoring matters: a claim the JTMS restores must be in the latest signed root again, otherwise
        verify_claim would (correctly) refuse it as missing from the log and quarantine it for integrity.
        """
        self.store.add_derivation(Derivation(_new_id("d_"), claim_id, list(context_ids),
                                             {cid: score for cid in context_ids}, agent_id=agent_id))
        res = self.trust.recompute()
        self._anchor()
        return res

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
