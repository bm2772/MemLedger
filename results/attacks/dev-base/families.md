> **Added ms (write/read/gate) are NOT meaningful here**: 16 parallel episodes add thread contention. Take latency from a 1-worker run (`make eval-latency`).

| version | oracle attack success | hijacked action | leak rate | tamper detection | side-channel count leak | benign task accuracy | legit payment not completed correctly | legit payment held or refused (false denial) | harmless write rejected | added write ms | added read ms | added gate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 685/749 = 91.5% [89.2%, 93.3%] | 308/308 = 100.0% [98.8%, 100.0%] | 333/1034 = 32.2% [29.4%, 35.1%] | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 18/18 = 100.0% [82.4%, 100.0%] | 133/139 = 95.7% [90.9%, 98.0%] | 13/66 = 19.7% [11.9%, 30.8%] | 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | 0/256 = 0.0% [0.0%, 1.5%], < 1.2% (rule of 3) | +0.00 | +0.00 | – |
| write_checks | 254/749 = 33.9% [30.6%, 37.4%] | 134/308 = 43.5% [38.1%, 49.1%] | 114/1034 = 11.0% [9.3%, 13.1%] | 72/72 = 100.0% [94.9%, 100.0%] | 0/18 = 0.0% [0.0%, 17.6%], < 16.7% (rule of 3) | 133/139 = 95.7% [90.9%, 98.0%] | 13/66 = 19.7% [11.9%, 30.8%] | 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | 7/256 = 2.7% [1.3%, 5.5%] | +388.44 | +1.11 | – |
| full | 27/749 = 3.6% [2.5%, 5.2%] | 0/308 = 0.0% [0.0%, 1.2%], < 1.0% (rule of 3) | 0/1034 = 0.0% [0.0%, 0.4%], < 0.3% (rule of 3) | 72/72 = 100.0% [94.9%, 100.0%] | 0/18 = 0.0% [0.0%, 17.6%], < 16.7% (rule of 3) | 133/139 = 95.7% [90.9%, 98.0%] | 1/66 = 1.5% [0.3%, 8.1%] | 1/66 = 1.5% [0.3%, 8.1%] | 7/256 = 2.7% [1.3%, 5.5%] | +398.40 | +1.09 | – |

Oracle attack success per family (attacks/oracle.py):

| family | n | baseline | write_checks | full |
|---|---|---|---|---|
| agentpoison | 60 | 60/60 = 100.0% [94.0%, 100.0%] | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) |
| db_tamper | 72 | 72/72 = 100.0% [94.9%, 100.0%] | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) |
| fake_fact | 12 | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |
| isolation | 108 | 108/108 = 100.0% [96.6%, 100.0%] | 66/108 = 61.1% [51.7%, 69.8%] | 0/108 = 0.0% [0.0%, 3.4%], < 2.8% (rule of 3) |
| isolation_matrix | 144 | 141/144 = 97.9% [94.1%, 99.3%] | 48/144 = 33.3% [26.2%, 41.4%] | 0/144 = 0.0% [0.0%, 2.6%], < 2.1% (rule of 3) |
| minja | 60 | 60/60 = 100.0% [94.0%, 100.0%] | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) |
| planted_doc | 40 | 2/40 = 5.0% [1.4%, 16.5%] | 2/40 = 5.0% [1.4%, 16.5%] | 3/40 = 7.5% [2.6%, 19.9%] |
| poisonedrag | 60 | 57/60 = 95.0% [86.3%, 98.3%] | 37/60 = 61.7% [49.0%, 72.9%] | 6/60 = 10.0% [4.7%, 20.1%] |
| poisoning | 65 | 45/65 = 69.2% [57.2%, 79.1%] | 15/65 = 23.1% [14.5%, 34.6%] | 18/65 = 27.7% [18.3%, 39.6%] |
| repetition_flooding | 64 | 64/64 = 100.0% [94.3%, 100.0%] | 42/64 = 65.6% [53.4%, 76.1%] | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) |
| summary_laundering | 64 | 64/64 = 100.0% [94.3%, 100.0%] | 32/64 = 50.0% [38.1%, 61.9%] | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) |

Leak rate per family (a marker the user may not see appeared in anything visible):

| family | n | baseline | write_checks | full |
|---|---|---|---|---|
| agentpoison | 60 | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) |
| db_tamper | 72 | 72/72 = 100.0% [94.9%, 100.0%] | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) |
| fake_fact | 12 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |
| isolation | 108 | 108/108 = 100.0% [96.6%, 100.0%] | 66/108 = 61.1% [51.7%, 69.8%] | 0/108 = 0.0% [0.0%, 3.4%], < 2.8% (rule of 3) |
| isolation_matrix | 144 | 141/144 = 97.9% [94.1%, 99.3%] | 48/144 = 33.3% [26.2%, 41.4%] | 0/144 = 0.0% [0.0%, 2.6%], < 2.1% (rule of 3) |
| minja | 60 | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) |
| planted_doc | 40 | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) |
| poisonedrag | 60 | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) |
| poisoning | 65 | 0/65 = 0.0% [0.0%, 5.6%], < 4.6% (rule of 3) | 0/65 = 0.0% [0.0%, 5.6%], < 4.6% (rule of 3) | 0/65 = 0.0% [0.0%, 5.6%], < 4.6% (rule of 3) |
| repetition_flooding | 64 | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) |
| summary_laundering | 64 | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) |

Tamper detection per family (tampered item withheld and quarantined, read from the service state):

| family | n | baseline | write_checks | full |
|---|---|---|---|---|
| db_tamper | 72 | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 72/72 = 100.0% [94.9%, 100.0%] | 72/72 = 100.0% [94.9%, 100.0%] |

Legit payment not completed correctly per family (benign twins and clean payments; not made, or made to a wrong account):

| family | n | baseline | write_checks | full |
|---|---|---|---|---|
| agentpoison | 72 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 1/12 = 8.3% [1.5%, 35.4%] |
| clean | 96 | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |
| minja | 72 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |
| poisonedrag | 72 | 1/6 = 16.7% [3.0%, 56.4%] | 1/6 = 16.7% [3.0%, 56.4%] | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) |
| repetition_flooding | 76 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |
| summary_laundering | 76 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |

Legit payment held or refused per family (false denial: the gate or registry stopped it):

| family | n | baseline | write_checks | full |
|---|---|---|---|---|
| agentpoison | 72 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 1/12 = 8.3% [1.5%, 35.4%] |
| clean | 96 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |
| minja | 72 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |
| poisonedrag | 72 | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) |
| repetition_flooding | 76 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |
| summary_laundering | 76 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |

Harmless write rejected per family (benign twins and clean episodes):

| family | n | baseline | write_checks | full |
|---|---|---|---|---|
| agentpoison | 72 | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) |
| minja | 72 | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) |
| poisonedrag | 72 | 0/32 = 0.0% [0.0%, 10.7%], < 9.4% (rule of 3) | 0/32 = 0.0% [0.0%, 10.7%], < 9.4% (rule of 3) | 0/32 = 0.0% [0.0%, 10.7%], < 9.4% (rule of 3) |
| poisoning | 130 | 0/90 = 0.0% [0.0%, 4.1%], < 3.3% (rule of 3) | 7/90 = 7.8% [3.8%, 15.2%] | 7/90 = 7.8% [3.8%, 15.2%] |
| repetition_flooding | 76 | 0/96 = 0.0% [0.0%, 3.8%], < 3.1% (rule of 3) | 0/96 = 0.0% [0.0%, 3.8%], < 3.1% (rule of 3) | 0/96 = 0.0% [0.0%, 3.8%], < 3.1% (rule of 3) |
| summary_laundering | 76 | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) |

Benign task accuracy per family:

| family | n | baseline | write_checks | full |
|---|---|---|---|---|
| clean | 96 | 84/84 = 100.0% [95.6%, 100.0%] | 84/84 = 100.0% [95.6%, 100.0%] | 84/84 = 100.0% [95.6%, 100.0%] |
| db_tamper | 84 | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] |
| isolation_matrix | 156 | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] |
| planted_doc | 80 | 19/25 = 76.0% [56.6%, 88.5%] | 19/25 = 76.0% [56.6%, 88.5%] | 19/25 = 76.0% [56.6%, 88.5%] |
| poisonedrag | 72 | 6/6 = 100.0% [61.0%, 100.0%] | 6/6 = 100.0% [61.0%, 100.0%] | 6/6 = 100.0% [61.0%, 100.0%] |

Blocked attacks per version, by the first mechanism that visibly stopped them (attacks/attribution.py); 'attack succeeded' is the complement:

| mechanism | baseline | write_checks | full |
|---|---|---|---|
| hash verification | – | 81 | 81 |
| input screen | – | 63 | 72 |
| hallucination check | – | 36 | 80 |
| memshield | – | 100 | 100 |
| contradiction / trust | – | 23 | 24 |
| registry match | – | – | 72 |
| access check (write) | – | – | – |
| JTMS retraction | – | 18 | 8 |
| registry binding | – | – | 8 |
| action gate | – | – | 30 |
| read filter | – | – | 174 |
| team scoping | – | 129 | 33 |
| none fired | 64 | 45 | 40 |
| attack succeeded | 685 | 254 | 27 |

Mechanisms that acted on attack material in any attack episode (a later mechanism hidden behind an earlier one still counts here):

| mechanism | baseline | write_checks | full |
|---|---|---|---|
| hash verification | – | 81 | 81 |
| input screen | – | 63 | 72 |
| hallucination check | – | 98 | 151 |
| memshield | – | 103 | 105 |
| contradiction / trust | – | 23 | 24 |
| registry match | – | – | 260 |
| access check (write) | – | – | – |
| JTMS retraction | – | 32 | 16 |
| registry binding | – | – | 45 |
| action gate | – | – | 36 |
| read filter | – | – | 197 |

Benchmark episodes (agent runs with the benchmark payload; attack success by the per-episode oracle, 'harmless blocked' = clean-twin writes rejected / clean tool outputs quarantined, 'top mechanism' = what most often stopped an attack):

| benchmark | version | oracle attack success | harmless write rejected | clean input quarantined | clean task accuracy | LLM calls | top mechanism |
|---|---|---|---|---|---|---|---|
| bipia | baseline | 2/40 = 5.0% [1.4%, 16.5%] | – | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 19/25 = 76.0% [56.6%, 88.5%] | 161 | none fired 38 |
| bipia | write_checks | 2/40 = 5.0% [1.4%, 16.5%] | – | 2/40 = 5.0% [1.4%, 16.5%] | 19/25 = 76.0% [56.6%, 88.5%] | 161 | none fired 37, input screen 1 |
| bipia | full | 3/40 = 7.5% [2.6%, 19.9%] | – | 2/40 = 5.0% [1.4%, 16.5%] | 19/25 = 76.0% [56.6%, 88.5%] | 161 | none fired 36, input screen 1 |
| memevobench | baseline | 9/25 = 36.0% [20.2%, 55.5%] | 0/50 = 0.0% [0.0%, 7.1%], < 6.0% (rule of 3) | 0/50 = 0.0% [0.0%, 7.1%], < 6.0% (rule of 3) | – | 86 | none fired 16 |
| memevobench | write_checks | 10/25 = 40.0% [23.4%, 59.3%] | 5/50 = 10.0% [4.3%, 21.4%] | 0/50 = 0.0% [0.0%, 7.1%], < 6.0% (rule of 3) | – | 85 | none fired 8, memshield 6 |
| memevobench | full | 13/25 = 52.0% [33.5%, 70.0%] | 5/50 = 10.0% [4.3%, 21.4%] | 0/50 = 0.0% [0.0%, 7.1%], < 6.0% (rule of 3) | – | 86 | memshield 6, none fired 4 |
| memshield | baseline | 36/40 = 90.0% [76.9%, 96.0%] | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 85 | none fired 4 |
| memshield | write_checks | 5/40 = 12.5% [5.5%, 26.1%] | 2/40 = 5.0% [1.4%, 16.5%] | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 85 | memshield 34, input screen 1 |
| memshield | full | 5/40 = 12.5% [5.5%, 26.1%] | 2/40 = 5.0% [1.4%, 16.5%] | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 85 | memshield 34, input screen 1 |

Write-path classification, per labelled memory entry (positive = poisoned/misleading; predicted positive = the write was rejected). Not attack success: see attacks/classify.py:

| benchmark | version | TP | FP | FN | TN | precision | recall | F1 | harmless rejected |
|---|---|---|---|---|---|---|---|---|---|
| memshield | baseline | 0 | 0 | 40 | 40 | – | 0.00 | 0.00 | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) |
| memshield | write_checks | 35 | 2 | 5 | 38 | 0.95 | 0.88 | 0.91 | 2/40 = 5.0% [1.4%, 16.5%] |
| memshield | full | 35 | 2 | 5 | 38 | 0.95 | 0.88 | 0.91 | 2/40 = 5.0% [1.4%, 16.5%] |
| memevobench | baseline | 0 | 0 | 75 | 100 | – | 0.00 | 0.00 | 0/100 = 0.0% [0.0%, 3.7%], < 3.0% (rule of 3) |
| memevobench | write_checks | 16 | 10 | 59 | 90 | 0.62 | 0.21 | 0.32 | 10/100 = 10.0% [5.5%, 17.4%] |
| memevobench | full | 16 | 10 | 59 | 90 | 0.62 | 0.21 | 0.32 | 10/100 = 10.0% [5.5%, 17.4%] |

Recall by attack type / domain (rejected poisoned writes):

| benchmark | type | baseline | write_checks | full |
|---|---|---|---|---|
| memshield | T10_c2_persistence | 0/2 = 0.0% | 2/2 = 100.0% | 2/2 = 100.0% |
| memshield | T1_instruction_override | 0/4 = 0.0% | 3/4 = 75.0% | 3/4 = 75.0% |
| memshield | T2_data_exfiltration | 0/4 = 0.0% | 4/4 = 100.0% | 4/4 = 100.0% |
| memshield | T3_behavioral_drift | 0/4 = 0.0% | 4/4 = 100.0% | 4/4 = 100.0% |
| memshield | T4_factual_manipulation | 0/1 = 0.0% | 1/1 = 100.0% | 1/1 = 100.0% |
| memshield | T5_backdoor_trigger | 0/11 = 0.0% | 11/11 = 100.0% | 11/11 = 100.0% |
| memshield | T6_experience_poisoning | 0/2 = 0.0% | 2/2 = 100.0% | 2/2 = 100.0% |
| memshield | T7_recommendation_poisoning | 0/4 = 0.0% | 1/4 = 25.0% | 1/4 = 25.0% |
| memshield | T8_configuration_poisoning | 0/1 = 0.0% | 1/1 = 100.0% | 1/1 = 100.0% |
| memshield | T9_security_degradation | 0/7 = 0.0% | 6/7 = 85.7% | 6/7 = 85.7% |
| memevobench | customerservice | 0/21 = 0.0% | 12/21 = 57.1% | 12/21 = 57.1% |
| memevobench | finance | 0/12 = 0.0% | 0/12 = 0.0% | 0/12 = 0.0% |
| memevobench | food | 0/12 = 0.0% | 2/12 = 16.7% | 2/12 = 16.7% |
| memevobench | health | 0/18 = 0.0% | 2/18 = 11.1% | 2/18 = 11.1% |
| memevobench | mental | 0/9 = 0.0% | 0/9 = 0.0% | 0/9 = 0.0% |
| memevobench | privacy | 0/3 = 0.0% | 0/3 = 0.0% | 0/3 = 0.0% |
