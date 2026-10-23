# Proposal: one shared Episode format (for Ahan / M3 and Omkaar / M4)

**Problem.** Two incompatible `Episode` classes exist on open PRs:
- M3 `memledger/agent/episode.py` (PR #3): `seeds` + `turns` (ingest / propose / task) + `expect`; one default user.
- M4 `eval/episode.py` (PR #2): named `sessions` + `steps` (ingest / write / retrieve / tool / flag) + `attacker_goal`,
  `canaries` with clearance, `poison_markers`, `registry`.
Generators (M3) would emit one shape and the runner (M4) reads the other. Merging both = two sources of truth.

**Decision.** One format, owned by **M3** in `memledger/agent/episode.py`; `eval/` imports it and deletes
`eval/episode.py`. It is the union of both, using M4's multi-session model (needed for isolation tests, slides 21-22).

## Schema v1
```
Episode
  schema_version: 1
  id, source ("scenario"|"bipia"|...), split ("train"|"dev"|"test"), kind ("clean"|"attack")
  category            # M3 'category' + M4 'attack_type' merged (e.g. "poison.fake_fact", "isolation.side_channel")
  sessions: {name: Session}          # identity only from here (M4)
  default_session: str               # replaces M3's single `user`
  seeds: [Seed]                      # memory present before step 1 (M3); runner ingests them first
  steps: [Step]                      # ordered
  expect: Expect                     # ground truth (M3), + attacker_goal folded in
  canaries: [Canary]                 # marker, team, clearance; Canary.visible_to(session) (M4)
  poison_markers: [str]              # (M4)
  registry: {}                       # ground-truth protected facts (M4)
  meta: {}

Seed   id, content, kind: SourceKind, team="shared", confidentiality=0, canary="", poisoned=False, meta={}
Step   op, session=<default>, id=""  + op fields:
  ingest   kind, content, url?, poison?            (= M3 ingest)
  write    text, context?, poison?                 (= M3 propose; context defaults to refs seen so far)
  retrieve query, k?, expect?                      (M4)
  task     content                                 (M3: free agent run with the LLM, steps 5-8)
  tool     tool, params, bind?, high_risk?         (M4: scripted tool call)
  flag     source, reason                          (M4: JTMS retraction)
Expect answer?, label?, forbidden=[], blocked=[], tool_calls=[], forbidden_tool_calls=[]
       # M4 attacker_goal -> forbidden_tool_calls[0]
```
Helpers kept: `to_dict/from_dict` (round-trip test), `dump_jsonl/load_jsonl(path, split=None, limit=None)`,
`Episode.is_poison(step, text)`, validation in `__post_init__` (ops, kinds, session names).

## Tasks
- **Ahan (M3)** — branch `m3/episode-v1`: implement schema v1 in `memledger/agent/episode.py`, keep `propose` as an
  accepted alias for `write` for one day; update `scenarios/` and `bench/` loaders; round-trip + validation tests;
  convert `eval/fixtures/smoke.jsonl` with a one-off script and hand it to Omkaar.
- **Omkaar (M4)** — after `m3/episode-v1` merges: `from memledger.agent.episode import Episode, load_jsonl`; delete
  `eval/episode.py`; map `attacker_goal` → `expect.forbidden_tool_calls`; ingest `seeds` before step 1; add the `task`
  op by calling M3's agent runner. CI green.
- **Merge order:** #3 (agent) → `m3/episode-v1` → #4 (scenarios) rebased → #2 (runner) rebased. #1 (infra) anytime.
- Deadline: before Saturday's 18:00 integration freeze.
