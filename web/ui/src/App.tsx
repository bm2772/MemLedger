import { useCallback, useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  Activity, BookLock, Bot, Brain, ChevronsUpDown, FlaskConical, Database, LayoutDashboard, LogOut, Menu, Moon,
  ScrollText, Search, Sun, BarChart3, Boxes, Route as RouteIcon,
} from "lucide-react";
import { api, ApiError, identity, useApi, type Config, type Session, type WorkspaceSummary } from "./api";
import { AppCtx, Spinner, useApp, useToasts, VERSION_LABEL } from "./components/ui";
import Workspaces from "./pages/Workspaces";
import Overview from "./pages/Overview";
import Memories from "./pages/Memories";
import Sources from "./pages/Sources";
import AgentPage from "./pages/Agent";
import Recall from "./pages/Recall";
import Registry from "./pages/Registry";
import Audit from "./pages/Audit";
import Lab from "./pages/Lab";
import Results from "./pages/Results";
import TourPage from "./pages/Tour";
import Login from "./pages/Login";

type Theme = "dark" | "light";
function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    try { return (localStorage.getItem("memledger.theme") as Theme) || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"); }
    catch { return "dark"; }
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("memledger.theme", theme); } catch { /* private mode */ }
  }, [theme]);
  return [theme, setTheme] as const;
}

export default function App() {
  const [config, setConfig] = useState<Config | null>(null);
  const [me, setMe] = useState<Session | null>(null);
  const [needLogin, setNeedLogin] = useState(false);
  const [fatal, setFatal] = useState<string | null>(null);
  const { toast, view: toasts } = useToasts();

  const load = useCallback(async () => {
    try {
      const c = await api<Config>("/config");
      setConfig(c);
      setMe(await api<Session>("/me"));
      setNeedLogin(false);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setNeedLogin(true);
      else setFatal(e instanceof Error ? e.message : String(e));
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  // pages remount under the new identity (Shell is keyed by user), so nothing shown belongs to the previous user
  const switchUser = useCallback((u: string) => { identity.setUser(u); api<Session>("/me").then(setMe, () => load()); }, [load]);
  const logout = useCallback(() => { identity.setToken(""); setMe(null); setNeedLogin(true); }, []);

  if (fatal) return <div className="login"><div className="card card-pad" style={{ maxWidth: 440 }}><h3 style={{ marginTop: 0 }}>Cannot reach the MemLedger server</h3><p className="muted">{fatal}</p><p className="small faint">Start it with <code>make web</code> (or <code>python -m web</code>).</p><button className="btn" onClick={() => { setFatal(null); load(); }}>Retry</button></div></div>;
  if (needLogin) return <Login onDone={load} />;
  if (!config || !me) return <div className="login"><Spinner size={22} /></div>;

  return (
    <AppCtx.Provider value={{ config, me, switchUser, logout, toast }}>
      <Shell key={me.user_id} />
      {toasts}
    </AppCtx.Provider>
  );
}

function Shell() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);
  const ws = loc.pathname.match(/^\/w\/([^/]+)/)?.[1];
  return (
    <div className="shell">
      <Sidebar ws={ws} open={open} />
      {open && <div className="drawer-bg" style={{ zIndex: 15 }} onClick={() => setOpen(false)} />}
      <main className="main">
        <TopBar ws={ws} onMenu={() => setOpen(true)} />
        <Routes>
          <Route path="/" element={<Workspaces />} />
          <Route path="/tour" element={<TourPage />} />
          <Route path="/lab" element={<Lab />} />
          <Route path="/results" element={<Results />} />
          <Route path="/w/:ws" element={<WsRoute el="overview" />} />
          <Route path="/w/:ws/memories" element={<WsRoute el="memories" />} />
          <Route path="/w/:ws/memories/:claim" element={<WsRoute el="memories" />} />
          <Route path="/w/:ws/sources" element={<WsRoute el="sources" />} />
          <Route path="/w/:ws/agent" element={<WsRoute el="agent" />} />
          <Route path="/w/:ws/recall" element={<WsRoute el="recall" />} />
          <Route path="/w/:ws/registry" element={<WsRoute el="registry" />} />
          <Route path="/w/:ws/audit" element={<WsRoute el="audit" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function WsRoute({ el }: { el: string }) {
  const { ws = "" } = useParams();
  const page = { overview: Overview, memories: Memories, sources: Sources, agent: AgentPage, recall: Recall, registry: Registry, audit: Audit }[el]!;
  const P = page;
  return <div className="page"><P ws={ws} key={ws} /></div>;
}

function Sidebar({ ws, open }: { ws?: string; open: boolean }) {
  const { config, me, switchUser, logout } = useApp();
  const [theme, setTheme] = useTheme();
  const items = ws ? [
    { to: `/w/${ws}`, icon: LayoutDashboard, label: "Overview", end: true },
    { to: `/w/${ws}/memories`, icon: Brain, label: "Memories" },
    { to: `/w/${ws}/sources`, icon: Database, label: "Sources" },
    { to: `/w/${ws}/agent`, icon: Bot, label: "Agent" },
    { to: `/w/${ws}/recall`, icon: Search, label: "Recall" },
    { to: `/w/${ws}/registry`, icon: BookLock, label: "Registry" },
    { to: `/w/${ws}/audit`, icon: ScrollText, label: "Audit & integrity" },
  ] : [];
  return (
    <nav className={`side ${open ? "open" : ""}`} aria-label="Main">
      <NavLink to="/" className="brand">
        <img src="/favicon.svg" width={30} height={30} alt="" />
        <div>MemLedger<small>Provenance-governed memory</small></div>
      </NavLink>
      <WorkspaceSwitcher ws={ws} />
      {ws && <div className="nav-label">Workspace</div>}
      <div className="nav">
        {items.map(({ to, icon: I, label, end }) => <NavLink key={to} to={to} end={end}><I />{label}</NavLink>)}
      </div>
      <div className="nav-label">Evaluate</div>
      <div className="nav">
        <NavLink to="/tour"><RouteIcon />How it works</NavLink>
        <NavLink to="/lab"><FlaskConical />Attack lab</NavLink>
        <NavLink to="/results"><BarChart3 />Results</NavLink>
        <NavLink to="/" end><Boxes />All workspaces</NavLink>
      </div>
      <div className="side-foot">
        {config.auth === "open" ? (
          <label className="field"><span>Acting as (local mode)</span>
            <select className="select" value={me.user_id} onChange={(e) => switchUser(e.target.value)}>
              {config.users.map((u) => <option key={u.user_id} value={u.user_id}>{u.user_id} · {u.role} · {u.team}</option>)}
            </select>
          </label>
        ) : (
          <div className="spread"><div className="small"><b>{me.user_id}</b><div className="faint">{me.role} · {me.team}</div></div><button className="btn ghost icon" aria-label="Sign out" onClick={logout}><LogOut /></button></div>
        )}
        <div className="spread small faint">
          <span><Activity size={12} style={{ verticalAlign: -1 }} /> guards: {config.guard_backend}</span>
          <button className="btn ghost sm icon" aria-label="Toggle theme" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? <Sun /> : <Moon />}</button>
        </div>
      </div>
    </nav>
  );
}

function WorkspaceSwitcher({ ws }: { ws?: string }) {
  const { data } = useApi<WorkspaceSummary[]>("/workspaces", [ws]);
  const nav = useNavigate();
  const cur = data?.find((w) => w.id === ws);
  if (!data?.length) return null;
  return (
    <label className="field" style={{ position: "relative" }}>
      <select className="select" style={{ appearance: "none", paddingRight: 30, fontWeight: 550 }} value={ws ?? ""}
        onChange={(e) => nav(e.target.value ? `/w/${e.target.value}` : "/")} aria-label="Workspace">
        {!cur && <option value="">Choose a workspace…</option>}
        {data.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
      </select>
      <ChevronsUpDown size={14} style={{ position: "absolute", right: 10, top: 11, pointerEvents: "none", color: "var(--muted)" }} />
    </label>
  );
}

function TopBar({ ws, onMenu }: { ws?: string; onMenu: () => void }) {
  const { data } = useApi<WorkspaceSummary[]>(ws ? "/workspaces" : null, [ws]);
  const cur = data?.find((w) => w.id === ws);
  const { me } = useApp();
  return (
    <header className="topbar">
      <button className="btn ghost icon menu-btn" aria-label="Menu" onClick={onMenu}><Menu /></button>
      <div className="crumbs grow">
        {cur ? <><NavLink to="/" className="faint">Workspaces</NavLink><span className="faint">/</span><b>{cur.name}</b><span className="badge outline">{VERSION_LABEL[cur.version] ?? cur.version}</span></> : <b>MemLedger console</b>}
      </div>
      <span className="badge outline" title="Identity comes from login, never from the model">{me.user_id} · {me.team} · clearance {me.clearance}</span>
    </header>
  );
}

