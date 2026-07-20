"""Pure NumPy style-profile construction and candidate scoring."""

from collections.abc import Sequence

import numpy as np


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
