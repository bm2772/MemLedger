"""Play an Episode (schema v1) against a MemoryService (any of the five versions) and collect what eval needs
(slides 17-18).

Seeds are written by a loader session of the seed's team and confidentiality; steps then run as the episode's
sessions. `task` steps run the LLM agent; the other ops are scripted. `leaks()` is leak check 2 (slide 22).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from memledger.agent.episode import Episode, Step
from memledger.agent.llm import LLM
from memledger.agent.loop import Agent, AgentRun
from memledger.agent.tools import RegistryLookup, RunState, StubTool, ToolBox, ToolRecord
from memledger.core.interfaces import ActionGate, MemoryService
from memledger.core.types import RetrievedMemory, Session, Source, WriteProposal, WriteResult


@dataclass
class EpisodeResult:
    episode_id: str
    refs: dict[str, str] = field(default_factory=dict)  # seed/step id -> service id
    seed_writes: dict[str, WriteResult] = field(default_factory=dict)
    ingested: dict[str, Source] = field(default_factory=dict)  # step id -> source
    proposals: dict[str, WriteResult] = field(default_factory=dict)  # write step id -> result
    retrievals: dict[str, list[RetrievedMemory]] = field(default_factory=dict)
    tool_records: dict[str, ToolRecord] = field(default_factory=dict)  # scripted tool steps
    flags: dict[str, dict] = field(default_factory=dict)
    runs: dict[str, AgentRun] = field(default_factory=dict)  # task step id -> agent run
    outbox: list[dict] = field(default_factory=list)  # high-risk actions that actually executed
    tool_ingests: list[Source] = field(default_factory=list)  # sources the agent's tool calls created (web, data stubs)
    tool_ingest_sessions: dict[str, Session] = field(default_factory=dict)  # source id -> session that fetched it

    @property
    def seed_sources(self) -> dict[str, str]:
        return {k: v for k, v in self.refs.items() if k in self.seed_writes}

    def visible_text(self) -> str:
        """Everything shown to the episode's users: agent runs, retrieved memories, tool calls."""
        parts = [r.visible_text() for r in self.runs.values()]
        parts += [h.claim.text for hits in self.retrievals.values() for h in hits]
        parts += [f"{r.params} {r.result} {r.reason}" for r in self.tool_records.values()]
        return "\n".join(parts)


def leaks(text: str, forbidden: list[str]) -> list[str]:
    return [f for f in forbidden if f and f in text]


def foreign_markers(episode: Episode, session: Session) -> list[str]:
    """Canary markers this session may not see (slide 21's Auth(p)) plus the episode's forbidden strings."""
    return sorted({c.marker for c in episode.canaries if not c.visible_to(session)} | set(episode.expect.forbidden))


def tool_call_matches(executed: dict, spec: dict) -> bool:
    """spec = {"tool": name, "params": {subset}}; executed = an outbox entry."""
    return executed["tool"] == spec["tool"] and all(
        str(executed["params"].get(k)) == str(v) for k, v in spec.get("params", {}).items())


def load_seeds(memory: MemoryService, episode: Episode, result: EpisodeResult) -> None:
    for s in episode.seeds:
        loader = Session(f"loader_{s.team}", s.team, "loader", s.confidentiality)
        src = memory.ingest(s.content, s.kind, loader)
        result.refs[s.id] = src.id
        result.seed_writes[s.id] = memory.propose_write(WriteProposal(s.content, [src.id], loader, "loader"))


class _Play:
    def __init__(self, episode: Episode, memory: MemoryService, agent: Agent, tools: ToolBox, result: EpisodeResult):
        self.ep, self.memory, self.agent, self.tools, self.res = episode, memory, agent, tools, result
        self.seen: dict[str, list[str]] = {n: [] for n in episode.sessions}  # each session's context window
        self.step_ids = {st.id for st in episode.steps if st.id} | {sd.id for sd in episode.seeds}
        self.read: dict[str, list[str]] = {n: [] for n in episode.sessions}  # texts of retrieved memories

    def ref(self, x: str) -> str:
        return self.res.refs.get(x, x)

    def step(self, i: int, s: Step) -> None:
        sid = s.id or f"t{i}"
        if s.op == "flag":
            self.res.flags[sid] = self.memory.flag_source(self.ref(s.source), s.reason)
            return
        name, user = s.session, self.ep.session_of(s)
        if s.op == "ingest":
            src = self.memory.ingest(s.content, s.kind, user)
            self.res.ingested[sid], self.res.refs[sid] = src, src.id
            self.seen[name].append(src.id)
        elif s.op == "write":
            # a step that produced nothing (a rejected write) has no id to cite: drop it rather than pass its name
            ctx = ([self.ref(r) for r in s.context if r in self.res.refs or r not in self.step_ids]
                   if s.context is not None else list(self.seen[name]))
            wr = self.memory.propose_write(WriteProposal(s.text, ctx, user, "agent"))
            self.res.proposals[sid] = wr
            if wr.accepted and wr.claim_ids:
                self.res.refs[sid] = wr.claim_ids[0]
        elif s.op == "retrieve":
            hits = self.memory.retrieve(s.query, user, s.k)
            self.res.retrievals[sid] = hits
            self.seen[name] += [h.claim.id for h in hits]
            self.read[name] += [h.claim.text for h in hits]
        elif s.op == "tool":
            params = dict(s.params)
            for param, pattern in s.bind.items():  # a fooled model copying a value from its memory
                if m := next((m for t in self.read[name] if (m := re.search(pattern, t))), None):
                    params[param] = m.group(1)
            state = RunState(user, "agent", list(self.seen[name]))
            self.res.tool_records[sid] = self.tools.call(s.tool, params, state)
        else:  # task
            self.res.runs[sid] = self.agent.run(s.content, user)


def run_episode(episode: Episode, memory: MemoryService, llm: LLM, registry_lookup: RegistryLookup | None = None,
                gate: ActionGate | None = None, max_steps: int = 6) -> EpisodeResult:
    result = EpisodeResult(episode.id)
    load_seeds(memory, episode, result)
    tools = ToolBox(memory, web=episode.meta.get("web"), registry_lookup=registry_lookup, gate=gate)
    for spec in episode.meta.get("stub_tools", []):  # benchmark adapters define their tools per episode (bench/loaders.py)
        tools.register_stub(StubTool.from_dict(spec))
    play = _Play(episode, memory, Agent(memory, llm, tools, max_steps=max_steps), tools, result)
    for i, s in enumerate(episode.steps):
        play.step(i, s)
    result.outbox = tools.outbox
    result.tool_ingests = tools.ingested
    result.tool_ingest_sessions = tools.ingested_by
    return result
