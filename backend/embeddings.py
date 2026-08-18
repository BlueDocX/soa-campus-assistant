"""Embedding provider abstraction. Primary: sentence-transformers all-MiniLM-L6-v2 (neural,
local). Fallback: deterministic hashed bag-of-words vector so retrieval never hard-fails.
Swap providers by changing get_provider().
"""
import re
import math
import hashlib
import logging
from typing import List

logger = logging.getLogger("soa.embeddings")
_DIM_FALLBACK = 384


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9\u0900-\u097F\u0B00-\u0B7F]+", (text or "").lower())


class _HashProvider:
    name = "hash-fallback"
    dim = _DIM_FALLBACK

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for tok in _tokens(text):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        n = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / n for v in vec]


class _STProvider:
    name = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self, model):
        self._model = model
        self.dim = model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> List[float]:
        v = self._model.encode(text or "", normalize_embeddings=True)
        return [float(x) for x in v]


_provider = None


def get_provider():
    global _provider
    if _provider is not None:
        return _provider
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        _provider = _STProvider(model)
        logger.info("Embedding provider: sentence-transformers all-MiniLM-L6-v2")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"sentence-transformers unavailable ({e}); using hashed fallback provider")
        _provider = _HashProvider()
    return _provider


def embed(text: str) -> List[float]:
    return get_provider().embed(text)


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
