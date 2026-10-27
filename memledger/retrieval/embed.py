"""Slide 15: embedders. HashEmbedder for tests, BGEM3Embedder for real runs."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol


class Embedder(Protocol):
    def __call__(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    """Deterministic hashed bag-of-words, L2-normalized."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def __call__(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            v = [0.0] * self.dim
            for tok in re.findall(r"\w+", text.lower()):
                h = int.from_bytes(hashlib.sha256(tok.encode()).digest()[:8], "big")
                v[h % self.dim] += 1.0
            n = math.sqrt(sum(x * x for x in v))
            out.append([x / n for x in v] if n else v)
        return out


class BGEM3Embedder:
    """BAAI/bge-m3 via sentence-transformers (lazy import)."""

    def __init__(self, model: str = "BAAI/bge-m3") -> None:
        self.model_name = model
        self._model = None

    def __call__(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model.encode(texts, normalize_embeddings=True).tolist()
