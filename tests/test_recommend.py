"""Tests for pure NumPy style-profile scoring."""

import numpy as np
import pytest

from app.recommend import (
    build_adjusted_profile,
    build_style_profile,
    score_candidates,
)


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


def test_adjusted_profile_without_swipes_equals_seed_profile() -> None:
    seeds = [
        np.array([1.0, 0.0], dtype=np.float32),
        np.array([0.0, 1.0], dtype=np.float32),
    ]

    adjusted = build_adjusted_profile(seeds, [], [])

    np.testing.assert_array_equal(adjusted, build_style_profile(seeds))


def test_likes_raise_and_dislikes_lower_direction_scores() -> None:
    seeds = [np.array([1.0, 0.0], dtype=np.float32)]
    feedback_direction = np.array([0.0, 1.0], dtype=np.float32)
    baseline = build_style_profile(seeds)
    liked_profile = build_adjusted_profile(seeds, [feedback_direction], [])
    disliked_profile = build_adjusted_profile(seeds, [], [feedback_direction])

    baseline_score = score_candidates(baseline, [feedback_direction])[0]
    liked_score = score_candidates(liked_profile, [feedback_direction])[0]
    disliked_score = score_candidates(disliked_profile, [feedback_direction])[0]

    assert liked_score > baseline_score
    assert disliked_score < baseline_score


def test_adjusted_profile_falls_back_when_feedback_cancels_seed() -> None:
    seeds = [np.array([1.0, 0.0], dtype=np.float32)]
    cancelling_dislike = np.array([4.0, 0.0], dtype=np.float32)

    adjusted = build_adjusted_profile(seeds, [], [cancelling_dislike])

    np.testing.assert_array_equal(adjusted, build_style_profile(seeds))
