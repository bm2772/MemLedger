# eval/ — 5-version runner and metrics (owner: M4)

```bash
python -m eval.runner --episodes eval/fixtures/smoke.jsonl --versions baseline --run-id my-run
python -m eval.runner --episodes <M3 set>.jsonl --split dev --versions baseline,provenance,write_checks,full,full_no_registry
```
Output: `results/raw/<run_id>/<version>.jsonl` (per episode, gitignored — copy off Brev before stopping) and
`results/<run_id>/summary.{json,md}` (commit these).

| File | What |
|---|---|
| `episode.py` | Episode format the runner consumes (docstring = the spec M3's generators/loaders should emit) |
| `versions.py` | The five versions as flags; resolves M1/M2 components lazily from `module:attr` paths |
| `runner.py` | Scripted replay agent + recording `Env`; per-episode records and a point-estimate summary |
| `metrics.md` | Every metric on slides 18–19 and properties I1–I10 with exact formulas |
| `fixtures/smoke.jsonl` | 5 hand-written episodes (slide 5 Acme attack, repetition flood, cross-team canary, 2 clean) — a smoke test, **not** the benchmark |

## Honest degradation
A version asks for components (e.g. `full` needs M1's `LedgerService`, M2's checks, input screen, action gate and
registry binder). Anything that cannot be imported yet is listed under `missing` in the manifest, every record of
that run carries `degraded: true`, and the summary table shows it. Nothing is stubbed in its place, so a degraded
`full` run looks like the baseline rather than pretending to be protected. Use `--strict` for the real runs.

## What M1 / M2 / M3 need to provide (default paths in `versions.DEFAULT_COMPONENTS`; override with `--components cfg.json`)
- **M1**: `memledger.core.service:LedgerService(checks=[...])` — already works on `m1/trust-retrieval`
  (checked in a local merge). Wanted: a plain mode without trust/quarantine so `baseline` uses the same retriever
  (today `baseline` = `MockMemoryService`, so task accuracy loss mixes retriever differences with layer effects).
- **M2**: no-arg classes implementing `Check` (hallucination, memshield, contradiction, registry match),
  `InputScreen`, `ActionGate`, and a registry binder `bind_params(tool, params, session) -> params` (I10).
  Tell M4 the real module paths and they go into `DEFAULT_COMPONENTS`.
- **M3**: Episodes in the format in `episode.py` (or a converter). Ground truth the runner needs: `poison` labels or
  `poison_markers`, `attacker_goal`, `canaries` (128-bit markers with team + clearance), `expect` on clean
  questions. An LLM agent plugs in by driving the same `Env` methods instead of `ScriptedAgent`.
