"""Tests for offline profile evaluation and database loading."""

from pathlib import Path

import numpy as np
import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app import db, evaluate
from app.embeddings import vector_to_bytes
from app.evaluate import evaluate_profiles, holdout_rank, load_evaluation_vectors
from app.models import Item, Swipe


def test_holdout_rank_orders_candidates_and_puts_ties_last() -> None:
    profile = np.array([1.0, 0.0], dtype=np.float32)

    rank = holdout_rank(
        profile,
        np.array([0.8, 0.6], dtype=np.float32),
        [
            np.array([1.0, 0.0], dtype=np.float32),
            np.array([0.0, 1.0], dtype=np.float32),
        ],
    )
    tied_rank = holdout_rank(
        profile,
        np.array([1.0, 0.0], dtype=np.float32),
        [np.array([1.0, 0.0], dtype=np.float32)],
    )

    assert rank == 2
    assert tied_rank == 2


def test_personalized_profile_beats_baseline_mrr() -> None:
    result = evaluate_profiles(
        seed_vectors=[np.array([1.0, 0.0], dtype=np.float32)],
        liked_vectors=[
            np.array([0.5, 0.866], dtype=np.float32),
            np.array([0.5, 0.866], dtype=np.float32),
        ],
        disliked_vectors=[np.array([0.866, -0.5], dtype=np.float32)],
    )

    assert result["n_evaluated"] == 2
    assert result["personalized"]["mrr"] > result["baseline"]["mrr"]
    assert result["personalized"]["mean_rank"] < result["baseline"]["mean_rank"]


def test_evaluator_ignores_unembedded_swipe_and_reports_not_enough_data(
    monkeypatch: pytest.MonkeyPatch,
    database_path: Path,
    test_engine: Engine,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(db, "DATABASE_PATH", database_path)
    monkeypatch.setattr(db, "engine", test_engine)
    db.init_db()

    with Session(test_engine) as session:
        seed = Item(
            source="seed",
            image_path="closet/seed.jpg",
            embedding=vector_to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
        )
        liked = Item(
            source="candidate",
            image_path="feed/liked.jpg",
            embedding=vector_to_bytes(np.array([0.5, 0.866], dtype=np.float32)),
        )
        unembedded_like = Item(
            source="candidate",
            image_path="feed/unembedded.jpg",
        )
        disliked = Item(
            source="candidate",
            image_path="feed/disliked.jpg",
            embedding=vector_to_bytes(np.array([0.866, -0.5], dtype=np.float32)),
        )
        session.add_all([seed, liked, unembedded_like, disliked])
        session.commit()
        for item in (liked, unembedded_like, disliked):
            session.refresh(item)
        session.add_all(
            [
                Swipe(item_id=liked.id, liked=True),
                Swipe(item_id=unembedded_like.id, liked=True),
                Swipe(item_id=disliked.id, liked=False),
            ]
        )
        session.commit()

    seeds, likes, dislikes = load_evaluation_vectors()
    assert len(seeds) == 1
    assert len(likes) == 1
    assert len(dislikes) == 1

    evaluate.main()

    assert "not enough swipe data" in capsys.readouterr().out


def test_evaluator_main_prints_both_profile_metrics(
    monkeypatch: pytest.MonkeyPatch,
    database_path: Path,
    test_engine: Engine,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(db, "DATABASE_PATH", database_path)
    monkeypatch.setattr(db, "engine", test_engine)
    db.init_db()

    vectors = [
        ("seed", True, np.array([1.0, 0.0], dtype=np.float32)),
        ("candidate", True, np.array([0.5, 0.866], dtype=np.float32)),
        ("candidate", True, np.array([0.5, 0.866], dtype=np.float32)),
        ("candidate", False, np.array([0.866, -0.5], dtype=np.float32)),
    ]
    with Session(test_engine) as session:
        items = [
            Item(
                source=source,
                image_path=f"item-{index}.jpg",
                embedding=vector_to_bytes(vector),
            )
            for index, (source, _liked, vector) in enumerate(vectors)
        ]
        session.add_all(items)
        session.commit()
        for item in items:
            session.refresh(item)
        session.add_all(
            [
                Swipe(item_id=item.id, liked=liked)
                for item, (_source, liked, _vector) in zip(
                    items[1:],
                    vectors[1:],
                    strict=True,
                )
            ]
        )
        session.commit()

    evaluate.main()

    output = capsys.readouterr().out
    assert "baseline: mean rank=" in output
    assert "personalized: mean rank=" in output
    assert output.count("MRR=") == 2
