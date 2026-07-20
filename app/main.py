"""FastAPI application and initial item endpoints."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Query, status
from sqlmodel import Session, SQLModel, select

from app.db import get_session, init_db
from app.models import Item


class ItemCreate(SQLModel):
    """Fields accepted when creating an item before embedding generation."""

    source: Literal["seed", "candidate"]
    image_path: str
    brand: str | None = None
    title: str | None = None
    product_url: str | None = None


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


@app.get("/health")
def health() -> dict[str, str]:
    """Report whether the backend is running."""
    return {"status": "ok"}


@app.get("/items", response_model=list[Item])
def list_items(
    session: SessionDependency,
    source: SourceFilter = None,
) -> list[Item]:
    """List all items, optionally restricted to one source."""
    statement = select(Item)
    if source is not None:
        statement = statement.where(Item.source == source)
    return list(session.exec(statement).all())


@app.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED)
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
