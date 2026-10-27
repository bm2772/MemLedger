"""MemLedger chat demo: talk to a live agent, with MemLedger protection switched on or off.

    pip install -e ".[demo]"
    bash demo/run.sh            # needs the agent LLM at $MEMLEDGER_LLM_URL and the checker models (see README)

Pick who you are in the sidebar, set the protection switch and type a prompt. The agent runs it on a shared memory
(demo/chat.py) and the chat shows its activity as it happens: what it planned to do (harmful steps marked), every
MemLedger checkpoint, what actually ran, its reply, and an outcome card: the harm done, or what MemLedger did to
prevent it. Flipping the switch starts a fresh memory with the same starting notes, so the same prompts can be typed
again. The insider's messages are SQL run directly on the database file. $DEMO_DELAY sets the seconds between steps.
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

import streamlit as st

from demo import chat
from eval.versions import guard_backend, load_guard_models

DELAY = float(os.environ.get("DEMO_DELAY", "0.6"))

st.set_page_config(page_title="MemLedger chat demo", page_icon="🛡️", layout="centered")
st.markdown("""
<style>
  .block-container { padding-top: 1.6rem; max-width: 56rem; }
  .ml-head { display: flex; align-items: baseline; gap: .6rem; margin-bottom: .2rem; }
  .ml-head h1 { font-size: 1.7rem; margin: 0; }
  .ml-head span { color: #8b949e; font-size: .95rem; }
  .ml-who { font-size: .78rem; color: #8b949e; margin-bottom: .2rem; }
  .ml-sql { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .9rem; }
  .ml-act { border: 1px solid rgba(139,148,158,.3); border-radius: 10px; padding: .45rem .7rem; margin: .1rem 0 .55rem;
            background: rgba(139,148,158,.06); }
  .ml-act-h { font-size: .74rem; letter-spacing: .04em; text-transform: uppercase; color: #8b949e; margin-bottom: .2rem; }
  .ml-step { display: flex; gap: .55rem; align-items: baseline; padding: .22rem 0; font-size: .9rem; line-height: 1.45; }
  .ml-step .ic { flex: 0 0 1.3rem; text-align: center; }
  .ml-step .lb { flex: 0 0 5.6rem; font-size: .74rem; font-weight: 600; color: #8b949e; text-transform: uppercase;
                 letter-spacing: .03em; }
  .ml-step .tx { flex: 1; min-width: 0; overflow-wrap: anywhere; }
  .ml-step.plan .tx { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .84rem; }
  .ml-step.plan.bad .tx { color: #ff7b72; }
  .ml-step.check .lb { color: #3fb950; }
  .ml-step.check .tx { color: #7ee787; }
  .ml-step.run.bad .tx { color: #ff7b72; font-weight: 600; }
  .ml-step.run.ok .tx { color: #56d364; }
  .ml-harm { display: inline-block; margin-left: .4rem; font-family: "Source Sans Pro", sans-serif; font-size: .74rem;
             font-weight: 700; padding: .05rem .45rem; border-radius: 99px; background: rgba(248,81,73,.2);
             color: #ff7b72; }
  .ml-wait { color: #8b949e; font-style: italic; font-size: .88rem; }
  .ml-out { border-radius: 10px; padding: .6rem .9rem; margin: .1rem 0 1.1rem; font-size: .92rem; }
  .ml-out b { font-size: 1rem; }
  .ml-out ul { margin: .3rem 0 0 1.1rem; padding: 0; }
  .ml-out li { margin: .1rem 0; }
  .ml-out.bad { background: rgba(248,81,73,.13); border: 1px solid rgba(248,81,73,.55); color: #ffa198; }
  .ml-out.bad b { color: #ff7b72; }
  .ml-out.ok { background: rgba(63,185,80,.11); border: 1px solid rgba(63,185,80,.55); color: #aff5b4; }
  .ml-out.ok b { color: #56d364; }
  .ml-sep { border-top: 1px dashed rgba(139,148,158,.45); margin: 1.2rem 0 .4rem; padding-top: .5rem;
            color: #8b949e; font-size: .88rem; text-align: center; }
</style>
<div class="ml-head"><h1>🛡️ MemLedger</h1><span>chat with an agent · memory protection on or off</span></div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Chat settings")
    person = chat.BY_KEY[st.selectbox("You are", list(chat.BY_KEY), format_func=lambda k: (
        f"{chat.BY_KEY[k].avatar} {chat.BY_KEY[k].label}"))]
    protected = st.toggle("MemLedger protection", value=False)
    reset = st.button("Reset memory and chat", width="stretch")


def mode(prot: bool) -> str:
    return "🟢 **Protection ON**: full MemLedger" if prot else "🔴 **Protection OFF**: plain memory"


@st.cache_resource(show_spinner="Loading the checker models…")
def guard_models() -> dict:
    """Loaded once per server and shared by every chat. The models load lazily, so a protected memory is built once
    here (its seeds run every check): otherwise the first switch to ON would stall for ~15 s mid-demo."""
    models = load_guard_models()
    chat.World(True, llm=agent_llm(), models=models)
    return models


@st.cache_resource
def agent_llm():
    return chat.default_llm()


CHECKERS = {"hf": "MiniCheck, DeBERTa NLI, injection classifier (Hugging Face)",
            "lexical": "code-only fallbacks (tests only, not the real models)"}
try:
    llm, models = agent_llm(), guard_models()
except Exception as e:  # noqa: BLE001 - no model, no demo: say what is missing instead of a traceback
    st.error(f"The real models are not available: {e}. Start vLLM (infra/README.md) and use demo/run.sh.")
    st.stop()


def new_world(prot: bool) -> chat.World:
    return chat.World(prot, llm=llm, models=models)


if "world" not in st.session_state or reset:
    st.session_state.world, st.session_state.log = new_world(protected), []
elif st.session_state.world.protected != protected:  # flipping the switch starts a fresh memory
    st.session_state.world = new_world(protected)
    sep = f"Protection switched {'ON' if protected else 'OFF'}: fresh memory with the same starting notes"
    st.session_state.log.append(("sep", sep))
world: chat.World = st.session_state.world
st.caption(mode(protected) + " · settings in the sidebar")

with st.sidebar:
    st.caption(mode(protected) + f"  \nAgent LLM: `{llm.model}`  \nCheckers: {CHECKERS.get(guard_backend(), guard_backend())}")
    with st.expander("Starting memory"):
        st.markdown(world.starting_notes() + "  \n**Signed registry:** Acme Ltd's account is 1234; lab reports go "
                    "to reports@lab.example.")
    with st.expander("Prompts to try"):
        for title, steps in chat.SCRIPT:
            st.markdown(f"**{title}**")
            for who, text in steps:
                st.caption(f"as {chat.BY_KEY[who].label}")
                st.code(text, language="sql" if who == "insider" else None, wrap_lines=True)


def esc(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


ICON = {"plan": ("🧠", "Plan"), "check": ("🛡️", "MemLedger"), "run": ("⚙️", "Result")}


def step_html(s: chat.Activity) -> str:
    icon, label = ICON[s.kind]
    harm = f'<span class="ml-harm">⚠ harmful: {esc(s.note)}</span>' if s.note else ""
    return (f'<div class="ml-step {s.kind} {s.tone}"><span class="ic">{icon}</span><span class="lb">{label}</span>'
            f'<span class="tx">{esc(s.text)}{harm}</span></div>')


def activity_html(t: chat.Turn, n: int, done: bool) -> str:
    """The agent's bubble: the first n steps of its activity, then (when done) its reply."""
    db = t.person.session is None
    steps = "".join(step_html(s) for s in t.steps[:n])
    wait = "" if done else '<div class="ml-wait">working…</div>'
    box = (f'<div class="ml-act"><div class="ml-act-h">{"Database" if db else "Agent activity"}</div>{steps}{wait}'
           "</div>") if t.steps or not done else ""
    reply = esc(t.reply) if done and t.reply else ""
    return f'<div class="ml-who">{"Database" if db else "Agent"}</div>{box}{reply}'


def outcome_html(t: chat.Turn) -> str:
    icon, sub = ("⚠️", "What happened:") if t.outcome == "bad" else ("🛡️", "What MemLedger did:")
    items = "".join(f"<li>{esc(p)}</li>" for p in t.points)
    return f'<div class="ml-out {t.outcome}"><b>{icon} {esc(t.headline)}</b><br>{sub}<ul>{items}</ul></div>'


def user_bubble(t: chat.Turn) -> None:
    body = f'<span class="ml-sql">{esc(t.prompt)}</span>' if t.person.session is None else esc(t.prompt)
    with st.chat_message("user", avatar=t.person.avatar):
        st.markdown(f'<div class="ml-who">{esc(t.person.label)}</div>{body}', unsafe_allow_html=True)


def agent_avatar(t: chat.Turn) -> str:
    return "🗄️" if t.person.session is None else ":material/smart_toy:"


def show(item) -> None:
    if item[0] == "sep":
        st.markdown(f'<div class="ml-sep">{esc(item[1])}</div>', unsafe_allow_html=True)
        return
    t: chat.Turn = item[1]
    user_bubble(t)
    with st.chat_message("assistant", avatar=agent_avatar(t)):
        st.markdown(activity_html(t, len(t.steps), True), unsafe_allow_html=True)
    if t.outcome:
        st.markdown(outcome_html(t), unsafe_allow_html=True)


def play(person: chat.Person, prompt: str) -> chat.Turn:
    """Run a prompt and show the turn as it happens: "working…" while the models run, then the activity step by step,
    the reply and the outcome."""
    t = chat.Turn(person, prompt)
    with st.chat_message("assistant", avatar=agent_avatar(t)):
        box = st.empty()
        box.markdown(activity_html(t, 0, False), unsafe_allow_html=True)
        t = world.send(person, prompt)
        st.session_state.log.append(("turn", t))  # logged before the animation: a rerun mid-way still keeps the turn
        for n in range(len(t.steps) + 1):
            box.markdown(activity_html(t, n, False), unsafe_allow_html=True)
            time.sleep(DELAY)
        box.markdown(activity_html(t, len(t.steps), True), unsafe_allow_html=True)
    if t.outcome:
        time.sleep(DELAY / 2)
        st.markdown(outcome_html(t), unsafe_allow_html=True)
    return t


for item in st.session_state.log:
    show(item)

hint = ("Type SQL to run directly on the database…" if person.session is None
        else f"Message the agent as {person.name}…")
if prompt := st.chat_input(hint):
    user_bubble(chat.Turn(person, prompt))
    play(person, prompt)
