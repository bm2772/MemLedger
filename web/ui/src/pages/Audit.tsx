import { useState } from "react";
import { Download, ShieldCheck } from "lucide-react";
import { api, useApi, when, type Activity, type StatusRow } from "../api";
import { Callout, Card, PageHead, Seg, Spinner, StatusBadge, useApp } from "../components/ui";
import { describe } from "./Overview";

type AuditData = { status_log: StatusRow[]; hash_log: { seq: number; root: string; signature: string; n_items: number; at: string }[]; activity: Activity[] };

export default function Audit({ ws }: { ws: string }) {
  const { data, reload } = useApi<AuditData>(`/workspaces/${ws}/audit`);
  const { toast } = useApp();
  const [tab, setTab] = useState<"activity" | "status" | "hash">("activity");
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState<{ enabled: boolean; checked: number; failed: string[]; chain_ok?: boolean } | null>(null);
  const verify = async () => {
    setVerifying(true);
    try { setResult(await api(`/workspaces/${ws}/verify`, { body: {} })); reload(); }
    catch (e) { toast((e as Error).message, "bad"); }
    setVerifying(false);
  };
  const exportJson = async () => {
    try {
      const doc = await api(`/workspaces/${ws}/export`);
      const url = URL.createObjectURL(new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" }));
      Object.assign(document.createElement("a"), { href: url, download: `memledger-${ws}.json` }).click();
      URL.revokeObjectURL(url);
    } catch (e) { toast((e as Error).message, "bad"); }
  };
  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHead title="Audit & integrity" sub="Content is append-only. Status changes go to an audited log, and a signed Merkle root is appended after every write batch."
        actions={<><button className="btn" onClick={exportJson}><Download />Export</button><button className="btn primary" disabled={verifying} onClick={verify}>{verifying ? <Spinner /> : <ShieldCheck />}Verify all memories</button></>} />
      {result && (!result.enabled ? <Callout tone="warn" title="Hash verification is off in this protection level" />
        : result.failed.length ? <Callout tone="bad" title={`${result.failed.length} of ${result.checked} memories failed and were quarantined`}>{result.failed.join(", ")}</Callout>
          : <Callout tone="ok" title={`All ${result.checked} live memories verified`}>Hashes recomputed from stored content and checked against the latest signed root{result.chain_ok ? "; the hash log is intact." : "."}</Callout>)}
      <Seg value={tab} onChange={setTab} options={[{ value: "activity", label: "Console activity" }, { value: "status", label: "Status log" }, { value: "hash", label: "Hash log" }]} />
      <Card pad={false}>
        {!data ? <div className="card-pad"><Spinner /></div> : <div className="table-wrap"><table className="t">
          {tab === "activity" && <><thead><tr><th>When</th><th>User</th><th>Event</th></tr></thead><tbody>{data.activity.map((a, i) => <tr key={i}><td className="small faint" style={{ whiteSpace: "nowrap" }}>{when(a.at)}</td><td><b>{a.user}</b></td><td className="muted">{describe(a)}</td></tr>)}</tbody></>}
          {tab === "status" && <><thead><tr><th>#</th><th>Entity</th><th>Status</th><th>Reason</th><th>Trust</th><th>When</th></tr></thead><tbody>{data.status_log.map((r) => <tr key={r.seq}><td className="mono faint">{r.seq}</td><td><code>{r.entity_id}</code></td><td><StatusBadge status={r.status} /></td><td>{r.reason}</td><td className="mono faint">{r.trust?.toFixed(2) ?? ""}</td><td className="small faint" style={{ whiteSpace: "nowrap" }}>{when(r.at)}</td></tr>)}</tbody></>}
          {tab === "hash" && <><thead><tr><th>#</th><th>Merkle root</th><th>Items</th><th>Signature</th><th>When</th></tr></thead><tbody>{data.hash_log.map((r) => <tr key={r.seq}><td className="mono faint">{r.seq}</td><td className="hash">{r.root}</td><td>{r.n_items}</td><td className="hash clip" style={{ maxWidth: 200 }}>{r.signature}</td><td className="small faint" style={{ whiteSpace: "nowrap" }}>{when(r.at)}</td></tr>)}</tbody></>}
        </table></div>}
      </Card>
    </div>
  );
}
