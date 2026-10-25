import { useState } from "react";
import { KeyRound } from "lucide-react";
import { api, identity, type Session } from "../api";
import { Callout } from "../components/ui";

export default function Login({ onDone }: { onDone: () => void }) {
  const [token, setToken] = useState("");
  const [err, setErr] = useState("");
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    identity.setToken(token.trim());
    try { await api<Session>("/me"); onDone(); }
    catch { identity.setToken(""); setErr("That token is not recognised."); }
  };
  return (
    <div className="login">
      <form className="card card-pad stack" style={{ width: "min(400px, 100%)" }} onSubmit={submit}>
        <div className="row"><img src="/favicon.svg" width={34} height={34} alt="" /><div><b style={{ fontSize: 16 }}>Sign in to MemLedger</b><div className="small muted">Your token sets your team, role and clearance.</div></div></div>
        <label className="field"><span>Access token</span>
          <input className="input mono" type="password" autoFocus value={token} onChange={(e) => setToken(e.target.value)} placeholder="paste the token your admin gave you" />
        </label>
        {err && <Callout tone="bad" title={err} />}
        <button className="btn primary" disabled={!token.trim()}><KeyRound />Sign in</button>
      </form>
    </div>
  );
}
