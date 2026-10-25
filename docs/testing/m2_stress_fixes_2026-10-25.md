# M2 fixes for the stress-test findings (branch m2/stress-fixes, 25 Oct 2026)

| Finding | Fix | Test |
|---|---|---|
| Gate trusted tool output (InjecAgent 52% on `full`, fake agent) | `SourceKind.TOOL` is now in `policy/items.py` UNTRUSTED_KINDS: a tool response taints the session (I4) and cannot be a trusted Ctx(a) item, so model-supplied high-risk params go to a person | `tests/policy/test_policy.py::test_tool_output_cannot_satisfy_the_gate_injecagent` |
| F10 fp16 checkers | `guards/models.py` loads every HF checker with `dtype=torch.float32` (`torch_dtype` on transformers < 4.56) | `tests/guards/test_models.py` |
| F11 gated Prompt Guard | default classifier falls back to `protectai/deberta-v3-base-prompt-injection-v2` (with its tuned cut-off) and warns when Prompt Guard 2 cannot load; an explicit `$MEMLEDGER_PROMPT_GUARD_MODEL` gets no fallback | `tests/guards/test_models.py` |
| MiniCheck rejected an identical code snippet | `guards/hallucination.py`: a proposal (or fact) found verbatim, whitespace-normalised, in its sources scores 1.0 before the model | `tests/guards/test_hallucination.py::test_identical_code_snippet_passes_without_the_model` |
| F5 PoisonedRAG answer goals pass `full` | **left open, by design of M2's area.** The planted answer comes from WEB passages that do support it, so the hallucination check is right to pass it, and `answer` is a low-risk tool the gate never blocks. The claims carry low trust (WEB prior 0.3 × s) and are labelled untrusted. Closing it needs either a minimum-trust filter for answers at retrieval (M1, `retrieval/`) or a contradiction check against registry/paper claims with the full NLI model (lexical backend cannot). Expect the HF run to catch some; report the lexical number as a known limit. | — |

Side effect to watch on Brev: benign InjecAgent/AgentDojo tasks whose high-risk call takes a model-chosen value after a tool read now wait for approval (approval load / FRR up, ASR down).
