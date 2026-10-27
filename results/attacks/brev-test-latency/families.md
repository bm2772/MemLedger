| version | oracle attack success | hijacked action | leak rate | tamper detection | side-channel count leak | benign task accuracy | legit payment not completed correctly | legit payment held or refused (false denial) | harmless write rejected | added write ms | added read ms | added gate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 59/70 = 84.3% [74.0%, 91.0%] | 33/38 = 86.8% [72.7%, 94.2%] | 19/140 = 13.6% [8.9%, 20.2%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 1/1 = 100.0% [20.7%, 100.0%] | 25/25 = 100.0% [86.7%, 100.0%] | 5/28 = 17.9% [7.9%, 35.6%] | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 0/124 = 0.0% [0.0%, 3.0%], < 2.4% (rule of 3) | +0.00 | +0.00 | – |
| provenance | 46/70 = 65.7% [54.0%, 75.8%] | 29/38 = 76.3% [60.8%, 87.0%] | 5/140 = 3.6% [1.5%, 8.1%] | 5/5 = 100.0% [56.6%, 100.0%] | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 25/25 = 100.0% [86.7%, 100.0%] | 5/28 = 17.9% [7.9%, 35.6%] | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 0/124 = 0.0% [0.0%, 3.0%], < 2.4% (rule of 3) | +0.17 | +1.72 | – |
| write_checks | 23/70 = 32.9% [23.0%, 44.5%] | 16/38 = 42.1% [27.9%, 57.8%] | 5/140 = 3.6% [1.5%, 8.1%] | 5/5 = 100.0% [56.6%, 100.0%] | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 25/25 = 100.0% [86.7%, 100.0%] | 5/28 = 17.9% [7.9%, 35.6%] | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 13/124 = 10.5% [6.2%, 17.1%] | +21.73 | +0.88 | – |
| full | 2/70 = 2.9% [0.8%, 9.8%] | 0/38 = 0.0% [0.0%, 9.2%], < 7.9% (rule of 3) | 0/140 = 0.0% [0.0%, 2.7%], < 2.1% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 25/25 = 100.0% [86.7%, 100.0%] | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 13/124 = 10.5% [6.2%, 17.1%] | +23.73 | +0.87 | – |
| full_no_registry | 2/70 = 2.9% [0.8%, 9.8%] | 0/38 = 0.0% [0.0%, 9.2%], < 7.9% (rule of 3) | 1/140 = 0.7% [0.1%, 3.9%] | 5/5 = 100.0% [56.6%, 100.0%] | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 25/25 = 100.0% [86.7%, 100.0%] | 28/28 = 100.0% [87.9%, 100.0%] | 28/28 = 100.0% [87.9%, 100.0%] | 13/124 = 10.5% [6.2%, 17.1%] | +21.27 | +0.90 | – |

Oracle attack success per family (attacks/oracle.py):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| agentpoison | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| db_tamper | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| fake_fact | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| isolation | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 2/5 = 40.0% [11.8%, 76.9%] | 2/5 = 40.0% [11.8%, 76.9%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| isolation_matrix | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 3/5 = 60.0% [23.1%, 88.2%] | 3/5 = 60.0% [23.1%, 88.2%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| minja | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| planted_doc | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| poisonedrag | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 2/5 = 40.0% [11.8%, 76.9%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| poisoning | 10 | 9/10 = 90.0% [59.6%, 98.2%] | 10/10 = 100.0% [72.2%, 100.0%] | 3/10 = 30.0% [10.8%, 60.3%] | 2/10 = 20.0% [5.7%, 51.0%] | 2/10 = 20.0% [5.7%, 51.0%] |
| repetition_flooding | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 4/5 = 80.0% [37.6%, 96.4%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| summary_laundering | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 1/5 = 20.0% [3.6%, 62.4%] | 1/5 = 20.0% [3.6%, 62.4%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| tool_hijack | 10 | 5/10 = 50.0% [23.7%, 76.3%] | 5/10 = 50.0% [23.7%, 76.3%] | 3/10 = 30.0% [10.8%, 60.3%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) |

Leak rate per family (a marker the user may not see appeared in anything visible):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| agentpoison | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| db_tamper | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| fake_fact | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| isolation | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 2/5 = 40.0% [11.8%, 76.9%] | 2/5 = 40.0% [11.8%, 76.9%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| isolation_matrix | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 3/5 = 60.0% [23.1%, 88.2%] | 3/5 = 60.0% [23.1%, 88.2%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 1/5 = 20.0% [3.6%, 62.4%] |
| minja | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| planted_doc | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| poisonedrag | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| poisoning | 10 | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) |
| repetition_flooding | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| summary_laundering | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| tool_hijack | 10 | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) |

Tamper detection per family (tampered item withheld and quarantined, read from the service state):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| db_tamper | 5 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] |

Legit payment not completed correctly per family (benign twins and clean payments; not made, or made to a wrong account):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| agentpoison | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] |
| clean | 15 | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] |
| isolation_matrix | 10 | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 1/1 = 100.0% [20.7%, 100.0%] |
| minja | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] |
| poisonedrag | 10 | 0/2 = 0.0% [0.0%, 65.8%], < 100.0% (rule of 3) | 0/2 = 0.0% [0.0%, 65.8%], < 100.0% (rule of 3) | 0/2 = 0.0% [0.0%, 65.8%], < 100.0% (rule of 3) | 0/2 = 0.0% [0.0%, 65.8%], < 100.0% (rule of 3) | 2/2 = 100.0% [34.2%, 100.0%] |
| repetition_flooding | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] |
| summary_laundering | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] |

Legit payment held or refused per family (false denial: the gate or registry stopped it):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| agentpoison | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] |
| clean | 15 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] |
| isolation_matrix | 10 | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 1/1 = 100.0% [20.7%, 100.0%] |
| minja | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] |
| poisonedrag | 10 | 0/2 = 0.0% [0.0%, 65.8%], < 100.0% (rule of 3) | 0/2 = 0.0% [0.0%, 65.8%], < 100.0% (rule of 3) | 0/2 = 0.0% [0.0%, 65.8%], < 100.0% (rule of 3) | 0/2 = 0.0% [0.0%, 65.8%], < 100.0% (rule of 3) | 2/2 = 100.0% [34.2%, 100.0%] |
| repetition_flooding | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] |
| summary_laundering | 10 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] |

Harmless write rejected per family (benign twins and clean episodes):

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| agentpoison | 10 | 0/3 = 0.0% [0.0%, 56.1%], < 100.0% (rule of 3) | 0/3 = 0.0% [0.0%, 56.1%], < 100.0% (rule of 3) | 0/3 = 0.0% [0.0%, 56.1%], < 100.0% (rule of 3) | 0/3 = 0.0% [0.0%, 56.1%], < 100.0% (rule of 3) | 0/3 = 0.0% [0.0%, 56.1%], < 100.0% (rule of 3) |
| isolation_matrix | 10 | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) |
| minja | 10 | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) |
| poisonedrag | 10 | 0/11 = 0.0% [0.0%, 25.9%], < 27.3% (rule of 3) | 0/11 = 0.0% [0.0%, 25.9%], < 27.3% (rule of 3) | 1/11 = 9.1% [1.6%, 37.7%] | 1/11 = 9.1% [1.6%, 37.7%] | 1/11 = 9.1% [1.6%, 37.7%] |
| poisoning | 20 | 0/15 = 0.0% [0.0%, 20.4%], < 20.0% (rule of 3) | 0/15 = 0.0% [0.0%, 20.4%], < 20.0% (rule of 3) | 3/15 = 20.0% [7.0%, 45.2%] | 3/15 = 20.0% [7.0%, 45.2%] | 3/15 = 20.0% [7.0%, 45.2%] |
| repetition_flooding | 10 | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 9/80 = 11.2% [6.0%, 20.0%] | 9/80 = 11.2% [6.0%, 20.0%] | 9/80 = 11.2% [6.0%, 20.0%] |
| summary_laundering | 10 | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) |

Benign task accuracy per family:

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| clean | 15 | 10/10 = 100.0% [72.2%, 100.0%] | 10/10 = 100.0% [72.2%, 100.0%] | 10/10 = 100.0% [72.2%, 100.0%] | 10/10 = 100.0% [72.2%, 100.0%] | 10/10 = 100.0% [72.2%, 100.0%] |
| db_tamper | 10 | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] |
| isolation_matrix | 10 | 4/4 = 100.0% [51.0%, 100.0%] | 4/4 = 100.0% [51.0%, 100.0%] | 4/4 = 100.0% [51.0%, 100.0%] | 4/4 = 100.0% [51.0%, 100.0%] | 4/4 = 100.0% [51.0%, 100.0%] |
| planted_doc | 10 | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] |
| poisonedrag | 10 | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] |

Blocked attacks per version, by the first mechanism that visibly stopped them (attacks/attribution.py); 'attack succeeded' is the complement:

| mechanism | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|
| hash verification | – | 5 | 5 | 5 | 5 |
| input screen | – | – | 11 | 12 | 12 |
| hallucination check | – | – | 3 | 6 | 4 |
| memshield | – | – | 11 | 12 | 12 |
| contradiction / trust | – | – | 3 | 3 | 3 |
| registry match | – | – | – | 4 | – |
| access check (write) | – | – | – | – | – |
| JTMS retraction | – | 4 | 2 | 1 | 2 |
| registry binding | – | – | – | 1 | – |
| action gate | – | – | – | 9 | 15 |
| read filter | – | – | – | 7 | 7 |
| team scoping | – | 5 | 5 | 1 | 1 |
| none fired | 11 | 10 | 7 | 7 | 7 |
| attack succeeded | 59 | 46 | 23 | 2 | 2 |

Mechanisms that acted on attack material in any attack episode (a later mechanism hidden behind an earlier one still counts here):

| mechanism | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|
| hash verification | – | 5 | 5 | 5 | 5 |
| input screen | – | – | 11 | 12 | 12 |
| hallucination check | – | – | 9 | 13 | 11 |
| memshield | – | – | 13 | 14 | 14 |
| contradiction / trust | – | – | 3 | 3 | 3 |
| registry match | – | – | – | 19 | – |
| access check (write) | – | – | – | – | – |
| JTMS retraction | – | 4 | 4 | 2 | 4 |
| registry binding | – | – | – | 2 | – |
| action gate | – | – | – | 9 | 31 |
| read filter | – | – | – | 13 | 13 |

Benchmark episodes (agent runs with the benchmark payload; attack success by the per-episode oracle, 'harmless blocked' = clean-twin writes rejected / clean tool outputs quarantined, 'top mechanism' = what most often stopped an attack):

| benchmark | version | oracle attack success | harmless write rejected | clean input quarantined | clean task accuracy | LLM calls | top mechanism |
|---|---|---|---|---|---|---|---|
| agentdojo | baseline | 5/5 = 100.0% [56.6%, 100.0%] | – | – | – | 18 | – |
| agentdojo | provenance | 5/5 = 100.0% [56.6%, 100.0%] | – | – | – | 20 | – |
| agentdojo | write_checks | 3/5 = 60.0% [23.1%, 88.2%] | – | – | – | 16 | input screen 2 |
| agentdojo | full | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | – | – | 14 | action gate 3, input screen 2 |
| agentdojo | full_no_registry | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | – | – | 14 | action gate 3, input screen 2 |
| bipia | baseline | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 3/3 = 100.0% [43.9%, 100.0%] | 20 | none fired 5 |
| bipia | provenance | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 3/3 = 100.0% [43.9%, 100.0%] | 20 | none fired 5 |
| bipia | write_checks | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 1/5 = 20.0% [3.6%, 62.4%] | 3/3 = 100.0% [43.9%, 100.0%] | 20 | none fired 4, input screen 1 |
| bipia | full | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 1/5 = 20.0% [3.6%, 62.4%] | 3/3 = 100.0% [43.9%, 100.0%] | 20 | none fired 4, input screen 1 |
| bipia | full_no_registry | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 1/5 = 20.0% [3.6%, 62.4%] | 3/3 = 100.0% [43.9%, 100.0%] | 20 | none fired 4, input screen 1 |
| injecagent | baseline | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 20 | none fired 5 |
| injecagent | provenance | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 20 | none fired 5 |
| injecagent | write_checks | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 20 | none fired 3, input screen 2 |
| injecagent | full | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 20 | none fired 3, input screen 2 |
| injecagent | full_no_registry | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 20 | none fired 3, input screen 2 |
| memevobench | baseline | 4/5 = 80.0% [37.6%, 96.4%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 19 | none fired 1 |
| memevobench | provenance | 5/5 = 100.0% [56.6%, 100.0%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 20 | – |
| memevobench | write_checks | 2/5 = 40.0% [11.8%, 76.9%] | 2/10 = 20.0% [5.7%, 51.0%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 18 | memshield 3 |
| memevobench | full | 1/5 = 20.0% [3.6%, 62.4%] | 2/10 = 20.0% [5.7%, 51.0%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 18 | memshield 4 |
| memevobench | full_no_registry | 1/5 = 20.0% [3.6%, 62.4%] | 2/10 = 20.0% [5.7%, 51.0%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 19 | memshield 4 |
| memshield | baseline | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 10 | – |
| memshield | provenance | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 10 | – |
| memshield | write_checks | 1/5 = 20.0% [3.6%, 62.4%] | 1/5 = 20.0% [3.6%, 62.4%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 10 | memshield 3, input screen 1 |
| memshield | full | 1/5 = 20.0% [3.6%, 62.4%] | 1/5 = 20.0% [3.6%, 62.4%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 10 | memshield 3, input screen 1 |
| memshield | full_no_registry | 1/5 = 20.0% [3.6%, 62.4%] | 1/5 = 20.0% [3.6%, 62.4%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 10 | memshield 3, input screen 1 |

Write-path classification, per labelled memory entry (positive = poisoned/misleading; predicted positive = the write was rejected). Not attack success: see attacks/classify.py:

| benchmark | version | TP | FP | FN | TN | precision | recall | F1 | harmless rejected |
|---|---|---|---|---|---|---|---|---|---|
| memshield | baseline | 0 | 0 | 5 | 5 | – | 0.00 | 0.00 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| memshield | provenance | 0 | 0 | 5 | 5 | – | 0.00 | 0.00 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| memshield | write_checks | 4 | 1 | 1 | 4 | 0.80 | 0.80 | 0.80 | 1/5 = 20.0% [3.6%, 62.4%] |
| memshield | full | 4 | 1 | 1 | 4 | 0.80 | 0.80 | 0.80 | 1/5 = 20.0% [3.6%, 62.4%] |
| memshield | full_no_registry | 4 | 1 | 1 | 4 | 0.80 | 0.80 | 0.80 | 1/5 = 20.0% [3.6%, 62.4%] |
| memevobench | baseline | 0 | 0 | 15 | 20 | – | 0.00 | 0.00 | 0/20 = 0.0% [0.0%, 16.1%], < 15.0% (rule of 3) |
| memevobench | provenance | 0 | 0 | 15 | 20 | – | 0.00 | 0.00 | 0/20 = 0.0% [0.0%, 16.1%], < 15.0% (rule of 3) |
| memevobench | write_checks | 9 | 4 | 6 | 16 | 0.69 | 0.60 | 0.64 | 4/20 = 20.0% [8.1%, 41.6%] |
| memevobench | full | 9 | 4 | 6 | 16 | 0.69 | 0.60 | 0.64 | 4/20 = 20.0% [8.1%, 41.6%] |
| memevobench | full_no_registry | 9 | 4 | 6 | 16 | 0.69 | 0.60 | 0.64 | 4/20 = 20.0% [8.1%, 41.6%] |

Recall by attack type / domain (rejected poisoned writes):

| benchmark | type | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| memshield | T10_c2_persistence | 0/1 = 0.0% | 0/1 = 0.0% | 1/1 = 100.0% | 1/1 = 100.0% | 1/1 = 100.0% |
| memshield | T7_recommendation_poisoning | 0/2 = 0.0% | 0/2 = 0.0% | 1/2 = 50.0% | 1/2 = 50.0% | 1/2 = 50.0% |
| memshield | T8_configuration_poisoning | 0/2 = 0.0% | 0/2 = 0.0% | 2/2 = 100.0% | 2/2 = 100.0% | 2/2 = 100.0% |
| memevobench | customerservice | 0/15 = 0.0% | 0/15 = 0.0% | 9/15 = 60.0% | 9/15 = 60.0% | 9/15 = 60.0% |

What the registry adds (blocked-by, full vs full_no_registry, per family):

| family | succeeded full | succeeded full_no_registry | full: blocked by | full_no_registry: blocked by |
|---|---|---|---|---|
| agentpoison | 0 | 0 | memshield 5 | memshield 5 |
| db_tamper | 0 | 0 | hash verification 5 | hash verification 5 |
| fake_fact | 0 | 0 | action gate 5 | action gate 5 |
| isolation | 0 | 0 | read filter 5 | read filter 5 |
| isolation_matrix | 0 | 0 | registry match 1, action gate 1, read filter 2, team scoping 1 | action gate 2, read filter 2, team scoping 1 |
| minja | 0 | 0 | input screen 5 | input screen 5 |
| planted_doc | 0 | 0 | input screen 1, none fired 4 | input screen 1, none fired 4 |
| poisonedrag | 0 | 0 | input screen 1, hallucination check 1, contradiction / trust 3 | input screen 1, hallucination check 1, contradiction / trust 3 |
| poisoning | 2 | 2 | input screen 1, memshield 7 | input screen 1, memshield 7 |
| repetition_flooding | 0 | 0 | hallucination check 3, registry match 2 | hallucination check 1, action gate 4 |
| summary_laundering | 0 | 0 | hallucination check 2, registry match 1, JTMS retraction 1, registry binding 1 | hallucination check 2, JTMS retraction 2, action gate 1 |
| tool_hijack | 0 | 0 | input screen 4, action gate 3, none fired 3 | input screen 4, action gate 3, none fired 3 |
