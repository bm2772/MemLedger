import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Bot, BrainCircuit, Globe, Lock, Mail, Plus, Send, Sparkles, UserRound, Wallet } from "lucide-react";
import { api, useApi, type AgentRun, type Overview, type ToolRecord } from "../api";
import { Badge, Callout, Card, Empty, Modal, PageHead, Seg, Spinner, useApp } from "../components/ui";

const TOOL_ICON: Record<string, typeof Bot> = { read_web: Globe, remember: BrainCircuit, send_payment: Wallet, send_email: Mail, search_docs: Sparkles };

export default function AgentPage({ ws }: { ws: string }) {
  const { config, me, switchUser, toast } = useApp();
  const loc = useLocation();
  const prefill = (loc.state as { task?: string; user?: string } | null) ?? null;
  const { data: o } = useApi<Overview>(`/workspaces/${ws}`);
  const status = useApi<{ reachable: boolean; available?: boolean; model: string; error?: string }>("/llm/status");
  const pages = useApi<{ url: string; content: string }[]>(`/workspaces/${ws}/web`);
  const [task, setTask] = useState(prefill?.task ?? "");
  const [llm, setLlm] = useState<"fake" | "server">("fake");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const runsKey = `memledger.runs.${ws}`;
  const [runs, setRuns] = useState<(AgentRun & { task: string; user: string })[]>(() => {
    try { return JSON.parse(sessionStorage.getItem(runsKey) ?? "[]"); } catch { return []; }
  });
  useEffect(() => { try { sessionStorage.setItem(runsKey, JSON.stringify(runs.slice(0, 10))); } catch { /* quota or private mode */ } }, [runs, runsKey]);
  const [addingPage, setAddingPage] = useState(false);
  useEffect(() => { if (prefill?.task) setTask(prefill.task); }, [prefill?.task]);

  const run = async () => {
    setBusy(true);
    try {
      const r = await api<AgentRun>(`/workspaces/${ws}/agent/run`, { body: { task, llm } });
      setRuns((rs) => [{ ...r, task, user: me.user_id }, ...rs]);
    } catch (e) { toast((e as Error).message, "bad"); }
    setBusy(false);
  };
  const wrongUser = prefill?.user && prefill.task === task && prefill.user !== me.user_id;

  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHead title="Agent" sub="A tool-using agent whose every read and write goes through this workspace's memory. High-risk actions pass the action gate; payment accounts are bound from the signed registry." />
      <div className="grid g-side">
        <div className="stack">
          <Card>
            <div className="stack">
              <textarea className="textarea" value={task} onChange={(e) => setTask(e.target.value)} placeholder="Give the agent a task, e.g. “Read https://… and remember anything useful.”"
                onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && task.trim() && !busy) run(); }} />
              {wrongUser && (
                <Callout tone="info" title={`This step is meant to run as ${prefill!.user}`}>
                  {config.auth === "open" ? <button className="btn sm" style={{ marginTop: 6 }} onClick={() => switchUser(prefill!.user!)}><UserRound />Switch to {prefill!.user}</button> : "Sign in as that user to follow the scenario."}
                </Callout>
              )}
              <div className="spread">
                <Seg value={llm} onChange={setLlm} options={[{ value: "fake", label: "Fooled test model" }, { value: "server", label: config.llm.model }]} />
                <button className="btn primary" disabled={busy || !task.trim()} onClick={run}>{busy ? <Spinner /> : <Send />}Run as {me.user_id}</button>
              </div>
              <div className="small faint">
                {llm === "fake" ? "Deterministic stand-in that believes everything it reads, so any difference comes from the memory layer."
                  : status.data?.reachable ? (status.data.available ? `${config.llm.model} is ready at ${config.llm.base_url}.` : `Server reachable, but ${config.llm.model} is not loaded.`) : `No model server at ${config.llm.base_url}.`}
              </div>
            </div>
          </Card>
          {busy && <Card><div className="row muted"><Spinner />Running… a real model can take a minute.</div></Card>}
          {runs.length === 0 && !busy ? <Card><Empty icon={<Bot />} title="No runs yet">The transcript shows every tool call as the model asked for it and as it was actually executed.</Empty></Card>
            : runs.map((r, i) => <RunView key={runs.length - i} r={r} />)}
        </div>
        <div className="stack">
          {o && o.tasks.length > 0 && (
            <Card title="Scenario steps">
              <div className="stack" style={{ gap: 10 }}>
                {o.tasks.map((t, i) => (
                  <button key={i} className="option" onClick={() => {
                    setTask(t.task);
                    nav(".", { replace: true, state: t });
                    if (config.auth === "open" && t.user !== me.user_id) switchUser(t.user);
                  }}>
                    <span className="small faint">Step {i + 1} · as {t.user}</span><span className="small">{t.task}</span>
                  </button>))}
              </div>
            </Card>
          )}
          <Card title="Web pages" sub="What read_web can fetch in this workspace" actions={<button className="btn sm" onClick={() => setAddingPage(true)}><Plus />Add</button>}>
            {!pages.data?.length ? <div className="small muted">No pages. Add one to test what the agent does with untrusted content.</div> : (
              <div className="stack" style={{ gap: 10 }}>{pages.data.map((p) => (
                <div key={p.url}><div className="mono small" style={{ color: "var(--info)" }}>{p.url}</div><div className="small muted">{p.content.slice(0, 160)}{p.content.length > 160 ? "…" : ""}</div></div>
              ))}</div>
            )}
          </Card>
        </div>
      </div>
      {addingPage && <AddPage ws={ws} onClose={() => setAddingPage(false)} onDone={pages.reload} />}
    </div>
  );
}

function RunView({ r }: { r: AgentRun & { task: string; user: string } }) {
  const executed = r.outbox.length;
  return (
    <Card title={<span className="row"><Badge tone="info">{r.user}</Badge><span className="clip" style={{ maxWidth: 460 }}>{r.task}</span></span>}
      sub={`${r.model} · ${r.steps} step(s) · ${r.context_ids.length} item(s) in context${r.tokens.prompt_tokens ? ` · ${r.tokens.prompt_tokens + r.tokens.completion_tokens} tokens` : ""}`}>
      <div className="timeline">
        {r.tool_calls.map((t, i) => <ToolStep key={i} t={t} />)}
        <div className="tl"><div className="rail"><i><Bot /></i></div><div className="body"><div className="small faint">Answer</div><div style={{ whiteSpace: "pre-wrap" }}>{r.answer || <span className="muted">(none)</span>}</div></div></div>
      </div>
      <hr className="sep" />
      <div className="small muted" style={{ marginTop: 8 }}>{executed ? `${executed} high-risk action(s) left the system.` : "No high-risk action left the system."}{r.written_claim_ids.length ? ` Memories touched: ${r.written_claim_ids.join(", ")}.` : ""}</div>
    </Card>
  );
}

function ToolStep({ t }: { t: ToolRecord }) {
  const I = TOOL_ICON[t.tool] ?? Bot;
  const bound = t.tool === "send_payment" && t.args.account !== undefined && t.args.account !== t.params.account;
  const tone = t.status === "ok" ? "ok" : t.status === "blocked" ? "bad" : "warn";
  return (
    <div className="tl">
      <div className="rail"><i style={{ color: `var(--${tone === "ok" ? "accent" : tone === "bad" ? "danger" : "warn"})` }}><I /></i><b /></div>
      <div className="body stack" style={{ gap: 6 }}>
        <div className="row"><code>{t.tool}</code><Badge tone={tone}>{t.status}</Badge>{t.reason && <span className="small muted">{t.reason}</span>}</div>
        <div className="small mono muted" style={{ wordBreak: "break-word" }}>{JSON.stringify(t.args)}</div>
        {bound && <Callout tone="ok" title={<span className="row"><Lock size={13} />Account bound from the signed registry</span>}>The model asked for <code>{String(t.args.account)}</code>; the payment used <code>{String(t.params.account)}</code>.</Callout>}
        {t.tool === "send_payment" && t.status === "ok" && !bound && <Callout tone="warn" title={`Paid account ${String(t.params.account)}`}>No registry binding in this workspace: the account came from the model.</Callout>}
        {t.result && t.tool !== "send_payment" && <div className="quote small" style={{ maxHeight: 140, overflow: "auto" }}>{t.result}</div>}
      </div>
    </div>
  );
}

function AddPage({ ws, onClose, onDone }: { ws: string; onClose: () => void; onDone: () => void }) {
  const { toast } = useApp();
  const [url, setUrl] = useState("https://");
  const [content, setContent] = useState("");
  const save = async () => {
    try { await api(`/workspaces/${ws}/web`, { method: "PUT", body: { url, content } }); onDone(); onClose(); }
    catch (e) { toast((e as Error).message, "bad"); }
  };
  return (
    <Modal title="Add a web page" onClose={onClose}>
      <div className="stack">
        <label className="field"><span>URL</span><input className="input mono" value={url} onChange={(e) => setUrl(e.target.value)} /></label>
        <label className="field"><span>Page text</span><textarea className="textarea" value={content} onChange={(e) => setContent(e.target.value)} /></label>
        <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn primary" disabled={!content.trim() || url.length < 9} onClick={save}>Save</button></div>
      </div>
    </Modal>
  );
}
