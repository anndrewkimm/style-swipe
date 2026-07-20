"""Tests for application startup and health reporting."""

from pathlib import Path

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_creates_database(
    client: TestClient,
    database_path: Path,
) -> None:
    assert client is not None
    assert database_path.is_file()
