"""Shared fixtures that isolate API tests from the user's database."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import create_engine

from app import db
from app.main import app


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    """Return a fresh database path outside the application's data directory."""
    return tmp_path / "styleswipe-test.db"


@pytest.fixture
def test_engine(database_path: Path) -> Generator[Engine, None, None]:
    """Provide the temporary SQLite engine used by one test."""
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    yield engine
    engine.dispose()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    database_path: Path,
    test_engine: Engine,
) -> Generator[TestClient, None, None]:
    """Run the app against the temporary database for one test."""
    monkeypatch.setattr(db, "DATABASE_PATH", database_path)
    monkeypatch.setattr(db, "engine", test_engine)

    with TestClient(app) as test_client:
        yield test_client
