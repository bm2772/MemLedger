# 3-minute demo script (30 Oct) — owner M4

Setup before the slot (do not rely on Wi-Fi): `bash demo/run.sh` (fake fooled model + lexical checkers, no network),
browser at http://localhost:8501, window zoomed so both columns fit. Fallback: play the screen recording
`demo/recording.mp4` (record it with this script after the final run; keep it out of git if > 20 MB, share by link).

| time | tab | do | say |
|---|---|---|---|
| 0:00 | 1 · Poisoned web page | read the blue box aloud in one line | "A researcher's agent reads a supplier page with one planted sentence. Two weeks later finance asks the same agent to pay Acme." |
| 0:15 | 1 | **Run the scenario on both systems** | Left: "Plain memory stored it, recalled it and paid account 9876 — the attacker." Right: "MemLedger refused it: bank accounts must match the signed registry. The page is flagged, the payment takes the account from the registry, and the other memory from that page is quarantined." |
| 0:55 | 2 · Lineage view | select D3 | "Every memory knows where it came from: here D3 depends on D2, which came from a web page." |
| 1:15 | 3 · Clean-up | **Flag the web page**, then **New independent evidence for D2** | "Flag one source: exactly the memories that depended only on it are quarantined; D1 survives because a paper and a tool output also support it. New evidence restores D2 automatically." |
| 1:45 | 4 · Isolation | **Ask on both systems** | "Team B asks the agent for team A's confidential result. Plain memory hands it over; MemLedger never lets it reach the model — the unique marker appears nowhere." |
| 2:10 | 5 · Tamper detection | **Tamper and read it back** (memory text) | "Someone edits the database directly. The hash no longer matches the signed root: withheld and quarantined on the next read." |
| 2:30 | 6 · Attack families | **Run selected families** | "Nine attack families, one example each: all work on plain memory, none on MemLedger, and this column names the mechanism that stopped each." |
| 2:50 | Results | scroll to the safety table | "The measured rates with 95% intervals are here and in the deck." |

If something fails live: say "here is the same run recorded" and switch to the recording; do not debug on stage.
Real-model variant (only if the venue network and a laptop with Ollama are confirmed): sidebar → Ollama / vLLM, model
`qwen3:8b` (thinking is switched off automatically); the slide 5 run then takes ~10–20 s instead of < 1 s.
