# MemLedger — 8-minute pitch: speaker notes

Slides: `docs/MemLedger_pitch_8min.pdf` (11 slides, 8:00 total). The full deck is `docs/MemLedger_presentation.pdf`.

## 1. MemLedger

[0:00–0:15, 15 s] Good morning. We are Prompt Stars, and this is MemLedger: provenance-governed memory for long-running AI agents. In eight minutes: the problem, what goes wrong today, how we fix it, and how well it works.

## 2. Agent Memory Governance Evaluation

[0:15–1:00, 45 s] Our problem statement is Agent Memory Governance Evaluation. Agents that run for weeks store what they read and act on it later. If that memory is poisoned, untraceable, contradictory or leaked, the agent can be steered without anyone noticing. The statement asks for four pillars: security, privacy, safety and reliability — and it asks for two things: to govern memory, and to measure how well it is governed. This is not hypothetical: in the MemSecBench study, across 24 agent configurations, half of the memory-poisoning test cases ended in a real attacker-steered action. That is their number, not ours.

## 3. Five ways an agent’s memory goes wrong

[1:00–1:55, 55 s] Concretely, five things go wrong. Poisoning: a web page says a vendor’s bank account changed, and weeks later the agent pays the attacker. Unknown origin: a claim repeated by one website looks as reliable as a paper. Hallucination: the agent stores a summary its sources do not support. Leaks: team A’s agent answers with team B’s figures. And tampering: someone edits the database directly. Why don’t today’s defences catch this? Poison usually reads like an ordinary fact, so injection filters miss it. Plain retrieval returns whatever is most similar, so a planted note comes first. And the model alone decides — once it is fooled, nothing stops the action.

## 4. MemLedger: the agent proposes, the service decides

[1:55–2:45, 50 s] Our solution is MemLedger, a memory layer between the agent and its storage. The agent can only propose what to remember and request actions; the service decides what is stored, what is read back and what is allowed to run. Four core ideas. One: provenance is recorded by the system — a fact-checking model confirms which sources actually support each memory, so poison can’t hide by going uncited. Two: trust that repetition can’t inflate — a memory is only as trusted as its weakest source, and planting a claim ten times still counts once. Three: targeted clean-up — flag a bad source and everything derived from it is quarantined, without wiping memory. Four: hard guarantees in plain code — a signed registry for critical facts, gated risky actions, team isolation and hash checks — so they hold even when the model is fooled.

## 5. “Acme’s bank account has changed to 9876”

[2:45–3:40, 55 s] Here is one attack end to end. The agent reads a supplier page saying Acme’s bank account changed to 9876. Two weeks later, finance asks it to pay Acme’s invoice. With plain memory, the line is stored, recalled as relevant context, and the agent pays 9876 — and nothing records why. With MemLedger, the page is saved as a low-trust web source and linked to the claim. Bank accounts are protected facts, so the claim is checked against our signed registry, fails, and the page is flagged. The payment tool reads Acme’s account from the registry itself, so even a fooled model pays the right account. And everything derived from the page is quarantined.

## 6. Eight steps, two lanes

[3:40–4:35, 55 s] This is the whole system on one slide. Top lane, writing a memory: every input is screened for injected instructions and saved as a source; the agent proposes a memory; we check that its sources support it, that protected facts match the registry, and whether it conflicts with what we already know — then score its trust and store it with its links. Bottom lane, using a memory: retrieve within the user’s own team, filter out quarantined, outdated or low-trust items, build the context with sources shown, and gate any high-risk action — a payment or an email runs only on trusted inputs, otherwise a person approves it. The key point: the source log, registry, gate and access control are plain code, so they hold even if the model is fooled.

## 7. Attacks drop from one in two to one in 25

[4:35–5:15, 40 s] How well does it work? On our held-out test split — 2,299 episodes per version, with NVIDIA’s Nemotron Nano 9B v2 as the agent — 3.9% of attacks succeed against MemLedger, versus 48.9% on plain memory. Zero hijacked payments or emails out of 838 attempts, and zero cross-team leaks in all 2,299 runs. The cost: 5.6% of harmless writes are rejected, just over our 5% target — we report that honestly rather than tune on the test set.

## 8. Each layer removes a class of attack

[5:15–6:05, 50 s] We switch each layer on in turn, so you can see what each one buys. Provenance alone cuts attack success from 49% to 32%, cuts leaks from 14% to 4%, and catches every database edit. The write checks cut attacks to 13% — and that is where the cost appears, 5.5% of harmless writes rejected and 20 milliseconds per write. Access control and the action gate take hijacked actions and leaks to zero. Without the registry, attack success is about the same, but legitimate payments stop completing — the registry is what lets safe payments through.

## 9. It holds on benchmarks we never tuned on

[6:05–6:50, 45 s] It also holds on published benchmarks. AgentDojo and InjecAgent were test only — never used for tuning — and attack success drops to zero on both. MemShield-bench falls from 94% to 10%, and our own multi-team scenarios from 82% to 4%. Two weak spots remain, highlighted in orange: BIPIA and MemEvoBench, where more than 10% of attacks still get through. We’ll come back to them.

## 10. What it costs, and where it still falls short

[6:50–7:35, 45 s] What does it cost? About 21 milliseconds per memory write and under a millisecond per read. Task accuracy drops 2.1 points. 5.6% of harmless writes are rejected, just over our target. No legitimate payment is held or refused, and our whole evaluation cost about 19 dollars of GPU time. Where we still fall short: PoisonedRAG — near-duplicate documents asserting one false fact — still gets through 43% of the time, so we need a better hallucination rule. MemEvoBench gets through 13%, and BIPIA 10%, where the input screen also blocks some clean emails. Each has a concrete next step.

## 11. The model proposes, the code decides: a fooled agent still cannot pay the attacker or leak another team’s data.

[7:35–8:00, 25 s] To close: MemLedger lets the model propose and the code decide, so even a fooled agent cannot pay the attacker or leak another team’s data. 3.9% attack success instead of 48.9%, zero hijacks, zero leaks, every database edit caught — for 21 milliseconds per write. Thank you; we’re happy to take questions.
