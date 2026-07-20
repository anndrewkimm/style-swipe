"""Tests for embedding serialization that do not load FashionCLIP."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from PIL import Image

from app import embeddings
from app.embeddings import EMBEDDING_DIM, bytes_to_vector, vector_to_bytes


def test_vector_bytes_round_trip_uses_float32() -> None:
    vector = np.array([0.25, -1.5, 3.0], dtype=np.float64)

    restored = bytes_to_vector(vector_to_bytes(vector))

    assert restored.dtype == np.float32
    np.testing.assert_array_equal(restored, vector.astype(np.float32))


def test_embed_image_normalizes_transformers_output_without_loading_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_path = tmp_path / "garment.png"
    Image.new("RGB", (2, 2), color="blue").save(image_path)

    class FakeProcessor:
        def __call__(self, **_kwargs):
            return {"pixel_values": torch.zeros((1, 3, 2, 2))}

    class FakeModel:
        def get_image_features(self, **_kwargs):
            features = torch.arange(1, EMBEDDING_DIM + 1, dtype=torch.float32)
            return SimpleNamespace(pooler_output=features.unsqueeze(0))

    monkeypatch.setattr(
        embeddings,
        "get_model",
        lambda: (FakeModel(), FakeProcessor()),
    )

    vector = embeddings.embed_image(image_path)

    assert vector.shape == (EMBEDDING_DIM,)
    assert vector.dtype == np.float32
    assert np.linalg.norm(vector) == pytest.approx(1.0)
