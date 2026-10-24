from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
APP = str(Path(__file__).resolve().parents[2] / "demo" / "app.py")


@pytest.fixture(autouse=True)
def lexical(monkeypatch):
    monkeypatch.setenv("MEMLEDGER_GUARD_BACKEND", "lexical")


def test_app_renders_and_runs_every_tab():
    at = st_testing.AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    at.button[0].click().run()  # slide 5 on both systems
    assert not at.exception
    texts = " ".join(e.value for e in at.error) + " ".join(e.value for e in at.success)
    assert "Paid the attacker" in texts and "Paid safely" in texts
    flag = next(b for b in at.button if b.label.startswith("Flag the web page"))
    flag.click().run()
    assert not at.exception and any("quarantined: ['D2', 'D3']" in m.value for m in at.markdown)
    tamper = next(b for b in at.button if b.label.startswith("Tamper"))
    tamper.click().run()
    assert not at.exception and any(s.value.startswith("Detected") for s in at.success)
