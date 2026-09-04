from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from typing import Any, Protocol

from retrieval.tokenization import tokenize


class Embedder(Protocol):
    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


class LocalHashEmbedder:
    """Small deterministic fallback for tests and offline demonstrations."""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for token in tokenize(text):
                index = int(hashlib.sha1(token.encode("utf-8")).hexdigest()[:8], 16) % self.dimensions
                vector[index] += 1.0
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors


class SentenceTransformerEmbedder:
    """Lazy multilingual embedding adapter for the production-like vector mode."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small"):
        self.model_name = model_name
        self._model: Any = None

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        values = self._model.encode(list(texts), normalize_embeddings=True)
        return [list(map(float, vector)) for vector in values]
