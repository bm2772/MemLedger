"""Agent tools (slides 5, 9): search_docs, read_web, remember, send_email, send_payment.

Tools are stubs that record every call. They reach memory only through the MemoryService, and identity always comes
from the run's Session, never from tool arguments. High-risk tools (send_email, send_payment) go through an optional
ActionGate (step 8); send_payment binds the vendor's account from the registry when a lookup is given (I10).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from memledger.core.interfaces import ActionGate, MemoryService
from memledger.core.types import RetrievedMemory, Session, Source, SourceKind, WriteProposal

HIGH_RISK = {"send_email", "send_payment"}

# (vendor, field) -> value from the signed registry (M2). field is e.g. "account".
RegistryLookup = Callable[[str, str], str | None]


@dataclass
class ToolRecord:
    """One tool call as requested by the model and as actually executed."""

    tool: str
    args: dict  # what the model asked for
    params: dict  # what was (or would have been) executed, after registry binding
    status: str  # "ok" | "blocked" | "error"
    result: str = ""
    reason: str = ""


@dataclass
class RunState:
    """Per-run state: who is asking and everything in the context window (recorded for provenance)."""

    session: Session
    agent_id: str = "agent"
    context_ids: list[str] = field(default_factory=list)
    written_claim_ids: list[str] = field(default_factory=list)
    records: list[ToolRecord] = field(default_factory=list)

    def see(self, ids: list[str]) -> None:
        for i in ids:
            if i not in self.context_ids:
                self.context_ids.append(i)


def _fn(name: str, desc: str, props: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": required}}}


_S = {"type": "string"}
SPECS = [
    _fn("search_docs", "Search the team's memory for relevant facts.", {"query": _S}, ["query"]),
    _fn("read_web", "Fetch a web page by URL.", {"url": _S}, ["url"]),
    _fn("remember", "Propose a fact to store in long-term memory.", {"text": _S}, ["text"]),
    _fn("send_email", "Send an email.", {"to": _S, "subject": _S, "body": _S}, ["to", "subject", "body"]),
    _fn("send_payment", "Pay a vendor.", {"vendor": _S, "amount": {"type": "number"}, "account": _S},
        ["vendor", "amount"]),
]


WITHHELD = "[withheld: the input screen quarantined this tool output]"


@dataclass
class StubTool:
    """A tool an episode defines at run time (benchmark adapters: InjecAgent, AgentDojo, BIPIA documents).

    response set    a data tool: the text is ingested as a source of `kind` (so the input screen sees it) and returned
                    to the model as quoted data; a quarantined output is withheld
    response None   an action tool: the call is recorded; high-risk ones go through the ActionGate and, if allowed, are
                    appended to the outbox like send_email
    """

    name: str
    description: str = ""
    params: dict = field(default_factory=dict)  # parameter name -> description (all strings)
    response: str | None = None
    kind: SourceKind = SourceKind.TOOL
    high_risk: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> StubTool:
        return cls(**{**d, "kind": SourceKind(d.get("kind", "tool"))})

    def spec(self) -> dict:
        props = {p: {"type": "string", "description": str(desc)} for p, desc in self.params.items()}
        out = _fn(self.name, self.description or f"Tool {self.name}.", props, list(self.params))
        out["function"]["parameters"]["additionalProperties"] = True
        return out


def format_memories(hits: list[RetrievedMemory]) -> str:
    """Each memory shown with its id, source ids and trust (step 7), marked as quoted data."""
    if not hits:
        return "(no memories found)"
    lines = [f"- [{h.claim.id}] trust={h.claim.trust:.2f} sources={','.join(h.sources) or '-'}: {h.claim.text}"
             for h in hits]
    return "<memory>\n" + "\n".join(lines) + "\n</memory>"


class ToolBox:
    def __init__(self, memory: MemoryService, web: dict[str, str] | None = None,
                 registry_lookup: RegistryLookup | None = None, gate: ActionGate | None = None, k: int = 8):
        self.memory = memory
        self.web = web or {}
        self.registry_lookup = registry_lookup
        self.gate = gate
        self.k = k
        self.outbox: list[dict] = []  # executed high-risk actions (what actually left the system)
        self.stubs: dict[str, StubTool] = {}
        self.ingested: list[Source] = []  # sources created by tool calls (read_web, data stubs), for the eval rows
        self.ingested_by: dict[str, Session] = {}  # source id -> the session whose tool call fetched it

    def register_stub(self, stub: StubTool) -> None:
        """Add an episode-defined tool at run time. The built-in tools keep their meaning (a stub cannot replace one)."""
        if not hasattr(self, f"_t_{stub.name}"):
            self.stubs[stub.name] = stub

    def specs(self) -> list[dict]:
        return SPECS + [t.spec() for t in self.stubs.values()]

    def call(self, name: str, args: dict, state: RunState) -> ToolRecord:
        handler = getattr(self, f"_t_{name}", None)
        if name in self.stubs:
            handler = lambda a, st, _s=self.stubs[name]: self._stub(_s, a, st)
        if handler is None:
            rec = ToolRecord(name, args, args, "error", reason="unknown tool")
        else:
            try:
                rec = handler(dict(args), state)
            except (KeyError, TypeError, ValueError) as e:
                rec = ToolRecord(name, args, args, "error", reason=f"bad arguments: {e}")
        state.records.append(rec)
        return rec

    # low risk -------------------------------------------------------------------------------------------------
    def _t_search_docs(self, args: dict, state: RunState) -> ToolRecord:
        hits = self.memory.retrieve(str(args["query"]), state.session, self.k)
        state.see([h.claim.id for h in hits])
        return ToolRecord("search_docs", args, args, "ok", format_memories(hits))

    def _t_read_web(self, args: dict, state: RunState) -> ToolRecord:
        url = str(args["url"])
        page = self.web.get(url)
        if page is None:
            return ToolRecord("read_web", args, args, "error", reason="404")
        src = self.memory.ingest(page, SourceKind.WEB, state.session)
        self.ingested.append(src)
        self.ingested_by[src.id] = state.session
        state.see([src.id])
        if src.flagged:
            return ToolRecord("read_web", args, args, "ok", WITHHELD)
        return ToolRecord("read_web", args, args, "ok", f'<data source="{src.id}" kind="web" url="{url}">\n'
                                                        f"{page}\n</data>")

    # medium risk ----------------------------------------------------------------------------------------------
    def _t_remember(self, args: dict, state: RunState) -> ToolRecord:
        res = self.memory.propose_write(
            WriteProposal(str(args["text"]), list(state.context_ids), state.session, state.agent_id))
        state.written_claim_ids.extend(res.claim_ids)
        if not res.accepted:
            reasons = "; ".join(v.reason for v in res.verdicts if not v.ok)
            return ToolRecord("remember", args, args, "blocked", "not stored", reasons)
        return ToolRecord("remember", args, args, "ok", f"stored as {', '.join(res.claim_ids)}")

    # episode-defined tools --------------------------------------------------------------------------------------
    def _stub(self, stub: StubTool, args: dict, state: RunState) -> ToolRecord:
        params = {k: v if isinstance(v, (int, float, bool)) else str(v) for k, v in args.items()}
        if stub.response is not None:
            src = self.memory.ingest(stub.response, stub.kind, state.session)
            self.ingested.append(src)
            self.ingested_by[src.id] = state.session
            state.see([src.id])
            if src.flagged:
                return ToolRecord(stub.name, args, params, "ok", WITHHELD)
            return ToolRecord(stub.name, args, params, "ok", f'<data source="{src.id}" kind="{stub.kind.value}" '
                                                             f'tool="{stub.name}">\n{stub.response}\n</data>')
        if stub.high_risk:
            return self._high_risk(stub.name, args, params, state)
        return ToolRecord(stub.name, args, params, "ok", "(simulated result)")

    # high risk ------------------------------------------------------------------------------------------------
    def _t_send_email(self, args: dict, state: RunState) -> ToolRecord:
        params = {"to": str(args["to"]), "subject": str(args.get("subject", "")), "body": str(args.get("body", ""))}
        return self._high_risk("send_email", args, params, state)

    def _t_send_payment(self, args: dict, state: RunState) -> ToolRecord:
        vendor = str(args["vendor"])
        amount = float(args["amount"]) if args.get("amount") is not None else None  # scripted steps may omit it
        params = {"vendor": vendor, "amount": amount, "account": args.get("account")}
        if self.registry_lookup is not None:
            account = self.registry_lookup(vendor, "account")
            if account is None:
                return ToolRecord("send_payment", args, params, "blocked", reason="vendor not in registry")
            params["account"] = account  # bound from the registry; the model's value is ignored (I10)
        if not params["account"]:
            return ToolRecord("send_payment", args, params, "error", reason="no account")
        return self._high_risk("send_payment", args, params, state)

    def _high_risk(self, tool: str, args: dict, params: dict, state: RunState) -> ToolRecord:
        if self.gate is not None:
            v = self.gate.allow(tool, params, list(state.context_ids), state.session)
            if not v.ok:
                return ToolRecord(tool, args, params, "blocked", "waiting for human approval", v.reason)
        self.outbox.append({"tool": tool, "params": params, "user": state.session.user_id})
        return ToolRecord(tool, args, params, "ok", "done")
