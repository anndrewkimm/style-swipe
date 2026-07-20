"""Offline evaluation of seed-only and personalized style profiles."""

from collections.abc import Sequence

import numpy as np
from sqlmodel import Session, select

from app import db
from app.embeddings import bytes_to_vector
from app.models import Item, Swipe
from app.recommend import (
    ALPHA,
    BETA,
    build_adjusted_profile,
    build_style_profile,
    score_candidates,
)


def holdout_rank(
    profile: np.ndarray,
    held_out: np.ndarray,
    negatives: Sequence[np.ndarray],
) -> int:
    """Return the held-out vector's 1-based rank, placing ties behind negatives."""
    held_out_score = float(score_candidates(profile, [held_out])[0])
    negative_scores = score_candidates(profile, negatives)
    return 1 + int(np.count_nonzero(negative_scores >= held_out_score))


def _summarize_ranks(ranks: Sequence[int]) -> dict[str, float]:
    if not ranks:
        return {"mean_rank": 0.0, "mrr": 0.0}
    return {
        "mean_rank": float(np.mean(ranks)),
        "mrr": float(np.mean([1.0 / rank for rank in ranks])),
    }


def evaluate_profiles(
    seed_vectors: Sequence[np.ndarray],
    liked_vectors: Sequence[np.ndarray],
    disliked_vectors: Sequence[np.ndarray],
    alpha: float = ALPHA,
    beta: float = BETA,
) -> dict:
    """Compare seed and leave-one-out personalized ranks for liked vectors."""
    baseline_profile = build_style_profile(seed_vectors)
    baseline_ranks: list[int] = []
    personalized_ranks: list[int] = []

    for held_out_index, held_out in enumerate(liked_vectors):
        remaining_likes = [
            vector
            for index, vector in enumerate(liked_vectors)
            if index != held_out_index
        ]
        personalized_profile = build_adjusted_profile(
            seed_vectors,
            remaining_likes,
            disliked_vectors,
            alpha=alpha,
            beta=beta,
        )
        baseline_ranks.append(
            holdout_rank(baseline_profile, held_out, disliked_vectors)
        )
        personalized_ranks.append(
            holdout_rank(personalized_profile, held_out, disliked_vectors)
        )

    return {
        "n_evaluated": len(liked_vectors),
        "baseline": _summarize_ranks(baseline_ranks),
        "personalized": _summarize_ranks(personalized_ranks),
    }


def load_evaluation_vectors() -> tuple[
    list[np.ndarray],
    list[np.ndarray],
    list[np.ndarray],
]:
    """Load embedded seeds and swipe vectors from the configured database."""
    db.init_db()
    with Session(db.engine) as session:
        seed_items = session.exec(
            select(Item).where(
                Item.source == "seed",
                Item.embedding.is_not(None),
            )
        ).all()
        swipe_rows = session.exec(
            select(Swipe, Item).join(Item, Swipe.item_id == Item.id)
        ).all()

    seed_vectors = [bytes_to_vector(item.embedding) for item in seed_items]
    liked_vectors: list[np.ndarray] = []
    disliked_vectors: list[np.ndarray] = []
    for swipe, item in swipe_rows:
        if item.embedding is None:
            continue
        vector = bytes_to_vector(item.embedding)
        if swipe.liked:
            liked_vectors.append(vector)
        else:
            disliked_vectors.append(vector)
    return seed_vectors, liked_vectors, disliked_vectors


def main() -> None:
    """Evaluate profiles from the local database and print summary metrics."""
    seed_vectors, liked_vectors, disliked_vectors = load_evaluation_vectors()
    if not seed_vectors or len(liked_vectors) < 2 or not disliked_vectors:
        print(
            "not enough swipe data: need an embedded seed, "
            "2 liked, and 1 disliked embedded swipes"
        )
        return

    results = evaluate_profiles(seed_vectors, liked_vectors, disliked_vectors)
    baseline = results["baseline"]
    personalized = results["personalized"]
    print(f"evaluated liked swipes: {results['n_evaluated']}")
    print(f"baseline: mean rank={baseline['mean_rank']:.3f}, MRR={baseline['mrr']:.3f}")
    print(
        f"personalized: mean rank={personalized['mean_rank']:.3f}, "
        f"MRR={personalized['mrr']:.3f}"
    )


if __name__ == "__main__":
    main()
