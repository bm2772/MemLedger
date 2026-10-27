"""Shared data types. Shared by every module (docs/interfaces.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


def now() -> datetime:
    return datetime.now(UTC)


class SourceKind(str, Enum):
    PAPER = "paper"
    REGISTRY = "registry"
    INTERNAL = "internal"
    USER = "user"
    TOOL = "tool"
    WEB = "web"
    AGENT = "agent"
    MODEL_PARAMETRIC = "model_parametric"


class Status(str, Enum):
    ACTIVE = "active"
    QUARANTINED = "quarantined"
    SUPERSEDED = "superseded"
    CONTESTED = "contested"
    RESTORED = "restored"


class Integrity(int, Enum):
    UNTRUSTED = 0
    NORMAL = 1
    TRUSTED = 2


@dataclass(frozen=True)
class Labels:
    """Access labels. team = tenant; 'shared' is readable by everyone."""

    team: str
    confidentiality: int = 0  # higher = more secret
    integrity: Integrity = Integrity.NORMAL


@dataclass
class Source:
    id: str
    kind: SourceKind
    content: str
    labels: Labels
    prior_trust: float
    content_hash: str = ""
    recorded_at: datetime = field(default_factory=now)
    flagged: bool = False


@dataclass
class Claim:
    """One atomic fact stored as memory."""

    id: str
    text: str
    labels: Labels
    trust: float = 0.0
    status: Status = Status.ACTIVE
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    recorded_at: datetime = field(default_factory=now)
    content_hash: str = ""


@dataclass
class FactSupport:
    """One fact of a written memory and the context items that support it (slide 6: sources point to facts)."""

    fact: str
    parents: dict[str, float]  # parent id -> support score of this fact by that parent on its own
    joint: bool = False  # no single parent supports it; the sources together do (a multi-source conclusion)


@dataclass
class Derivation:
    """A write event: which claim was produced, what the model saw, what supports it."""

    id: str
    claim_id: str
    exposed_to: list[str]  # every source/claim id in the context window (recorded by the service)
    # verifier-confirmed parent id -> s (the write's support score, slide 7): the parents of at least one fact in
    # `facts`. Without a verifier (baseline, provenance) every context item, since nothing can tell them apart.
    supported_by: dict[str, float]
    model: str = ""
    prompt_hash: str = ""
    agent_id: str = ""
    created_at: datetime = field(default_factory=now)
    facts: list[FactSupport] = field(default_factory=list)  # per-fact support; empty without a verifier


@dataclass(frozen=True)
class Session:
    """Identity comes from login, never from the model."""

    user_id: str
    team: str
    role: str
    clearance: int


@dataclass
class WriteProposal:
    text: str
    context_ids: list[str]
    session: Session
    agent_id: str = ""


@dataclass
class Verdict:
    ok: bool
    score: float
    reason: str = ""
    check: str = ""


@dataclass
class WriteResult:
    accepted: bool
    claim_ids: list[str]
    verdicts: list[Verdict]


@dataclass
class RetrievedMemory:
    claim: Claim
    sources: list[str]
    relevance: float
