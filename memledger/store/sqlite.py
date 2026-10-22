"""Slides 6, 10, 14: provenance graph + change log + hash log."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime

from memledger.core.types import Claim, Derivation, Integrity, Labels, Source, SourceKind, Status, now

TABLES = ["sources", "claims", "derivations", "edges", "status_log", "hash_log", "triples"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(
  id TEXT PRIMARY KEY, kind TEXT, content TEXT, team TEXT, confidentiality INTEGER,
  integrity INTEGER, prior_trust REAL, content_hash TEXT, recorded_at TEXT);
CREATE TABLE IF NOT EXISTS claims(
  id TEXT PRIMARY KEY, text TEXT, team TEXT, confidentiality INTEGER, integrity INTEGER,
  valid_from TEXT, valid_to TEXT, recorded_at TEXT, content_hash TEXT);
CREATE TABLE IF NOT EXISTS derivations(
  id TEXT PRIMARY KEY, claim_id TEXT, model TEXT, prompt_hash TEXT, agent_id TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS edges(
  id INTEGER PRIMARY KEY AUTOINCREMENT, src TEXT, dst TEXT,
  type TEXT CHECK(type IN ('exposed_to','supported_by','contradicts','supersedes')),
  score REAL, derivation_id TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS status_log(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, entity_id TEXT, status TEXT, trust REAL,
  reason TEXT NOT NULL, at TEXT);
CREATE TABLE IF NOT EXISTS hash_log(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, root TEXT, signature BLOB, n_items INTEGER, at TEXT);
CREATE TABLE IF NOT EXISTS triples(
  id INTEGER PRIMARY KEY AUTOINCREMENT, claim_id TEXT, subject TEXT, property TEXT, value TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
  claim_id UNINDEXED, team UNINDEXED, text, tokenize='porter unicode61');
CREATE INDEX IF NOT EXISTS ix_triples_subject ON triples(subject COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS ix_edges_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS ix_status_entity ON status_log(entity_id);
"""


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


class SQLiteStore:
    """Append-only provenance store; status changes live in status_log, never in place."""

    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        for t in TABLES:
            for op in ("UPDATE", "DELETE"):
                self.conn.execute(
                    f"CREATE TRIGGER IF NOT EXISTS {t}_no_{op.lower()} BEFORE {op} ON {t} "
                    "BEGIN SELECT RAISE(ABORT, 'append-only'); END"
                )
        self.conn.commit()

    # ---- sources
    def add_source(self, s: Source) -> None:
        self.conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?)",
            (s.id, s.kind.value, s.content, s.labels.team, s.labels.confidentiality,
             int(s.labels.integrity), s.prior_trust, s.content_hash, _iso(s.recorded_at)),
        )
        self.conn.commit()

    def _source(self, r: sqlite3.Row) -> Source:
        last = self._latest_status(r["id"])
        return Source(
            r["id"], SourceKind(r["kind"]), r["content"],
            Labels(r["team"], r["confidentiality"], Integrity(r["integrity"])),
            r["prior_trust"], r["content_hash"], _dt(r["recorded_at"]),
            flagged=bool(last and last["status"] == "flagged"),
        )

    def get_source(self, source_id: str) -> Source | None:
        r = self.conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        return self._source(r) if r else None

    def list_sources(self) -> list[Source]:
        rows = self.conn.execute("SELECT * FROM sources ORDER BY rowid").fetchall()
        return [self._source(r) for r in rows]

    # ---- claims
    def add_claim(self, c: Claim) -> None:
        self.conn.execute(
            "INSERT INTO claims VALUES (?,?,?,?,?,?,?,?,?)",
            (c.id, c.text, c.labels.team, c.labels.confidentiality, int(c.labels.integrity),
             _iso(c.valid_from), _iso(c.valid_to), _iso(c.recorded_at), c.content_hash),
        )
        self.conn.execute(
            "INSERT INTO claims_fts(claim_id, team, text) VALUES (?,?,?)", (c.id, c.labels.team, c.text)
        )
        self.conn.commit()
        self.set_status(c.id, c.status.value, "created", c.trust)

    def _claim(self, r: sqlite3.Row) -> Claim:
        last = self._latest_status(r["id"])
        return Claim(
            r["id"], r["text"], Labels(r["team"], r["confidentiality"], Integrity(r["integrity"])),
            trust=(last["trust"] or 0.0) if last else 0.0,
            status=Status(last["status"]) if last else Status.ACTIVE,
            valid_from=_dt(r["valid_from"]), valid_to=_dt(r["valid_to"]),
            recorded_at=_dt(r["recorded_at"]), content_hash=r["content_hash"],
        )

    def get_claim(self, claim_id: str) -> Claim | None:
        r = self.conn.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
        return self._claim(r) if r else None

    def list_claims(self, team: str | None = None, teams: list[str] | None = None) -> list[Claim]:
        rows = self.conn.execute("SELECT * FROM claims ORDER BY rowid").fetchall()
        allowed = set(teams) if teams is not None else None
        return [
            self._claim(r) for r in rows
            if (team is None or r["team"] == team) and (allowed is None or r["team"] in allowed)
        ]

    def keyword_search(self, teams: list[str], query: str, k: int) -> list[tuple[str, float]]:
        """BM25 over claim text (FTS5). Score = -bm25, higher is better."""
        tokens = re.findall(r"[A-Za-z0-9]+", query)
        team_list = list(dict.fromkeys(teams))
        if not tokens or not team_list:
            return []
        match = " OR ".join(f'"{t}"' for t in dict.fromkeys(tokens))
        marks = ",".join("?" * len(team_list))
        rows = self.conn.execute(
            f"SELECT claim_id, bm25(claims_fts) AS b FROM claims_fts "
            f"WHERE claims_fts MATCH ? AND team IN ({marks}) ORDER BY b LIMIT ?",
            (match, *team_list, k),
        ).fetchall()
        return [(r["claim_id"], -r["b"]) for r in rows]

    # ---- triples (exact-fact route)
    def add_triple(self, claim_id: str, subject: str, property: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO triples(claim_id,subject,property,value) VALUES (?,?,?,?)",
            (claim_id, subject, property, value),
        )
        self.conn.commit()

    def lookup_triples(self, subject: str, property: str | None = None) -> list[str]:
        sql = "SELECT DISTINCT claim_id FROM triples WHERE lower(subject)=lower(?)"
        args: list[str] = [subject]
        if property is not None:
            sql += " AND lower(property)=lower(?)"
            args.append(property)
        return [r["claim_id"] for r in self.conn.execute(sql + " ORDER BY id", args).fetchall()]

    def triple_subjects(self) -> list[str]:
        rows = self.conn.execute("SELECT DISTINCT lower(subject) AS s FROM triples").fetchall()
        return [r["s"] for r in rows]

    # ---- derivations and edges
    def add_derivation(self, d: Derivation) -> None:
        self.conn.execute(
            "INSERT INTO derivations VALUES (?,?,?,?,?,?)",
            (d.id, d.claim_id, d.model, d.prompt_hash, d.agent_id, _iso(d.created_at)),
        )
        for pid in d.exposed_to:
            self._edge(pid, d.claim_id, "exposed_to", None, d.id, d.created_at)
        for pid, score in d.supported_by.items():
            self._edge(pid, d.claim_id, "supported_by", score, d.id, d.created_at)
        self.conn.commit()

    def get_derivation(self, derivation_id: str) -> Derivation | None:
        r = self.conn.execute("SELECT * FROM derivations WHERE id=?", (derivation_id,)).fetchone()
        return self._derivation(r) if r else None

    def derivations_for(self, claim_id: str) -> list[Derivation]:
        rows = self.conn.execute("SELECT * FROM derivations WHERE claim_id=? ORDER BY rowid", (claim_id,))
        return [self._derivation(r) for r in rows.fetchall()]

    def _derivation(self, r: sqlite3.Row) -> Derivation:
        edges = self.conn.execute(
            "SELECT * FROM edges WHERE derivation_id=? ORDER BY id", (r["id"],)
        ).fetchall()
        return Derivation(
            r["id"], r["claim_id"],
            [e["src"] for e in edges if e["type"] == "exposed_to"],
            {e["src"]: e["score"] for e in edges if e["type"] == "supported_by"},
            r["model"], r["prompt_hash"], r["agent_id"], _dt(r["created_at"]),
        )

    def _edge(self, src, dst, type_, score, derivation_id, at) -> None:
        self.conn.execute(
            "INSERT INTO edges(src,dst,type,score,derivation_id,created_at) VALUES (?,?,?,?,?,?)",
            (src, dst, type_, score, derivation_id, _iso(at or now())),
        )

    def add_edge(self, src: str, dst: str, type: str, score: float | None = None,
                 derivation_id: str | None = None) -> None:
        self._edge(src, dst, type, score, derivation_id, now())
        self.conn.commit()

    def edges(self, src: str | None = None, dst: str | None = None, type: str | None = None) -> list[dict]:
        where, args = [], []
        for col, val in (("src", src), ("dst", dst), ("type", type)):
            if val is not None:
                where.append(f"{col}=?")
                args.append(val)
        sql = "SELECT * FROM edges" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    # ---- status log
    def set_status(self, entity_id: str, status: str, reason: str, trust: float | None = None) -> None:
        if not reason or not reason.strip():
            raise ValueError("status change requires a reason")
        if trust is None:
            prev = self._latest_status(entity_id)
            trust = prev["trust"] if prev else None
        self.conn.execute(
            "INSERT INTO status_log(entity_id,status,trust,reason,at) VALUES (?,?,?,?,?)",
            (entity_id, status, trust, reason, _iso(now())),
        )
        self.conn.commit()

    def _latest_status(self, entity_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM status_log WHERE entity_id=? ORDER BY seq DESC LIMIT 1", (entity_id,)
        ).fetchone()

    def status_history(self, entity_id: str) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM status_log WHERE entity_id=? ORDER BY seq", (entity_id,))
        return [dict(r) for r in rows.fetchall()]

    def flag_source(self, source_id: str, reason: str) -> None:
        self.set_status(source_id, "flagged", reason)

    # ---- hash log
    def append_hash_log(self, root: str, signature: bytes, n_items: int) -> int:
        cur = self.conn.execute(
            "INSERT INTO hash_log(root,signature,n_items,at) VALUES (?,?,?,?)",
            (root, signature, n_items, _iso(now())),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def hash_log(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM hash_log ORDER BY seq").fetchall()]

    def latest_root(self) -> dict | None:
        r = self.conn.execute("SELECT * FROM hash_log ORDER BY seq DESC LIMIT 1").fetchone()
        return dict(r) if r else None
