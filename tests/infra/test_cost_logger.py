import csv
from types import SimpleNamespace

import pytest

from infra.cost_logger import FIELDS, TokenMeter, log_session, main, summarize


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def test_log_session_creates_file_with_header(tmp_path):
    p = tmp_path / "budget.csv"
    log_session(member="M4", instance="brev-1", gpu="A10G", hours=2.0, rate=1.5, purpose="dev", path=p,
                date="2026-10-23")
    (r,) = rows(p)
    assert list(r) == FIELDS
    assert r["usd"] == "3.00" and r["hours"] == "2.00" and r["date"] == "2026-10-23"


def test_explicit_usd_wins_and_rows_append(tmp_path):
    p = tmp_path / "budget.csv"
    log_session(member="M4", instance="a", gpu="L4", hours=1.0, usd=0.8, purpose="x", path=p)
    log_session(member="M2", instance="b", gpu="L4", hours=1.0, usd=1.2, purpose="y", path=p,
                prompt_tokens=10, completion_tokens=5)
    rs = rows(p)
    assert [r["usd"] for r in rs] == ["0.80", "1.20"]
    assert rs[1]["prompt_tokens"] == "10" and rs[1]["completion_tokens"] == "5"


def test_needs_usd_or_rate(tmp_path):
    with pytest.raises(ValueError):
        log_session(member="M4", instance="a", gpu="L4", hours=1.0, purpose="x", path=tmp_path / "b.csv")


def test_old_header_without_token_columns_is_kept(tmp_path):
    p = tmp_path / "budget.csv"
    p.write_text("date,member,instance,gpu,hours,usd,purpose\n")
    log_session(member="M4", instance="a", gpu="L4", hours=1.0, usd=1.0, purpose="x", path=p, prompt_tokens=3)
    (r,) = rows(p)
    assert "prompt_tokens" not in r and r["usd"] == "1.00"


def test_token_meter_reads_openai_usage_objects_and_dicts():
    m = TokenMeter()
    m.add(SimpleNamespace(usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20)))
    m.add({"usage": {"prompt_tokens": 5, "completion_tokens": 1}})
    m.add(SimpleNamespace(usage=None))
    assert (m.prompt_tokens, m.completion_tokens, m.calls) == (105, 21, 3)


def test_summary_totals_and_remaining(tmp_path):
    p = tmp_path / "budget.csv"
    log_session(member="M4", instance="a", gpu="L4", hours=1.0, usd=40, purpose="dev", path=p)
    log_session(member="M4", instance="a", gpu="L4", hours=2.0, usd=60, purpose="main runs", path=p)
    s = summarize(p, budget=1000)
    assert s["usd"] == pytest.approx(100) and s["hours"] == pytest.approx(3)
    assert s["remaining"] == pytest.approx(900)
    assert s["by_purpose"] == {"dev": pytest.approx(40), "main runs": pytest.approx(60)}


def test_cli_session_and_summary(tmp_path, capsys):
    p = tmp_path / "budget.csv"
    main(["--path", str(p), "session", "--member", "M4", "--instance", "a", "--gpu", "L4",
          "--hours", "0.5", "--rate", "2", "--purpose", "smoke"])
    main(["--path", str(p), "summary"])
    out = capsys.readouterr().out
    assert "1.00" in out and "999.00" in out
