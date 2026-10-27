# Demo script (chat demo) — owner M4

Setup (no Wi-Fi needed): `bash demo/run.sh`, browser at http://localhost:8501, full screen (F11), zoom 100%.
Fallback: the recorded video. If anything misbehaves on stage, switch to the recording; don't debug live.

For each test case: pick it in the dropdown, protection **off**, **▶ Run**; then protection **on**, **▶ Run**. Both runs
stay in the chat, one under the other. Press **Clear chat** before the next case.

| case | off: point at | on: point at | say |
|---|---|---|---|
| 1 Poisoned web page → payment | red "Paid account 9876" | "Write refused…", "Account bound… unknown → 1234" | "Plain memory believes the page and pays the attacker. MemLedger refuses the fake account, flags the page and pays from the signed registry." |
| 2 Memory injection through chat | "remember … 5550 → stored", red payment | "Input screen flagged this message", "Write refused" | "Anyone in the chat can plant a fact in plain memory. MemLedger refuses it." |
| 3 Hidden instruction in a document | red "Sent to reports@evil-mail.example" | "Input screen flagged this page on arrival" | "A hidden instruction exfiltrates the report. MemLedger keeps the page out of the agent's memory." |
| 4 Another team's confidential data | 93.1 in the agent's answer | "Access control: … never shown to the agent" | "Plain memory has no notion of teams. MemLedger only ever shows the agent what this user may read." |
| 5 Direct database edit | "19%" in the answer | "Integrity check failed on read" | "A direct database edit is served as fact by plain memory and caught by MemLedger's hash chain." |

Optional, after any ON run: type the suggested question in the chat box to show the memory itself is clean.
