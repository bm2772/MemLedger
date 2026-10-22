"""Slide 10: vector and keyword index, one per team."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable
from typing import Protocol


class VectorIndex(Protocol):
    def add(self, team: str, item_id: str, text: str) -> None: ...

    def query(self, teams: list[str], text: str, k: int = 8) -> list[tuple[str, float]]:
        """Return (item_id, score), higher = more similar, sorted descending."""
        ...


def _bag(text: str) -> Counter:
    return Counter(text.lower().split())


def _cosine(a: Counter, b: Counter) -> float:
    dot = sum(v * b.get(w, 0) for w, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


class InMemoryIndex:
    """Word-count cosine similarity, one dict per team."""

    def __init__(self) -> None:
        self._teams: dict[str, dict[str, Counter]] = {}

    def add(self, team: str, item_id: str, text: str) -> None:
        self._teams.setdefault(team, {})[item_id] = _bag(text)

    def query(self, teams: list[str], text: str, k: int = 8) -> list[tuple[str, float]]:
        q = _bag(text)
        hits = []
        for t in dict.fromkeys(teams):
            for item_id, bag in self._teams.get(t, {}).items():
                score = _cosine(q, bag)
                if score > 0:
                    hits.append((item_id, score))
        return sorted(hits, key=lambda h: -h[1])[:k]


class ChromaIndex:
    """ChromaDB-backed index, one collection per team (optional dependency)."""

    def __init__(self, path: str | None = None,
                 embed: Callable[[list[str]], list[list[float]]] | None = None) -> None:
        try:
            import chromadb
        except ImportError as e:
            raise ImportError('chromadb is required: pip install -e ".[store]"') from e
        self._client = chromadb.PersistentClient(path=path) if path else chromadb.EphemeralClient()
        self._embed = embed
        self._cols: dict[str, object] = {}

    def _col(self, team: str):
        if team not in self._cols:
            self._cols[team] = self._client.get_or_create_collection(
                f"team_{team}", metadata={"hnsw:space": "cosine"}
            )
        return self._cols[team]

    def add(self, team: str, item_id: str, text: str) -> None:
        kw = {"embeddings": self._embed([text])} if self._embed else {}
        self._col(team).add(ids=[item_id], documents=[text], **kw)

    def query(self, teams: list[str], text: str, k: int = 8) -> list[tuple[str, float]]:
        hits: list[tuple[str, float]] = []
        for t in dict.fromkeys(teams):
            col = self._col(t)
            if col.count() == 0:
                continue
            kw = ({"query_embeddings": self._embed([text])} if self._embed else {"query_texts": [text]})
            res = col.query(n_results=min(k, col.count()), **kw)
            hits += [(i, 1.0 - d) for i, d in zip(res["ids"][0], res["distances"][0], strict=True)]
        return sorted(hits, key=lambda h: -h[1])[:k]
