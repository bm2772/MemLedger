"""Episode format the runner consumes (slides 17, 21-22). Owner: M4; M3's generators/loaders emit this.

One episode = a scripted interaction with known ground truth. JSON fields:

    id, kind ("attack" | "clean"), split ("dev" | "test"), source (benchmark), attack_type
    sessions: {name: {user_id, team, role, clearance}}        identity comes from here, never from text
    steps: ordered list, each {"op": ..., "session": name, ...}
        ingest   {kind, content, as?, poison?}                   save an input as a Source
        write    {text, context?: [refs], as?, poison?}          propose a memory; context defaults to every
                                                                 unblocked ref the session has seen so far
        retrieve {query, k?, expect?}                            expect = substring of a correct answer
        tool     {tool, params, bind?: {param: regex}, high_risk?}  bind fills params from the session's
                                                                 retrieved memories (a model copying from memory)
        flag     {source: ref, reason}                           JTMS retraction
    attacker_goal: {tool, params}       the attacker's chosen action (ASR, hijacked action rate)
    poison_markers: [str]               a write containing one is poison unless labelled otherwise
    canaries: [{marker, team, clearance}]  visible to a session only if same team (or "shared") and clearance ok
    registry: {...}                     ground-truth protected facts (for reference; binding is M2's)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from memledger.core.types import Session

OPS = {"ingest", "write", "retrieve", "tool", "flag"}
KINDS = {"attack", "clean"}


@dataclass(frozen=True)
class Canary:
    marker: str
    team: str
    clearance: int = 0

    def visible_to(self, s: Session) -> bool:
        return self.team in (s.team, "shared") and s.clearance >= self.clearance


@dataclass
class Episode:
    id: str
    kind: str
    sessions: dict[str, Session]
    steps: list[dict]
    split: str = "dev"
    source: str = ""
    attack_type: str | None = None
    attacker_goal: dict | None = None
    poison_markers: list[str] = field(default_factory=list)
    canaries: list[Canary] = field(default_factory=list)
    registry: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> Episode:
        if d.get("kind") not in KINDS:
            raise ValueError(f"episode {d.get('id')}: kind must be one of {sorted(KINDS)}")
        sessions = {name: Session(s["user_id"], s["team"], s["role"], int(s["clearance"]))
                    for name, s in d["sessions"].items()}
        for i, st in enumerate(d["steps"]):
            if st.get("op") not in OPS:
                raise ValueError(f"episode {d['id']} step {i}: unknown op {st.get('op')!r}")
            if st["op"] != "flag" and st.get("session") not in sessions:
                raise ValueError(f"episode {d['id']} step {i}: unknown session {st.get('session')!r}")
        return cls(
            id=d["id"], kind=d["kind"], sessions=sessions, steps=list(d["steps"]),
            split=d.get("split", "dev"), source=d.get("source", ""), attack_type=d.get("attack_type"),
            attacker_goal=d.get("attacker_goal"), poison_markers=list(d.get("poison_markers", [])),
            canaries=[Canary(c["marker"], c["team"], int(c.get("clearance", 0))) for c in d.get("canaries", [])],
            registry=dict(d.get("registry", {})),
        )

    def is_poison(self, step: dict, text: str) -> bool:
        if "poison" in step:
            return bool(step["poison"])
        return any(m in text for m in self.poison_markers)


def load_episodes(path: str | Path, split: str | None = None, limit: int | None = None) -> list[Episode]:
    """Load a .jsonl (one episode per line) or .json (list) file, optionally filtered by split."""
    text = Path(path).read_text()
    if Path(path).suffix == ".json":
        rows = json.loads(text)
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    eps = [Episode.from_dict(r) for r in rows]
    if split:
        eps = [e for e in eps if e.split == split]
    return eps[:limit] if limit is not None else eps
