"""Download scripts for the published benchmarks (slide 23, Appendix A2). Data is never committed: it goes to
data/<name>/ (gitignored) or $MEMLEDGER_DATA/<name>/.

Usage: python -m bench.download [name ...]        (no names = all; already-downloaded files are skipped)

Notes: LLM-AggreFact is gated: accept its terms on Hugging Face and export HF_TOKEN. AgentDojo ships its tasks as
Python code: `pip install agentdojo` (loaded in-process, nothing to download). BIPIA's qa/abstract sets need
third-party licences and are not used.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

GH = "https://raw.githubusercontent.com"
HF = "https://huggingface.co/datasets"

FILES: dict[str, dict[str, str]] = {
    "longmemeval": {  # s variant: ~115k-token haystacks, 500 questions (277 MB)
        "longmemeval_s_cleaned.json": f"{HF}/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json",
    },
    "locomo": {"locomo10.json": f"{GH}/snap-research/locomo/main/data/locomo10.json"},
    "bipia": {
        **{f"{task}/{split}.jsonl": f"{GH}/microsoft/BIPIA/main/benchmark/{task}/{split}.jsonl"
           for task in ("email", "table") for split in ("train", "test")},
        **{f"text_attack_{split}.json": f"{GH}/microsoft/BIPIA/main/benchmark/text_attack_{split}.json"
           for split in ("train", "test")},
    },
    "injecagent": {f"test_cases_{s}_base.json": f"{GH}/uiuc-kang-lab/InjecAgent/main/data/test_cases_{s}_base.json"
                   for s in ("dh", "ds")},
    "memshield": {f"{s}.jsonl": f"{HF}/npow/memshield-bench/resolve/main/data/{s}.jsonl"
                  for s in ("train", "validation", "test")},
    "memevobench": {f"{d}.json": f"{GH}/xiewwee11/MemEvoBench/main/memorybench/QA/{d}_memory_triplequery.json"
                    for d in ("customerservice", "finance", "food", "health", "mental", "privacy", "traffic")},
    "ragtruth": {f: f"{GH}/ParticleMedia/RAGTruth/main/dataset/{f}" for f in ("response.jsonl", "source_info.jsonl")},
    "halueval": {"qa_data.json": f"{GH}/RUCAIBox/HaluEval/main/data/qa_data.json"},
}
AGGREFACT_ROWS = "https://datasets-server.huggingface.co/rows?dataset=lytang/LLM-AggreFact&config=default"
AGGREFACT_MAX_ROWS = 3000  # per split, sampled at evenly spaced offsets so every sub-dataset is represented
NAMES = [*FILES, "llm_aggrefact", "agentdojo"]


def data_dir(name: str = "", root: str | Path | None = None) -> Path:
    base = Path(root or os.environ.get("MEMLEDGER_DATA") or os.environ.get("MEMLEDGER_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
    return base / name if name else base


def _ssl_context() -> ssl.SSLContext:
    """python.org macOS builds ship without CA roots; use certifi's bundle when it is installed."""
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _open(url: str, headers: dict | None = None, timeout: float = 300):
    req = urllib.request.Request(url, headers={"User-Agent": "memledger-bench", **(headers or {})})
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=_ssl_context())
    except urllib.error.URLError as e:
        if not isinstance(e.reason, ssl.SSLCertVerificationError):
            raise
        raise RuntimeError("TLS certificate check failed: `pip install certifi` or run Python's "
                           "'Install Certificates.command' (macOS)") from e


def _fetch(url: str, dest: Path, headers: dict | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with _open(url, headers) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.replace(dest)


def _rows_page(split: str, offset: int, length: int, auth: dict) -> dict:
    with _open(f"{AGGREFACT_ROWS}&split={split}&offset={offset}&length={length}", auth, 120) as r:
        return json.load(r)


def _aggrefact(dest_dir: Path) -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("LLM-AggreFact is gated: accept its terms on huggingface.co and export HF_TOKEN")
    auth = {"Authorization": f"Bearer {token}"}
    for split in ("dev", "test"):
        dest = dest_dir / f"{split}.jsonl"
        if dest.exists():
            continue
        total = _rows_page(split, 0, 1, auth)["num_rows_total"]
        n_pages = max(1, min(total, AGGREFACT_MAX_ROWS) // 100)
        rows = []
        for i in range(n_pages):
            rows += [r["row"] for r in _rows_page(split, i * total // n_pages, 100, auth)["rows"]]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text("".join(json.dumps(r) + "\n" for r in rows))


def download(name: str, root: str | Path | None = None) -> Path:
    dest_dir = data_dir(name, root)
    if name == "agentdojo":
        return dest_dir  # tasks come from the installed `agentdojo` package
    if name == "llm_aggrefact":
        _aggrefact(dest_dir)
        return dest_dir
    for rel, url in FILES[name].items():
        dest = dest_dir / rel
        if not dest.exists():
            print(f"  {name}/{rel}", file=sys.stderr)
            _fetch(url, dest)
    return dest_dir


def main(argv: list[str] | None = None) -> None:
    names = (argv if argv is not None else sys.argv[1:]) or NAMES
    for n in names:
        if n not in NAMES:
            raise SystemExit(f"unknown dataset {n!r}; choose from {NAMES}")
        try:
            print(f"{n}: {download(n)}")
        except (RuntimeError, OSError) as e:
            print(f"{n}: skipped ({e})", file=sys.stderr)


if __name__ == "__main__":
    main()

