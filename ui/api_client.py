"""HTTP client helpers for the Streamlit interface."""

import os

import httpx

DEFAULT_API_URL = "http://127.0.0.1:8000"


class NoSeedsError(Exception):
    """Raised when the backend cannot build a feed without embedded seeds."""


def get_api_url() -> str:
    """Return the configured backend URL or the local default."""
    return os.getenv("STYLESWIPE_API_URL", DEFAULT_API_URL)


def get_feed(client: httpx.Client, limit: int = 20) -> list[dict]:
    """Fetch a ranked batch of candidate items."""
    response = client.get("/feed", params={"limit": limit})
    if response.status_code == 409:
        detail = response.json().get(
            "detail",
            "no embedded seed items; POST /embed first",
        )
        raise NoSeedsError(detail)
    response.raise_for_status()
    return response.json()


def post_swipe(client: httpx.Client, item_id: int, liked: bool) -> dict:
    """Record swipe feedback, treating an existing swipe as success."""
    response = client.post(
        "/swipes",
        json={"item_id": item_id, "liked": liked},
    )
    if response.status_code == 409:
        return {}
    response.raise_for_status()
    return response.json()


def post_embed(client: httpx.Client) -> dict:
    """Embed all pending backend items and return the batch summary."""
    response = client.post("/embed")
    response.raise_for_status()
    return response.json()
