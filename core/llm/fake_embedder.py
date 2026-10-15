"""Deterministic offline embedder used in tests and CI.

Feature hashing over stemmed unigrams and bigrams with sublinear term frequency.
It is a lexical model, not a semantic one, but it is stable across machines and
good enough to exercise retrieval, thresholds and citations without an API key.
"""

from __future__ import annotations

import hashlib
import itertools
import math
from collections import Counter
from collections.abc import Sequence

from core.llm.text import tokenize


class FakeEmbedder:
    name = "fake-hash-v2"

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _bucket(self, feature: str) -> tuple[int, float]:
        digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
        value = int.from_bytes(digest, "little")
        return value % self.dim, 1.0 if (value >> 63) & 1 else -1.0

    def embed_one(self, text: str) -> list[float]:
        tokens = tokenize(text)
        features: Counter[str] = Counter(tokens)
        features.update(f"{a}_{b}" for a, b in itertools.pairwise(tokens))
        vector = [0.0] * self.dim
        for feature, count in features.items():
            index, sign = self._bucket(feature)
            weight = 1.0 + math.log(count)
            if "_" in feature:
                weight *= 0.5
            vector[index] += sign * weight
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            # pgvector cannot compute cosine distance for a zero vector
            vector[0] = 1.0
            return vector
        return [v / norm for v in vector]

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed_one(t) for t in texts]
