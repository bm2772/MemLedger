"""Common Episode format produced by scenarios/, bench/ and attacks/ and consumed by the eval runner (slides 17-18, 23).

An episode is: seed items loaded into memory before the run, then a list of turns, then the ground truth.
Turn actions:
  ingest   an input arrives (web page, email, tool output); it must pass the input screen (step 1)
  propose  an agent-proposed memory whose sources are the episode's seeds (write checks, steps 2-4)
  task     a user request run through the agent (steps 5-8)
Everything is JSON-serialisable; `Episode.from_dict(e.to_dict()) == e`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from memledger.core.types import Session, SourceKind

ACTIONS = ("ingest", "propose", "task")


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
class Turn:
    action: str
    content: str
    user: Session | None = None  # None -> the episode's default user
    kind: SourceKind | None = None  # for ingest
    url: str = ""  # ingest via read_web
    id: str = ""


@dataclass
class Expect:
    """Ground truth. Every field is optional; eval uses the ones that are set."""

    answer: str | None = None  # substring a correct answer contains
    label: str | None = None  # classification episodes, e.g. injected/clean, poisoned/clean, supported/hallucinated
    forbidden: list[str] = field(default_factory=list)  # strings that must never be visible to the user
    blocked: list[str] = field(default_factory=list)  # seed/turn ids that a defended system should reject
    tool_calls: list[dict] = field(default_factory=list)  # e.g. {"tool": "send_payment", "params": {"account": ..}}
    forbidden_tool_calls: list[dict] = field(default_factory=list)  # tool (+ optional params subset) = attack goal


@dataclass
class Episode:
    id: str
    source: str  # "scenario", "locomo", "bipia", ...
    split: str  # "dev" | "test" | "train"
    kind: str  # "clean" | "attack"
    category: str
    user: Session
    seeds: list[Seed] = field(default_factory=list)
    turns: list[Turn] = field(default_factory=list)
    expect: Expect = field(default_factory=Expect)
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in ("clean", "attack"):
            raise ValueError(f"kind must be clean or attack, got {self.kind!r}")
        for t in self.turns:
            if t.action not in ACTIONS:
                raise ValueError(f"unknown turn action {t.action!r}")

    def to_dict(self) -> dict:
        return json.loads(json.dumps(asdict(self), default=_enc))

    @classmethod
    def from_dict(cls, d: dict) -> Episode:
        d = dict(d)
        d["user"] = Session(**d["user"])
        d["seeds"] = [Seed(**{**s, "kind": SourceKind(s["kind"])}) for s in d.get("seeds", [])]
        d["turns"] = [Turn(**{**t, "user": Session(**t["user"]) if t.get("user") else None,
                              "kind": SourceKind(t["kind"]) if t.get("kind") else None}) for t in d.get("turns", [])]
        d["expect"] = Expect(**d.get("expect", {}))
        return cls(**d)


def _enc(o: object) -> object:
    if isinstance(o, SourceKind):
        return o.value
    raise TypeError(type(o))


def dump_jsonl(episodes: list[Episode], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.writelines(json.dumps(e.to_dict()) + "\n" for e in episodes)


def load_jsonl(path: str | Path) -> list[Episode]:
    with open(path) as f:
        return [Episode.from_dict(json.loads(line)) for line in f if line.strip()]
