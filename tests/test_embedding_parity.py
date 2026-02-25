from __future__ import annotations

from algl_pdf_helper.embedding import build_hash_embedding


def test_hash_embedding_matches_expected_vector():
    # Expected values were computed once using the reference algorithm.
    text = "select from where join group by having order"
    vec = build_hash_embedding(text, 24)

    expected = [
        0.0,
        0.0,
        0.0,
        0.0,
        1 / 3,
        0.0,
        1 / 3,
        0.0,
        0.0,
        0.0,
        1 / 3,
        0.0,
        0.0,
        1 / 3,
        0.0,
        0.0,
        0.0,
        0.0,
        1 / 3,
        0.0,
        0.0,
        0.0,
        0.0,
        2 / 3,
    ]

    assert len(vec) == len(expected)
    for got, exp in zip(vec, expected):
        assert abs(got - exp) < 1e-12
