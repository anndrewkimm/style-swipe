"""Tests for batch embedding, ranked feeds, and swipe endpoints."""

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app import main
from app.embeddings import vector_to_bytes
from app.models import Item, Swipe


def _create_item(client: TestClient, source: str, image_path: str) -> dict:
    response = client.post(
        "/items",
        json={"source": source, "image_path": image_path},
    )
    assert response.status_code == 201
    return response.json()


def test_embed_fills_pending_items_and_is_noop_on_rerun(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    test_engine: Engine,
) -> None:
    seed = _create_item(client, "seed", "closet/seed.jpg")
    candidate = _create_item(client, "candidate", "feed/candidate.jpg")
    embedded_paths: list[Path] = []

    def fake_embed_image(image_path: Path) -> np.ndarray:
        embedded_paths.append(image_path)
        return np.array([1.0, 0.0], dtype=np.float32)

    monkeypatch.setattr(main, "embed_image", fake_embed_image)

    response = client.post("/embed")

    assert response.status_code == 200
    assert response.json() == {"embedded": 2, "failed": []}
    assert embedded_paths == [Path("closet/seed.jpg"), Path("feed/candidate.jpg")]
    with Session(test_engine) as session:
        assert session.get(Item, seed["id"]).embedding is not None
        assert session.get(Item, candidate["id"]).embedding is not None

    rerun_response = client.post("/embed")
    assert rerun_response.status_code == 200
    assert rerun_response.json() == {"embedded": 0, "failed": []}


def test_embed_reports_failure_without_aborting_batch(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    test_engine: Engine,
) -> None:
    missing = _create_item(client, "seed", "closet/missing.jpg")
    valid = _create_item(client, "candidate", "feed/valid.jpg")

    def fake_embed_image(image_path: Path) -> np.ndarray:
        if image_path.name == "missing.jpg":
            raise FileNotFoundError("image not found")
        return np.array([0.0, 1.0], dtype=np.float32)

    monkeypatch.setattr(main, "embed_image", fake_embed_image)

    response = client.post("/embed")

    assert response.status_code == 200
    assert response.json() == {
        "embedded": 1,
        "failed": [{"item_id": missing["id"], "error": "image not found"}],
    }
    with Session(test_engine) as session:
        assert session.get(Item, missing["id"]).embedding is None
        assert session.get(Item, valid["id"]).embedding is not None


def test_feed_orders_candidates_and_excludes_swiped_items(
    client: TestClient,
    test_engine: Engine,
) -> None:
    seed = _create_item(client, "seed", "closet/seed.jpg")
    high = _create_item(client, "candidate", "feed/high.jpg")
    swiped = _create_item(client, "candidate", "feed/swiped.jpg")
    low = _create_item(client, "candidate", "feed/low.jpg")
    _create_item(client, "candidate", "feed/unembedded.jpg")

    vectors = {
        seed["id"]: np.array([1.0, 0.0], dtype=np.float32),
        high["id"]: np.array([1.0, 0.0], dtype=np.float32),
        swiped["id"]: np.array([1.0, 1.0], dtype=np.float32),
        low["id"]: np.array([0.0, 1.0], dtype=np.float32),
    }
    with Session(test_engine) as session:
        for item_id, vector in vectors.items():
            item = session.get(Item, item_id)
            item.embedding = vector_to_bytes(vector)
            session.add(item)
        session.commit()

    swipe_response = client.post(
        "/swipes",
        json={"item_id": swiped["id"], "liked": False},
    )
    assert swipe_response.status_code == 201

    response = client.get("/feed")

    assert response.status_code == 200
    feed = response.json()
    assert [item["id"] for item in feed] == [high["id"], low["id"]]
    assert feed[0]["score"] == pytest.approx(1.0)
    assert feed[1]["score"] == pytest.approx(0.0)
    assert all("embedding" not in item for item in feed)


def test_feed_requires_embedded_seed(client: TestClient) -> None:
    _create_item(client, "candidate", "feed/candidate.jpg")

    response = client.get("/feed")

    assert response.status_code == 409
    assert response.json() == {"detail": "no embedded seed items; POST /embed first"}


def test_feed_limit_is_capped_at_100(client: TestClient) -> None:
    response = client.get("/feed", params={"limit": 101})

    assert response.status_code == 422


def test_swipes_create_and_reject_missing_or_duplicate_items(
    client: TestClient,
    test_engine: Engine,
) -> None:
    candidate = _create_item(client, "candidate", "feed/candidate.jpg")
    payload = {"item_id": candidate["id"], "liked": True}

    response = client.post("/swipes", json=payload)

    assert response.status_code == 201
    assert response.json()["item_id"] == candidate["id"]
    assert response.json()["liked"] is True
    with Session(test_engine) as session:
        assert session.exec(select(Swipe)).one().item_id == candidate["id"]

    missing_response = client.post(
        "/swipes",
        json={"item_id": 9999, "liked": False},
    )
    assert missing_response.status_code == 404

    duplicate_response = client.post("/swipes", json=payload)
    assert duplicate_response.status_code == 409
