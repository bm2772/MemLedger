"""One-off converter: M4's pre-v1 eval episodes (eval/episode.py) -> shared schema v1 (memledger.agent.episode).

    python -m scenarios.convert_v0 eval/fixtures/smoke.jsonl scenarios/fixtures/smoke_v1.jsonl

Mapping: attack_type -> category (source if absent); attacker_goal -> expect.forbidden_tool_calls[0];
step "as" -> id; first session -> default_session; canaries, poison_markers, registry unchanged.
Delete this file once eval/ reads v1 (docs/proposals/episode-format.md).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from memledger.agent.episode import Episode, dump_jsonl


def from_eval_v0(d: dict) -> Episode:
    goal = d.get("attacker_goal")
    return Episode.from_dict({
        "id": d["id"], "source": d.get("source", ""), "split": d.get("split", "dev"), "kind": d["kind"],
        "category": d.get("attack_type") or d.get("source") or d["kind"],
        "sessions": d["sessions"], "default_session": next(iter(d["sessions"])),
        "steps": d["steps"], "expect": {"forbidden_tool_calls": [goal] if goal else []},
        "canaries": d.get("canaries", []), "poison_markers": d.get("poison_markers", []),
        "registry": d.get("registry", {}),
    })


def main(argv: list[str] | None = None) -> None:
    src, dst = argv if argv is not None else sys.argv[1:]
    rows = [json.loads(x) for x in Path(src).read_text().splitlines() if x.strip()]
    eps = [from_eval_v0(r) for r in rows]
    dump_jsonl(eps, dst)
    print(f"converted {len(eps)} episodes -> {dst}")


if __name__ == "__main__":
    main()
