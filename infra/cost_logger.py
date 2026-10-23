"""Brev GPU cost + token logger (M4 owns the $1,000 budget, docs/TEAM_PLAN.md).

Every GPU session gets one row in infra/budget.csv (hours, dollars, tokens served). TokenMeter counts tokens from
OpenAI-compatible responses (vLLM / Ollama) so runs can report tokens next to dollars.

    python infra/cost_logger.py session --member M4 --instance brev-a10g-1 --gpu A10G --hours 1.5 \
        --rate 1.10 --purpose "baseline run" [--prompt-tokens N --completion-tokens N]
    python infra/cost_logger.py summary
"""

from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as _date
from pathlib import Path

BUDGET_CSV = Path(__file__).with_name("budget.csv")
BUDGET_USD = 1000.0
FIELDS = ["date", "member", "instance", "gpu", "hours", "usd", "purpose", "prompt_tokens", "completion_tokens"]


def _header(path: Path) -> list[str] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    with path.open(newline="") as f:
        return next(csv.reader(f), None)


def log_session(*, member: str, instance: str, gpu: str, hours: float, purpose: str,
                usd: float | None = None, rate: float | None = None, prompt_tokens: int = 0,
                completion_tokens: int = 0, date: str | None = None, path: Path | str = BUDGET_CSV) -> dict:
    """Append one session row. usd is given directly or computed as hours * rate (USD per GPU-hour)."""
    if usd is None:
        rate = rate if rate is not None else _env_rate()
        if rate is None:
            raise ValueError("give usd or rate (or set BREV_RATE_USD_PER_HOUR)")
        usd = hours * rate
    path = Path(path)
    row = {"date": date or _date.today().isoformat(), "member": member, "instance": instance, "gpu": gpu,
           "hours": f"{hours:.2f}", "usd": f"{usd:.2f}", "purpose": purpose,
           "prompt_tokens": str(prompt_tokens), "completion_tokens": str(completion_tokens)}
    fields = _header(path)
    new = fields is None
    fields = fields or FIELDS  # keep an existing file's columns rather than rewriting history
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)
    return row


def _env_rate() -> float | None:
    v = os.environ.get("BREV_RATE_USD_PER_HOUR")
    return float(v) if v else None


@dataclass
class TokenMeter:
    """Accumulates usage from OpenAI-style responses (objects or dicts with .usage / ['usage'])."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0

    def add(self, response) -> None:
        self.calls += 1
        usage = response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
        if not usage:
            return
        get = usage.get if isinstance(usage, dict) else lambda k, d=0: getattr(usage, k, d)
        self.prompt_tokens += int(get("prompt_tokens", 0) or 0)
        self.completion_tokens += int(get("completion_tokens", 0) or 0)


def summarize(path: Path | str = BUDGET_CSV, budget: float = BUDGET_USD) -> dict:
    path = Path(path)
    usd = hours = 0.0
    by_purpose: dict[str, float] = defaultdict(float)
    if path.exists():
        with path.open(newline="") as f:
            for r in csv.DictReader(f):
                usd += float(r.get("usd") or 0)
                hours += float(r.get("hours") or 0)
                by_purpose[r.get("purpose") or ""] += float(r.get("usd") or 0)
    return {"usd": usd, "hours": hours, "remaining": budget - usd, "by_purpose": dict(by_purpose)}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--path", default=str(BUDGET_CSV))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("session", help="append one GPU session")
    for name in ("member", "instance", "gpu", "purpose"):
        s.add_argument(f"--{name}", required=True)
    s.add_argument("--hours", type=float, required=True)
    s.add_argument("--usd", type=float)
    s.add_argument("--rate", type=float, help="USD per hour; defaults to $BREV_RATE_USD_PER_HOUR")
    s.add_argument("--prompt-tokens", type=int, default=0)
    s.add_argument("--completion-tokens", type=int, default=0)
    s.add_argument("--date")
    sub.add_parser("summary", help="totals against the $1,000 budget")
    a = ap.parse_args(argv)
    if a.cmd == "session":
        row = log_session(member=a.member, instance=a.instance, gpu=a.gpu, hours=a.hours, purpose=a.purpose,
                          usd=a.usd, rate=a.rate, prompt_tokens=a.prompt_tokens,
                          completion_tokens=a.completion_tokens, date=a.date, path=a.path)
        print(f"logged {row['hours']} h, ${row['usd']} ({row['purpose']})")
    else:
        s = summarize(a.path)
        print(f"spent ${s['usd']:.2f} over {s['hours']:.2f} GPU-h; remaining ${s['remaining']:.2f} of "
              f"${BUDGET_USD:.0f}")
        for purpose, usd in sorted(s["by_purpose"].items(), key=lambda x: -x[1]):
            print(f"  {purpose:<24} ${usd:.2f}")


if __name__ == "__main__":
    main()
