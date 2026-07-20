"""Tests for non-recursive local image ingestion."""

from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app import db
from app.ingest import ingest_folder
from app.models import Item


def test_ingest_folder_adds_images_and_skips_existing_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    database_path: Path,
    test_engine: Engine,
) -> None:
    image_folder = tmp_path / "images"
    image_folder.mkdir()
    expected_images = [
        image_folder / "jacket.jpg",
        image_folder / "shirt.JPEG",
        image_folder / "trousers.png",
        image_folder / "sweater.webp",
    ]
    for image_path in expected_images:
        image_path.write_bytes(b"fake image data")
    (image_folder / "notes.txt").write_text("not an image")
    nested_folder = image_folder / "nested"
    nested_folder.mkdir()
    (nested_folder / "ignored.jpg").write_bytes(b"fake image data")

    monkeypatch.setattr(db, "DATABASE_PATH", database_path)
    monkeypatch.setattr(db, "engine", test_engine)

    assert ingest_folder(image_folder, "seed") == 4
    assert ingest_folder(image_folder, "seed") == 0

    with Session(test_engine) as session:
        items = session.exec(select(Item)).all()
    assert {item.image_path for item in items} == {
        str(path) for path in expected_images
    }
    assert {item.source for item in items} == {"seed"}
