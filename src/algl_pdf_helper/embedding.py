from __future__ import annotations

import math
import re


_NON_ALNUM = re.compile(r"[^a-z0-9\s]")


def tokenize(text: str) -> list[str]:
    cleaned = _NON_ALNUM.sub(" ", text.lower())
    tokens = []
    for tok in cleaned.split():
        tok = tok.strip()
        if len(tok) >= 3:
            tokens.append(tok)
    return tokens


def hash_token(token: str) -> int:
    h = 0
    for ch in token:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def build_hash_embedding(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    for tok in tokenize(text):
        idx = hash_token(tok) % dim
        vec[idx] += 1.0

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec

    return [v / norm for v in vec]
