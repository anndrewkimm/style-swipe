"""FastAPI application and initial item endpoints."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlmodel import Session, SQLModel, select

from app.db import get_session, init_db
from app.embeddings import bytes_to_vector, embed_image, vector_to_bytes
from app.models import Item, Swipe
from app.recommend import (
    build_adjusted_profile,
    build_style_profile,
    score_candidates,
)


class ItemCreate(SQLModel):
    """Fields accepted when creating an item before embedding generation."""

    source: Literal["seed", "candidate"]
    image_path: str
    brand: str | None = None
    title: str | None = None
    product_url: str | None = None


class ItemRead(SQLModel):
    """Public item fields, excluding the stored embedding."""

    id: int
    source: str
    image_path: str
    brand: str | None
    title: str | None
    product_url: str | None
    created_at: datetime


class FeedItem(ItemRead):
    """A candidate item paired with its style-profile score."""

    score: float


class EmbedFailure(SQLModel):
    """An item that could not be embedded."""

    item_id: int
    error: str


class EmbedResult(SQLModel):
    """Summary of a batch embedding attempt."""

    embedded: int
    failed: list[EmbedFailure]


class SwipeCreate(SQLModel):
    """Feedback accepted for a candidate item."""

    item_id: int
    liked: bool


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize persistent storage before accepting requests."""
    init_db()
    yield


app = FastAPI(title="StyleSwipe", lifespan=lifespan)

SessionDependency = Annotated[Session, Depends(get_session)]
SourceFilter = Annotated[
    Literal["seed", "candidate"] | None,
    Query(),
]
FeedLimit = Annotated[int, Query(ge=1, le=100)]
FeedProfile = Annotated[Literal["seed", "personalized"], Query()]


@app.get("/health")
def health() -> dict[str, str]:
    """Report whether the backend is running."""
    return {"status": "ok"}


@app.get("/items", response_model=list[ItemRead])
def list_items(
    session: SessionDependency,
    source: SourceFilter = None,
) -> list[Item]:
    """List all items, optionally restricted to one source."""
    statement = select(Item)
    if source is not None:
        statement = statement.where(Item.source == source)
    return list(session.exec(statement).all())


@app.post("/items", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    item: ItemCreate,
    session: SessionDependency,
) -> Item:
    """Persist an item without an embedding."""
    db_item = Item.model_validate(item)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


@app.post("/embed", response_model=EmbedResult)
def embed_pending_items(session: SessionDependency) -> EmbedResult:
    """Embed every item that does not already have a stored vector."""
    items = session.exec(select(Item).where(Item.embedding.is_(None))).all()
    failures: list[EmbedFailure] = []
    embedded = 0

    for item in items:
        try:
            vector = embed_image(Path(item.image_path))
            item.embedding = vector_to_bytes(vector)
        except Exception as exc:
            failures.append(EmbedFailure(item_id=item.id, error=str(exc)))
            continue

        session.add(item)
        embedded += 1

    session.commit()
    return EmbedResult(embedded=embedded, failed=failures)


@app.get("/feed", response_model=list[FeedItem])
def get_feed(
    session: SessionDependency,
    limit: FeedLimit = 20,
    profile: FeedProfile = "personalized",
) -> list[FeedItem]:
    """Rank embedded, unswiped candidates against the seed style profile."""
    seeds = session.exec(
        select(Item).where(
            Item.source == "seed",
            Item.embedding.is_not(None),
        )
    ).all()
    if not seeds:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="no embedded seed items; POST /embed first",
        )

    seed_vectors = [bytes_to_vector(item.embedding) for item in seeds]
    swipe_rows = session.exec(
        select(Swipe, Item).join(Item, Swipe.item_id == Item.id)
    ).all()
    swiped_item_ids = {swipe.item_id for swipe, _item in swipe_rows}

    if profile == "personalized":
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
        ranking_profile = build_adjusted_profile(
            seed_vectors,
            liked_vectors,
            disliked_vectors,
        )
    else:
        ranking_profile = build_style_profile(seed_vectors)

    candidates = session.exec(
        select(Item).where(
            Item.source == "candidate",
            Item.embedding.is_not(None),
        )
    ).all()
    candidates = [item for item in candidates if item.id not in swiped_item_ids]
    candidate_vectors = [bytes_to_vector(item.embedding) for item in candidates]
    scores = score_candidates(ranking_profile, candidate_vectors)

    ranked = sorted(
        zip(candidates, scores, strict=True),
        key=lambda pair: float(pair[1]),
        reverse=True,
    )
    return [
        FeedItem(
            **item.model_dump(exclude={"embedding"}),
            score=float(score),
        )
        for item, score in ranked[:limit]
    ]


@app.post("/swipes", response_model=Swipe, status_code=status.HTTP_201_CREATED)
def create_swipe(
    swipe: SwipeCreate,
    session: SessionDependency,
) -> Swipe:
    """Persist one like or dislike for an existing item."""
    if session.get(Item, swipe.item_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="item not found",
        )

    existing_swipe = session.exec(
        select(Swipe).where(Swipe.item_id == swipe.item_id)
    ).first()
    if existing_swipe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="swipe already exists for this item",
        )

    db_swipe = Swipe.model_validate(swipe)
    session.add(db_swipe)
    session.commit()
    session.refresh(db_swipe)
    return db_swipe
