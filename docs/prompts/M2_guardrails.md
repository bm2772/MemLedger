# M2 — Guardrails (memledger/guards, policy, registry)

## Day 1 (22 Oct) — branch m2/registry
Read CLAUDE.md, docs/interfaces.md, core/types.py, core/interfaces.py and slides 8, 9, 12, 13 of the deck. Implement
memledger/registry: JSON schema (key, value, confidentiality, owner, valid_from), Ed25519 sign/verify (cryptography
lib), a CLI `python -m memledger.registry sign|verify|get`, refusal of unsigned or altered files, and an admin-role
check stub (role 'registry-admin' from Session). Key files never committed (.gitignore covers *.key). Tests first.

## Day 2 (23 Oct) — branch m2/screens
memledger/guards/input_screen.py implementing InputScreen (slide 12): (1) unhide — NFKC normalise, strip zero-width
chars, decode Base64 and HTML entities, extract HTML comments/alt text/hidden styling; (2) regex rules for instruction
phrases, role markers, tool-call syntax, store/send requests; (3) classifier — Llama Prompt Guard 2 86M via
transformers on 512-token chunks, injectable so tests use a fake; (4) spotlighting helper that wraps passing text as
quoted data with its source. score() returns max over layers; thresholds high/mid/low configurable. Then
memledger/guards/hallucination.py: a Check that splits a proposal into atomic sentences and scores each against the
sources' text with MiniCheck (or AlignScore), injectable model; reject below threshold.

## Day 3 (24 Oct) — branch m2/checks-policy
memledger/guards: contradiction Check (DeBERTa-v3 MNLI cross-encoder on top-k similar claims; non-overlapping validity
intervals = update), registry-match Check (protected keys must equal registry value), memshield Check (fine-tune
DeBERTa-v3-base on memshield-bench train split, report on its test split; training script in memledger/guards/train/,
weights NOT committed). memledger/policy: access control (team/shared scope, clearance, label propagation c=max,
integrity=min, taint rules I3/I4) and ActionGate (low/medium/high risk tools; high risk allowed only if params come from
registry or re-checked facts; else enqueue for human approval; registry-bound parameters for send_payment). Tests for
each, including a fully "fooled model" test that still cannot redirect a payment.

## Day 4 (25 Oct) — branch m2/integration
Plug all checks into M1's LedgerService (pull main). Run threshold sweeps on DEV data only (BIPIA train split for the
input screen; never InjecAgent/AgentDojo). Integration freeze 18:00.

## Day 5–6 (26–27 Oct)
Calibrate fact-checker scores (held-out data), fix bugs. On 27 Oct test M1's area (core/store/retrieval) against the
checklist and file issues.
