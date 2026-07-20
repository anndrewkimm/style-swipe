# Conventions — single source of truth for all agents

## Stack (v1)

- **Language:** Python 3.12+, managed with `uv`
- **Backend:** FastAPI + SQLite (SQLModel). Runs locally, single user.
- **Embeddings:** FashionCLIP (`patrickjohncyh/fashion-clip` via Hugging Face `transformers`). One vector per garment image, stored in SQLite as a blob; cosine similarity in numpy. No vector DB until item count demands it.
- **Frontend (v1):** Streamlit swipe UI, calling the FastAPI backend. React + Vite comes later as its own spec — do not start it early.
- **Tests:** pytest. **Lint/format:** ruff.

## Commands

- Install deps: `uv sync`
- Run backend: `uv run uvicorn app.main:app --reload`
- Run UI: `uv run streamlit run ui/app.py`
- Tests: `uv run pytest`
- Lint: `uv run ruff check . && uv run ruff format --check .`

## Layout

```
app/          FastAPI backend (main.py, models.py, embeddings.py, recommend.py)
ui/           Streamlit frontend
plans/        numbered specs (the Claude ↔ Codex handoff queue)
docs/         this file + any design notes
data/         images, SQLite db — gitignored, never committed
tests/        pytest suite, mirrors app/ structure
```

## Code style

- Type hints on all public functions; pydantic/SQLModel models for API shapes.
- Small modules over clever abstractions. This is a portfolio repo — readable beats terse.
- No secrets or personal photos in git. Anything user-specific goes in `data/` or `.env` (both gitignored).

## Domain vocabulary

- **Item:** a garment (owned or candidate from a shop feed) with image + embedding.
- **Seed item:** owned/loved garment provided at onboarding; defines the style profile.
- **Style profile:** aggregate of seed embeddings + brand weights.
- **Swipe:** like/dislike on a candidate item; refines ranking on top of the seeded profile.
