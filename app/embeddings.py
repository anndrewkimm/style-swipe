"""FashionCLIP image embedding helpers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

if TYPE_CHECKING:
    from transformers import CLIPModel, CLIPProcessor

FASHION_CLIP_MODEL = "patrickjohncyh/fashion-clip"
EMBEDDING_DIM = 512

_model_and_processor: tuple[CLIPModel, CLIPProcessor] | None = None


def get_model() -> tuple[CLIPModel, CLIPProcessor]:
    """Return a lazily loaded FashionCLIP model and processor singleton."""
    global _model_and_processor

    if _model_and_processor is None:
        from transformers import CLIPModel, CLIPProcessor

        model = CLIPModel.from_pretrained(FASHION_CLIP_MODEL)
        model.eval()
        processor = CLIPProcessor.from_pretrained(FASHION_CLIP_MODEL)
        _model_and_processor = (model, processor)

    return _model_and_processor


def embed_image(image_path: Path) -> np.ndarray:
    """Embed an image as an L2-normalized float32 FashionCLIP vector."""
    import torch

    model, processor = get_model()
    with Image.open(image_path) as image:
        inputs = processor(images=image.convert("RGB"), return_tensors="pt")

    with torch.inference_mode():
        feature_output = model.get_image_features(**inputs)

    if hasattr(feature_output, "pooler_output"):
        features = feature_output.pooler_output
    elif isinstance(feature_output, tuple):
        if len(feature_output) < 2:
            raise ValueError("FashionCLIP returned incomplete image features")
        features = feature_output[1]
    else:
        features = feature_output

    vector = features[0].detach().cpu().numpy().astype(np.float32)
    if vector.shape != (EMBEDDING_DIM,):
        raise ValueError(
            f"expected a {EMBEDDING_DIM}-dimension embedding, got {vector.shape}"
        )
    norm = np.linalg.norm(vector)
    if norm == 0:
        raise ValueError("FashionCLIP returned a zero-length embedding")
    return vector / norm


def vector_to_bytes(vec: np.ndarray) -> bytes:
    """Serialize a vector in SQLite-friendly float32 form."""
    return np.asarray(vec, dtype=np.float32).tobytes()


def bytes_to_vector(blob: bytes) -> np.ndarray:
    """Deserialize a float32 vector stored by :func:`vector_to_bytes`."""
    return np.frombuffer(blob, dtype=np.float32).copy()
