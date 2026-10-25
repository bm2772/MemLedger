import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, Loader2, X, XCircle } from "lucide-react";
import type { Config, Session, Status } from "../api";

// ------------------------------------------------------------------------------------------------ app context
type Toast = { id: number; kind: "ok" | "bad" | "info"; text: string };
type Ctx = {
  config: Config; me: Session; switchUser: (u: string) => void; logout: () => void;
  toast: (text: string, kind?: Toast["kind"]) => void;
};
export const AppCtx = createContext<Ctx | null>(null);
export const useApp = () => {
  const c = useContext(AppCtx);
  if (!c) throw new Error("useApp outside AppCtx");
  return c;
};

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const toast = useCallback((text: string, kind: Toast["kind"] = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5200);
  }, []);
  const view = (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.kind}`}>
          {t.kind === "ok" ? <CheckCircle2 size={17} color="var(--accent)" /> : t.kind === "bad"
            ? <XCircle size={17} color="var(--danger)" /> : <Info size={17} color="var(--info)" />}
          <div className="grow">{t.text}</div>
          <button className="btn ghost sm icon" aria-label="Dismiss" onClick={() => setToasts((x) => x.filter((y) => y.id !== t.id))}><X /></button>
        </div>
      ))}
    </div>
  );
  return { toast, view };
}

// ------------------------------------------------------------------------------------------------ primitives
export function Badge({ tone, children, dot }: { tone?: string; children: ReactNode; dot?: boolean }) {
  return <span className={`badge ${tone ?? ""}`}>{dot && <span className="dot" />}{children}</span>;
}

const STATUS_TONE: Record<string, string> = {
  active: "ok", restored: "info", quarantined: "bad", contested: "warn", superseded: "", flagged: "bad",
};
export function StatusBadge({ status }: { status: Status | string }) {
  return <Badge tone={STATUS_TONE[status] ?? ""} dot>{status}</Badge>;
}

export function trustColor(t: number) {
  return t >= 0.75 ? "var(--accent)" : t >= 0.45 ? "var(--warn)" : "var(--danger)";
}
export function TrustBar({ value }: { value: number }) {
  return (
    <div className="trust" title={`trust ${value.toFixed(3)}`}>
      <div className="bar"><i style={{ width: `${Math.max(2, value * 100)}%`, background: trustColor(value) }} /></div>
      <span>{value.toFixed(2)}</span>
    </div>
  );
}

export function Empty({ icon, title, children }: { icon: ReactNode; title: string; children?: ReactNode }) {
  return <div className="empty">{icon}<h4>{title}</h4>{children && <div className="small">{children}</div>}</div>;
}

export function Callout({ tone = "info", title, children }: { tone?: "ok" | "bad" | "warn" | "info"; title?: ReactNode; children?: ReactNode }) {
  const Icon = tone === "ok" ? CheckCircle2 : tone === "bad" ? XCircle : tone === "warn" ? AlertTriangle : Info;
  return (
    <div className={`callout ${tone}`}>
      <Icon />
      <div className="grow">{title && <div style={{ fontWeight: 600 }}>{title}</div>}{children && <div className="small muted" style={{ marginTop: title ? 2 : 0 }}>{children}</div>}</div>
    </div>
  );
}

export function Spinner({ size = 15 }: { size?: number }) {
  return <Loader2 size={size} className="spin" />;
}

export function Card({ title, sub, actions, children, pad = true }: { title?: ReactNode; sub?: ReactNode; actions?: ReactNode; children: ReactNode; pad?: boolean }) {
  return (
    <section className="card">
      {title && <div className="card-head"><div><h3>{title}</h3>{sub && <div className="sub">{sub}</div>}</div>{actions && <div className="row">{actions}</div>}</div>}
      {pad ? <div className="card-pad">{children}</div> : children}
    </section>
  );
}

export function PageHead({ title, sub, actions }: { title: string; sub?: ReactNode; actions?: ReactNode }) {
  useEffect(() => { document.title = `${title} · MemLedger`; }, [title]);
  return (
    <div className="page-head">
      <div><h1>{title}</h1>{sub && <p>{sub}</p>}</div>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}

export function Drawer({ title, onClose, children, actions }: { title: ReactNode; onClose: () => void; children: ReactNode; actions?: ReactNode }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  return (
    <>
      <div className="drawer-bg" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true">
        <div className="drawer-head"><div className="grow" style={{ fontWeight: 600 }}>{title}</div>{actions}<button className="btn ghost icon" aria-label="Close" onClick={onClose}><X /></button></div>
        <div className="drawer-body">{children}</div>
      </aside>
    </>
  );
}

export function Modal({ title, onClose, children }: { title: ReactNode; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  return (
    <>
      <div className="drawer-bg" onClick={onClose} />
      <div className="modal card" role="dialog" aria-modal="true">
        <div className="card-head"><h3>{title}</h3><button className="btn ghost icon sm" aria-label="Close" onClick={onClose}><X /></button></div>
        <div className="card-pad">{children}</div>
      </div>
    </>
  );
}

export function Seg<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: ReactNode }[]; onChange: (v: T) => void }) {
  return (
    <div className="seg" role="tablist">
      {options.map((o) => <button key={o.value} role="tab" aria-selected={o.value === value} className={o.value === value ? "on" : ""} onClick={() => onChange(o.value)}>{o.label}</button>)}
    </div>
  );
}

export function Id({ id }: { id: string }) {
  return <code className="faint" title={id}>{id}</code>;
}

export const PROTECTION_LABEL: Record<string, string> = {
  provenance: "Provenance graph", hash_chain: "Hash chain", jtms: "JTMS retraction", team_scope: "Team scoping",
  input_screen: "Input screen", write_checks: "Write checks", access_control: "Access control",
  action_gate: "Action gate", registry: "Signed registry",
};
export const VERSION_LABEL: Record<string, string> = {
  full: "MemLedger (full)", full_no_registry: "Full, no registry", write_checks: "Write checks",
  provenance: "Provenance only", baseline: "Plain memory (unprotected)",
};
