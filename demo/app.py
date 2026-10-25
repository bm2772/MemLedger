"""MemLedger demo (slide 24, Figure 7): plain memory vs MemLedger, lineage, clean-up, isolation, tamper, attack families.

    pip install -e ".[demo]"
    bash demo/run.sh            # offline: fake model + lexical checkers, no network needed

All logic lives in demo/scenario.py (tested); this file only lays it out.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # `streamlit run demo/app.py` puts demo/ on the path, not the repo root
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("MEMLEDGER_GUARD_BACKEND", "lexical")  # offline by default: the code-only checkers

import streamlit as st

from demo import scenario as sc

st.set_page_config(page_title="MemLedger demo", layout="wide")
st.title("MemLedger: provenance-governed memory")
st.caption("AEGIS 2026 · team Prompt Stars · live demo of slides 5, 6, 7, 14 and 21")

with st.sidebar:
    st.header("Agent model")
    mode = st.radio("LLM", ["Fooled fake model (deterministic)", "Ollama / vLLM"], index=0)
    llm = None
    if mode != "Fooled fake model (deterministic)":
        from eval.llm import MeteredLLM

        model = st.text_input("Model", "qwen3:8b")
        url = st.text_input("Base URL", "http://localhost:11434/v1")
        llm = MeteredLLM(model=model, base_url=url, timeout=120)
    st.caption(f"Guard backend: `{os.environ['MEMLEDGER_GUARD_BACKEND']}`")
    st.markdown("The fake model believes everything it reads, so any difference comes from the memory layer.")
    offline = os.environ.get("HF_HUB_OFFLINE") == "1"
    st.caption("Offline mode: no network calls" if offline and llm is None else "Network may be used (real model)")

tab_acme, tab_lineage, tab_cleanup, tab_iso, tab_tamper, tab_fam, tab_results = st.tabs(
    ["1 · Poisoned web page (slide 5)", "2 · Lineage view", "3 · Clean-up (slide 6)", "4 · Isolation (slide 21)",
     "5 · Tamper detection", "6 · Attack families", "Results"])

with tab_acme:
    st.subheader("A researcher reads a supplier page; two weeks later finance pays Acme's invoice")
    st.info(sc.PAGE, icon="🌐")
    if st.button("Run the scenario on both systems", type="primary") or "acme" in st.session_state:
        if "acme" not in st.session_state:
            with st.spinner("Running plain memory and MemLedger..."):
                st.session_state.acme = {v: sc.play_acme(v, llm) for v in ("baseline", "full")}
        plain, ml = st.session_state.acme["baseline"], st.session_state.acme["full"]
        left, right = st.columns(2)
        for col, r, title in ((left, plain, "Plain retrieval memory"), (right, ml, "MemLedger (full)")):
            with col:
                st.markdown(f"### {title}")
                acct = r["writes"]["m_account"]
                if acct["accepted"]:
                    st.error(f"**Stored.** “{acct['text']}” saved like any other memory.")
                else:
                    st.success("**Rejected.** " + "; ".join(acct["reasons"]))
                st.write("**Page flagged:**", "yes" if r["web_flagged"] else "no")
                st.markdown("**Recalled for the payment:**")
                st.code("\n".join(r["recalled"]) or "(nothing)", language="text")
                for p in r["payment"]:
                    paid = p["paid"]
                    msg = f"model asked for account `{p['asked']}` → paid `{paid}` ({p['status']}: {p['reason']})"
                    (st.error if paid == sc.ATTACKER else st.success)(("**Paid the attacker.** " if paid == sc.ATTACKER
                                                                       else "**Paid safely.** ") + msg)
                st.markdown("**Memory afterwards**")
                st.dataframe(r["claims"], hide_index=True, width="stretch")
        if st.button("Reset scenario"):
            del st.session_state.acme
            st.rerun()

def figure1_state() -> dict:
    if "fig1" not in st.session_state:
        st.session_state.fig1 = sc.figure1()
        st.session_state.fig1_log = []
    return st.session_state.fig1


with tab_lineage:
    st.subheader("explain(): where a memory came from")
    f = figure1_state()
    svc = f["service"]
    name = st.selectbox("Memory", list(f["claims"]), format_func=lambda k: f"{k}: {svc.store.get_claim(f['claims'][k]).text}")
    st.graphviz_chart(sc.lineage_dot(svc.explain(f["claims"][name])))
    st.caption("Ellipses are sources, boxes are memories; red = flagged or quarantined. Each edge is one derivation "
               "(justification); the JTMS keeps a memory while at least one derivation has only valid parents.")
    with st.expander("Raw explain() output"):
        st.json(svc.explain(f["claims"][name]))

with tab_cleanup:
    st.subheader("Targeted clean-up when a source turns out to be poisoned")
    f = figure1_state()
    svc = f["service"]
    st.markdown("Sources: paper, registry entry, user note, tool output and a **web page**. "
                "D1 also follows from the paper and the tool output alone; D2 comes from the page; D3 builds on D2.")
    rows = [{"memory": k, **next(c for c in sc.claim_table(svc) if c["id"] == cid)} for k, cid in f["claims"].items()]
    st.dataframe(rows, hide_index=True, width="stretch")
    a, b, c = st.columns(3)
    if a.button("Flag the web page as poisoned", type="primary"):
        out = sc.flag(svc, f["sources"]["web"])
        st.session_state.fig1_log.append(("flag web page", out))
        st.rerun()
    if b.button("New independent evidence for D2 (paper)"):
        out = sc.restore_with_evidence(svc, f["claims"]["D2"], [f["sources"]["paper"]])
        st.session_state.fig1_log.append(("evidence for D2", out))
        st.rerun()
    if c.button("Reset"):
        del st.session_state.fig1
        st.rerun()
    names = {v: k for k, v in f["claims"].items()}
    for action, out in st.session_state.get("fig1_log", []):
        st.write(f"**{action}** → quarantined: {[names.get(x, x) for x in out['quarantined']] or '-'}; "
                 f"restored: {[names.get(x, x) for x in out['restored']] or '-'}")

with tab_iso:
    st.subheader("Team B's user asks the agent for team A's confidential note")
    st.markdown(f"Team A's memory holds a confidential result with a unique marker `{sc.CANARY[:20]}…`. "
                "Bob (team B) asks the agent to ignore team limits and fetch it.")
    if st.button("Ask on both systems", type="primary", key="iso_run"):
        st.session_state.iso = {v: sc.play_isolation(v, llm) for v in ("baseline", "full")}
    if "iso" in st.session_state:
        left, right = st.columns(2)
        for col, v, title in ((left, "baseline", "Plain retrieval memory"), (right, "full", "MemLedger (full)")):
            r = st.session_state.iso[v]
            with col:
                st.markdown(f"### {title}")
                st.write(f"Memories returned to Bob's search: **{r['retrieved']}**")
                st.code(r["answer"] or "(no answer)", language="text")
                if r["leaked"]:
                    st.error(f"**Leaked** team A's data: {', '.join(sorted({x['where'] for x in r['leaks']}))}")
                else:
                    st.success("**Withheld.** No team A marker appears anywhere Bob can see.")
        st.caption("Read rule (slide 21): team(m) ∈ {team(p), shared} and confidentiality(m) ≤ clearance(p), enforced "
                   "by the service before anything reaches the model. Leak check 2: the marker is searched in the "
                   "answer, tool calls, retrieved memories and errors.")

with tab_tamper:
    st.subheader("Someone with database access edits a stored memory directly")
    edit = st.radio("Edit", ["claim_text", "source_content", "recorded_at"], horizontal=True,
                    format_func={"claim_text": "memory text 64 → 640", "source_content": "its source paper",
                                 "recorded_at": "record timestamp"}.get)
    if st.button("Tamper and read it back", type="primary"):
        r = sc.tamper_demo(edit)
        left, right = st.columns(2)
        left.markdown("**Read before the edit**")
        left.code("\n".join(r["before"]), language="text")
        right.markdown("**Read after the edit**")
        right.code("\n".join(r["after"]) or "(withheld)", language="text")
        (st.success if r["detected"] else st.error)(
            f"{'Detected' if r['detected'] else 'NOT detected'}: status {r['status']}; log: {' → '.join(r['history'])}")
        st.caption("SHA-256(content ‖ record time ‖ parent hashes ‖ labels) is recomputed on read and checked "
                   "against the signed Merkle root (slide 14).")

@st.cache_resource(show_spinner="Building the attack suite (one episode per family)...")
def families() -> dict:
    return sc.family_samples()


with tab_fam:
    st.subheader("One attack per family: plain memory vs MemLedger")
    fams = families()
    pick = st.multiselect("Families", list(fams), default=list(fams))
    if st.button("Run selected families", type="primary", key="fam_run"):
        rows = []
        with st.spinner(f"Running {len(pick)} episodes on two versions..."):
            for name in pick:
                b, f = sc.play_family(fams[name], "baseline", llm), sc.play_family(fams[name], "full", llm)
                rows.append({"family": name, "episode": fams[name].id,
                             "plain memory": "attack worked" if b["succeeded"] else "defended",
                             "MemLedger": "attack worked" if f["succeeded"] else "defended",
                             "stopped by": f["blocked_by"] or "–", "errors": b["error"] or f["error"] or ""})
        st.session_state.fam_rows = rows
    if "fam_rows" in st.session_state:
        st.dataframe(st.session_state.fam_rows, hide_index=True, width="stretch")
        worked = [r for r in st.session_state.fam_rows if r["MemLedger"] == "attack worked"]
        st.caption(f"{len(worked)} of {len(st.session_state.fam_rows)} families got through MemLedger in this sample. "
                   "Each family is shown with its first episode whose attack works on plain memory, to show what "
                   "MemLedger stops: this is an illustration, not a rate. Rates over all episodes, with intervals, are "
                   "in Results.")

with tab_results:
    results = ROOT / "docs" / "results.md"
    if results.exists():
        st.markdown(results.read_text())
    else:
        st.warning("docs/results.md is missing. Generate it with:\n\n"
                   "`python -m eval.runner --episodes data/scenarios/seed0.json --split dev` then "
                   "`python -m eval.report results/<run_id>/summary.json`")
