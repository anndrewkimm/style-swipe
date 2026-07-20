"""Database models for garments and swipe feedback."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Item(SQLModel, table=True):
    """A garment owned by the user or discovered from a shop feed."""

    id: int | None = Field(default=None, primary_key=True)
    source: str
    image_path: str
    brand: str | None = None
    title: str | None = None
    product_url: str | None = None
    embedding: bytes | None = None
    created_at: datetime = Field(default_factory=_utc_now)


class Swipe(SQLModel, table=True):
    """A user's like or dislike of a candidate item."""

    id: int | None = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="item.id")
    liked: bool
    created_at: datetime = Field(default_factory=_utc_now)
