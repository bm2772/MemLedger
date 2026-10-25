"""Step 8: the action gate and human approval queue (slides 9, 11; properties I4, I10).

Tools are grouped by risk: low (answer, search, read), medium (edit internal data, remember), high (external
actions: payment, email). Unknown tools count as high risk. Only high-risk calls are gated:

1 Protected parameters (registry/binding.py) must equal the signed registry value. A different value is a hijack
  attempt and is denied outright; a missing registry value goes to a person.
2 A call a reviewer already approved (same tool, params and user) runs once.
3 Every fact it relies on must be verified. Ctx(a) is only the context items that supplied a parameter value the
  model chose (a value found in the item's text, or the item's text copied into a free-text parameter); parameters
  bound from or checked against the registry need none, so a registry-bound payment does not depend on unrelated
  memories in the window. Each item in Ctx(a) must be trusted, uncontested, unquarantined and above the high-risk
  trust threshold unless recheck(id) re-confirms it at its source. Taint (I4): if the session read untrusted input,
  no call with model-supplied parameters runs. Email recipients must be registry contacts. Otherwise the call waits
  in the approval queue.

This is plain code: a fully fooled model still cannot redirect a payment.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from memledger.core.types import Integrity, Session, Verdict, now
from memledger.policy.access import AccessControl
from memledger.policy.items import (
    INSTRUCTION_CHANNELS,
    Item,
    Resolver,
    integrity_of,
    resolver,
    taints_sending,
)
from memledger.registry import signing
from memledger.registry.binding import default_registry, protected_params, registry_value
from memledger.registry.registry import Registry

LOW, MEDIUM, HIGH = "low", "medium", "high"
RISK: dict[str, str] = {
    "answer": LOW, "search_docs": LOW, "read_web": LOW, "explain": LOW,
    "remember": MEDIUM, "edit_internal": MEDIUM, "flag_source": MEDIUM,
    "send_email": HIGH, "send_payment": HIGH, "call_api": HIGH,
}
CONTACT_FIELDS = ("email", "contact")
REVIEWER_ROLES = frozenset({"approver", "registry-admin"})


def _norm(v: object) -> str:
    return "".join(str(v).split()).replace("-", "").lower() if v is not None else ""


def _as_text(v: object) -> str:
    if isinstance(v, bool) or v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return " ".join(str(v).split()).lower()


def _plain(text: str) -> str:
    return re.sub(r"(?<=\d),(?=\d{3})", "", " ".join(text.split()).lower())


def supplied(value: object, text: str, min_len: int = 3) -> bool:
    """Did this text supply the parameter value? (value appears as a whole token run, or the text was copied in)"""
    v, t = _plain(_as_text(value)), _plain(text)
    if not v or not t:
        return False
    if len(v) >= min_len and re.search(r"(?<![\w.])" + re.escape(v) + r"(?![\w]|\.\d)", t):
        return True
    return len(t) >= 12 and t.rstrip(".") in v


@dataclass
class Approval:
    id: str
    tool: str
    params: dict
    user_id: str
    reason: str
    status: str = "pending"  # pending | approved | denied | used
    created_at: datetime = field(default_factory=now)
    reviewer: str = ""
    decided_at: datetime | None = None
    signature: str = ""

    def record(self) -> dict:
        return {"id": self.id, "tool": self.tool, "params": self.params, "user_id": self.user_id,
                "reason": self.reason, "reviewer": self.reviewer,
                "decided_at": self.decided_at.isoformat() if self.decided_at else None}


class ApprovalQueue:
    """High-risk calls waiting for a person. Reviewers need an approver role and cannot approve their own call."""

    def __init__(self) -> None:
        self._ids = itertools.count(1)
        self.items: dict[str, Approval] = {}
        self.log: list[dict] = []

    def enqueue(self, tool: str, params: dict, session: Session, reason: str) -> Approval:
        for a in self.items.values():
            if a.status == "pending" and (a.tool, a.params, a.user_id) == (tool, params, session.user_id):
                a.reason = reason  # same request again: keep one entry, show the latest reason
                return a
        a = Approval(f"apr{next(self._ids)}", tool, dict(params), session.user_id, reason)
        self.items[a.id] = a
        self.log.append({"event": "enqueued", "id": a.id, "tool": tool, "user": session.user_id, "at": a.created_at})
        return a

    def pending(self) -> list[Approval]:
        return [a for a in self.items.values() if a.status == "pending"]

    def _decide(self, approval_id: str, reviewer: Session, status: str) -> Approval:
        a = self.items[approval_id]
        if reviewer.role not in REVIEWER_ROLES:
            raise PermissionError(f"{reviewer.user_id!r} (role {reviewer.role!r}) may not review actions")
        if reviewer.user_id == a.user_id:
            raise PermissionError("a request cannot be approved by the person who made it")
        if a.status != "pending":
            raise ValueError(f"{approval_id} is already {a.status}")
        a.status, a.reviewer, a.decided_at = status, reviewer.user_id, now()
        self.log.append({"event": status, "id": a.id, "reviewer": reviewer.user_id, "at": a.decided_at})
        return a

    def approve(self, approval_id: str, reviewer: Session, key: Ed25519PrivateKey | None = None) -> Approval:
        a = self._decide(approval_id, reviewer, "approved")
        if key is not None:  # signed human approval (slide 9)
            a.signature = signing.sign(signing.canonical(a.record()), key)
        return a

    def deny(self, approval_id: str, reviewer: Session) -> Approval:
        return self._decide(approval_id, reviewer, "denied")

    def consume(self, tool: str, params: dict, session: Session) -> Approval | None:
        for a in self.items.values():
            if a.status == "approved" and (a.tool, a.params, a.user_id) == (tool, params, session.user_id):
                a.status = "used"
                self.log.append({"event": "used", "id": a.id, "at": now()})
                return a
        return None


_DEFAULT_REGISTRY: object = object()


class ActionGate:
    """Implements core.interfaces.ActionGate. registry omitted = the default registry (registry.binding);
    registry=None = no registry at all (the full_no_registry version)."""

    name = "action_gate"

    def __init__(self, registry: Registry | None | object = _DEFAULT_REGISTRY, resolve: Resolver | None = None,
                 access: AccessControl | None = None, queue: ApprovalQueue | None = None,
                 recheck: Callable[[str], bool] | None = None, min_trust: float = 0.7,
                 risk: dict[str, str] | None = None) -> None:
        self.registry = registry
        self.resolve = resolve
        self.access = access
        self.queue = queue or ApprovalQueue()
        self.recheck = recheck  # live facts: re-check at the source just before use (slide 8)
        self.min_trust = min_trust  # read-filter threshold for high-risk use (slide 7, step 7)
        self.risk_table = {**RISK, **(risk or {})}

    def attach(self, memory: object) -> ActionGate:
        self.resolve = resolver(memory)
        return self

    def risk(self, tool: str) -> str:
        return self.risk_table.get(tool, HIGH)

    def _verdict(self, ok: bool, reason: str) -> Verdict:
        return Verdict(ok, 1.0 if ok else 0.0, reason, self.name)

    def _unverified(self, cid: str) -> str | None:
        item: Item | None = self.resolve(cid) if self.resolve else None
        if item is None:
            problem = "unknown origin"
        elif integrity_of(item) == Integrity.UNTRUSTED:
            problem = "untrusted, contested or quarantined"
        elif item.is_source and item.kind in INSTRUCTION_CHANNELS:
            problem = f"untrusted channel ({item.kind.value} output)"
        elif not item.is_source and item.trust < self.min_trust:
            problem = f"trust {item.trust:.2f} < {self.min_trust:.2f}"
        else:
            return None
        if self.recheck is not None and self.recheck(cid):
            return None
        return f"{cid}: {problem}"

    def ctx(self, params: dict, model_params: list[str], context_ids: list[str]) -> dict[str, list[str]]:
        """Ctx(a): context id -> the model-supplied parameters it supplied. Unresolvable ids are kept (unknown
        origin) when any parameter is model-supplied, since they may have supplied it."""
        out: dict[str, list[str]] = {}
        for cid in dict.fromkeys(context_ids):
            item = self.resolve(cid) if self.resolve else None
            if item is None:
                if model_params:
                    out[cid] = []
                continue
            if used := [p for p in model_params if supplied(params[p], item.text)]:
                out[cid] = used
        return out

    def _read_untrusted_input(self, session: Session, context_ids: list[str]) -> bool:
        """Taint (I4): the session read untrusted input (web/tool/flagged/untrusted-labelled sources or claims)."""
        if self.access is not None and self.access.send_tainted(session):
            return True
        for cid in context_ids:
            item = self.resolve(cid) if self.resolve else None
            if item is not None and (taints_sending(item) if item.is_source
                                     else item.labels.integrity == Integrity.UNTRUSTED):
                return True
        return False

    def allow(self, tool: str, params: dict, context_claim_ids: list[str], session: Session) -> Verdict:
        level = self.risk(tool)
        if level != HIGH:
            return self._verdict(True, f"{level} risk")
        reg = default_registry() if self.registry is _DEFAULT_REGISTRY else self.registry
        problems: list[str] = []
        verified: set[str] = set()  # parameters whose value the registry vouches for
        for p, (subject_param, _) in protected_params(tool).items():  # 1: protected params from the registry (I10)
            want = registry_value(tool, p, params, reg)
            if want is None:
                problems.append(f"no registry value for {p}")
            elif _norm(params.get(p)) != _norm(want):
                return self._verdict(False, f"denied: {p} does not match the signed registry")
            else:
                verified |= {p, subject_param}
        if tool == "send_email":
            to = _norm(params.get("to"))
            contacts = {_norm(e.value) for e in reg.current() if e.field.lower() in CONTACT_FIELDS} if reg else set()
            if to and to in contacts:
                verified.add("to")
            else:
                problems.append("recipient is not a registry contact")
        if (a := self.queue.consume(tool, params, session)) is not None:  # 2
            return self._verdict(True, f"approved by {a.reviewer} ({a.id})")
        model_params = [p for p, v in params.items() if p not in verified and _as_text(v)]  # 3
        if model_params and self._read_untrusted_input(session, context_claim_ids):
            problems.append(f"session read untrusted content; {', '.join(model_params)} not from the registry (I4)")
        for cid, used in self.ctx(params, model_params, context_claim_ids).items():
            if (p := self._unverified(cid)) is not None:
                problems.append(p + (f" (supplied {', '.join(used)})" if used else ""))
        if problems:
            reason = "; ".join(problems)
            a = self.queue.enqueue(tool, params, session, reason)
            return self._verdict(False, f"waiting for human approval ({a.id}): {reason}")
        return self._verdict(True, "high risk: registry-bound and verified")
