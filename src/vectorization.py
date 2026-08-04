from __future__ import annotations

from typing import Iterable

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from src.settings import SETTINGS


_VECTORIZER = HashingVectorizer(
    n_features=SETTINGS.vector_dimensions,
    alternate_sign=False,
    norm=None,
    ngram_range=(1, 2),
)


def _normalize_dense(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


def embed_text(text: str) -> list[float]:
    matrix = _VECTORIZER.transform([text])
    dense = matrix.toarray()[0].astype(float)
    return _normalize_dense(dense).tolist()


def embed_many(texts: Iterable[str]) -> list[list[float]]:
    matrix = _VECTORIZER.transform(list(texts))
    dense = matrix.toarray().astype(float)
    return [_normalize_dense(row).tolist() for row in dense]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    left_arr = np.array(left, dtype=float)
    right_arr = np.array(right, dtype=float)
    if left_arr.size == 0 or right_arr.size == 0:
        return 0.0
    denom = np.linalg.norm(left_arr) * np.linalg.norm(right_arr)
    if denom == 0:
        return 0.0
    return float(np.dot(left_arr, right_arr) / denom)
