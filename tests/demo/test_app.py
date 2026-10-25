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


def test_isolation_and_attack_family_tabs():
    at = st_testing.AppTest.from_file(APP, default_timeout=120).run()
    next(b for b in at.button if b.label == "Ask on both systems").click().run()
    assert not at.exception
    assert any(e.value.startswith("**Leaked**") for e in at.error)
    assert any(s.value.startswith("**Withheld.**") for s in at.success)
    at.multiselect[0].set_value(["minja", "db_tamper"]).run()
    next(b for b in at.button if b.label == "Run selected families").click().run()
    assert not at.exception
    rows = at.dataframe[-1].value
    assert list(rows["family"]) == ["minja", "db_tamper"]
    assert set(rows["plain memory"]) == {"attack worked"} and set(rows["MemLedger"]) == {"defended"}
