from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
APP = str(Path(__file__).resolve().parents[2] / "demo" / "app.py")


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")
    monkeypatch.setenv("DEMO_DELAY", "0")


def html(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_off_then_on_shows_both_verdicts_in_one_chat():
    at = st_testing.AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception and at.chat_input[0].disabled
    next(b for b in at.button if "Run" in b.label).click().run()
    assert "Attack succeeded" in html(at) and "PROTECTION OFF" in html(at)
    at.toggle[0].set_value(True).run()
    next(b for b in at.button if "Run" in b.label).click().run()
    page = html(at)
    assert not at.exception and "Attack blocked" in page and "PROTECTION ON" in page and "Attack succeeded" in page


def test_every_case_can_be_picked_and_the_chat_box_asks_the_agent():
    at = st_testing.AppTest.from_file(APP, default_timeout=60).run()
    at.selectbox[0].set_value("leak").run()
    next(b for b in at.button if "Run" in b.label).click().run()
    assert "Team A&#x27;s confidential result was shown" in html(at) or "confidential result was shown" in html(at)
    at.chat_input[0].set_value("What do you know about project Falcon?").run()
    assert not at.exception and "93.1" in html(at)
    next(b for b in at.button if b.label == "Clear chat").click().run()
    assert "Attack succeeded" not in html(at)
