"""Pure NumPy style-profile construction and candidate scoring."""

from collections.abc import Sequence

import numpy as np

ALPHA = 0.5
BETA = 0.25


def _normalize(vector: np.ndarray) -> np.ndarray:
    normalized_input = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(normalized_input)
    if norm == 0:
        raise ValueError("cannot normalize a zero-length vector")
    return normalized_input / norm


def build_style_profile(seed_vectors: Sequence[np.ndarray]) -> np.ndarray:
    """Build an L2-normalized mean vector from embedded seed items."""
    if not seed_vectors:
        raise ValueError("at least one seed vector is required")

    mean_vector = np.mean(
        np.stack([np.asarray(vector, dtype=np.float32) for vector in seed_vectors]),
        axis=0,
        dtype=np.float32,
    )
    return _normalize(mean_vector)


def build_adjusted_profile(
    seed_vectors: Sequence[np.ndarray],
    liked_vectors: Sequence[np.ndarray],
    disliked_vectors: Sequence[np.ndarray],
    alpha: float = ALPHA,
    beta: float = BETA,
) -> np.ndarray:
    """Adjust the seed profile toward likes and away from dislikes."""
    seed_profile = build_style_profile(seed_vectors)
    if not liked_vectors and not disliked_vectors:
        return seed_profile

    adjusted_profile = seed_profile.copy()

    if liked_vectors:
        liked_mean = np.mean(
            np.stack(
                [np.asarray(vector, dtype=np.float32) for vector in liked_vectors]
            ),
            axis=0,
            dtype=np.float32,
        )
        adjusted_profile += np.float32(alpha) * liked_mean

    if disliked_vectors:
        disliked_mean = np.mean(
            np.stack(
                [np.asarray(vector, dtype=np.float32) for vector in disliked_vectors]
            ),
            axis=0,
            dtype=np.float32,
        )
        adjusted_profile -= np.float32(beta) * disliked_mean

    if np.linalg.norm(adjusted_profile) == 0:
        return seed_profile
    return _normalize(adjusted_profile)


def score_candidates(
    profile: np.ndarray,
    candidate_vectors: Sequence[np.ndarray],
) -> np.ndarray:
    """Return the cosine similarity between a profile and each candidate."""
    if not candidate_vectors:
        return np.array([], dtype=np.float32)

    normalized_profile = _normalize(profile)
    candidates = np.stack(
        [_normalize(vector) for vector in candidate_vectors],
    )
    return np.asarray(candidates @ normalized_profile, dtype=np.float32)
