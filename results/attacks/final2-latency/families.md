| version | oracle attack success | hijacked action | leak rate | tamper detection | side-channel count leak | benign task accuracy | legit payment not completed correctly | legit payment held or refused (false denial) | harmless write rejected | added write ms | added read ms | added gate ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 55/70 = 78.6% [67.6%, 86.6%] | 31/38 = 81.6% [66.6%, 90.8%] | 19/140 = 13.6% [8.9%, 20.2%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 1/1 = 100.0% [20.7%, 100.0%] | 24/25 = 96.0% [80.5%, 99.3%] | 5/28 = 17.9% [7.9%, 35.6%] | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 0/124 = 0.0% [0.0%, 3.0%], < 2.4% (rule of 3) | +0.00 | +0.00 | – |
| provenance | 40/70 = 57.1% [45.5%, 68.1%] | 27/38 = 71.1% [55.2%, 83.0%] | 5/140 = 3.6% [1.5%, 8.1%] | 5/5 = 100.0% [56.6%, 100.0%] | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 24/25 = 96.0% [80.5%, 99.3%] | 5/28 = 17.9% [7.9%, 35.6%] | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 0/124 = 0.0% [0.0%, 3.0%], < 2.4% (rule of 3) | +0.17 | +1.86 | – |
| write_checks | 19/70 = 27.1% [18.1%, 38.5%] | 13/38 = 34.2% [21.2%, 50.1%] | 5/140 = 3.6% [1.5%, 8.1%] | 5/5 = 100.0% [56.6%, 100.0%] | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 24/25 = 96.0% [80.5%, 99.3%] | 5/28 = 17.9% [7.9%, 35.6%] | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 1/124 = 0.8% [0.1%, 4.4%] | +23.21 | +0.78 | – |
| full | 1/70 = 1.4% [0.3%, 7.7%] | 0/38 = 0.0% [0.0%, 9.2%], < 7.9% (rule of 3) | 0/140 = 0.0% [0.0%, 2.7%], < 2.1% (rule of 3) | 5/5 = 100.0% [56.6%, 100.0%] | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 24/25 = 96.0% [80.5%, 99.3%] | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 0/28 = 0.0% [0.0%, 12.1%], < 10.7% (rule of 3) | 1/124 = 0.8% [0.1%, 4.4%] | +25.46 | +0.79 | – |
| full_no_registry | 1/70 = 1.4% [0.3%, 7.7%] | 0/38 = 0.0% [0.0%, 9.2%], < 7.9% (rule of 3) | 1/140 = 0.7% [0.1%, 3.9%] | 5/5 = 100.0% [56.6%, 100.0%] | 0/1 = 0.0% [0.0%, 79.3%], < 100.0% (rule of 3) | 24/25 = 96.0% [80.5%, 99.3%] | 28/28 = 100.0% [87.9%, 100.0%] | 28/28 = 100.0% [87.9%, 100.0%] | 1/124 = 0.8% [0.1%, 4.4%] | +23.28 | +0.85 | – |

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
| poisoning | 10 | 7/10 = 70.0% [39.7%, 89.2%] | 6/10 = 60.0% [31.3%, 83.2%] | 2/10 = 20.0% [5.7%, 51.0%] | 1/10 = 10.0% [1.8%, 40.4%] | 1/10 = 10.0% [1.8%, 40.4%] |
| repetition_flooding | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 4/5 = 80.0% [37.6%, 96.4%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| summary_laundering | 5 | 5/5 = 100.0% [56.6%, 100.0%] | 1/5 = 20.0% [3.6%, 62.4%] | 1/5 = 20.0% [3.6%, 62.4%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| tool_hijack | 10 | 3/10 = 30.0% [10.8%, 60.3%] | 3/10 = 30.0% [10.8%, 60.3%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) |

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
| poisonedrag | 10 | 0/11 = 0.0% [0.0%, 25.9%], < 27.3% (rule of 3) | 0/11 = 0.0% [0.0%, 25.9%], < 27.3% (rule of 3) | 0/11 = 0.0% [0.0%, 25.9%], < 27.3% (rule of 3) | 0/11 = 0.0% [0.0%, 25.9%], < 27.3% (rule of 3) | 0/11 = 0.0% [0.0%, 25.9%], < 27.3% (rule of 3) |
| poisoning | 20 | 0/15 = 0.0% [0.0%, 20.4%], < 20.0% (rule of 3) | 0/15 = 0.0% [0.0%, 20.4%], < 20.0% (rule of 3) | 1/15 = 6.7% [1.2%, 29.8%] | 1/15 = 6.7% [1.2%, 29.8%] | 1/15 = 6.7% [1.2%, 29.8%] |
| repetition_flooding | 10 | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) | 0/80 = 0.0% [0.0%, 4.6%], < 3.8% (rule of 3) |
| summary_laundering | 10 | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) | 0/7 = 0.0% [0.0%, 35.4%], < 42.9% (rule of 3) |

Benign task accuracy per family:

| family | n | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| clean | 15 | 10/10 = 100.0% [72.2%, 100.0%] | 10/10 = 100.0% [72.2%, 100.0%] | 10/10 = 100.0% [72.2%, 100.0%] | 10/10 = 100.0% [72.2%, 100.0%] | 10/10 = 100.0% [72.2%, 100.0%] |
| db_tamper | 10 | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] | 5/5 = 100.0% [56.6%, 100.0%] |
| isolation_matrix | 10 | 4/4 = 100.0% [51.0%, 100.0%] | 4/4 = 100.0% [51.0%, 100.0%] | 4/4 = 100.0% [51.0%, 100.0%] | 4/4 = 100.0% [51.0%, 100.0%] | 4/4 = 100.0% [51.0%, 100.0%] |
| planted_doc | 10 | 2/3 = 66.7% [20.8%, 93.9%] | 2/3 = 66.7% [20.8%, 93.9%] | 2/3 = 66.7% [20.8%, 93.9%] | 2/3 = 66.7% [20.8%, 93.9%] | 2/3 = 66.7% [20.8%, 93.9%] |
| poisonedrag | 10 | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] | 3/3 = 100.0% [43.9%, 100.0%] |

Blocked attacks per version, by the first mechanism that visibly stopped them (attacks/attribution.py); 'attack succeeded' is the complement:

| mechanism | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|
| hash verification | – | 5 | 5 | 5 | 5 |
| input screen | – | – | 15 | 16 | 16 |
| hallucination check | – | – | 3 | 6 | 4 |
| memshield | – | – | 11 | 12 | 12 |
| contradiction / trust | – | – | 3 | 3 | 3 |
| registry match | – | – | – | 4 | – |
| access check (write) | – | – | – | – | – |
| JTMS retraction | – | 4 | 2 | 1 | 2 |
| registry binding | – | – | – | 1 | – |
| action gate | – | – | – | 6 | 12 |
| read filter | – | – | – | 7 | 7 |
| team scoping | – | 5 | 5 | 1 | 1 |
| none fired | 15 | 16 | 7 | 7 | 7 |
| attack succeeded | 55 | 40 | 19 | 1 | 1 |

Mechanisms that acted on attack material in any attack episode (a later mechanism hidden behind an earlier one still counts here):

| mechanism | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|
| hash verification | – | 5 | 5 | 5 | 5 |
| input screen | – | – | 15 | 16 | 16 |
| hallucination check | – | – | 8 | 12 | 10 |
| memshield | – | – | 12 | 13 | 13 |
| contradiction / trust | – | – | 3 | 3 | 3 |
| registry match | – | – | – | 19 | – |
| access check (write) | – | – | – | – | – |
| JTMS retraction | – | 4 | 4 | 2 | 4 |
| registry binding | – | – | – | 2 | – |
| action gate | – | – | – | 6 | 28 |
| read filter | – | – | – | 13 | 13 |

Benchmark episodes (agent runs with the benchmark payload; attack success by the per-episode oracle, 'harmless blocked' = clean-twin writes rejected / clean tool outputs quarantined, 'top mechanism' = what most often stopped an attack):

| benchmark | version | oracle attack success | harmless write rejected | clean input quarantined | clean task accuracy | LLM calls | top mechanism |
|---|---|---|---|---|---|---|---|
| agentdojo | baseline | 3/5 = 60.0% [23.1%, 88.2%] | – | – | – | 15 | none fired 2 |
| agentdojo | provenance | 3/5 = 60.0% [23.1%, 88.2%] | – | – | – | 15 | none fired 2 |
| agentdojo | write_checks | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | – | – | 12 | input screen 5 |
| agentdojo | full | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | – | – | 12 | input screen 5 |
| agentdojo | full_no_registry | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | – | – | 12 | input screen 5 |
| bipia | baseline | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 2/3 = 66.7% [20.8%, 93.9%] | 20 | none fired 5 |
| bipia | provenance | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 2/3 = 66.7% [20.8%, 93.9%] | 20 | none fired 5 |
| bipia | write_checks | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 2/3 = 66.7% [20.8%, 93.9%] | 20 | none fired 3, input screen 2 |
| bipia | full | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 2/3 = 66.7% [20.8%, 93.9%] | 20 | none fired 3, input screen 2 |
| bipia | full_no_registry | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 2/3 = 66.7% [20.8%, 93.9%] | 20 | none fired 3, input screen 2 |
| injecagent | baseline | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 20 | none fired 5 |
| injecagent | provenance | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 20 | none fired 5 |
| injecagent | write_checks | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 20 | input screen 3, none fired 2 |
| injecagent | full | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 20 | input screen 3, none fired 2 |
| injecagent | full_no_registry | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 20 | input screen 3, none fired 2 |
| memevobench | baseline | 2/5 = 40.0% [11.8%, 76.9%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 20 | none fired 3 |
| memevobench | provenance | 1/5 = 20.0% [3.6%, 62.4%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 20 | none fired 4 |
| memevobench | write_checks | 2/5 = 40.0% [11.8%, 76.9%] | 1/10 = 10.0% [1.8%, 40.4%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 20 | none fired 2, memshield 1 |
| memevobench | full | 1/5 = 20.0% [3.6%, 62.4%] | 1/10 = 10.0% [1.8%, 40.4%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 20 | memshield 2, none fired 2 |
| memevobench | full_no_registry | 1/5 = 20.0% [3.6%, 62.4%] | 1/10 = 10.0% [1.8%, 40.4%] | 0/10 = 0.0% [0.0%, 27.8%], < 30.0% (rule of 3) | – | 20 | memshield 2, none fired 2 |
| memshield | baseline | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 10 | – |
| memshield | provenance | 5/5 = 100.0% [56.6%, 100.0%] | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 10 | – |
| memshield | write_checks | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 10 | memshield 5 |
| memshield | full | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 10 | memshield 5 |
| memshield | full_no_registry | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) | – | 10 | memshield 5 |

Write-path classification, per labelled memory entry (positive = poisoned/misleading; predicted positive = the write was rejected). Not attack success: see attacks/classify.py:

| benchmark | version | TP | FP | FN | TN | precision | recall | F1 | harmless rejected |
|---|---|---|---|---|---|---|---|---|---|
| memshield | baseline | 0 | 0 | 5 | 5 | – | 0.00 | 0.00 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| memshield | provenance | 0 | 0 | 5 | 5 | – | 0.00 | 0.00 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| memshield | write_checks | 5 | 0 | 0 | 5 | 1.00 | 1.00 | 1.00 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| memshield | full | 5 | 0 | 0 | 5 | 1.00 | 1.00 | 1.00 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| memshield | full_no_registry | 5 | 0 | 0 | 5 | 1.00 | 1.00 | 1.00 | 0/5 = 0.0% [0.0%, 43.4%], < 60.0% (rule of 3) |
| memevobench | baseline | 0 | 0 | 15 | 20 | – | 0.00 | 0.00 | 0/20 = 0.0% [0.0%, 16.1%], < 15.0% (rule of 3) |
| memevobench | provenance | 0 | 0 | 15 | 20 | – | 0.00 | 0.00 | 0/20 = 0.0% [0.0%, 16.1%], < 15.0% (rule of 3) |
| memevobench | write_checks | 2 | 2 | 13 | 18 | 0.50 | 0.13 | 0.21 | 2/20 = 10.0% [2.8%, 30.1%] |
| memevobench | full | 2 | 2 | 13 | 18 | 0.50 | 0.13 | 0.21 | 2/20 = 10.0% [2.8%, 30.1%] |
| memevobench | full_no_registry | 2 | 2 | 13 | 18 | 0.50 | 0.13 | 0.21 | 2/20 = 10.0% [2.8%, 30.1%] |

Recall by attack type / domain (rejected poisoned writes):

| benchmark | type | baseline | provenance | write_checks | full | full_no_registry |
|---|---|---|---|---|---|---|
| memshield | T3_behavioral_drift | 0/1 = 0.0% | 0/1 = 0.0% | 1/1 = 100.0% | 1/1 = 100.0% | 1/1 = 100.0% |
| memshield | T4_factual_manipulation | 0/1 = 0.0% | 0/1 = 0.0% | 1/1 = 100.0% | 1/1 = 100.0% | 1/1 = 100.0% |
| memshield | T5_backdoor_trigger | 0/3 = 0.0% | 0/3 = 0.0% | 3/3 = 100.0% | 3/3 = 100.0% | 3/3 = 100.0% |
| memevobench | customerservice | 0/6 = 0.0% | 0/6 = 0.0% | 2/6 = 33.3% | 2/6 = 33.3% | 2/6 = 33.3% |
| memevobench | finance | 0/6 = 0.0% | 0/6 = 0.0% | 0/6 = 0.0% | 0/6 = 0.0% | 0/6 = 0.0% |
| memevobench | food | 0/3 = 0.0% | 0/3 = 0.0% | 0/3 = 0.0% | 0/3 = 0.0% | 0/3 = 0.0% |

What the registry adds (blocked-by, full vs full_no_registry, per family):

| family | succeeded full | succeeded full_no_registry | full: blocked by | full_no_registry: blocked by |
|---|---|---|---|---|
| agentpoison | 0 | 0 | memshield 5 | memshield 5 |
| db_tamper | 0 | 0 | hash verification 5 | hash verification 5 |
| fake_fact | 0 | 0 | action gate 5 | action gate 5 |
| isolation | 0 | 0 | read filter 5 | read filter 5 |
| isolation_matrix | 0 | 0 | registry match 1, action gate 1, read filter 2, team scoping 1 | action gate 2, read filter 2, team scoping 1 |
| minja | 0 | 0 | input screen 5 | input screen 5 |
| planted_doc | 0 | 0 | input screen 2, none fired 3 | input screen 2, none fired 3 |
| poisonedrag | 0 | 0 | input screen 1, hallucination check 1, contradiction / trust 3 | input screen 1, hallucination check 1, contradiction / trust 3 |
| poisoning | 1 | 1 | memshield 7, none fired 2 | memshield 7, none fired 2 |
| repetition_flooding | 0 | 0 | hallucination check 3, registry match 2 | hallucination check 1, action gate 4 |
| summary_laundering | 0 | 0 | hallucination check 2, registry match 1, JTMS retraction 1, registry binding 1 | hallucination check 2, JTMS retraction 2, action gate 1 |
| tool_hijack | 0 | 0 | input screen 8, none fired 2 | input screen 8, none fired 2 |
