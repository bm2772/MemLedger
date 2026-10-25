# demo/ — Streamlit demo (owner: M4, slide 24 Figure 7)

```bash
pip install -e ".[demo]"
bash demo/run.sh        # offline: fake fooled model + lexical checkers, HF offline, no telemetry
```
3-minute presenter script: [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).

| Tab | Shows | Mechanism |
|---|---|---|
| 1 · Poisoned web page | Slide 5 side by side: plain memory stores the fake account and pays 9876; MemLedger rejects it (registry match), flags the page, binds the account from the registry and quarantines the other memory derived from the page | registry check, input/source flagging, I10 binding, JTMS |
| 2 · Lineage view | `explain()` as a graph: sources, memories, one edge per derivation; flagged/quarantined in red | provenance graph |
| 3 · Clean-up | Slide 6 Figure 1: flag the web page → D2, D3 quarantined, D1 kept (independent justification); new evidence restores | JTMS retraction / restore |
| 4 · Isolation | Team B asks the agent for team A's confidential note: plain memory leaks it (marker in the answer), MemLedger withholds it | access control read filter, leak check 2 |
| 5 · Tamper detection | Edit a memory, its source or its timestamp directly in SQLite → withheld and quarantined on the next read | hash chain + signed Merkle root |
| 6 · Attack families | One episode per family (`data/attacks/dev.jsonl` if built, else generated offline) on plain memory vs MemLedger, with the mechanism that stopped it. Each family shows its first episode that works on plain memory: an illustration, not a rate | attacks/oracle.py, attacks/attribution.py |
| Results | `docs/results.md`, or how to generate it if missing | eval/report.py |

The default agent is `eval.llm.GullibleLLM`, which believes everything, so the live demo is deterministic and the
difference comes only from the memory layer. The sidebar switches to a real model (Ollama or vLLM). Logic is in
`scenario.py` (tested in `tests/demo/`); `app.py` only lays it out.
