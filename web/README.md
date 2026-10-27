# web/ — MemLedger console (owner: M3)

A product UI for MemLedger. It is separate from `demo/` (M4's Streamlit slide demo), which stays unchanged. The console
is a FastAPI server over `LedgerService` (`web/api.py`) plus a React + TypeScript app (`web/ui`, built with Vite).

```bash
make web          # npm ci + build the UI, then serve everything on http://127.0.0.1:8000
make web-dev      # API on :8000 + Vite hot reload on :5173 (proxies /api)
```

API docs: http://127.0.0.1:8000/api/docs.

## What it does

| Page | What you can do | Mechanism (deck) |
|---|---|---|
| Workspaces | Create a persistent memory from a template (Acme slide 5, Figure 1 slide 6, empty) at any of the 5 protection levels | eval/versions.py, slide 17 |
| Overview | Memory / quarantine / source counts, ledger integrity, protections on, trust histogram, activity | — |
| Memories | Browse, filter, propose a memory (shows every check's verdict), open one: lineage graph, hash check on read, status history, add evidence to restore | slides 6, 7, 12–14 |
| Sources | Ingest (input screen flags injections on arrival), flag a source → JTMS quarantines only what depended on it | slides 7, 12 |
| Agent | Run the tool-using agent as the signed-in user, with the fooled test model or the server's LLM; see each tool call as asked vs executed (registry binding, gate blocks) | slides 5, 9, 16 |
| Recall | Exactly what the agent would be shown for a query, for your identity | slide 15 |
| Registry | The Ed25519-signed registry; admins set values, and the history is kept and re-signed | slides 8, 9 |
| Audit & integrity | Console activity, status log, signed Merkle hash log, "verify all", JSON export | slide 14 |
| Attack lab | Slide 5 side by side (plain memory vs MemLedger) and the DB-tamper drill on throw-away memories | slides 5, 14 |
| Results | `docs/results.md` and the attack-suite manifest | eval/report.py |

## Identity and deployment

The rule is that identity comes from login, never from the browser or the model.

- **Local (open mode):** without `$MEMLEDGER_USERS`, the sidebar lets you act as a demo user (ria, fin, bo, admin).
  Open mode only starts on localhost; `python -m web --host 0.0.0.0` refuses it unless you pass `--allow-open`.
- **Deployed (token mode):** point `$MEMLEDGER_USERS` at a JSON file that maps tokens to identities:
  ```json
  {"<long random token>": {"user_id": "ria", "team": "team_a", "role": "researcher", "clearance": 1}}
  ```
  Every request then needs `Authorization: Bearer <token>`, and the UI shows a sign-in screen. The registry and
  workspace deletion need `role: "registry-admin"`.
- **Docker:** `docker build -f web/Dockerfile -t memledger-console .`, then run it with a volume on `/data`. The header
  of `web/Dockerfile` has the full command. Put TLS in front of it (Caddy, nginx or a cloud load balancer).

| Variable | Default | Meaning |
|---|---|---|
| `MEMLEDGER_DATA_DIR` | `var/memledger` | One folder per workspace: `store.sqlite`, `ledger.key`, `registry.json`/`.key`, `activity.jsonl`. Back it up and keep it private: the keys sign the ledger. |
| `MEMLEDGER_USERS` | unset (open mode) | Token file, see above |
| `MEMLEDGER_GUARD_BACKEND` | `lexical` | `hf` uses the real checker models (needs `make setup-models`) |
| `MEMLEDGER_LLM_MODEL` / `MEMLEDGER_LLM_BASE_URL` | `qwen3:8b` / Ollama on :11434 | The "server" model on the Agent page and in the Attack lab. It is set on the server only, so the browser cannot point it elsewhere. |

## Brand media (e.g. Higgsfield)

The landing hero plays `web/ui/public/brand/hero.mp4` if that file exists (or shows `hero.jpg`), at low opacity
behind the headline. Nothing breaks without it. To use a generated clip:

1. Generate a short, seamless, dark, abstract loop (for example "slow drifting green ledger lines on near-black,
   subtle, no text") at 1920×1080, 6–10 s.
2. Save it as `web/ui/public/brand/hero.mp4`. Keep it under about 4 MB (`ffmpeg -i in.mp4 -an -vcodec libx264 -crf 30 hero.mp4`).
3. Run `make web-build`.

Check the generator's licence terms before shipping its output.

## Tests

`tests/console/test_api.py` covers:

- the Acme attack, blocked end to end on full and successful on baseline;
- Figure 1 flag/restore;
- team isolation;
- the admin-only signed registry;
- restart persistence with roots that still verify;
- token-mode identity;
- the lab endpoints.

To type-check and build the UI, run `npm run build` in `web/ui`.
