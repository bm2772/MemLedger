"""Direct database tampering (slides 14, 22: attack type "Tampering"): edit storage behind the service's back.

`drop_triggers` removes the append-only triggers (an attacker with file access can); the `tamper_*` functions edit
one kind of record; `TamperingService` wraps a service so that an Episode with `meta["tamper"]` is attacked after its
seeds are loaded and before the first read, which is the only moment the Episode v1 runner leaves open. It records what
was returned afterwards: `report()` is stored in the eval row as `tamper` and graded by attacks/oracle.py.

    meta["tamper"] = {"kind": one of KINDS, "targets": [seed ids]}   (hash_log_row: every claim is affected)
    labels: {"kind": "labels", "targets": [...], "to_team": "team_b", "subjects": [triple subjects for the read route]}
    targets are seed ids or ids of write steps (their text is the claim's text).

The helpers are shared with tests/integration/test_properties.py.
"""

from __future__ import annotations

import statistics
import time

KINDS = ["claim_text", "source_content", "recorded_at", "derivation_edge", "labels", "hash_log_row"]
OLD_TIME = "2001-01-01T00:00:00+00:00"


def drop_triggers(svc) -> None:
    for (name,) in svc.store.conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall():
        svc.store.conn.execute(f"DROP TRIGGER {name}")


def claim_source(svc, claim_id: str) -> str | None:
    """The first source in the claim's context window (its exposed_to edge)."""
    row = svc.store.conn.execute("SELECT src FROM edges WHERE dst=? AND type='exposed_to' ORDER BY id LIMIT 1",
                                 (claim_id,)).fetchone()
    return row["src"] if row else None


def tamper(svc, kind: str, claim_id: str, to_team: str = "team_b", rng=None) -> None:
    """Edit storage directly for one claim (triggers dropped first); `hash_log_row` deletes a non-final log row."""
    conn = svc.store.conn
    drop_triggers(svc)
    if kind == "claim_text":
        conn.execute("UPDATE claims SET text = text || ' (edited)' WHERE id=?", (claim_id,))
    elif kind == "source_content":
        conn.execute("UPDATE sources SET content='tampered content' WHERE id=?", (claim_source(svc, claim_id),))
    elif kind == "recorded_at":
        conn.execute("UPDATE claims SET recorded_at=? WHERE id=?", (OLD_TIME, claim_id))
    elif kind == "derivation_edge":
        row = conn.execute("SELECT id FROM edges WHERE dst=? AND type='exposed_to' ORDER BY id LIMIT 1",
                           (claim_id,)).fetchone()
        conn.execute("UPDATE edges SET src='s_forged' WHERE id=?", (row["id"],))
    elif kind == "labels":
        conn.execute("UPDATE claims SET team=? WHERE id=?", (to_team, claim_id))
    elif kind == "hash_log_row":
        seqs = [r["seq"] for r in svc.store.hash_log()]
        pick = (rng.choice(seqs[:-1] or seqs) if rng is not None else (seqs[:-1] or seqs)[0])
        conn.execute("DELETE FROM hash_log WHERE seq=?", (pick,))
    else:
        raise ValueError(f"unknown tamper kind {kind!r}")
    conn.commit()


class TamperingService:
    """Service wrapper: tamper once after the seeds, before the first retrieve; everything else passes through."""

    def __init__(self, svc, episode) -> None:
        self.svc, self.ep, self.spec = svc, episode, episode.meta["tamper"]
        self.armed = False
        self.victims: list[str] = []
        self.returned: set[str] = set()

    def __getattr__(self, name):
        return getattr(self.svc, name)

    def _claims_of(self, texts: list[str]) -> list[str]:
        conn = self.svc.store.conn
        return [r["id"] for t in texts for r in conn.execute("SELECT id FROM claims WHERE text=?", (t,)).fetchall()]

    def _arm(self) -> None:
        if self.armed:
            return
        self.armed = True
        text_of = {s.id: s.content for s in self.ep.seeds} | {s.id: s.text for s in self.ep.steps if s.op == "write"}
        kind = self.spec["kind"]
        ids = self._claims_of([text_of[t] for t in self.spec["targets"] if t in text_of])
        self.all_ids = self._claims_of([s.content for s in self.ep.seeds])
        # a target the write checks rejected was never stored: tamper the first stored seed instead, so the attack is
        # still carried out (scoring the untouched memories as "tampered" turned a rejected seed into a false leak)
        self.retargeted = not ids and bool(self.all_ids)
        if self.retargeted:
            ids = self.all_ids[:1]
        if kind == "labels":  # the triple route reads the claims table, not the FTS/vector copies (so edit is visible)
            for cid in ids:
                for subject in self.spec.get("subjects", []):
                    self.svc.add_triple(cid, subject.lower(), "measured", "x")
        for cid in ids:
            tamper(self.svc, kind, cid, self.spec.get("to_team", "team_b"))
            if kind == "hash_log_row":
                break
        self.victims = list(self.all_ids if kind == "hash_log_row" else ids)

    def retrieve(self, query, session, k=8):
        self._arm()
        hits = self.svc.retrieve(query, session, k)
        self.returned |= {h.claim.id for h in hits}
        return hits

    def report(self) -> dict:
        """Which tampered claims were still returned, and which ended up quarantined."""
        self._arm()
        status = {v: self.svc.store.get_claim(v).status.value for v in self.victims}
        returned = sorted(set(self.victims) & self.returned)
        quarantined = [v for v, s in status.items() if s == "quarantined"]
        # measured from the service's own state: withheld from every read AND quarantined, with the recorded reason
        detected = bool(self.victims) and not returned and len(quarantined) == len(self.victims)
        reasons = {self.svc.store.status_history(v)[-1]["reason"] for v in quarantined}
        by = None if not detected else ("hash verification" if all(r.startswith("integrity") for r in reasons)
                                        else "other: " + "; ".join(sorted(reasons)))
        return {"kind": self.spec["kind"], "victims": len(self.victims), "returned": len(returned),
                "quarantined": len(quarantined), "detected": detected, "detected_by": by,
                "retargeted": getattr(self, "retargeted", False),
                "carried_out": bool(self.victims)}  # False: the write checks stored no seed, nothing to tamper with


class ProbeService:
    """Service wrapper for side-channel episodes: records, per retrieve call, the query, the result count and the latency.

    `meta["side_channel"] = {"pairs": [{"hit": query, "miss": query}]}`: the "hit" query targets another team's marker,
    the "miss" query is the same shape but matches nothing anywhere. A system that keeps teams apart returns the same
    number of results for both. `report()` -> {"pairs": [...], "count_leak": bool, "timing_diff_ms": median(hit - miss)};
    the count difference is the leak (graded by attacks/oracle.py), the timing difference is informational (a single
    in-process call is noisy; a real timing channel would need many samples).
    """

    def __init__(self, svc, episode) -> None:
        self.svc, self.spec = svc, episode.meta["side_channel"]
        self.calls: list[dict] = []

    def __getattr__(self, name):
        return getattr(self.svc, name)

    def retrieve(self, query, session, k=8):
        t0 = time.perf_counter()
        hits = self.svc.retrieve(query, session, k)
        self.calls.append({"query": query, "n": len(hits), "ms": (time.perf_counter() - t0) * 1000})
        return hits

    def report(self) -> dict:
        def find(q: str) -> dict | None:
            return next((c for c in self.calls if c["query"] == q), None)

        pairs = []
        for p in self.spec["pairs"]:
            hit, miss = find(p["hit"]), find(p["miss"])
            if hit and miss:
                pairs.append({"n_hit": hit["n"], "n_miss": miss["n"], "ms_hit": round(hit["ms"], 3),
                              "ms_miss": round(miss["ms"], 3)})
        diffs = [x["ms_hit"] - x["ms_miss"] for x in pairs]
        return {"pairs": pairs, "count_leak": any(x["n_hit"] != x["n_miss"] for x in pairs),
                "timing_diff_ms": statistics.median(diffs) if diffs else None}


def wrap_service(episode, svc):
    """The service itself, or a wrapper when the episode carries a tamper spec / a side-channel probe spec."""
    if episode.meta.get("tamper"):
        return TamperingService(svc, episode)
    return ProbeService(svc, episode) if episode.meta.get("side_channel") else svc
