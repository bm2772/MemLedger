"""Attack suite (slides 17-18, 21-23): the fixed dev set and the final test set, as Episode v1.

Two parts, each episode with ground truth (expect.blocked / forbidden / forbidden_tool_calls / label) and a family tag
in meta["family"]:

  scenario   our multi-team world (scenarios/generator.py): fake-fact payment poisoning (slide 5), cross-team and
             clearance leaks via the model (I1), plus the clean recall/payment episodes that measure usefulness.
             Dev and test use disjoint worlds (dev seeds 0.., test seeds 1000..), so no memory, canary or vendor
             account is shared between them.
  families    seven attack families generated from seeds (attacks/<family>.py, Episode v1 with an oracle in
             meta["oracle"]): agentpoison, poisonedrag, minja, summary_laundering, repetition_flooding, db_tamper and the
             8x6 isolation_matrix. They count as part "scenario". Dev seeds are 0..n-1, test seeds 10000..10000+n-1.
  benchmark  published payloads adapted to agent episodes (bench/loaders.py): memshield-bench and MemEvoBench memory
             entries (family "poisoning"; ingested as sources, written with that source as support, then a question),
             BIPIA documents with an inserted text attack (planted_doc), InjecAgent tool-response hijacks and AgentDojo
             injection tasks (tool_hijack, test only). Every attack episode has a goal oracle (meta["oracle"]) and a
             clean counterpart. Official splits where they exist; dev never draws on test data (BIPIA: train for
             tuning, test for evaluation).

Benchmarks whose data is missing are skipped and reported in the manifest (run `python -m bench.download <name>`).

    python -m attacks.suite --out data/attacks          # writes dev.jsonl, test.jsonl, manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from attacks import agentpoison, db_tamper, flooding, isolation, laundering, minja, poisonedrag
from bench import load
from memledger.agent.episode import Episode, dump_jsonl
from scenarios.generator import Config, generate

SPLITS = ("dev", "test")
TEST_SEED_OFFSET = 1000  # test worlds never reuse a dev world's seed
FAMILY = {  # scenario category / benchmark name -> attack family
    "fake_fact": "fake_fact", "cross_team": "isolation", "clearance": "isolation",
    "memshield": "poisoning", "memevobench": "poisoning", "bipia": "planted_doc",
    "injecagent": "tool_hijack", "agentdojo": "tool_hijack",
}
FAMILIES = {m.FAMILY: m for m in (agentpoison, poisonedrag, minja, laundering, flooding, db_tamper, isolation)}
FAMILY.update({name: name for name in FAMILIES})
DEV_SEED0, TEST_SEED0 = 0, 10_000  # per-family generator seeds; the ranges never overlap
FAMILY_SIZES = {"agentpoison": 60, "poisonedrag": 60, "minja": 60, "summary_laundering": 64, "repetition_flooding": 64,
                "db_tamper": 72, "isolation_matrix": 144}  # per split; multiples of the variant count (>= 500 in all)
# (benchmark, splits it may be used for); InjecAgent and AgentDojo are test only (never tuned on)
BENCHMARKS = [("memshield", SPLITS), ("memevobench", SPLITS), ("bipia", SPLITS),
              ("injecagent", ("test",)), ("agentdojo", ("test",))]
# Test-split sample per benchmark (None = all); dev keeps SuiteConfig.bench_limit because it is used for tuning. The
# unit is the loader's: memshield poisoned entries (and as many clean), MemEvoBench items, BIPIA documents, InjecAgent
# attack cases (each with a clean twin), AgentDojo (injection task, user task) pairs. Test then has memshield 179,
# MemEvoBench 166, BIPIA 300, InjecAgent 600 and AgentDojo 230 episodes (was 80/80/80/80/15 with 40 each).
TEST_BENCH_LIMITS: dict[str, int | None] = {"memshield": None, "memevobench": None, "bipia": None,
                                            "injecagent": 300, "agentdojo": 230}


@dataclass
class SuiteConfig:
    dev_worlds: int = 3  # 72 episodes per world with the default scenario Config
    test_worlds: int = 3
    n_teams: int = 3
    bench_limit: int = 40  # per benchmark on dev (and on test for a benchmark missing from test_bench_limits)
    seed: int = 0
    benchmarks: list[str] = field(default_factory=lambda: [b for b, _ in BENCHMARKS])
    family_sizes: dict[str, int] = field(default_factory=lambda: dict(FAMILY_SIZES))  # episodes per family and split
    test_bench_limits: dict[str, int | None] = field(default_factory=lambda: dict(TEST_BENCH_LIMITS))

    def limit(self, name: str, split: str) -> int | None:
        return self.test_bench_limits.get(name, self.bench_limit) if split == "test" else self.bench_limit


DEFAULT_ORACLE = {"fake_fact": "tool_call", "cross_team": "canary", "clearance": "canary"}  # scenario categories


def _oracle(e: Episode) -> dict | None:
    """Families from attacks/<family>.py carry their own oracle; give the others one so every attack is graded."""
    if e.kind != "attack" or "oracle" in e.meta:
        return e.meta.get("oracle")
    if e.category in DEFAULT_ORACLE:
        return {"type": DEFAULT_ORACLE[e.category]}
    return {"type": "blocked"} if e.expect.blocked else None


def _tag(e: Episode, split: str, part: str) -> Episode:
    e.split = split
    e.meta = {**e.meta, "part": part, "family": FAMILY.get(e.category) or FAMILY.get(e.source) or e.kind}
    if (o := _oracle(e)) is not None:
        e.meta["oracle"] = o
    return e


def scenario_episodes(split: str, cfg: SuiteConfig) -> list[Episode]:
    n, base = (cfg.dev_worlds, 0) if split == "dev" else (cfg.test_worlds, TEST_SEED_OFFSET)
    out = []
    for i in range(n):
        out += [_tag(e, split, "scenario") for e in generate(Config(seed=cfg.seed + base + i, n_teams=cfg.n_teams)).episodes]
    return out


def family_episodes(split: str, cfg: SuiteConfig) -> list[Episode]:
    base = DEV_SEED0 if split == "dev" else TEST_SEED0
    return [_tag(FAMILIES[name].generate(base + i), split, "scenario")
            for name, n in cfg.family_sizes.items() for i in range(n)]


def benchmark_episodes(split: str, cfg: SuiteConfig, root: str | Path | None = None) -> tuple[list[Episode], dict]:
    out, skipped = [], {}
    for name, allowed in BENCHMARKS:
        if name not in cfg.benchmarks or split not in allowed:
            continue
        try:
            eps = load(name, split=split, limit=cfg.limit(name, split), seed=cfg.seed, root=root)
        except (FileNotFoundError, ImportError) as e:
            skipped[name] = str(e).splitlines()[0]
            continue
        out += [_tag(e, split, "benchmark") for e in eps]
    return out, skipped


def build(split: str, cfg: SuiteConfig | None = None, root: str | Path | None = None) -> tuple[list[Episode], dict]:
    if split not in SPLITS:
        raise ValueError(f"split must be one of {SPLITS}, got {split!r}")
    cfg = cfg or SuiteConfig()
    bench_eps, skipped = benchmark_episodes(split, cfg, root)
    return scenario_episodes(split, cfg) + family_episodes(split, cfg) + bench_eps, skipped


def manifest(eps: list[Episode], skipped: dict) -> dict:
    blob = "\n".join(json.dumps(e.to_dict(), sort_keys=True) for e in eps).encode()
    return {"n": len(eps), "sha256": hashlib.sha256(blob).hexdigest(), "skipped": skipped,
            "by_kind": dict(Counter(e.kind for e in eps)),
            "by_family": dict(sorted(Counter(e.meta["family"] for e in eps).items())),
            "by_source": dict(sorted(Counter(e.source for e in eps).items()))}


def write(out: str | Path, cfg: SuiteConfig | None = None, root: str | Path | None = None) -> dict:
    out = Path(out)
    report = {}
    for split in SPLITS:
        eps, skipped = build(split, cfg, root)
        dump_jsonl(eps, out / f"{split}.jsonl")
        report[split] = manifest(eps, skipped)
    (out / "manifest.json").write_text(json.dumps(report, indent=1))
    return report


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="data/attacks")
    p.add_argument("--dev-worlds", type=int, default=3)
    p.add_argument("--test-worlds", type=int, default=3)
    p.add_argument("--bench-limit", type=int, default=40, help="per benchmark on dev")
    p.add_argument("--test-bench-limit", type=int,
                   help="one limit for every benchmark on test (default: TEST_BENCH_LIMITS; 40 = the old suite)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--family-scale", type=float, default=1.0, help="scale the per-family episode counts")
    p.add_argument("--manifest", help="also copy manifest.json here (committed, e.g. docs/results/suite_manifest.json)")
    a = p.parse_args(argv)
    sizes = {k: max(1, round(v * a.family_scale)) for k, v in FAMILY_SIZES.items()}
    test_limits = dict(TEST_BENCH_LIMITS) if a.test_bench_limit is None else \
        {name: a.test_bench_limit for name in TEST_BENCH_LIMITS}
    report = write(a.out, SuiteConfig(a.dev_worlds, a.test_worlds, bench_limit=a.bench_limit, seed=a.seed,
                                      family_sizes=sizes, test_bench_limits=test_limits))
    if a.manifest:
        Path(a.manifest).parent.mkdir(parents=True, exist_ok=True)
        Path(a.manifest).write_text(json.dumps(report, indent=1) + "\n")
    for split, m in report.items():
        print(f"{split}: {m['n']} episodes {m['by_family']} skipped={sorted(m['skipped'])}")


if __name__ == "__main__":
    main()
