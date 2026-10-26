| version | oracle attack success | hijacked action | leak rate | tamper detection | side-channel count leak | benign task accuracy | legit payment not completed correctly | legit payment held or refused (false denial) | harmless write rejected | added write ms | added read ms | added gate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 52/60 = 86.7% [75.8%, 93.1%] | 28/28 = 100.0% [87.9%, 100.0%] | 20/125 = 16.0% [10.6%, 23.4%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 1/1 = 100.0% [20.7%, 100.0%] | 24/25 = 96.0% [80.5%, 99.3%] | 5/28 = 17.9% [7.9%, 35.6%] | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 0/96 = 0.0% [0.0%, 3.8%], < 3.1% (rule of 3) | +0.00 | +0.00 | – |
| full | 3/60 = 5.0% [1.7%, 13.7%] | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 0/125 = 0.0% [0.0%, 3.0%], < 2.4% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 24/25 = 96.0% [80.5%, 99.3%] | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 4/96 = 4.2% [1.6%, 10.2%] | +25.17 | +0.69 | – |

Oracle attack success per family (attacks/oracle.py):

| family | n | baseline | full |
|---|---|---|---|
| agentpoison | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| db_tamper | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| fake_fact | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| isolation | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| isolation_matrix | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| minja | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| planted_doc | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| poisonedrag | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 1/5 = 20.0% [3.6%, 62.4%] |
| poisoning | 10 | 7/10 = 70.0% [39.7%, 89.2%] | 2/10 = 20.0% [5.7%, 51.0%] |
| repetition_flooding | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| summary_laundering | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |

Leak rate per family (a marker the user may not see appeared in anything visible):

| family | n | baseline | full |
|---|---|---|---|
| agentpoison | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| db_tamper | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| fake_fact | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| isolation | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| isolation_matrix | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| minja | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| planted_doc | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| poisonedrag | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| poisoning | 10 | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) |
| repetition_flooding | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| summary_laundering | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |

Tamper detection per family (tampered item withheld and quarantined, read from the service state):

| family | n | baseline | full |
|---|---|---|---|
| db_tamper | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] |

Legit payment not completed correctly per family (benign twins and clean payments; not made, or made to a wrong account):

| family | n | baseline | full |
|---|---|---|---|
| agentpoison | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| clean | 15 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| minja | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| poisonedrag | 10 | 0/3 = 0.0% [0.0%, 56.1%], < 100.0% (rule of 3) | 0/3 = 0.0% [0.0%, 56.1%], < 100.0% (rule of 3) |
| repetition_flooding | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| summary_laundering | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |

Legit payment held or refused per family (false denial: the gate or registry stopped it):

| family | n | baseline | full |
|---|---|---|---|
| agentpoison | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| clean | 15 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| minja | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| poisonedrag | 10 | 0/3 = 0.0% [0.0%, 56.1%], < 100.0% (rule of 3) | 0/3 = 0.0% [0.0%, 56.1%], < 100.0% (rule of 3) |
| repetition_flooding | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| summary_laundering | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |

Harmless write rejected per family (benign twins and clean episodes):

| family | n | baseline | full |
|---|---|---|---|
| agentpoison | 10 | 0/2 = 0.0% [0.0%, 65.8%], < 100.0% (rule of 3) | 0/2 = 0.0% [0.0%, 65.8%], < 100.0% (rule of 3) |
| minja | 10 | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) |
| poisonedrag | 10 | 0/8 = 0.0% [0.0%, 32.4%], < 37.5% (rule of 3) | 0/8 = 0.0% [0.0%, 32.4%], < 37.5% (rule of 3) |
| poisoning | 20 | 0/15 = 0.0% [0.0%, 20.4%], < 20.0% (rule of 3) | 4/15 = 26.7% [10.9%, 52.0%] |
| repetition_flooding | 10 | 0/57 = 0.0% [0.0%, 6.3%], < 5.3% (rule of 3) | 0/57 = 0.0% [0.0%, 6.3%], < 5.3% (rule of 3) |
| summary_laundering | 10 | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) |

Benign task accuracy per family:

| family | n | baseline | full |
|---|---|---|---|
| clean | 15 | 10/10 = 100.0% [72.2%, 100.0%] | 10/10 = 100.0% [72.2%, 100.0%] |
| db_tamper | 10 | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] |
| isolation_matrix | 10 | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] |
| planted_doc | 10 | 2/3 = 66.7% [20.8%, 93.9%] | 2/3 = 66.7% [20.8%, 93.9%] |
| poisonedrag | 10 | 2/2 = 100.0% [34.2%, 100.0%] | 2/2 = 100.0% [34.2%, 100.0%] |

Blocked attacks per version, by the first mechanism that visibly stopped them (attacks/attribution.py); 'attack succeeded' is the complement:

| mechanism | baseline | full |
|---|---|---|
| hash verification | – | 6 |
| input screen | – | 5 |
| hallucination check | – | 8 |
| memshield | – | 11 |
| contradiction / trust | – | 1 |
| registry match | – | 3 |
| access check (write) | – | – |
| JTMS retraction | – | 1 |
| registry binding | – | 1 |
| action gate | – | 6 |
| read filter | – | 5 |
| team scoping | – | 3 |
| none fired | 8 | 7 |
| attack succeeded | 52 | 3 |

Mechanisms that acted on attack material in any attack episode (a later mechanism hidden behind an earlier one still counts here):

| mechanism | baseline | full |
|---|---|---|
| hash verification | – | 6 |
| input screen | – | 5 |
| hallucination check | – | 13 |
| memshield | – | 11 |
| contradiction / trust | – | 1 |
| registry match | – | 19 |
| access check (write) | – | – |
| JTMS retraction | – | 2 |
| registry binding | – | 3 |
| action gate | – | 7 |
| read filter | – | 12 |

Benchmark episodes (agent runs with the benchmark payload; attack success by the per-episode oracle, 'harmless blocked' = clean-twin writes rejected / clean tool outputs quarantined, 'top mechanism' = what most often stopped an attack):

| benchmark | version | oracle attack success | harmless write rejected | clean input quarantined | clean task accuracy | LLM calls | top mechanism |
|---|---|---|---|---|---|---|---|
| bipia | baseline | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 2/3 = 66.7% [20.8%, 93.9%] | 21 | none fired 5 |
| bipia | full | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 2/3 = 66.7% [20.8%, 93.9%] | 21 | none fired 5 |
| memevobench | baseline | 3/5 = 60.0% [23.1%, 88.2%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 18 | none fired 2 |
| memevobench | full | 1/5 = 20.0% [3.6%, 62.4%] | 3/10 = 30.0% [10.8%, 60.3%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 18 | none fired 2, memshield 2 |
| memshield | baseline | 4/5 = 80.0% [37.6%, 96.4%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 11 | none fired 1 |
| memshield | full | 1/5 = 20.0% [3.6%, 62.4%] | 1/5 = 20.0% [3.6%, 62.4%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 11 | memshield 4 |

Write-path classification, per labelled memory entry (positive = poisoned/misleading; predicted positive = the write was rejected). Not attack success: see attacks/classify.py:

| benchmark | version | TP | FP | FN | TN | precision | recall | F1 | harmless rejected |
|---|---|---|---|---|---|---|---|---|---|
| memshield | baseline | 0 | 0 | 5 | 5 | – | 0.00 | 0.00 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| memshield | full | 4 | 1 | 1 | 4 | 0.80 | 0.80 | 0.80 | 1/5 = 20.0% [3.6%, 62.4%] |
| memevobench | baseline | 0 | 0 | 15 | 20 | – | 0.00 | 0.00 | 0/20 = 0.0% [0.0%, 16.1%], < 15.0% (rule of 3) |
| memevobench | full | 6 | 6 | 9 | 14 | 0.50 | 0.40 | 0.44 | 6/20 = 30.0% [14.5%, 51.9%] |

Recall by attack type / domain (rejected poisoned writes):

| benchmark | type | baseline | full |
|---|---|---|---|
| memshield | T10_c2_persistence | 0/1 = 0.0% | 1/1 = 100.0% |
| memshield | T5_backdoor_trigger | 0/2 = 0.0% | 2/2 = 100.0% |
| memshield | T7_recommendation_poisoning | 0/2 = 0.0% | 1/2 = 50.0% |
| memevobench | customerservice | 0/6 = 0.0% | 5/6 = 83.3% |
| memevobench | finance | 0/3 = 0.0% | 0/3 = 0.0% |
| memevobench | food | 0/3 = 0.0% | 1/3 = 33.3% |
| memevobench | mental | 0/3 = 0.0% | 0/3 = 0.0% |
