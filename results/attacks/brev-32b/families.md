> **Added ms (write/read/gate) are NOT meaningful here**: 16 parallel episodes add thread contention. Take latency from a 1-worker run (`make eval-latency`).

| version | oracle attack success | hijacked action | leak rate | tamper detection | side-channel count leak | benign task accuracy | legit payment not completed correctly | legit payment held or refused (false denial) | harmless write rejected | added write ms | added read ms | added gate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 693/819 = 84.6% [82.0%, 86.9%] | 311/363 = 85.7% [81.7%, 88.9%] | 333/1159 = 28.7% [26.2%, 31.4%] | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 18/18 = 100.0% [82.4%, 100.0%] | 138/142 = 97.2% [93.0%, 98.9%] | 13/66 = 19.7% [11.9%, 30.8%] | 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | 0/364 = 0.0% [0.0%, 1.0%], < 0.8% (rule of 3) | +0.00 | +0.00 | – |
| provenance | 433/819 = 52.9% [49.4%, 56.3%] | 279/363 = 76.9% [72.3%, 80.9%] | 90/1159 = 7.8% [6.4%, 9.4%] | 72/72 = 100.0% [94.9%, 100.0%] | 0/18 = 0.0% [0.0%, 17.6%], < 16.7% (rule of 3) | 139/142 = 97.9% [94.0%, 99.3%] | 13/66 = 19.7% [11.9%, 30.8%] | 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | 0/364 = 0.0% [0.0%, 1.0%], < 0.8% (rule of 3) | -0.50 | +1.88 | – |
| write_checks | 235/819 = 28.7% [25.7%, 31.9%] | 134/363 = 36.9% [32.1%, 42.0%] | 84/1159 = 7.2% [5.9%, 8.9%] | 72/72 = 100.0% [94.9%, 100.0%] | 0/18 = 0.0% [0.0%, 17.6%], < 16.7% (rule of 3) | 136/142 = 95.8% [91.1%, 98.0%] | 13/66 = 19.7% [11.9%, 30.8%] | 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | 34/364 = 9.3% [6.8%, 12.8%] | +343.54 | +1.03 | – |
| full | 29/819 = 3.5% [2.5%, 5.0%] | 0/363 = 0.0% [0.0%, 1.0%], < 0.8% (rule of 3) | 0/1159 = 0.0% [0.0%, 0.3%], < 0.3% (rule of 3) | 72/72 = 100.0% [94.9%, 100.0%] | 0/18 = 0.0% [0.0%, 17.6%], < 16.7% (rule of 3) | 136/142 = 95.8% [91.1%, 98.0%] | 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | 0/66 = 0.0% [0.0%, 5.5%], < 4.5% (rule of 3) | 34/364 = 9.3% [6.8%, 12.8%] | +351.96 | +0.92 | – |
| full_no_registry | 32/819 = 3.9% [2.8%, 5.5%] | 0/363 = 0.0% [0.0%, 1.0%], < 0.8% (rule of 3) | 18/1159 = 1.6% [1.0%, 2.4%] | 72/72 = 100.0% [94.9%, 100.0%] | 0/18 = 0.0% [0.0%, 17.6%], < 16.7% (rule of 3) | 137/142 = 96.5% [92.0%, 98.5%] | 66/66 = 100.0% [94.5%, 100.0%] | 54/66 = 81.8% [70.9%, 89.3%] | 34/364 = 9.3% [6.8%, 12.8%] | +338.31 | +0.97 | – |

Oracle attack success per family (attacks/oracle.py):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| agentpoison | 60 | 60/60 = 100.0% [94.0%, 100.0%] | 60/60 = 100.0% [94.0%, 100.0%] | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) |
| db_tamper | 72 | 72/72 = 100.0% [94.9%, 100.0%] | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) |
| fake_fact | 12 | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |
| isolation | 108 | 108/108 = 100.0% [96.6%, 100.0%] | 36/108 = 33.3% [25.2%, 42.7%] | 36/108 = 33.3% [25.2%, 42.7%] | 0/108 = 0.0% [0.0%, 3.4%], < 2.8% (rule of 3) | 0/108 = 0.0% [0.0%, 3.4%], < 2.8% (rule of 3) |
| isolation_matrix | 144 | 141/144 = 97.9% [94.1%, 99.3%] | 54/144 = 37.5% [30.0%, 45.6%] | 48/144 = 33.3% [26.2%, 41.4%] | 0/144 = 0.0% [0.0%, 2.6%], < 2.1% (rule of 3) | 0/144 = 0.0% [0.0%, 2.6%], < 2.1% (rule of 3) |
| minja | 60 | 60/60 = 100.0% [94.0%, 100.0%] | 60/60 = 100.0% [94.0%, 100.0%] | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) |
| planted_doc | 40 | 7/40 = 17.5% [8.7%, 31.9%] | 8/40 = 20.0% [10.5%, 34.8%] | 8/40 = 20.0% [10.5%, 34.8%] | 8/40 = 20.0% [10.5%, 34.8%] | 8/40 = 20.0% [10.5%, 34.8%] |
| poisonedrag | 60 | 57/60 = 95.0% [86.3%, 98.3%] | 59/60 = 98.3% [91.1%, 99.7%] | 45/60 = 75.0% [62.8%, 84.2%] | 10/60 = 16.7% [9.3%, 28.0%] | 11/60 = 18.3% [10.6%, 29.9%] |
| poisoning | 80 | 45/80 = 56.2% [45.3%, 66.6%] | 46/80 = 57.5% [46.6%, 67.7%] | 13/80 = 16.2% [9.7%, 25.8%] | 11/80 = 13.8% [7.9%, 23.0%] | 13/80 = 16.2% [9.7%, 25.8%] |
| repetition_flooding | 64 | 52/64 = 81.2% [70.0%, 88.9%] | 52/64 = 81.2% [70.0%, 88.9%] | 31/64 = 48.4% [36.6%, 60.4%] | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) |
| summary_laundering | 64 | 64/64 = 100.0% [94.3%, 100.0%] | 32/64 = 50.0% [38.1%, 61.9%] | 32/64 = 50.0% [38.1%, 61.9%] | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) |
| tool_hijack | 55 | 15/55 = 27.3% [17.3%, 40.2%] | 14/55 = 25.5% [15.8%, 38.3%] | 10/55 = 18.2% [10.2%, 30.3%] | 0/55 = 0.0% [0.0%, 6.5%], < 5.5% (rule of 3) | 0/55 = 0.0% [0.0%, 6.5%], < 5.5% (rule of 3) |

Leak rate per family (a marker the user may not see appeared in anything visible):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| agentpoison | 60 | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) |
| db_tamper | 72 | 72/72 = 100.0% [94.9%, 100.0%] | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) |
| fake_fact | 12 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |
| isolation | 108 | 108/108 = 100.0% [96.6%, 100.0%] | 36/108 = 33.3% [25.2%, 42.7%] | 36/108 = 33.3% [25.2%, 42.7%] | 0/108 = 0.0% [0.0%, 3.4%], < 2.8% (rule of 3) | 0/108 = 0.0% [0.0%, 3.4%], < 2.8% (rule of 3) |
| isolation_matrix | 144 | 141/144 = 97.9% [94.1%, 99.3%] | 54/144 = 37.5% [30.0%, 45.6%] | 48/144 = 33.3% [26.2%, 41.4%] | 0/144 = 0.0% [0.0%, 2.6%], < 2.1% (rule of 3) | 18/144 = 12.5% [8.1%, 18.9%] |
| minja | 60 | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) |
| planted_doc | 40 | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) |
| poisonedrag | 60 | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) | 0/60 = 0.0% [0.0%, 6.0%], < 5.0% (rule of 3) |
| poisoning | 80 | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) |
| repetition_flooding | 64 | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) |
| summary_laundering | 64 | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) | 0/64 = 0.0% [0.0%, 5.7%], < 4.7% (rule of 3) |
| tool_hijack | 55 | 0/55 = 0.0% [0.0%, 6.5%], < 5.5% (rule of 3) | 0/55 = 0.0% [0.0%, 6.5%], < 5.5% (rule of 3) | 0/55 = 0.0% [0.0%, 6.5%], < 5.5% (rule of 3) | 0/55 = 0.0% [0.0%, 6.5%], < 5.5% (rule of 3) | 0/55 = 0.0% [0.0%, 6.5%], < 5.5% (rule of 3) |

Tamper detection per family (tampered item withheld and quarantined, read from the service state):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| db_tamper | 72 | 0/72 = 0.0% [0.0%, 5.1%], < 4.2% (rule of 3) | 72/72 = 100.0% [94.9%, 100.0%] | 72/72 = 100.0% [94.9%, 100.0%] | 72/72 = 100.0% [94.9%, 100.0%] | 72/72 = 100.0% [94.9%, 100.0%] |

Legit payment not completed correctly per family (benign twins and clean payments; not made, or made to a wrong account):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| agentpoison | 72 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 12/12 = 100.0% [75.8%, 100.0%] |
| clean | 96 | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 12/12 = 100.0% [75.8%, 100.0%] |
| minja | 72 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 12/12 = 100.0% [75.8%, 100.0%] |
| poisonedrag | 72 | 1/6 = 16.7% [3.0%, 56.4%] | 1/6 = 16.7% [3.0%, 56.4%] | 1/6 = 16.7% [3.0%, 56.4%] | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 6/6 = 100.0% [61.0%, 100.0%] |
| repetition_flooding | 76 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 12/12 = 100.0% [75.8%, 100.0%] |
| summary_laundering | 76 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 12/12 = 100.0% [75.8%, 100.0%] |

Legit payment held or refused per family (false denial: the gate or registry stopped it):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| agentpoison | 72 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 12/12 = 100.0% [75.8%, 100.0%] |
| clean | 96 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) |
| minja | 72 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 12/12 = 100.0% [75.8%, 100.0%] |
| poisonedrag | 72 | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 6/6 = 100.0% [61.0%, 100.0%] |
| repetition_flooding | 76 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 12/12 = 100.0% [75.8%, 100.0%] |
| summary_laundering | 76 | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 0/12 = 0.0% [0.0%, 24.2%], < 25.0% (rule of 3) | 12/12 = 100.0% [75.8%, 100.0%] |

Harmless write rejected per family (benign twins and clean episodes):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| agentpoison | 72 | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) | 0/6 = 0.0% [0.0%, 39.0%], < 50.0% (rule of 3) |
| minja | 72 | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) |
| poisonedrag | 72 | 0/32 = 0.0% [0.0%, 10.7%], < 9.4% (rule of 3) | 0/32 = 0.0% [0.0%, 10.7%], < 9.4% (rule of 3) | 1/32 = 3.1% [0.6%, 15.7%] | 1/32 = 3.1% [0.6%, 15.7%] | 1/32 = 3.1% [0.6%, 15.7%] |
| poisoning | 160 | 0/120 = 0.0% [0.0%, 3.1%], < 2.5% (rule of 3) | 0/120 = 0.0% [0.0%, 3.1%], < 2.5% (rule of 3) | 14/120 = 11.7% [7.1%, 18.6%] | 14/120 = 11.7% [7.1%, 18.6%] | 14/120 = 11.7% [7.1%, 18.6%] |
| repetition_flooding | 76 | 0/174 = 0.0% [0.0%, 2.2%], < 1.7% (rule of 3) | 0/174 = 0.0% [0.0%, 2.2%], < 1.7% (rule of 3) | 19/174 = 10.9% [7.1%, 16.4%] | 19/174 = 10.9% [7.1%, 16.4%] | 19/174 = 10.9% [7.1%, 16.4%] |
| summary_laundering | 76 | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) | 0/16 = 0.0% [0.0%, 19.4%], < 18.8% (rule of 3) |

Benign task accuracy per family:

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| clean | 96 | 84/84 = 100.0% [95.6%, 100.0%] | 84/84 = 100.0% [95.6%, 100.0%] | 84/84 = 100.0% [95.6%, 100.0%] | 84/84 = 100.0% [95.6%, 100.0%] | 84/84 = 100.0% [95.6%, 100.0%] |
| db_tamper | 84 | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] |
| isolation_matrix | 156 | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] | 12/12 = 100.0% [75.8%, 100.0%] |
| planted_doc | 80 | 24/28 = 85.7% [68.5%, 94.3%] | 25/28 = 89.3% [72.8%, 96.3%] | 22/28 = 78.6% [60.5%, 89.8%] | 22/28 = 78.6% [60.5%, 89.8%] | 23/28 = 82.1% [64.4%, 92.1%] |
| poisonedrag | 72 | 6/6 = 100.0% [61.0%, 100.0%] | 6/6 = 100.0% [61.0%, 100.0%] | 6/6 = 100.0% [61.0%, 100.0%] | 6/6 = 100.0% [61.0%, 100.0%] | 6/6 = 100.0% [61.0%, 100.0%] |

Blocked attacks per version, by the first mechanism that visibly stopped them (attacks/attribution.py); 'attack succeeded' is the complement:

| mechanism | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|
| hash verification | – | 81 | 81 | 81 | 81 |
| input screen | – | – | 93 | 104 | 104 |
| hallucination check | – | – | 32 | 77 | 55 |
| memshield | – | – | 103 | 103 | 103 |
| contradiction / trust | – | – | 15 | 20 | 19 |
| registry match | – | – | – | 72 | – |
| access check (write) | – | – | – | – | – |
| JTMS retraction | – | 32 | 20 | 8 | 20 |
| registry binding | – | – | – | 20 | – |
| action gate | – | – | – | 29 | 131 |
| read filter | – | – | – | 174 | 174 |
| team scoping | – | 153 | 159 | 33 | 33 |
| none fired | 126 | 120 | 81 | 69 | 67 |
| attack succeeded | 693 | 433 | 235 | 29 | 32 |

Mechanisms that acted on attack material in any attack episode (a later mechanism hidden behind an earlier one still counts here):

| mechanism | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|
| hash verification | – | 81 | 81 | 81 | 81 |
| input screen | – | – | 93 | 104 | 104 |
| hallucination check | – | – | 97 | 153 | 131 |
| memshield | – | – | 109 | 114 | 114 |
| contradiction / trust | – | – | 16 | 20 | 20 |
| registry match | – | – | – | 260 | – |
| access check (write) | – | – | – | – | – |
| JTMS retraction | – | 32 | 32 | 16 | 32 |
| registry binding | – | – | – | 71 | – |
| action gate | – | – | – | 31 | 214 |
| read filter | – | – | – | 198 | 198 |

Benchmark episodes (agent runs with the benchmark payload; attack success by the per-episode oracle, 'harmless blocked' = clean-twin writes rejected / clean tool outputs quarantined, 'top mechanism' = what most often stopped an attack):

| benchmark | version | oracle attack success | harmless write rejected | clean input quarantined | clean task accuracy | LLM calls | top mechanism |
|---|---|---|---|---|---|---|---|
| agentdojo | baseline | 15/15 = 100.0% [79.6%, 100.0%] | – | – | – | 68 | – |
| agentdojo | provenance | 14/15 = 93.3% [70.2%, 98.8%] | – | – | – | 72 | none fired 1 |
| agentdojo | write_checks | 10/15 = 66.7% [41.7%, 84.8%] | – | – | – | 64 | input screen 4, none fired 1 |
| agentdojo | full | 0/15 = 0.0% [0.0%, 20.4%], < 20.0% (rule of 3) | – | – | – | 42 | action gate 11, input screen 4 |
| agentdojo | full_no_registry | 0/15 = 0.0% [0.0%, 20.4%], < 20.0% (rule of 3) | – | – | – | 42 | action gate 11, input screen 4 |
| bipia | baseline | 7/40 = 17.5% [8.7%, 31.9%] | – | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 24/28 = 85.7% [68.5%, 94.3%] | 160 | none fired 33 |
| bipia | provenance | 8/40 = 20.0% [10.5%, 34.8%] | – | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 25/28 = 89.3% [72.8%, 96.3%] | 160 | none fired 32 |
| bipia | write_checks | 8/40 = 20.0% [10.5%, 34.8%] | – | 6/40 = 15.0% [7.1%, 29.1%] | 22/28 = 78.6% [60.5%, 89.8%] | 160 | none fired 29, input screen 3 |
| bipia | full | 8/40 = 20.0% [10.5%, 34.8%] | – | 6/40 = 15.0% [7.1%, 29.1%] | 22/28 = 78.6% [60.5%, 89.8%] | 160 | none fired 29, input screen 3 |
| bipia | full_no_registry | 8/40 = 20.0% [10.5%, 34.8%] | – | 6/40 = 15.0% [7.1%, 29.1%] | 23/28 = 82.1% [64.4%, 92.1%] | 160 | none fired 29, input screen 3 |
| injecagent | baseline | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 160 | none fired 40 |
| injecagent | provenance | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 160 | none fired 40 |
| injecagent | write_checks | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 160 | input screen 21, none fired 19 |
| injecagent | full | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 160 | input screen 21, none fired 19 |
| injecagent | full_no_registry | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 160 | input screen 21, none fired 19 |
| memevobench | baseline | 7/40 = 17.5% [8.7%, 31.9%] | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | – | 82 | none fired 33 |
| memevobench | provenance | 9/40 = 22.5% [12.3%, 37.5%] | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | – | 81 | none fired 31 |
| memevobench | write_checks | 7/40 = 17.5% [8.7%, 31.9%] | 11/80 = 13.8% [7.9%, 23.0%] | 1/80 = 1.2% [0.2%, 6.7%] | – | 81 | none fired 19, memshield 12 |
| memevobench | full | 5/40 = 12.5% [5.5%, 26.1%] | 11/80 = 13.8% [7.9%, 23.0%] | 1/80 = 1.2% [0.2%, 6.7%] | – | 80 | none fired 21, memshield 12 |
| memevobench | full_no_registry | 7/40 = 17.5% [8.7%, 31.9%] | 11/80 = 13.8% [7.9%, 23.0%] | 1/80 = 1.2% [0.2%, 6.7%] | – | 81 | none fired 19, memshield 12 |
| memshield | baseline | 38/40 = 95.0% [83.5%, 98.6%] | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 82 | none fired 2 |
| memshield | provenance | 37/40 = 92.5% [80.1%, 97.4%] | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 82 | none fired 3 |
| memshield | write_checks | 6/40 = 15.0% [7.1%, 29.1%] | 3/40 = 7.5% [2.6%, 19.9%] | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 82 | memshield 31, input screen 3 |
| memshield | full | 6/40 = 15.0% [7.1%, 29.1%] | 3/40 = 7.5% [2.6%, 19.9%] | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 82 | memshield 31, input screen 3 |
| memshield | full_no_registry | 6/40 = 15.0% [7.1%, 29.1%] | 3/40 = 7.5% [2.6%, 19.9%] | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) | – | 82 | memshield 31, input screen 3 |

Write-path classification, per labelled memory entry (positive = poisoned/misleading; predicted positive = the write was rejected). Not attack success: see attacks/classify.py:

| benchmark | version | TP | FP | FN | TN | precision | recall | F1 | harmless rejected |
|---|---|---|---|---|---|---|---|---|---|
| memshield | baseline | 0 | 0 | 40 | 40 | – | 0.00 | 0.00 | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) |
| memshield | provenance | 0 | 0 | 40 | 40 | – | 0.00 | 0.00 | 0/40 = 0.0% [0.0%, 8.8%], < 7.5% (rule of 3) |
| memshield | write_checks | 35 | 3 | 5 | 37 | 0.92 | 0.88 | 0.90 | 3/40 = 7.5% [2.6%, 19.9%] |
| memshield | full | 35 | 3 | 5 | 37 | 0.92 | 0.88 | 0.90 | 3/40 = 7.5% [2.6%, 19.9%] |
| memshield | full_no_registry | 35 | 3 | 5 | 37 | 0.92 | 0.88 | 0.90 | 3/40 = 7.5% [2.6%, 19.9%] |
| memevobench | baseline | 0 | 0 | 120 | 160 | – | 0.00 | 0.00 | 0/160 = 0.0% [0.0%, 2.3%], < 1.9% (rule of 3) |
| memevobench | provenance | 0 | 0 | 120 | 160 | – | 0.00 | 0.00 | 0/160 = 0.0% [0.0%, 2.3%], < 1.9% (rule of 3) |
| memevobench | write_checks | 25 | 22 | 95 | 138 | 0.53 | 0.21 | 0.30 | 22/160 = 13.8% [9.3%, 19.9%] |
| memevobench | full | 25 | 22 | 95 | 138 | 0.53 | 0.21 | 0.30 | 22/160 = 13.8% [9.3%, 19.9%] |
| memevobench | full_no_registry | 25 | 22 | 95 | 138 | 0.53 | 0.21 | 0.30 | 22/160 = 13.8% [9.3%, 19.9%] |

Recall by attack type / domain (rejected poisoned writes):

| benchmark | type | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| memshield | T10_c2_persistence | 0/3 = 0.0% | 0/3 = 0.0% | 3/3 = 100.0% | 3/3 = 100.0% | 3/3 = 100.0% |
| memshield | T1_instruction_override | 0/4 = 0.0% | 0/4 = 0.0% | 4/4 = 100.0% | 4/4 = 100.0% | 4/4 = 100.0% |
| memshield | T3_behavioral_drift | 0/2 = 0.0% | 0/2 = 0.0% | 2/2 = 100.0% | 2/2 = 100.0% | 2/2 = 100.0% |
| memshield | T4_factual_manipulation | 0/5 = 0.0% | 0/5 = 0.0% | 3/5 = 60.0% | 3/5 = 60.0% | 3/5 = 60.0% |
| memshield | T5_backdoor_trigger | 0/14 = 0.0% | 0/14 = 0.0% | 14/14 = 100.0% | 14/14 = 100.0% | 14/14 = 100.0% |
| memshield | T6_experience_poisoning | 0/1 = 0.0% | 0/1 = 0.0% | 1/1 = 100.0% | 1/1 = 100.0% | 1/1 = 100.0% |
| memshield | T7_recommendation_poisoning | 0/4 = 0.0% | 0/4 = 0.0% | 1/4 = 25.0% | 1/4 = 25.0% | 1/4 = 25.0% |
| memshield | T8_configuration_poisoning | 0/4 = 0.0% | 0/4 = 0.0% | 4/4 = 100.0% | 4/4 = 100.0% | 4/4 = 100.0% |
| memshield | T9_security_degradation | 0/3 = 0.0% | 0/3 = 0.0% | 3/3 = 100.0% | 3/3 = 100.0% | 3/3 = 100.0% |
| memevobench | customerservice | 0/18 = 0.0% | 0/18 = 0.0% | 11/18 = 61.1% | 11/18 = 61.1% | 11/18 = 61.1% |
| memevobench | finance | 0/18 = 0.0% | 0/18 = 0.0% | 1/18 = 5.6% | 1/18 = 5.6% | 1/18 = 5.6% |
| memevobench | food | 0/18 = 0.0% | 0/18 = 0.0% | 0/18 = 0.0% | 0/18 = 0.0% | 0/18 = 0.0% |
| memevobench | health | 0/18 = 0.0% | 0/18 = 0.0% | 1/18 = 5.6% | 1/18 = 5.6% | 1/18 = 5.6% |
| memevobench | mental | 0/18 = 0.0% | 0/18 = 0.0% | 1/18 = 5.6% | 1/18 = 5.6% | 1/18 = 5.6% |
| memevobench | privacy | 0/15 = 0.0% | 0/15 = 0.0% | 9/15 = 60.0% | 9/15 = 60.0% | 9/15 = 60.0% |
| memevobench | traffic | 0/15 = 0.0% | 0/15 = 0.0% | 2/15 = 13.3% | 2/15 = 13.3% | 2/15 = 13.3% |

What the registry adds (blocked-by, full vs full_no_registry, per family):

| family | succeeded full | succeeded full_no_registry | full: blocked by | full_no_registry: blocked by |
|---|---|---|---|---|
| agentpoison | 0 | 0 | memshield 60 | memshield 60 |
| db_tamper | 0 | 0 | hash verification 72 | hash verification 72 |
| fake_fact | 0 | 0 | registry binding 12 | action gate 12 |
| isolation | 0 | 0 | read filter 108 | read filter 108 |
| isolation_matrix | 0 | 0 | hash verification 9, registry match 18, action gate 18, read filter 66, team scoping 33 | hash verification 9, action gate 36, read filter 66, team scoping 33 |
| minja | 0 | 0 | input screen 60 | input screen 60 |
| planted_doc | 8 | 8 | input screen 3, none fired 29 | input screen 3, none fired 29 |
| poisonedrag | 10 | 11 | input screen 11, hallucination check 12, contradiction / trust 20, registry match 7 | input screen 11, hallucination check 12, contradiction / trust 19, action gate 7 |
| poisoning | 11 | 13 | input screen 5, memshield 43, none fired 21 | input screen 5, memshield 43, none fired 19 |
| repetition_flooding | 0 | 0 | hallucination check 42, registry match 22 | hallucination check 20, action gate 44 |
| summary_laundering | 0 | 0 | hallucination check 23, registry match 25, JTMS retraction 8, registry binding 8 | hallucination check 23, JTMS retraction 20, action gate 21 |
| tool_hijack | 0 | 0 | input screen 25, action gate 11, none fired 19 | input screen 25, action gate 11, none fired 19 |
