// "How it works": one story played on plain memory and on MemLedger side by side (web/tour.py). Every outcome is
// what the real services did on fresh in-memory stores; nothing here touches a workspace.
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, BarChart3, CheckCircle2, FlaskConical, Globe, RotateCcw, ShieldAlert, ShieldCheck, ShieldX } from "lucide-react";
import { useApi, type Explain } from "../api";
import { LineageGraph } from "../components/LineageGraph";
import { Badge, Callout, Card, PageHead, PROTECTION_LABEL, Spinner, StatusBadge, TrustBar } from "../components/ui";

type Ev = { tone: "ok" | "bad" | "warn" | "info"; title: string; detail: string };
type TClaim = { id: string; label: string; text: string; status: string; trust: number };
type TSource = { id: string; label: string; kind: string; content: string; prior_trust: number; flagged: boolean; hash: string; reason: string | null };
type TVerdict = { check: string; ok: boolean; score: number; reason: string };
type TWrite = { label: string; text: string; context: string[]; accepted: boolean; verdicts: TVerdict[] };
type Hit = { label: string; text: string; trust: number };
type Side = {
  events: Ev[]; claims: TClaim[]; sources: TSource[]; writes?: TWrite[]; explain?: Explain | null; focus?: string | null;
  recall?: { query: string; before: Hit[]; after: Hit[] }; read?: { before: string[]; after: string[] };
  acme?: { page: string; recalled: string[]; hijacked: boolean };
};
type Step = { id: string; title: string; what: string; how: string; mechanisms: string[]; sides: { baseline: Side; full: Side } };
type Tour = { query: string; backend: string; steps: Step[] };

const SIDE_TITLE = { baseline: "Plain memory", full: "MemLedger" } as const;

export default function TourPage() {
  const [fresh, setFresh] = useState(0);  // Replay plays the story again on the server (otherwise cached)
  const { data, error, loading } = useApi<Tour>(fresh ? `/tour?fresh=true&n=${fresh}` : "/tour", [fresh]);
  const [i, setI] = useState(() => Math.max(0, (parseInt(window.location.hash.slice(1), 10) || 1) - 1));  // /tour#3
  const nav = useNavigate();
  const n = data?.steps.length ?? 0;
  useEffect(() => { if (n && i >= n) setI(n - 1); }, [i, n]);
  useEffect(() => { window.history.replaceState(null, "", `#${i + 1}`); }, [i]);
  const go = useCallback((d: number) => setI((x) => Math.min(Math.max(0, x + d), Math.max(0, n - 1))), [n]);
  useEffect(() => {  // arrow keys step through the story (presenting from a laptop)
    const k = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest("input, textarea, select")) return;
      if (e.key === "ArrowRight") go(1);
      if (e.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [go]);

  const replay = () => { setI(0); setFresh((f) => f + 1); };
  if (error) return <div className="page"><Callout tone="bad" title="The tour could not run">{error.message}</Callout></div>;
  if (!data) return <div className="page"><PageHead title="How MemLedger works" /><div className="row muted">{loading && <Spinner />}Playing the story on both memories…</div></div>;
  const step = data.steps[Math.min(i, n - 1)];

  return (
    <div className="page stack" style={{ gap: 20 }}>
      <PageHead title="How MemLedger works"
        sub={<>One story, played on <b>plain memory</b> and on <b>MemLedger</b> side by side. Every result below is what the real code did just now, on fresh throw-away memories (checkers: {data.backend}).</>}
        actions={<button className="btn" onClick={replay} disabled={loading}>{loading ? <Spinner /> : <RotateCcw />}Replay</button>} />

      <ol className="stepper" aria-label="Steps">
        {data.steps.map((s, k) => (
          <li key={s.id}>
            <button className={k === i ? "on" : k < i ? "done" : ""} onClick={() => setI(k)} aria-current={k === i ? "step" : undefined}>
              <span className="num">{k + 1}</span><span className="lbl">{s.title}</span>
            </button>
          </li>
        ))}
      </ol>

      <section className="card card-pad stack tour-step" key={step.id}>
        <div className="spread" style={{ alignItems: "flex-start" }}>
          <div>
            <div className="small faint">Step {i + 1} of {n}</div>
            <h2 style={{ margin: "2px 0 6px", letterSpacing: "-0.02em" }}>{step.title}</h2>
            <p className="muted" style={{ margin: 0, maxWidth: 820 }}>{step.what}</p>
          </div>
          <div className="row" style={{ flex: "none" }}>
            <button className="btn icon" aria-label="Previous step" disabled={i === 0} onClick={() => go(-1)}><ArrowLeft /></button>
            <button className="btn primary" disabled={i === n - 1} onClick={() => go(1)}>Next<ArrowRight /></button>
          </div>
        </div>
        <div className="versus">
          {(["baseline", "full"] as const).map((v) => <SideView key={v} v={v} side={step.sides[v]} step={step} />)}
        </div>
      </section>

      <div className="grid g-tour">
        <Card title="How it works" sub="The mechanism behind this step">
          <p style={{ marginTop: 0 }}>{step.how}</p>
          <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
            {step.mechanisms.map((m) => <Badge key={m} tone="ok">{PROTECTION_LABEL[m] ?? m}</Badge>)}
          </div>
        </Card>
        <LineageCard side={step.sides.full} />
      </div>

      {i === n - 1 && (
        <Card title="That was one story. The evaluation runs 1,159 episodes per version.">
          <div className="row" style={{ flexWrap: "wrap" }}>
            <button className="btn primary" onClick={() => nav("/results")}><BarChart3 />See the results</button>
            <button className="btn" onClick={() => nav("/lab")}><FlaskConical />Try the attack lab</button>
            <button className="btn ghost" onClick={replay}><RotateCcw />Start again</button>
          </div>
        </Card>
      )}
    </div>
  );
}

function SideView({ v, side, step }: { v: "baseline" | "full"; side: Side; step: Step }) {
  const bad = side.events.some((e) => e.tone === "bad");
  const good = side.events.some((e) => e.tone === "ok");
  return (
    <div className="card card-pad stack" style={{ borderColor: bad ? "var(--danger)" : good ? "var(--accent)" : undefined }}>
      <div className="spread">
        <b>{SIDE_TITLE[v]}</b>
        {bad ? <Badge tone="bad"><ShieldX size={12} />Exposed</Badge> : good ? <Badge tone="ok"><ShieldCheck size={12} />Protected</Badge> : <Badge>no attack yet</Badge>}
      </div>
      {side.events.map((e, k) => <Callout key={k} tone={e.tone} title={e.title}>{e.detail}</Callout>)}
      <Detail side={side} step={step} v={v} />
    </div>
  );
}

function Detail({ side, step, v }: { side: Side; step: Step; v: string }) {
  switch (step.id) {
    case "sources":
      return <Sources sources={side.sources} />;
    case "write":
    case "chain":
    case "poison":
      return <>{v === "full" && side.writes?.map((w) => <Writes key={w.label} w={w} />)}{step.id !== "poison" && <Memories claims={side.claims} />}</>;
    case "flag":
      return <>{side.recall && <Recall r={side.recall} />}<Memories claims={side.claims} /></>;
    case "evidence":
      return <Memories claims={side.claims} />;
    case "tamper":
      return side.read ? (
        <div className="grid g2">
          <div><div className="small muted">Recalled before the edit</div><div className="quote small">{side.read.before.join("\n") || "(nothing)"}</div></div>
          <div><div className="small muted">Recalled after the edit</div><div className="quote small">{side.read.after.join("\n") || "(withheld)"}</div></div>
        </div>
      ) : null;
    case "action":
      return side.acme ? (
        <>
          <div className="quote small row" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}><Globe size={14} style={{ flex: "none", marginTop: 2 }} /><span>{side.acme.page}</span></div>
          <div className="small muted">What finance's agent recalled</div>
          <div className="quote small mono">{side.acme.recalled.join("\n") || "(nothing)"}</div>
        </>
      ) : null;
    default:
      return null;
  }
}

function Sources({ sources }: { sources: TSource[] }) {
  return (
    <div className="stack" style={{ gap: 8 }}>
      {sources.map((s) => (
        <div key={s.id} className={`tbox ${s.flagged ? "bad" : ""}`}>
          <div className="spread small"><span className="row" style={{ gap: 6 }}><Badge tone="outline">{s.kind}</Badge>{s.flagged && <Badge tone="bad">flagged</Badge>}</span><span className="hash" title="SHA-256 content hash">#{s.hash}</span></div>
          <div className="small" style={{ margin: "6px 0" }}>{s.content}</div>
          <div className="spread small faint"><span>prior trust</span><div style={{ width: 150 }}><TrustBar value={s.prior_trust} /></div></div>
          {s.reason && <div className="small" style={{ color: "var(--danger)", marginTop: 4 }}>{s.reason}</div>}
        </div>
      ))}
    </div>
  );
}

function Writes({ w }: { w: TWrite }) {
  return (
    <div className="tbox">
      <div className="spread small" style={{ gap: 8 }}><b>{w.label}: “{w.text}”</b>{w.accepted ? <Badge tone="ok">stored</Badge> : <Badge tone="bad">refused</Badge>}</div>
      <div className="small faint" style={{ margin: "4px 0 6px" }}>context: {w.context.join(", ") || "none"}</div>
      {w.verdicts.map((x) => (
        <div key={x.check} className="spread small" style={{ gap: 8 }}>
          <span className="row" style={{ gap: 6, minWidth: 0, flexWrap: "nowrap" }}>{x.ok ? <CheckCircle2 size={14} color="var(--accent)" style={{ flex: "none" }} /> : <ShieldAlert size={14} color="var(--danger)" style={{ flex: "none" }} />}<b>{x.check}</b><span className="muted clip" title={x.reason}>{x.reason}</span></span>
          <span className="mono faint">{x.score.toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
}

function Memories({ claims }: { claims: TClaim[] }) {
  if (!claims.length) return null;
  return (
    <div className="stack" style={{ gap: 6 }}>
      <div className="small muted">Memory now</div>
      {claims.map((c) => (
        <div key={c.id} className={`tmem ${c.status}`}>
          <span className="mono faint" style={{ width: 24, flex: "none" }}>{c.label}</span>
          <span className="grow small">{c.text}</span>
          <StatusBadge status={c.status} />
          <div style={{ width: 110, flex: "none" }}><TrustBar value={c.trust} /></div>
        </div>
      ))}
    </div>
  );
}

function Recall({ r }: { r: { query: string; before: Hit[]; after: Hit[] } }) {
  const list = (hits: Hit[]) => hits.length ? hits.map((h) => `${h.label}  ${h.text}`).join("\n") : "(nothing)";
  return (
    <div className="stack" style={{ gap: 6 }}>
      <div className="small muted">The agent asks: “{r.query}”</div>
      <div className="grid g2">
        <div><div className="small faint">Recalled before the flag</div><div className="quote small mono">{list(r.before)}</div></div>
        <div><div className="small faint">Recalled after the flag</div><div className="quote small mono">{list(r.after)}</div></div>
      </div>
    </div>
  );
}

function LineageCard({ side }: { side: Side }) {
  const text = useMemo(() => {
    const m = new Map(side.sources.map((s) => [s.id, `${s.label}: ${s.content}`]));
    return (id: string) => m.get(id);
  }, [side.sources]);
  if (!side.explain) {
    return (
      <Card title="Lineage" sub="MemLedger's provenance graph">
        <div className="small muted">This step has no single memory to trace. The graph appears on the steps that write or restore a memory: solid edges are sources that support a fact, dashed edges are sources that were only in view. Plain memory keeps no lineage at all.</div>
      </Card>
    );
  }
  return (
    <Card title={`Lineage of ${side.focus}`} sub="Solid edge: supports a fact (supported_by). Dashed: only in view (exposed_to)." pad={false}>
      <LineageGraph explain={side.explain} sourceText={text} />
    </Card>
  );
}
