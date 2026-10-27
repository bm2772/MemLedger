"""Access control in code (slides 10, 21; properties I1-I5). Runs under every step; never asks the model.

Auth(p): user p may read memory m iff team(m) in {team(p), 'shared'} and c(m) <= clr(p) and the role policy allows.
Label propagation (I2): a derived memory gets c = max(parents), integrity = min(parents); mixing teams is refused.
Taint (I3-I5): after a session reads untrusted content it cannot write high-trust memory or send data out, until
the session ends or a person approves.

As a Check (write path), it refuses derivations from data outside Auth(p) or from another team, and caps the
support score of writes from a tainted session so they cannot become high-trust (the service uses min score as s).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from memledger.core.types import Integrity, Labels, RetrievedMemory, Session, Source, Verdict, WriteProposal
from memledger.policy.items import Item, Resolver, integrity_of, resolver, taints_sending

SHARED = "shared"
RolePolicy = Callable[[Session, Labels], bool]
DEFAULT_ROLES: dict[str, RolePolicy] = {
    "guest": lambda s, labels: labels.team == SHARED,  # guests see only shared, trusted material
}


class AccessDenied(PermissionError):
    pass


class AccessControl:
    name = "access"

    def __init__(self, roles: dict[str, RolePolicy] | None = None, resolve: Resolver | None = None,
                 tainted_score_cap: float = 0.5) -> None:
        self.roles = {**DEFAULT_ROLES, **(roles or {})}
        self.resolve = resolve
        self.tainted_score_cap = tainted_score_cap
        self._taint: dict[Session, list[str]] = {}  # untrusted content read: I3 and I4
        self._send_taint: dict[Session, list[str]] = {}  # tool output read: I4 only
        self.log: list[dict] = []

    def attach(self, memory: object) -> AccessControl:
        self.resolve = resolver(memory)
        return self

    # ---- I1: who may read what
    def can_read(self, session: Session, labels: Labels) -> bool:
        if labels.team not in (session.team, SHARED) or labels.confidentiality > session.clearance:
            return False
        policy = self.roles.get(session.role)
        return policy(session, labels) if policy else True

    def filter(self, session: Session, memories: Iterable[RetrievedMemory]) -> list[RetrievedMemory]:
        return [m for m in memories if self.can_read(session, m.claim.labels)]

    # ---- I2: label propagation
    def derive_labels(self, session: Session, parents: list[Labels]) -> Labels:
        teams = {p.team for p in parents} - {SHARED}
        if teams - {session.team}:
            raise AccessDenied(f"derivation mixes teams {sorted(teams | {session.team})}")
        if any(not self.can_read(session, p) for p in parents):
            raise AccessDenied("derivation uses data the session may not read")
        conf = max((p.confidentiality for p in parents), default=0)
        integ = min((p.integrity for p in parents), default=Integrity.NORMAL)
        return Labels(session.team, conf, Integrity(integ))

    # ---- I3-I5: taint
    def observe(self, session: Session, items: Iterable[Item | Source | str]) -> None:
        """Record what a session has read; anything untrusted taints it (I3, I4); tool output only blocks
        sending (I4), since its content is not untrusted (policy/items.py)."""
        for x in items:
            item = self._item(x)
            if item is None or integrity_of(item) == Integrity.UNTRUSTED:
                self._taint.setdefault(session, []).append(item.id if item else str(x))
            elif taints_sending(item):
                self._send_taint.setdefault(session, []).append(item.id)

    def _item(self, x: Item | Source | str) -> Item | None:
        if isinstance(x, Item):
            return x
        if isinstance(x, Source):
            return Item.of(x)
        return self.resolve(x) if self.resolve else None

    def tainted(self, session: Session) -> bool:
        return bool(self._taint.get(session))

    def send_tainted(self, session: Session) -> bool:
        return self.tainted(session) or bool(self._send_taint.get(session))

    def taint_reasons(self, session: Session) -> list[str]:
        return list(self._taint.get(session, []))

    def can_write_trusted(self, session: Session) -> bool:  # I3
        return not self.tainted(session)

    def can_send_out(self, session: Session) -> bool:  # I4
        return not self.send_tainted(session)

    def end_session(self, session: Session) -> None:  # I5
        self._taint.pop(session, None)
        self._send_taint.pop(session, None)
        self.log.append({"event": "session_end", "user": session.user_id})

    def clear_taint(self, session: Session, approval: object) -> None:  # I5: only a person's approval
        if getattr(approval, "status", None) != "approved" or getattr(approval, "user_id", None) != session.user_id:
            raise AccessDenied("taint can only be cleared by an approved request of this user")
        self._taint.pop(session, None)
        self._send_taint.pop(session, None)
        self.log.append({"event": "taint_cleared", "user": session.user_id,
                         "approval": getattr(approval, "id", None), "reviewer": getattr(approval, "reviewer", None)})

    # ---- Check (write path)
    def check(self, proposal: WriteProposal, sources: list[Source]) -> Verdict:
        s = proposal.session
        try:
            labels = self.derive_labels(s, [x.labels for x in sources])
        except AccessDenied as e:
            return Verdict(False, 0.0, str(e), self.name)
        self.observe(s, sources)
        if self.tainted(s) or labels.integrity == Integrity.UNTRUSTED:
            return Verdict(True, self.tainted_score_cap, "derived after reading untrusted content: capped (I3)",
                           self.name)
        return Verdict(True, 1.0, "within Auth(p)", self.name)
