"""Tests for the Streamlit UI's HTTP client without importing Streamlit."""

import httpx
import pytest

from ui.api_client import (
    DEFAULT_API_URL,
    NoSeedsError,
    get_api_url,
    get_feed,
    post_embed,
    post_swipe,
)


def test_get_feed_returns_ranked_items() -> None:
    feed = [{"id": 7, "image_path": "feed/jacket.jpg", "score": 0.875}]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/feed"
        assert request.url.params["limit"] == "5"
        return httpx.Response(200, json=feed)

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test",
    ) as client:
        assert get_feed(client, limit=5) == feed


def test_get_feed_raises_no_seeds_error_for_conflict() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={"detail": "no embedded seed items; POST /embed first"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test",
    ) as client:
        with pytest.raises(NoSeedsError, match="no embedded seed items"):
            get_feed(client)


def test_post_swipe_returns_created_swipe() -> None:
    created_swipe = {"id": 3, "item_id": 8, "liked": True}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/swipes"
        assert request.method == "POST"
        assert request.content == b'{"item_id":8,"liked":true}'
        return httpx.Response(201, json=created_swipe)

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test",
    ) as client:
        assert post_swipe(client, item_id=8, liked=True) == created_swipe


def test_post_swipe_treats_duplicate_as_success() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": "already swiped"})

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test",
    ) as client:
        assert post_swipe(client, item_id=8, liked=False) == {}


def test_post_embed_returns_summary() -> None:
    summary = {
        "embedded": 2,
        "failed": [{"item_id": 9, "error": "missing image"}],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/embed"
        assert request.method == "POST"
        return httpx.Response(200, json=summary)

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test",
    ) as client:
        assert post_embed(client) == summary


def test_get_api_url_uses_environment_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("STYLESWIPE_API_URL", raising=False)
    assert get_api_url() == DEFAULT_API_URL

    monkeypatch.setenv("STYLESWIPE_API_URL", "http://backend.internal:9000")
    assert get_api_url() == "http://backend.internal:9000"
