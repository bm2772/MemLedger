import { useCallback, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Brain, CheckCircle2, FilePlus2, Fingerprint, Plus, Search, ShieldAlert, XCircle } from "lucide-react";
import { api, useApi, when, type Claim, type ClaimDetail, type Source, type Verdict } from "../api";
import { LineageGraph } from "../components/LineageGraph";
import { Badge, Callout, Card, Drawer, Empty, Id, Modal, PageHead, Seg, Spinner, StatusBadge, TrustBar, useApp } from "../components/ui";

export default function Memories({ ws }: { ws: string }) {
  const { claim } = useParams();
  const nav = useNavigate();
  const claims = useApi<Claim[]>(`/workspaces/${ws}/claims`);
  const sources = useApi<Source[]>(`/workspaces/${ws}/sources`);
  const [filter, setFilter] = useState<"all" | "live" | "quarantined">("all");
  const [q, setQ] = useState("");
  const [writing, setWriting] = useState(false);
  const rows = useMemo(() => (claims.data ?? []).filter((c) =>
    (filter === "all" || (filter === "quarantined" ? c.status === "quarantined" : c.status !== "quarantined"))
    && (!q || c.text.toLowerCase().includes(q.toLowerCase()) || c.id.includes(q))), [claims.data, filter, q]);
  const reload = () => { claims.reload(); sources.reload(); };

  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHead title="Memories" sub="Every fact the agent stored, with its trust and status. Click one to see where it came from."
        actions={<button className="btn primary" onClick={() => setWriting(true)}><Plus />Propose memory</button>} />
      <Card pad={false} title={<div className="row"><Seg value={filter} onChange={setFilter} options={[{ value: "all", label: "All" }, { value: "live", label: "Live" }, { value: "quarantined", label: "Quarantined" }]} /></div>}
        actions={<div style={{ position: "relative", width: 240 }}><Search size={14} style={{ position: "absolute", left: 10, top: 11, color: "var(--faint)" }} /><input className="input" style={{ paddingLeft: 30 }} placeholder="Search memories" value={q} onChange={(e) => setQ(e.target.value)} /></div>}>
        {!claims.data ? <div className="card-pad"><Spinner /></div> : rows.length === 0 ? (
          <Empty icon={<Brain />} title={claims.data.length ? "No memories match" : "No memories yet"}>{claims.data.length ? "Try another filter." : "Run the agent or propose a memory from a source."}</Empty>
        ) : (
          <div className="table-wrap"><table className="t">
            <thead><tr><th>Memory</th><th>Status</th><th>Trust</th><th>Derivations</th><th>Recorded</th></tr></thead>
            <tbody>{rows.map((c) => (
              <tr key={c.id} className={`click ${claim === c.id ? "sel" : ""}`} onClick={() => nav(`/w/${ws}/memories/${c.id}`)}>
                <td style={{ maxWidth: 520 }}><div>{c.text}</div><Id id={c.id} /></td>
                <td><StatusBadge status={c.status} /></td>
                <td><TrustBar value={c.trust} /></td>
                <td className="muted">{c.derivations}</td>
                <td className="small faint" style={{ whiteSpace: "nowrap" }}>{when(c.recorded_at)}</td>
              </tr>))}
            </tbody>
          </table></div>
        )}
      </Card>
      {claim && <ClaimDrawer ws={ws} id={claim} sources={sources.data ?? []} onClose={() => nav(`/w/${ws}/memories`)} onChanged={reload} />}
      {writing && <ProposeWrite ws={ws} sources={sources.data ?? []} claims={claims.data ?? []} onClose={() => setWriting(false)} onDone={reload} />}
    </div>
  );
}

function ClaimDrawer({ ws, id, sources, onClose, onChanged }: { ws: string; id: string; sources: Source[]; onClose: () => void; onChanged: () => void }) {
  const { data: d, error, reload } = useApi<ClaimDetail>(`/workspaces/${ws}/claims/${id}`);
  const nav = useNavigate();
  const { toast } = useApp();
  const [pick, setPick] = useState("");
  const text = useCallback((sid: string) => sources.find((s) => s.id === sid)?.content, [sources]);
  const addEvidence = async () => {
    try {
      const r = await api<{ restored: string[]; quarantined: string[] }>(`/workspaces/${ws}/claims/${id}/evidence`, { body: { source_ids: [pick] } });
      toast(r.restored.length ? `Restored ${r.restored.length} memory(ies)` : "Evidence recorded", "ok");
      setPick(""); reload(); onChanged();
    } catch (e) { toast((e as Error).message, "bad"); }
  };
  return (
    <Drawer title={d ? <span className="row"><StatusBadge status={d.status} /><span className="clip" style={{ maxWidth: 420 }}>{d.text}</span></span> : "Memory"} onClose={onClose}>
      {error ? <Callout tone="bad" title="Not found">{error.message}</Callout> : !d ? <Spinner /> : <>
        <div className="grid g3">
          <div className="card kpi"><div className="label">Trust</div><div className="value" style={{ fontSize: 22 }}>{d.trust.toFixed(3)}</div><div className="hint">T = s · min(parent trust)</div></div>
          <div className="card kpi"><div className="label">Integrity on read</div><div className="value" style={{ fontSize: 18, marginTop: 10 }}>
            {d.verified === null ? <span className="muted">not checked</span> : d.verified ? <span style={{ color: "var(--accent)" }}><CheckCircle2 size={16} style={{ verticalAlign: -2 }} /> hash ok</span> : <span style={{ color: "var(--danger)" }}><XCircle size={16} style={{ verticalAlign: -2 }} /> mismatch</span>}
          </div><div className="hint">SHA-256 chain + signed root</div></div>
          <div className="card kpi"><div className="label">Labels</div><div className="value" style={{ fontSize: 16, marginTop: 10 }}>{d.labels.team}</div><div className="hint">confidentiality {d.labels.confidentiality}</div></div>
        </div>
        {d.status === "quarantined" && <Callout tone="bad" title="Quarantined: withheld from every read">{d.history.at(-1)?.reason}</Callout>}
        <Card title="Lineage" sub="Solid = verified support · dashed = only in the context window · red = flagged or quarantined" pad={false}>
          <div style={{ padding: 12 }}><LineageGraph explain={d.explain} sourceText={text} onOpen={(cid) => nav(`/w/${ws}/memories/${cid}`)} /></div>
        </Card>
        <Card title="Add independent evidence" sub="A new justification from a valid source can restore a quarantined memory (JTMS).">
          <div className="row" style={{ flexWrap: "nowrap" }}>
            <select className="select grow" value={pick} onChange={(e) => setPick(e.target.value)}>
              <option value="">Choose a source…</option>
              {sources.filter((s) => !s.flagged).map((s) => <option key={s.id} value={s.id}>[{s.kind}] {s.content.slice(0, 80)}</option>)}
            </select>
            <button className="btn" disabled={!pick} onClick={addEvidence}><FilePlus2 />Add</button>
          </div>
        </Card>
        <Card title="Status history" pad={false}>
          <div className="table-wrap"><table className="t"><tbody>{d.history.map((h) => (
            <tr key={h.seq}><td style={{ width: 120 }}><StatusBadge status={h.status} /></td><td>{h.reason}</td><td className="mono faint">{h.trust?.toFixed(2) ?? ""}</td><td className="small faint" style={{ whiteSpace: "nowrap" }}>{when(h.at)}</td></tr>
          ))}</tbody></table></div>
        </Card>
        <div className="stack" style={{ gap: 4 }}><span className="small muted row"><Fingerprint size={13} />Content hash</span><div className="hash">{d.content_hash}</div><Id id={d.id} /></div>
      </>}
    </Drawer>
  );
}

function ProposeWrite({ ws, sources, claims, onClose, onDone }: { ws: string; sources: Source[]; claims: Claim[]; onClose: () => void; onDone: () => void }) {
  const { toast } = useApp();
  const [text, setText] = useState("");
  const [ctx, setCtx] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<{ accepted: boolean; claim_ids: string[]; verdicts: Verdict[] } | null>(null);
  const toggle = (id: string) => setCtx((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c, id]));
  const submit = async () => {
    setBusy(true);
    try {
      const r = await api<typeof res>(`/workspaces/${ws}/claims`, { body: { text, context_ids: ctx } });
      setRes(r); onDone();
      toast(r!.accepted ? "Stored" : "Refused by the write checks", r!.accepted ? "ok" : "bad");
    } catch (e) { toast((e as Error).message, "bad"); }
    setBusy(false);
  };
  const items = [...sources.map((s) => ({ id: s.id, label: s.content, tag: s.kind, bad: s.flagged })),
    ...claims.filter((c) => c.status !== "quarantined").map((c) => ({ id: c.id, label: c.text, tag: "memory", bad: false }))];
  return (
    <Modal title="Propose a memory" onClose={onClose}>
      <div className="stack">
        <label className="field"><span>Fact to remember</span><textarea className="textarea" style={{ minHeight: 70 }} value={text} onChange={(e) => setText(e.target.value)} placeholder="One atomic fact, e.g. “The Orion cluster has 64 nodes”" /></label>
        <div className="field"><span>Context it was derived from ({ctx.length} selected)</span>
          <div className="card" style={{ maxHeight: 200, overflowY: "auto" }}>
            {items.length === 0 ? <div className="card-pad small muted">No sources yet. Ingest one on the Sources page.</div> : items.map((i) => (
              <label key={i.id} className="row" style={{ padding: "8px 12px", borderBottom: "1px solid var(--line)", flexWrap: "nowrap", cursor: "pointer" }}>
                <input type="checkbox" checked={ctx.includes(i.id)} onChange={() => toggle(i.id)} />
                <Badge tone={i.bad ? "bad" : "outline"}>{i.tag}</Badge><span className="small clip grow">{i.label}</span>
              </label>))}
          </div>
        </div>
        {res && (
          <div className="stack" style={{ gap: 6 }}>
            <Callout tone={res.accepted ? "ok" : "bad"} title={res.accepted ? `Stored as ${res.claim_ids.join(", ")}` : "Refused"} />
            {res.verdicts.map((v, i) => (
              <div key={i} className="spread small"><span className="row">{v.ok ? <CheckCircle2 size={14} color="var(--accent)" /> : <ShieldAlert size={14} color="var(--danger)" />}<b>{v.check}</b><span className="muted">{v.reason}</span></span><span className="mono faint">{v.score.toFixed(2)}</span></div>
            ))}
          </div>
        )}
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn ghost" onClick={onClose}>Close</button>
          <button className="btn primary" disabled={busy || !text.trim()} onClick={submit}>{busy ? <Spinner /> : <Plus />}Run write checks</button>
        </div>
      </div>
    </Modal>
  );
}
