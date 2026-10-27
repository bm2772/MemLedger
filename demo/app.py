"""MemLedger chat demo: attack test cases as a conversation, with MemLedger protection switched on or off.

    pip install -e ".[demo]"
    bash demo/run.sh            # offline: fooled test model + code-only checkers, no network needed

Pick a test case, set the protection switch, press Run: the conversation is played on the real services (demo/chat.py)
and ends with a verdict. Run it again with the switch flipped to compare. The chat box asks the agent a follow-up
question against the memory the last run left behind. $DEMO_DELAY sets the seconds between messages (default 0.6).
"""

from __future__ import annotations

import html
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # `streamlit run demo/app.py` puts demo/ on the path, not the repo root
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("MEMLEDGER_GUARD_BACKEND", "lexical")  # offline by default: the code-only checkers

import streamlit as st

from demo import chat

DELAY = float(os.environ.get("DEMO_DELAY", "0.6"))

st.set_page_config(page_title="MemLedger chat demo", page_icon="🛡️", layout="centered")
st.markdown("""
<style>
  .block-container { padding-top: 1.6rem; max-width: 860px; }
  .ml-head { display: flex; align-items: baseline; gap: .6rem; margin-bottom: .2rem; }
  .ml-head h1 { font-size: 1.7rem; margin: 0; }
  .ml-head span { color: #8b949e; font-size: .95rem; }
  .ml-who { font-size: .78rem; color: #8b949e; margin-bottom: .15rem; }
  .ml-tool { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .86rem; padding: .35rem .6rem;
             border-radius: 8px; background: rgba(139,148,158,.12); display: inline-block; }
  .ml-tool.bad { background: rgba(248,81,73,.16); color: #ff7b72; }
  .ml-tool.ok { background: rgba(63,185,80,.16); color: #56d364; }
  .ml-guard { border-left: 3px solid #3fb950; background: rgba(63,185,80,.10); padding: .45rem .7rem;
              border-radius: 6px; font-size: .92rem; }
  .ml-sys { color: #8b949e; font-size: .9rem; font-style: italic; }
  .ml-case { border: 1px solid rgba(139,148,158,.35); border-radius: 10px; padding: .6rem .8rem; font-size: .93rem; }
  .ml-case b { font-size: 1rem; }
  .ml-pill { display: inline-block; font-size: .75rem; font-weight: 600; padding: .1rem .5rem; border-radius: 99px;
             margin-left: .4rem; vertical-align: middle; }
  .ml-pill.on { background: rgba(63,185,80,.2); color: #56d364; }
  .ml-pill.off { background: rgba(248,81,73,.2); color: #ff7b72; }
  .ml-verdict { border-radius: 10px; padding: .7rem .9rem; font-weight: 600; font-size: 1rem; margin: .3rem 0 1.2rem; }
  .ml-verdict.bad { background: rgba(248,81,73,.15); border: 1px solid rgba(248,81,73,.55); color: #ff7b72; }
  .ml-verdict.ok { background: rgba(63,185,80,.13); border: 1px solid rgba(63,185,80,.55); color: #56d364; }
  .ml-sep { border-top: 1px dashed rgba(139,148,158,.35); margin: 1.2rem 0 .8rem; }
</style>
<div class="ml-head"><h1>🛡️ MemLedger</h1><span>chat demo · attacks on an AI agent's memory</span></div>
""", unsafe_allow_html=True)

if "log" not in st.session_state:
    st.session_state.log = []  # rendered items: ("case", ...), ("msg", Msg), ("verdict", ...), ("sep",)
    st.session_state.played = None

titles = {c.key: f"{i}. {c.title}" for i, c in enumerate(chat.CASES, 1)}
c1, c2, c3 = st.columns([3.2, 2.2, 1.1], vertical_alignment="bottom")
key = c1.selectbox("Test case", list(titles), format_func=titles.get, label_visibility="collapsed")
protected = c2.toggle("MemLedger protection", value=False)
run = c3.button("▶ Run", type="primary", width="stretch")
cols = st.columns([5, 1])
cols[0].caption(("🟢 **Protection ON**: full MemLedger" if protected else "🔴 **Protection OFF**: plain memory")
                + " · agent: fooled test model (believes everything it reads)")
if cols[1].button("Clear chat", width="stretch"):
    st.session_state.log, st.session_state.played = [], None
    st.rerun()


def esc(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def show(item) -> None:
    kind = item[0]
    if kind == "case":
        _, case, prot = item
        pill = ('<span class="ml-pill on">PROTECTION ON</span>' if prot
                else '<span class="ml-pill off">PROTECTION OFF</span>')
        with st.chat_message("assistant", avatar="🎯"):
            st.markdown(f'<div class="ml-case"><b>Test case: {esc(case.title)}</b>{pill}<br>{esc(case.attack)}</div>',
                        unsafe_allow_html=True)
    elif kind == "verdict":
        _, attacked, text = item
        cls, head = ("bad", "❌ Attack succeeded") if attacked else ("ok", "🛡️ Attack blocked")
        st.markdown(f'<div class="ml-verdict {cls}">{head}: {esc(text)}</div>', unsafe_allow_html=True)
    elif kind == "sep":
        st.markdown('<div class="ml-sep"></div>', unsafe_allow_html=True)
    else:
        m = item[1]
        if m.role == "user":
            with st.chat_message("user", avatar=m.avatar or "🧑"):
                st.markdown(f'<div class="ml-who">{esc(m.who)}</div>{esc(m.text)}', unsafe_allow_html=True)
        elif m.role == "agent":
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(f'<div class="ml-who">Agent</div>{esc(m.text)}', unsafe_allow_html=True)
        elif m.role == "guard":
            with st.chat_message("assistant", avatar="🛡️"):
                st.markdown(f'<div class="ml-who">MemLedger</div><div class="ml-guard">{esc(m.text)}</div>',
                            unsafe_allow_html=True)
        elif m.role == "tool":
            with st.chat_message("assistant", avatar="⚙️"):
                st.markdown(f'<div class="ml-who">{esc(m.who)}</div>'
                            f'<span class="ml-tool {m.tone}">{esc(m.text)}</span>', unsafe_allow_html=True)
        else:
            with st.chat_message("assistant", avatar="📁" if m.who == "Memory" else "🛠️"):
                st.markdown(f'<div class="ml-sys">{esc(m.text)}</div>', unsafe_allow_html=True)


for item in st.session_state.log:
    show(item)


def stream(items: list) -> None:
    for item in items:
        show(item)
        st.session_state.log.append(item)
        time.sleep(DELAY if item[0] != "verdict" else DELAY / 2)


if run:
    case = chat.BY_KEY[key]
    played = chat.play(case, protected)
    st.session_state.played = played
    items = ([("sep",)] if st.session_state.log else []) + [("case", case, protected)]
    items += [("msg", m) for m in played.messages] + [("verdict", played.attacked, played.verdict)]
    stream(items)

played = st.session_state.played
hint = f"Ask the agent… e.g. {played.case.probe}" if played else "Run a test case first, then ask the agent"
if q := st.chat_input(hint, disabled=played is None):
    stream([("msg", m) for m in chat.ask(played, q)])
