"""Play an Episode against a MemoryService (any of the five versions) and collect what eval needs (slides 17-18).

Seeds are written by a loader session of the seed's team and clearance; turns then run as the episode's users.
`leaks()` is leak check 2 (slide 22): any forbidden marker visible to the user.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from memledger.agent.episode import Episode
from memledger.agent.llm import LLM
from memledger.agent.loop import Agent, AgentRun
from memledger.agent.tools import RegistryLookup, ToolBox
from memledger.core.interfaces import ActionGate, MemoryService
from memledger.core.types import Session, Source, WriteProposal, WriteResult


@dataclass
class EpisodeResult:
    episode_id: str
    seed_sources: dict[str, str] = field(default_factory=dict)  # seed id -> source id
    seed_writes: dict[str, WriteResult] = field(default_factory=dict)
    ingested: dict[str, Source] = field(default_factory=dict)  # turn id -> source
    proposals: dict[str, WriteResult] = field(default_factory=dict)  # turn id -> write result
    runs: dict[str, AgentRun] = field(default_factory=dict)  # turn id -> agent run
    outbox: list[dict] = field(default_factory=list)  # high-risk actions that actually executed

    def visible_text(self) -> str:
        return "\n".join(r.visible_text() for r in self.runs.values())


def leaks(text: str, forbidden: list[str]) -> list[str]:
    return [f for f in forbidden if f and f in text]


def tool_call_matches(executed: dict, spec: dict) -> bool:
    """spec = {"tool": name, "params": {subset}}; executed = an outbox entry."""
    return executed["tool"] == spec["tool"] and all(
        str(executed["params"].get(k)) == str(v) for k, v in spec.get("params", {}).items())


def load_seeds(memory: MemoryService, episode: Episode, result: EpisodeResult) -> None:
    for s in episode.seeds:
        loader = Session(f"loader_{s.team}", s.team, "loader", s.confidentiality)
        src = memory.ingest(s.content, s.kind, loader)
        result.seed_sources[s.id] = src.id
        result.seed_writes[s.id] = memory.propose_write(WriteProposal(s.content, [src.id], loader, "loader"))


def run_episode(episode: Episode, memory: MemoryService, llm: LLM, registry_lookup: RegistryLookup | None = None,
                gate: ActionGate | None = None, max_steps: int = 6) -> EpisodeResult:
    result = EpisodeResult(episode.id)
    load_seeds(memory, episode, result)
    tools = ToolBox(memory, web=episode.meta.get("web"), registry_lookup=registry_lookup, gate=gate)
    agent = Agent(memory, llm, tools, max_steps=max_steps)
    for i, t in enumerate(episode.turns):
        tid, user = t.id or f"t{i}", t.user or episode.user
        if t.action == "ingest":
            result.ingested[tid] = memory.ingest(t.content, t.kind, user)
        elif t.action == "propose":
            ctx = list(result.seed_sources.values())
            result.proposals[tid] = memory.propose_write(WriteProposal(t.content, ctx, user, "agent"))
        else:
            result.runs[tid] = agent.run(t.content, user)
    result.outbox = tools.outbox
    return result
