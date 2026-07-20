---
status: DONE
author: claude
created: 2026-07-19
---

# 001 — Project scaffold: backend skeleton, data models, test rig

## Goal
A runnable FastAPI backend with the core data models and an empty-but-wired test/lint setup, so every later spec builds on a working skeleton.

## Context
Fresh repo. Stack and layout are defined in `docs/CONVENTIONS.md` — follow it exactly. No embedding logic yet (that's spec 002); this spec is pure scaffolding.

## Tasks
1. Initialize the project with `uv init` (Python 3.12); add deps: `fastapi`, `uvicorn[standard]`, `sqlmodel`, `pytest`, `httpx` (test client), `ruff` (dev).
2. Create `app/models.py` with SQLModel tables:
   - `Item`: `id: int PK`, `source: str` ("seed" | "candidate"), `image_path: str`, `brand: str | None`, `title: str | None`, `product_url: str | None`, `embedding: bytes | None`, `created_at: datetime`
   - `Swipe`: `id: int PK`, `item_id: int FK -> Item`, `liked: bool`, `created_at: datetime`
3. Create `app/db.py`: engine pointing at `data/styleswipe.db`, `init_db()` creating tables, session dependency for FastAPI.
4. Create `app/main.py`: FastAPI app with `GET /health` → `{"status": "ok"}`, and startup hook calling `init_db()`.
5. Add `GET /items` (list, optional `?source=` filter) and `POST /items` (create without embedding) endpoints.
6. Create `tests/test_health.py` and `tests/test_items.py` using httpx TestClient with a temp-file SQLite db (not the real `data/` db).
7. Add `ruff` config in `pyproject.toml` and make the repo pass lint clean.

## Acceptance criteria
- [x] `uv run uvicorn app.main:app` starts; `GET /health` returns 200 `{"status": "ok"}`.
- [x] `POST /items` then `GET /items` round-trips an item; `?source=seed` filters correctly.
- [x] Database file is created under `data/` on startup, and `data/` stays gitignored.
- [x] `uv run pytest` passes; tests never touch `data/styleswipe.db`.
- [x] `uv run ruff check .` passes with zero errors.

## Out of scope
- Embeddings, FashionCLIP, or any ML dependency (spec 002).
- Streamlit UI (spec 003).
- Auth of any kind — single local user.
- Docker, deployment, CI.

## Implementation notes
- Initialized the Python 3.12+ `uv` project and added the requested runtime and
  development dependencies, lockfile, Ruff configuration, and pytest discovery
  configuration.
- Added the `Item` and `Swipe` SQLModel tables, SQLite engine/session wiring,
  startup table creation under `data/styleswipe.db`, health endpoint, and item
  create/list endpoints with source filtering.
- Added five tests covering health, startup database creation, item round trips,
  source filtering, embedding omission, and Swipe persistence. Tests monkeypatch
  both the engine and database path to a per-test temporary SQLite file.
- Verification passed through uv's module entrypoint: `py -m uv run pytest`
  (5 passed), Ruff check/format, and an actual Uvicorn `/health` smoke test.
  The module form was used because this agent shell does not include Python's
  user Scripts directory on `PATH`; it invokes the same installed uv executable.
- Deviations: none. The current Starlette TestClient emits a deprecation warning
  recommending `httpx2`; `httpx` remains installed because this spec explicitly
  requires it, and the suite passes.

## Review feedback
*(Claude fills this in if review fails.)*
