import { Link, useNavigate } from "react-router-dom";
import { AlertOctagon, Brain, CheckCircle2, Database, Fingerprint, Play, ShieldCheck, ShieldOff } from "lucide-react";
import { useApi, when, type Overview as O } from "../api";
import { Badge, Callout, Card, Empty, PageHead, PROTECTION_LABEL, Spinner, StatusBadge, useApp, VERSION_LABEL } from "../components/ui";

const ALL = ["provenance", "hash_chain", "jtms", "team_scope", "input_screen", "write_checks", "access_control", "action_gate", "registry"];

export default function Overview({ ws }: { ws: string }) {
  const { data: o, error } = useApi<O>(`/workspaces/${ws}`);
  const { config } = useApp();
  const nav = useNavigate();
  if (error) return <Callout tone="bad" title="Could not load the workspace">{error.message}</Callout>;
  if (!o) return <Spinner />;
  const quarantined = o.by_status.quarantined ?? 0;
  const maxH = Math.max(1, ...o.trust_histogram);
  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHead title={o.name} sub={o.description || undefined}
        actions={<><Link className="btn" to={`/w/${ws}/memories`}><Brain />Memories</Link><Link className="btn primary" to={`/w/${ws}/agent`}><Play />Run the agent</Link></>} />

      {o.version === "baseline" && <Callout tone="warn" title="This workspace runs as plain memory">Nothing is screened, checked, scoped or verified. Use it to compare against a protected workspace.</Callout>}

      <div className="grid g4">
        <Kpi icon={<Brain size={14} />} label="Memories" value={o.memories} hint={`${o.by_status.active ?? 0} active · ${o.by_status.restored ?? 0} restored`} />
        <Kpi icon={<AlertOctagon size={14} />} label="Quarantined" value={quarantined} hint="withheld from every read" tone={quarantined ? "var(--danger)" : undefined} />
        <Kpi icon={<Database size={14} />} label="Sources" value={o.sources} hint={`${o.flagged_sources} flagged`} tone={o.flagged_sources ? "var(--warn)" : undefined} />
        <div className="card kpi">
          <div className="label"><Fingerprint size={14} />Ledger integrity</div>
          <div className="value" style={{ fontSize: 20, marginTop: 10 }}>
            {o.chain.ok === null ? <span className="muted">No writes yet</span> : o.chain.ok ? <span style={{ color: "var(--accent)" }}><CheckCircle2 size={18} style={{ verticalAlign: -3 }} /> Verified</span> : <span style={{ color: "var(--danger)" }}>Broken</span>}
          </div>
          <div className="hint mono clip" title={o.chain.root ?? ""}>{o.chain.root ? `root ${o.chain.root.slice(0, 16)}… · #${o.chain.anchors}` : "signed Merkle root after each write"}</div>
        </div>
      </div>

      <div className="grid g-side">
        <div className="stack">
          {o.tasks.length > 0 && (
            <Card title="Try it" sub="Suggested steps for this template. Each runs the agent as the named user.">
              <div className="stack">
                {o.tasks.map((t, i) => (
                  <div key={i} className="spread" style={{ gap: 14 }}>
                    <div className="row grow" style={{ flexWrap: "nowrap" }}><Badge tone="info">{i + 1}</Badge><div className="grow"><div className="small faint">as {t.user}</div><div>{t.task}</div></div></div>
                    <button className="btn sm" onClick={() => nav(`/w/${ws}/agent`, { state: t })}><Play />Open</button>
                  </div>
                ))}
              </div>
            </Card>
          )}
          <Card title="Recent activity" pad={false}>
            {o.activity.length === 0 ? <Empty icon={<Database />} title="Nothing yet">Ingest a source or run the agent.</Empty> : (
              <div className="table-wrap"><table className="t"><tbody>
                {o.activity.map((a, i) => (
                  <tr key={i}><td style={{ width: 110 }} className="small faint">{when(a.at)}</td><td><b>{a.user}</b> <span className="muted">{describe(a)}</span></td></tr>
                ))}
              </tbody></table></div>
            )}
          </Card>
        </div>
        <div className="stack">
          <Card title="Protection" sub={VERSION_LABEL[o.version]}>
            <div className="stack" style={{ gap: 8 }}>
              {ALL.map((p) => {
                const on = o.protections.includes(p);
                return <div key={p} className="spread small"><span className={on ? "" : "faint"}>{PROTECTION_LABEL[p]}</span>{on ? <ShieldCheck size={15} color="var(--accent)" /> : <ShieldOff size={15} color="var(--faint)" />}</div>;
              })}
              <hr className="sep" />
              <div className="small faint">Guard models: {config.guard_backend}. Registry entries: {o.registry_entries}. Web pages: {o.web_pages}.</div>
            </div>
          </Card>
          <Card title="Trust distribution" sub="Live memories by JTMS trust">
            <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 110 }}>
              {o.trust_histogram.map((n, i) => (
                <div key={i} style={{ flex: 1, display: "grid", gap: 6, justifyItems: "center" }}>
                  <span className="small faint">{n}</span>
                  <div style={{ width: "100%", height: `${(n / maxH) * 70 + 2}px`, borderRadius: 6, background: i >= 4 ? "var(--accent)" : i >= 2 ? "var(--warn)" : "var(--danger)", opacity: n ? 0.9 : 0.25 }} />
                  <span className="small faint mono">{(i / 5).toFixed(1)}</span>
                </div>
              ))}
            </div>
          </Card>
          <Card title="Status">
            <div className="row">{Object.entries(o.by_status).filter(([, n]) => n).map(([s, n]) => <span key={s} className="row" style={{ gap: 4 }}><StatusBadge status={s} /><b className="small">{n}</b></span>)}{o.memories === 0 && <span className="muted small">No memories yet</span>}</div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Kpi({ icon, label, value, hint, tone }: { icon: React.ReactNode; label: string; value: number; hint: string; tone?: string }) {
  return <div className="card kpi"><div className="label">{icon}{label}</div><div className="value" style={{ color: tone }}>{value}</div><div className="hint">{hint}</div></div>;
}

export function describe(a: Record<string, unknown>): string {
  switch (a.action) {
    case "ingest": return `ingested a ${a.kind} source${a.flagged ? " (flagged by the input screen)" : ""}`;
    case "write": return `${a.accepted ? "stored" : "was refused"}: “${a.text}”`;
    case "flag_source": return `flagged ${a.source}: ${(a.quarantined as string[])?.length ?? 0} quarantined, ${(a.restored as string[])?.length ?? 0} restored`;
    case "agent_run": return `ran the agent (${(a.tools as string[])?.join(", ") || "no tools"})${a.outbox ? `, ${a.outbox} action(s) executed` : ""}`;
    case "evidence": return `added evidence for ${a.claim}`;
    case "registry": return `signed a registry change: ${a.key}`;
    case "verify": return `verified ${a.checked} memories, ${(a.failed as string[])?.length ?? 0} failed`;
    case "create_workspace": return `created the workspace (${a.version}, ${a.sample})`;
    case "web_page": return `published a web page ${a.url}`;
    case "sample": return "loaded the sample data";
    default: return String(a.action);
  }
}
