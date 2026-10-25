import { useState } from "react";
import { Search } from "lucide-react";
import { api, type Claim } from "../api";
import { Callout, Card, Empty, Id, PageHead, Spinner, StatusBadge, TrustBar, useApp } from "../components/ui";

type Hit = Claim & { sources: string[]; relevance: number };

export default function Recall({ ws }: { ws: string }) {
  const { me, toast } = useApp();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[] | null>(null);
  const [busy, setBusy] = useState(false);
  const go = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try { setHits(await api<Hit[]>(`/workspaces/${ws}/recall`, { body: { query: q, k: 10 } })); }
    catch (err) { toast((err as Error).message, "bad"); }
    setBusy(false);
  };
  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHead title="Recall" sub="Exactly what the agent would be shown for a query: team-scoped, access-filtered and hash-verified on read." />
      <form className="row" style={{ flexWrap: "nowrap" }} onSubmit={go}>
        <input className="input grow" autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Acme bank account" />
        <button className="btn primary" disabled={busy || !q.trim()}>{busy ? <Spinner /> : <Search />}Recall</button>
      </form>
      <Callout>Results are for <b>{me.user_id}</b> ({me.team}, clearance {me.clearance}). Another team sees different memories.</Callout>
      {hits && (
        <Card pad={false} title={`${hits.length} memories`}>
          {hits.length === 0 ? <Empty icon={<Search />} title="Nothing recalled">Either nothing matches, or you may not read it.</Empty> : (
            <div className="table-wrap"><table className="t">
              <thead><tr><th>Memory</th><th>Status</th><th>Trust</th><th>Relevance</th><th>Sources</th></tr></thead>
              <tbody>{hits.map((h) => (
                <tr key={h.id}><td><div>{h.text}</div><Id id={h.id} /></td><td><StatusBadge status={h.status} /></td><td><TrustBar value={h.trust} /></td><td className="mono muted">{h.relevance.toFixed(3)}</td><td className="small faint">{h.sources.join(", ") || "-"}</td></tr>
              ))}</tbody>
            </table></div>
          )}
        </Card>
      )}
    </div>
  );
}
