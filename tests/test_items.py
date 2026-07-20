"""Tests for item persistence, filtering, and the swipe model."""

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.models import Item, Swipe


def test_create_and_list_items(client: TestClient) -> None:
    seed_payload = {
        "source": "seed",
        "image_path": "closet/jacket.jpg",
        "brand": "Example Brand",
        "title": "Denim jacket",
        "product_url": None,
    }
    candidate_payload = {
        "source": "candidate",
        "image_path": "feed/shirt.jpg",
        "brand": None,
        "title": "Linen shirt",
        "product_url": "https://example.com/linen-shirt",
    }

    seed_response = client.post("/items", json=seed_payload)
    candidate_response = client.post("/items", json=candidate_payload)

    assert seed_response.status_code == 201
    assert candidate_response.status_code == 201
    created_seed = seed_response.json()
    assert created_seed["id"] == 1
    assert created_seed["embedding"] is None
    assert {key: created_seed[key] for key in seed_payload} == seed_payload

    all_response = client.get("/items")
    assert all_response.status_code == 200
    assert [item["source"] for item in all_response.json()] == [
        "seed",
        "candidate",
    ]

    seed_only_response = client.get("/items", params={"source": "seed"})
    assert seed_only_response.status_code == 200
    assert [item["id"] for item in seed_only_response.json()] == [1]


def test_create_item_ignores_embedding_input(client: TestClient) -> None:
    response = client.post(
        "/items",
        json={
            "source": "seed",
            "image_path": "closet/sweater.jpg",
            "embedding": "not-accepted-yet",
        },
    )

    assert response.status_code == 201
    assert response.json()["embedding"] is None


def test_swipe_records_feedback_for_an_item(
    client: TestClient,
    test_engine: Engine,
) -> None:
    create_response = client.post(
        "/items",
        json={"source": "candidate", "image_path": "feed/trousers.jpg"},
    )
    item_id = create_response.json()["id"]

    with Session(test_engine) as session:
        swipe = Swipe(item_id=item_id, liked=True)
        session.add(swipe)
        session.commit()
        session.refresh(swipe)

        assert swipe.id == 1
        assert swipe.item_id == item_id
        assert swipe.liked is True

        item = session.get(Item, item_id)
        assert item is not None
