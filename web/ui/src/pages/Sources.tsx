import { useState } from "react";
import { Database, Flag, Plus } from "lucide-react";
import { api, useApi, when, type Source } from "../api";
import { Badge, Callout, Card, Empty, Id, Modal, PageHead, Spinner, StatusBadge, TrustBar, useApp } from "../components/ui";

const KIND_HELP: Record<string, string> = {
  paper: "Peer-reviewed paper", registry: "Company registry extract", internal: "Internal document", user: "Note from a person",
  tool: "Tool or API output", web: "Web page (untrusted)", agent: "Another agent", model_parametric: "The model's own knowledge",
};

export default function Sources({ ws }: { ws: string }) {
  const { data, reload } = useApi<Source[]>(`/workspaces/${ws}/sources`);
  const [adding, setAdding] = useState(false);
  const [flagging, setFlagging] = useState<Source | null>(null);
  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHead title="Sources" sub="Everything the agent read. Each source starts at its kind's prior trust; flagging one retracts every memory that depended only on it."
        actions={<button className="btn primary" onClick={() => setAdding(true)}><Plus />Ingest source</button>} />
      <Card pad={false}>
        {!data ? <div className="card-pad"><Spinner /></div> : data.length === 0 ? <Empty icon={<Database />} title="No sources yet">Ingest a document, or let the agent read a web page.</Empty> : (
          <div className="table-wrap"><table className="t">
            <thead><tr><th>Content</th><th>Kind</th><th>Prior trust</th><th>Status</th><th>Recorded</th><th /></tr></thead>
            <tbody>{data.map((s) => (
              <tr key={s.id}>
                <td style={{ maxWidth: 520 }}><div>{s.content.length > 220 ? s.content.slice(0, 217) + "…" : s.content}</div><Id id={s.id} /></td>
                <td><Badge tone={s.kind === "web" ? "warn" : "outline"}>{s.kind}</Badge></td>
                <td><TrustBar value={s.prior_trust} /></td>
                <td>{s.flagged ? <StatusBadge status="flagged" /> : <StatusBadge status="active" />}</td>
                <td className="small faint" style={{ whiteSpace: "nowrap" }}>{when(s.recorded_at)}</td>
                <td>{!s.flagged && <button className="btn sm danger" onClick={() => setFlagging(s)}><Flag />Flag</button>}</td>
              </tr>))}
            </tbody>
          </table></div>
        )}
      </Card>
      {adding && <IngestModal ws={ws} onClose={() => setAdding(false)} onDone={reload} />}
      {flagging && <FlagModal ws={ws} source={flagging} onClose={() => setFlagging(null)} onDone={reload} />}
    </div>
  );
}

function IngestModal({ ws, onClose, onDone }: { ws: string; onClose: () => void; onDone: () => void }) {
  const { config, toast } = useApp();
  const [kind, setKind] = useState("user");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<Source | null>(null);
  const submit = async () => {
    setBusy(true);
    try { const s = await api<Source>(`/workspaces/${ws}/sources`, { body: { content, kind } }); setRes(s); onDone(); }
    catch (e) { toast((e as Error).message, "bad"); }
    setBusy(false);
  };
  return (
    <Modal title="Ingest a source" onClose={onClose}>
      <div className="stack">
        <label className="field"><span>Kind</span>
          <select className="select" value={kind} onChange={(e) => setKind(e.target.value)}>
            {config.kinds.map((k) => <option key={k} value={k}>{KIND_HELP[k] ?? k}</option>)}
          </select>
        </label>
        <label className="field"><span>Content</span><textarea className="textarea" value={content} onChange={(e) => setContent(e.target.value)} placeholder="Paste the text the agent read" /></label>
        {res && (res.flagged
          ? <Callout tone="bad" title="Flagged on arrival by the input screen">{res.screen} It is stored for the audit trail but can never support a memory.</Callout>
          : <Callout tone="ok" title={`Stored as ${res.id}`}>Prior trust {res.prior_trust.toFixed(2)}. Your team, role and clearance were taken from your login.</Callout>)}
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn ghost" onClick={onClose}>Close</button>
          <button className="btn primary" disabled={busy || !content.trim()} onClick={submit}>{busy ? <Spinner /> : <Plus />}Ingest</button>
        </div>
      </div>
    </Modal>
  );
}

function FlagModal({ ws, source, onClose, onDone }: { ws: string; source: Source; onClose: () => void; onDone: () => void }) {
  const { toast } = useApp();
  const [reason, setReason] = useState("found to be poisoned");
  const [res, setRes] = useState<{ quarantined: string[]; restored: string[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try { setRes(await api(`/workspaces/${ws}/sources/${source.id}/flag`, { body: { reason } })); onDone(); }
    catch (e) { toast((e as Error).message, "bad"); }
    setBusy(false);
  };
  return (
    <Modal title="Flag source as poisoned" onClose={onClose}>
      <div className="stack">
        <div className="quote">{source.content}</div>
        {!res ? <>
          <label className="field"><span>Reason (kept in the audit log)</span><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} /></label>
          <Callout tone="warn">The JTMS will quarantine every memory with no valid justification left, and keep memories that other sources still support.</Callout>
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button className="btn ghost" onClick={onClose}>Cancel</button>
            <button className="btn danger" disabled={busy || !reason.trim()} onClick={submit}>{busy ? <Spinner /> : <Flag />}Flag and retract</button>
          </div>
        </> : <>
          <Callout tone={res.quarantined.length ? "bad" : "ok"} title={`${res.quarantined.length} memory(ies) quarantined, ${res.restored.length} restored`}>
            {res.quarantined.length ? res.quarantined.join(", ") : "Nothing depended only on this source."}
          </Callout>
          <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn primary" onClick={onClose}>Done</button></div>
        </>}
      </div>
    </Modal>
  );
}
