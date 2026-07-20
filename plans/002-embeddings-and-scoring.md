---
status: DONE
author: claude
created: 2026-07-19
---

# 002 — FashionCLIP embeddings + style-profile scoring

## Goal
Items can be embedded with FashionCLIP, a style profile is built from seed items, and a `/feed` endpoint returns candidate items ranked by similarity to that profile. After this spec, the backend can do end-to-end discovery: ingest images → embed → rank → record swipes.

## Context
Spec 001 (DONE) built the scaffold: `Item`/`Swipe` tables in `app/models.py`, engine + `get_session` in `app/db.py`, `/health` + `/items` endpoints in `app/main.py`. Conventions in `docs/CONVENTIONS.md`: FashionCLIP `patrickjohncyh/fashion-clip` via Hugging Face `transformers`, embeddings stored as SQLite blobs, cosine similarity in numpy.

Two constraints shape this spec:
- **The model must never load during tests.** It's a ~600 MB download. Load it lazily; tests monkeypatch `embed_image`.
- **Tests monkeypatch `app.db.engine`** (see `tests/conftest.py`). Any new code must resolve the engine at call time (`db.engine` inside the function), never `from app.db import engine` at module top.

## Tasks
1. Add deps: `transformers`, `torch`, `pillow`, `numpy` (runtime group). CPU torch is fine.
2. Create `app/embeddings.py`:
   - `FASHION_CLIP_MODEL = "patrickjohncyh/fashion-clip"`, `EMBEDDING_DIM = 512`
   - `get_model()` — lazy module-level singleton returning `(CLIPModel, CLIPProcessor)`; nothing imports/loads the model until first call.
   - `embed_image(image_path: Path) -> np.ndarray` — open with PIL, return L2-normalized float32 vector of shape `(512,)`.
   - `vector_to_bytes(vec: np.ndarray) -> bytes` and `bytes_to_vector(blob: bytes) -> np.ndarray` (float32 round-trip).
3. Create `app/recommend.py` (pure numpy, no FastAPI imports):
   - `build_style_profile(seed_vectors: Sequence[np.ndarray]) -> np.ndarray` — L2-normalized mean of seed vectors.
   - `score_candidates(profile: np.ndarray, candidate_vectors: Sequence[np.ndarray]) -> np.ndarray` — cosine similarity per candidate.
4. In `app/main.py`:
   - Add `ItemRead` (all `Item` fields except `embedding`) and switch `GET /items` + `POST /items` response models to it.
   - `POST /embed` → embeds every item with `embedding IS NULL` via `embed_image(Path(item.image_path))`; stores `vector_to_bytes` result. Response: `{"embedded": int, "failed": [{"item_id": int, "error": str}]}`. A missing/unreadable image goes in `failed` and doesn't abort the batch. Re-run with nothing to do → `{"embedded": 0, "failed": []}`.
   - `GET /feed?limit=20` → candidate items (`source == "candidate"`, embedding present, item id not in any `Swipe`), ranked by `score_candidates` against the profile built from all embedded seed items. Response model `FeedItem = ItemRead + score: float`, sorted descending. If no embedded seed items exist → 409 with detail `"no embedded seed items; POST /embed first"`. `limit` capped at 100.
   - `POST /swipes` body `{"item_id": int, "liked": bool}` → 201 with the `Swipe`; 404 if item doesn't exist; 409 if a swipe for that item already exists.
5. Create `app/ingest.py` runnable as `uv run python -m app.ingest <folder> --source seed|candidate`: walks the folder for `.jpg/.jpeg/.png/.webp` (non-recursive), creates an `Item` per file with `image_path` set to the file's path, skips paths already present in the table, prints a count. Core logic in `ingest_folder(folder: Path, source: str) -> int` so tests can call it directly (engine via `db.engine` at call time).
6. Tests — `tests/test_embeddings.py` (bytes round-trip), `tests/test_recommend.py` (profile is normalized mean; identical-to-seed candidate outranks orthogonal one), `tests/test_feed.py` (`/embed` with monkeypatched `embed_image`, `/feed` ordering + swiped-item exclusion + 409-no-seeds, `/swipes` 201/404/409), `tests/test_ingest.py` (tmp folder with fake image files + one `.txt` that's ignored; second run skips existing). All use handcrafted vectors — never the real model.

## Acceptance criteria
- [x] `POST /embed` fills embeddings for all null-embedding items, reports per-item failures without aborting, and is a no-op on re-run.
- [x] `GET /feed` returns only unswiped candidates with embeddings, sorted by cosine similarity to the seed profile with a `score` per item, and 409s when no embedded seeds exist.
- [x] `POST /swipes` returns 201 and persists; 404 for unknown item; 409 for duplicate swipe.
- [x] `GET /items` and `POST /items` responses no longer include `embedding`.
- [x] `python -m app.ingest` creates items from a folder, skips non-images and already-ingested paths.
- [x] `uv run pytest` passes offline — importing `app.main` and running the suite never loads or downloads the model.
- [x] `uv run ruff check .` and `uv run ruff format --check .` pass.

## Out of scope
- Brand weights in the style profile (needs a favorite-brands input — later spec).
- Swipe-informed re-ranking (feed only *excludes* swiped items for now; using likes/dislikes to adjust scores is spec 004+).
- Streamlit UI (spec 003).
- Real shop-feed scraping/ingestion; `app/ingest.py` only handles local folders.
- Vector DB, ANN indexes, embedding caching layers.

## Implementation notes
- Added the requested NumPy, Pillow, Torch, and Transformers runtime dependencies
  and updated the uv lockfile.
- Added lazy FashionCLIP model/processor loading, normalized 512-dimensional image
  embeddings, and float32 SQLite blob serialization. Importing `app.main` does not
  import Torch or Transformers. The embedding adapter supports the installed
  Transformers 5.x `pooler_output` response as well as older direct-tensor output.
- Added pure NumPy style-profile construction and cosine candidate scoring.
- Added public item response schemas without embeddings, batch `/embed`, ranked
  `/feed`, and create-once `/swipes` endpoints with all specified status handling.
- Added non-recursive local image ingestion through both `ingest_folder()` and
  `python -m app.ingest`; it resolves `db.engine` at call time and skips duplicate
  paths and non-image files.
- Added the four requested test modules and expanded item tests. Verification passed
  with Hugging Face/Transformers forced offline: `py -m uv run --offline pytest`
  (16 passed), `ruff check .`, `ruff format --check .`, uv lock validation, lazy
  import inspection, and the ingestion CLI help smoke test.
- Deviations: none. The existing Starlette TestClient still emits its upstream
  `httpx`/`httpx2` deprecation warning; `httpx` remains because spec 001 requires it.

## Review feedback
*(Claude fills this in if the review fails: concrete fixes required.)*
