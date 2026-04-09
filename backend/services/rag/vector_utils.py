# -*- coding: utf-8 -*-
"""Vector and token helpers for rule RAG."""

from __future__ import annotations

import math
import re
from collections import Counter


TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+")
DENSE_DIMS = 64
SPARSE_DIMS = 2048


def tokenize(text: str) -> list[str]:
    base_tokens = TOKEN_PATTERN.findall((text or "").lower())
    extra_tokens: list[str] = []
    for index in range(len(base_tokens) - 1):
        left = base_tokens[index]
        right = base_tokens[index + 1]
        if len(left) == 1 and len(right) == 1:
            extra_tokens.append(f"{left}{right}")
    return base_tokens + extra_tokens


def sparse_vector(tokens: list[str]) -> Counter:
    return Counter(tokens)


def sparse_milvus_vector(tokens: list[str], dims: int = SPARSE_DIMS) -> dict[int, float]:
    counter = sparse_vector(tokens)
    if not counter:
        return {}
    norm = math.sqrt(sum(value * value for value in counter.values())) or 1.0
    result: dict[int, float] = {}
    for token, value in counter.items():
        result[hash(token) % dims] = result.get(hash(token) % dims, 0.0) + (value / norm)
    return result


def dense_vector(tokens: list[str], dims: int = DENSE_DIMS) -> list[float]:
    vector = [0.0] * dims
    if not tokens:
        return vector
    for token in tokens:
        vector[hash(token) % dims] += 1.0
    norm = math.sqrt(sum(item * item for item in vector)) or 1.0
    return [item / norm for item in vector]


def normalize_dense_vector(vector: list[float]) -> list[float]:
    if not vector:
        return []
    norm = math.sqrt(sum(item * item for item in vector)) or 1.0
    return [item / norm for item in vector]


def bm25_like(query_tokens: list[str], doc_tokens: list[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    counter = Counter(doc_tokens)
    score = 0.0
    for token in query_tokens:
        tf = counter.get(token, 0)
        if tf:
            score += (tf * 2.2) / (tf + 1.2)
    return score / max(len(doc_tokens), 1)
