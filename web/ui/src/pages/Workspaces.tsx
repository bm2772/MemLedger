import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Boxes, FlaskConical, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { api, useApi, when, type WorkspaceSummary } from "../api";
import { Badge, Empty, Modal, PageHead, Spinner, useApp, VERSION_LABEL } from "../components/ui";

/** Optional brand media: drop web/ui/public/brand/hero.mp4 (or hero.jpg) in and it plays behind the hero. */
function HeroMedia() {
  const [video, setVideo] = useState(true);
  const [img, setImg] = useState(true);
  if (video) return <video className="hero-media" src="/brand/hero.mp4" autoPlay muted loop playsInline onError={() => setVideo(false)} />;
  if (img) return <img className="hero-media" src="/brand/hero.jpg" alt="" onError={() => setImg(false)} />;
  return null;
}

export default function Workspaces() {
  const { data, loading, reload } = useApi<WorkspaceSummary[]>("/workspaces");
  const [creating, setCreating] = useState(false);
  const nav = useNavigate();
  const { me, toast } = useApp();

  const remove = async (w: WorkspaceSummary) => {
    if (!confirm(`Delete "${w.name}" and all its memory? This cannot be undone.`)) return;
    try { await api(`/workspaces/${w.id}`, { method: "DELETE" }); toast("Workspace deleted", "ok"); reload(); }
    catch (e) { toast((e as Error).message, "bad"); }
  };

  return (
    <div className="page stack" style={{ gap: 24 }}>
      <section className="hero">
        <HeroMedia />
        <Badge tone="ok" dot>Provenance-governed memory</Badge>
        <h1 style={{ marginTop: 14 }}>Every memory your agent keeps has a source, a trust score and an audit trail.</h1>
        <p>MemLedger screens what agents read, checks what they remember, quarantines whatever depended on a poisoned source, and detects tampering on every read.</p>
        <div className="row" style={{ marginTop: 20 }}>
          <button className="btn primary" onClick={() => setCreating(true)}><Plus />New workspace</button>
          <button className="btn" onClick={() => nav("/lab")}><FlaskConical />Open the attack lab</button>
        </div>
      </section>

      <div>
        <PageHead title="Workspaces" sub="Each workspace is one persistent, signed memory, run as one of the five protection levels." />
        {loading && !data ? <div className="grid g3">{[0, 1, 2].map((i) => <div key={i} className="card card-pad stack"><div className="skeleton" style={{ width: "60%" }} /><div className="skeleton" /></div>)}</div>
          : !data?.length ? (
            <div className="card"><Empty icon={<Boxes />} title="No workspaces yet">Create one from a template to see MemLedger stop a poisoned web page.<div style={{ marginTop: 14 }}><button className="btn primary" onClick={() => setCreating(true)}><Plus />New workspace</button></div></Empty></div>
          ) : (
            <div className="grid g3">
              {data.map((w) => (
                <div key={w.id} className="card ws-card" onClick={() => nav(`/w/${w.id}`)} role="link" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && nav(`/w/${w.id}`)}>
                  <div className="spread"><b className="clip">{w.name}</b><ArrowRight size={16} className="faint" /></div>
                  <div className="small muted" style={{ minHeight: 38 }}>{w.description || "—"}</div>
                  <div className="spread">
                    <Badge tone={w.version === "baseline" ? "bad" : w.version === "full" ? "ok" : "info"}>{w.version === "baseline" ? null : <ShieldCheck size={12} />}{VERSION_LABEL[w.version]}</Badge>
                    <div className="row"><span className="small faint">{when(w.created_at)}</span>
                      {me.admin && <button className="btn ghost sm icon" aria-label={`Delete ${w.name}`} onClick={(e) => { e.stopPropagation(); remove(w); }}><Trash2 /></button>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
      </div>
      {creating && <CreateWorkspace onClose={() => setCreating(false)} onCreated={(id) => nav(`/w/${id}`)} />}
    </div>
  );
}

function CreateWorkspace({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const { config, toast } = useApp();
  const [sample, setSample] = useState("acme");
  const [name, setName] = useState("Supplier payments");
  const [version, setVersion] = useState(config.samples.acme?.version ?? "full");
  const [busy, setBusy] = useState(false);
  const pick = (k: string) => {
    setSample(k); setVersion(config.samples[k].version);
    setName(k === "acme" ? "Supplier payments" : k === "figure1" ? "Kestrel model review" : "");
  };
  const create = async () => {
    setBusy(true);
    try {
      const w = await api<WorkspaceSummary>("/workspaces", { body: { name, version, sample } });
      toast(`Created ${w.name}`, "ok"); onCreated(w.id);
    } catch (e) { toast((e as Error).message, "bad"); setBusy(false); }
  };
  return (
    <Modal title="New workspace" onClose={onClose}>
      <div className="stack">
        <div className="field"><span>Start from</span>
          <div className="stack" style={{ gap: 8 }}>
            {Object.entries(config.samples).map(([k, s]) => (
              <button key={k} type="button" className={`option ${sample === k ? "on" : ""}`} onClick={() => pick(k)}>
                <b>{s.title}</b><span className="small muted">{s.description}</span>
              </button>
            ))}
          </div>
        </div>
        <label className="field"><span>Name</span><input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Finance agent" /></label>
        <label className="field"><span>Protection level</span>
          <select className="select" value={version} onChange={(e) => setVersion(e.target.value)}>
            {config.versions.map((v) => <option key={v} value={v}>{VERSION_LABEL[v] ?? v}</option>)}
          </select>
        </label>
        <div className="small muted">Pick "Plain memory" to see what happens without MemLedger, then compare.</div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn primary" disabled={busy || !name.trim()} onClick={create}>{busy ? <Spinner /> : <Plus />}Create</button>
        </div>
      </div>
    </Modal>
  );
}
