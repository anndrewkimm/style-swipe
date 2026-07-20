"""Tests for pure NumPy style-profile scoring."""

import numpy as np
import pytest

from app.recommend import build_style_profile, score_candidates


def test_style_profile_is_normalized_mean() -> None:
    profile = build_style_profile(
        [
            np.array([1.0, 0.0], dtype=np.float32),
            np.array([0.0, 1.0], dtype=np.float32),
        ]
    )

    expected = np.array([1.0, 1.0], dtype=np.float32) / np.sqrt(2.0)
    np.testing.assert_allclose(profile, expected)
    assert np.linalg.norm(profile) == pytest.approx(1.0)


def test_identical_candidate_outscores_orthogonal_candidate() -> None:
    profile = build_style_profile([np.array([1.0, 0.0], dtype=np.float32)])

    scores = score_candidates(
        profile,
        [
            np.array([1.0, 0.0], dtype=np.float32),
            np.array([0.0, 1.0], dtype=np.float32),
        ],
    )

    assert scores[0] == pytest.approx(1.0)
    assert scores[1] == pytest.approx(0.0)
