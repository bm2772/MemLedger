import { useState } from "react";
import { BookLock, KeyRound, Plus } from "lucide-react";
import { api, useApi, when } from "../api";
import { Badge, Callout, Card, Empty, Modal, PageHead, useApp } from "../components/ui";

type Reg = { used: boolean; signed_by: string | null; signed_at: string | null; signature: string | null;
  entries: { key: string; value: string; confidentiality: number; owner: string; valid_from: string }[] };

export default function Registry({ ws }: { ws: string }) {
  const { data, reload } = useApi<Reg>(`/workspaces/${ws}/registry`);
  const { me } = useApp();
  const [adding, setAdding] = useState(false);
  const latest = new Map<string, string>();
  for (const e of data?.entries ?? []) if (!latest.has(e.key) || latest.get(e.key)! < e.valid_from) latest.set(e.key, e.valid_from);
  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHead title="Signed registry" sub="Protected facts with exactly one correct value: bank accounts, contacts, limits. High-risk tool parameters are bound from here, never from model text."
        actions={me.admin ? <button className="btn primary" onClick={() => setAdding(true)}><Plus />Set value</button> : <Badge tone="outline"><KeyRound size={12} />registry-admin only</Badge>} />
      {data && !data.used && <Callout tone="warn" title="This workspace does not use the registry">Only the full protection level checks writes and binds payments against it.</Callout>}
      {data?.signature && (
        <Card><div className="row" style={{ gap: 18 }}>
          <div><div className="small muted">Signed by</div><b>{data.signed_by}</b></div>
          <div><div className="small muted">Signed</div><b>{when(data.signed_at)}</b></div>
          <div className="grow"><div className="small muted">Ed25519 signature</div><div className="hash clip">{data.signature}</div></div>
        </div></Card>
      )}
      <Card pad={false}>
        {!data?.entries.length ? <Empty icon={<BookLock />} title="No entries">An admin can add the facts agents must never take from text, such as a vendor's bank account.</Empty> : (
          <div className="table-wrap"><table className="t">
            <thead><tr><th>Key</th><th>Value</th><th>Confidentiality</th><th>Owner</th><th>Valid from</th></tr></thead>
            <tbody>{[...data.entries].reverse().map((e, i) => {
              const current = latest.get(e.key) === e.valid_from;
              return (
                <tr key={i} style={{ opacity: current ? 1 : 0.5 }}>
                  <td><code>{e.key}</code></td><td><b className="mono">{e.value}</b> {!current && <Badge>superseded</Badge>}</td>
                  <td>{e.confidentiality}</td><td className="muted">{e.owner || "system"}</td><td className="small faint">{e.valid_from.startsWith("1970") ? "always" : when(e.valid_from)}</td>
                </tr>);
            })}</tbody>
          </table></div>
        )}
      </Card>
      {adding && <SetValue ws={ws} onClose={() => setAdding(false)} onDone={reload} />}
    </div>
  );
}

function SetValue({ ws, onClose, onDone }: { ws: string; onClose: () => void; onDone: () => void }) {
  const { toast } = useApp();
  const [f, setF] = useState({ subject: "", field: "account", value: "", confidentiality: 0 });
  const save = async () => {
    try { await api(`/workspaces/${ws}/registry`, { body: f }); toast("Registry re-signed", "ok"); onDone(); onClose(); }
    catch (e) { toast((e as Error).message, "bad"); }
  };
  return (
    <Modal title="Set a registry value" onClose={onClose}>
      <div className="stack">
        <div className="grid g2">
          <label className="field"><span>Subject</span><input className="input" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} placeholder="Acme Ltd" /></label>
          <label className="field"><span>Field</span><input className="input" value={f.field} onChange={(e) => setF({ ...f, field: e.target.value })} /></label>
        </div>
        <label className="field"><span>Value</span><input className="input mono" value={f.value} onChange={(e) => setF({ ...f, value: e.target.value })} /></label>
        <label className="field"><span>Confidentiality</span><input className="input" type="number" min={0} max={5} value={f.confidentiality} onChange={(e) => setF({ ...f, confidentiality: Number(e.target.value) })} /></label>
        <Callout>The previous value is kept as history; the whole registry is re-signed with your identity.</Callout>
        <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn primary" disabled={!f.subject.trim() || !f.value.trim()} onClick={save}>Sign and save</button></div>
      </div>
    </Modal>
  );
}
