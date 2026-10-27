// Typed client for web/api.py. Identity: a bearer token (token mode) or a demo user name (open mode, localhost).
import { useCallback, useEffect, useState } from "react";

export type Labels = { team: string; confidentiality: number; integrity: number };
export type Session = { user_id: string; team: string; role: string; clearance: number; admin: boolean };
export type Status = "active" | "quarantined" | "superseded" | "contested" | "restored";
export type Claim = {
  id: string; text: string; status: Status; trust: number; labels: Labels; recorded_at: string;
  content_hash: string; derivations?: number; parents?: string[];
};
export type Source = {
  id: string; kind: string; content: string; labels: Labels; prior_trust: number; content_hash: string;
  recorded_at: string; flagged: boolean; screen?: string | null;
};
export type Verdict = { check: string; ok: boolean; score: number; reason: string };
export type ExplainNode =
  | { type: "source"; id: string; kind: string; content_hash: string; flagged: boolean }
  | { type: "claim"; id: string; claim: string }
  | Explain;
export type Explain = {
  claim: string; text: string; status: Status; trust: number; content_hash: string;
  lineage: { derivation: string; agent_id: string; exposed_to: ExplainNode[]; supported_by: Record<string, number> }[];
};
export type StatusRow = { seq: number; entity_id: string; status: string; trust: number | null; reason: string; at: string };
export type ClaimDetail = Claim & { verified: boolean | null; explain: Explain; history: StatusRow[]; conflicts: unknown[] };
export type Activity = { at: string; user: string; team: string; action: string; [k: string]: unknown };
export type Task = { user: string; task: string };
export type Overview = {
  id: string; name: string; version: string; created_at: string; description: string; protections: string[];
  memories: number; by_status: Record<Status, number>; sources: number; flagged_sources: number;
  trust_histogram: number[];
  chain: { ok: boolean | null; root: string | null; anchors: number | null; items: number | null; at: string | null };
  registry_entries: number; web_pages: number; tasks: Task[]; activity: Activity[];
};
export type WorkspaceSummary = { id: string; name: string; version: string; created_at: string; description: string };
export type ToolRecord = { tool: string; args: Record<string, unknown>; params: Record<string, unknown>; status: string; result: string; reason: string };
export type AgentRun = {
  answer: string; steps: number; model: string; tool_calls: ToolRecord[]; context_ids: string[];
  written_claim_ids: string[]; outbox: { tool: string; params: Record<string, unknown>; user: string }[];
  tokens: { calls: number; prompt_tokens: number; completion_tokens: number };
};
export type Config = {
  auth: "open" | "token"; guard_backend: string; users: Session[]; versions: string[];
  protections: Record<string, string[]>; kinds: string[];
  samples: Record<string, { title: string; version: string; description: string }>;
  llm: { model: string; base_url: string };
};

const KEY_TOKEN = "memledger.token";
const KEY_USER = "memledger.user";

function store(): Storage | null {
  try { return window.localStorage; } catch { return null; }
}
export const identity = {
  token: () => store()?.getItem(KEY_TOKEN) ?? "",
  user: () => store()?.getItem(KEY_USER) ?? "ria",
  setToken: (t: string) => { try { t ? store()?.setItem(KEY_TOKEN, t) : store()?.removeItem(KEY_TOKEN); } catch { /* private mode */ } },
  setUser: (u: string) => { try { store()?.setItem(KEY_USER, u); } catch { /* private mode */ } },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = { "X-MemLedger-User": identity.user() };
  const token = identity.token();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api${path}`, {
    method: init.method ?? (init.body !== undefined ? "POST" : "GET"),
    headers, body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = (data as { detail?: unknown }).detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? d.map((x: { msg?: string }) => x.msg).join("; ") : res.statusText;
    throw new ApiError(res.status, msg || `HTTP ${res.status}`);
  }
  return data as T;
}

/** GET a path; `null` skips. `reload()` refetches without clearing the current data. */
export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [loading, setLoading] = useState(false);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!path) return;
    let live = true;
    setLoading(true);
    api<T>(path).then(
      (d) => { if (live) { setData(d); setError(null); } },
      (e) => { if (live) setError(e); },
    ).finally(() => live && setLoading(false));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, ...deps]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload, setData };
}

export const short = (id: string, n = 10) => (id.length > n ? id.slice(0, n) : id);
export const when = (iso: string | null | undefined) => {
  if (!iso) return "";
  const d = new Date(iso);
  const s = (Date.now() - d.getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
};
