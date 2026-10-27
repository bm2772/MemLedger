from pathlib import Path

import pytest
import streamlit as st

from demo import chat

st_testing = pytest.importorskip("streamlit.testing.v1")
APP = str(Path(__file__).resolve().parents[2] / "demo" / "app.py")


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    monkeypatch.setenv("DEMO_DELAY", "0")


def html(at) -> str:
    return " ".join(m.value for m in at.markdown)


def type_as(at, who: str, text: str):
    at.selectbox[0].set_value(who).run()
    return at.chat_input[0].set_value(text).run()


def test_same_prompts_get_through_off_and_are_stopped_on():
    at = st_testing.AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    for who, text in chat.SCRIPT[0][1]:
        type_as(at, who, text)
    assert "Harmful action carried out" in html(at) and "account 9876" in html(at)
    at.toggle[0].set_value(True).run()
    assert "Protection switched ON" in html(at)
    for who, text in chat.SCRIPT[0][1]:
        type_as(at, who, text)
    page = html(at)
    assert not at.exception and "prevented by MemLedger" in page and "account 1234" in page


def test_insider_sql_and_reset():
    at = st_testing.AppTest.from_file(APP, default_timeout=60).run()
    for who, text in chat.SCRIPT[5][1]:
        type_as(at, who, text)
    assert not at.exception and "19% recall" in html(at) and "Harmful action carried out" in html(at)
    next(b for b in at.button if b.label.startswith("Reset")).click().run()
    assert "Harmful action carried out" not in html(at)


def test_without_the_real_models_the_app_says_so(monkeypatch):
    def missing():
        raise RuntimeError("no agent LLM")

    monkeypatch.setattr(chat, "default_llm", missing)
    st.cache_resource.clear()  # the app keeps its LLM for the server's lifetime
    at = st_testing.AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception and "real models are not available" in at.error[0].value and not at.chat_input
