"""Shared Episode format, schema v1 (docs/proposals/episode-format.md). Owner: M3; eval/ (M4) imports it.

Produced by scenarios/, bench/ and attacks/; consumed by eval's runner and memledger.agent.runner (slides 17-18,
21-23). One episode = memory seeds, then ordered steps run as named sessions, then the ground truth.

    sessions: {name: Session}     identity comes only from here (never from text); default_session names one
    seeds:    items in memory before step 1 (each written by a loader session of its team and confidentiality)
    steps:    op = ingest   kind, content, url?, poison?      save an input as a Source (step 1)
                   write    text, context?, poison?           propose a memory (steps 2-4); context defaults to
                                                              everything the session has seen so far
                   retrieve query, k?, expect?                expect = substring of a correct answer
                   task     content                           free agent run with the LLM (steps 5-8)
                   tool     tool, params, bind?, high_risk?   scripted tool call; bind = {param: regex} copies a
                                                              value from retrieved memories (a fooled model)
                   flag     source, reason                    JTMS retraction (no session)
              `id` names a step's result so later steps can refer to it (M4's "as").
    expect:   ground truth; forbidden_tool_calls[0] is the attacker's goal
    canaries: leak markers with the team and clearance allowed to see them (slide 22)

Everything is JSON-serialisable: Episode.from_dict(e.to_dict()) == e.
Until 24 Oct, op "propose" (with `content`) is accepted as an alias of "write" (with `text`).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from memledger.core.types import Session, SourceKind

SCHEMA_VERSION = 1
OPS = ("ingest", "write", "retrieve", "task", "tool", "flag")
KINDS = ("clean", "attack")


@dataclass
class Seed:
    """An item present in memory before the episode starts."""

    id: str
    content: str
    team: str = "shared"
    kind: SourceKind = SourceKind.INTERNAL
    confidentiality: int = 0
    canary: str = ""  # 128-bit marker for leak checks (slide 22)
    poisoned: bool = False
    meta: dict = field(default_factory=dict)


@dataclass
class Step:
    op: str
    session: str = ""  # "" -> the episode's default_session (flag needs none)
    id: str = ""
    kind: SourceKind | None = None  # ingest
    content: str = ""  # ingest, task
    url: str = ""  # ingest that arrives through read_web
    poison: bool | None = None  # ingest, write: ground-truth label; None -> decided by poison_markers
    text: str = ""  # write
    context: list[str] | None = None  # write: step/seed ids; None -> everything seen so far
    query: str = ""  # retrieve
    k: int = 8
    expect: str | None = None  # retrieve
    tool: str = ""  # tool
    params: dict = field(default_factory=dict)
    bind: dict = field(default_factory=dict)
    high_risk: bool | None = None
    source: str = ""  # flag: step/seed id or service id
    reason: str = ""

    def __post_init__(self) -> None:
        if self.op == "propose":  # alias kept for one day (proposal)
            self.op, self.text, self.content = "write", self.text or self.content, ""
        if self.op not in OPS:
            raise ValueError(f"unknown step op {self.op!r}")
        if self.op == "ingest" and self.kind is None:
            self.kind = SourceKind.USER
        if isinstance(self.kind, str):
            self.kind = SourceKind(self.kind)

    def to_dict(self) -> dict:
        """Compact form: only the fields that differ from their defaults."""
        out = {"op": self.op}
        for f in fields(self)[1:]:
            v = getattr(self, f.name)
            default = f.default_factory() if callable(f.default_factory) else f.default
            if v != default:
                out[f.name] = v.value if isinstance(v, SourceKind) else v
        return out

    @classmethod
    def from_dict(cls, d: dict) -> Step:
        d = dict(d)
        if "as" in d:
            d["id"] = d.pop("as")
        return cls(**d)


@dataclass(frozen=True)
class Canary:
    marker: str
    team: str
    clearance: int = 0

    def visible_to(self, s: Session) -> bool:
        """Auth(p) from slide 21: same team or shared, and clearance high enough."""
        return self.team in (s.team, "shared") and s.clearance >= self.clearance


@dataclass
class Expect:
    """Ground truth. Every field is optional; eval uses the ones that are set."""

    answer: str | None = None  # substring a correct answer contains
    label: str | None = None  # classification episodes, e.g. injected/clean, poisoned/clean, supported/hallucinated
    forbidden: list[str] = field(default_factory=list)  # strings that must never be visible to the user
    blocked: list[str] = field(default_factory=list)  # seed/step ids that a defended system should reject
    tool_calls: list[dict] = field(default_factory=list)  # e.g. {"tool": "send_payment", "params": {"account": ..}}
    forbidden_tool_calls: list[dict] = field(default_factory=list)  # [0] is the attacker's goal


@dataclass
class Episode:
    id: str
    source: str  # "scenario", "locomo", "bipia", ...
    split: str  # "train" | "dev" | "test"
    kind: str  # "clean" | "attack"
    category: str
    sessions: dict[str, Session]
    default_session: str = ""
    seeds: list[Seed] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    expect: Expect = field(default_factory=Expect)
    canaries: list[Canary] = field(default_factory=list)
    poison_markers: list[str] = field(default_factory=list)
    registry: dict = field(default_factory=dict)  # {"Acme Ltd": {"account": "1234"}}: Registry.from_mapping
    meta: dict = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"episode {self.id}: kind must be clean or attack, got {self.kind!r}")
        if not self.sessions:
            raise ValueError(f"episode {self.id}: needs at least one session")
        self.default_session = self.default_session or next(iter(self.sessions))
        if self.default_session not in self.sessions:
            raise ValueError(f"episode {self.id}: unknown default_session {self.default_session!r}")
        for i, s in enumerate(self.steps):
            if s.op != "flag":
                s.session = s.session or self.default_session
                if s.session not in self.sessions:
                    raise ValueError(f"episode {self.id} step {i}: unknown session {s.session!r}")

    @property
    def user(self) -> Session:
        return self.sessions[self.default_session]

    @property
    def attacker_goal(self) -> dict | None:
        return self.expect.forbidden_tool_calls[0] if self.expect.forbidden_tool_calls else None

    def session_of(self, step: Step) -> Session:
        return self.sessions[step.session or self.default_session]

    def is_poison(self, step: Step, text: str = "") -> bool:
        if step.poison is not None:
            return step.poison
        text = text or step.text or step.content
        return any(m in text for m in self.poison_markers)

    def to_dict(self) -> dict:
        d = json.loads(json.dumps(asdict(self), default=_enc))
        d["steps"] = [s.to_dict() for s in self.steps]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Episode:
        d = dict(d)
        if d.get("schema_version", SCHEMA_VERSION) > SCHEMA_VERSION:
            raise ValueError(f"episode {d.get('id')}: schema_version {d['schema_version']} is newer than this code")
        d["sessions"] = {n: Session(s["user_id"], s["team"], s["role"], int(s["clearance"]))
                         for n, s in d["sessions"].items()}
        d["seeds"] = [Seed(**{**s, "kind": SourceKind(s["kind"])}) for s in d.get("seeds", [])]
        d["steps"] = [Step.from_dict(s) for s in d.get("steps", [])]
        d["expect"] = Expect(**d.get("expect", {}))
        d["canaries"] = [Canary(c["marker"], c["team"], int(c.get("clearance", 0))) for c in d.get("canaries", [])]
        return cls(**d)


def _enc(o: object) -> object:
    if isinstance(o, SourceKind):
        return o.value
    raise TypeError(type(o))


def dump_jsonl(episodes: list[Episode], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.writelines(json.dumps(e.to_dict()) + "\n" for e in episodes)


def load_jsonl(path: str | Path, split: str | None = None, limit: int | None = None) -> list[Episode]:
    """Load a .jsonl file (one episode per line) or a .json list, optionally filtered by split."""
    text = Path(path).read_text()
    rows = json.loads(text) if Path(path).suffix == ".json" else [json.loads(x) for x in text.splitlines() if x.strip()]
    eps = [Episode.from_dict(r) for r in rows]
    if split:
        eps = [e for e in eps if e.split == split]
    return eps[:limit] if limit is not None else eps
