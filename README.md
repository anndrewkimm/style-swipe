# StyleSwipe

Personal clothing-discovery assistant: Tinder-style swiping on shopping items, ranked against a style profile seeded from my existing wardrobe and favorite brands — no cold-start training.

Swiping refines the ranking over time, giving the project a measurable ML story: seed profile → candidate scoring → feedback loop.

## Stack

- **Backend:** FastAPI + SQLite (SQLModel), Python 3.12+ managed with `uv`
- **Embeddings:** FashionCLIP (`patrickjohncyh/fashion-clip`), one vector per garment image, cosine similarity in numpy
- **Frontend (v1):** Streamlit swipe UI
- **Tooling:** pytest, ruff

## Quickstart

```sh
uv sync                                # install deps
uv run uvicorn app.main:app --reload   # start the backend
uv run streamlit run ui/app.py         # start the swipe UI
uv run pytest                          # run tests
uv run ruff check .                    # lint
```

## Roadmap

| Spec | Feature | Status |
|------|---------|--------|
| [001](plans/001-project-scaffold.md) | Backend skeleton, data models, test rig | ✅ Done |
| [002](plans/002-embeddings-and-scoring.md) | FashionCLIP embeddings + style-profile scoring | ✅ Done |
| [003](plans/003-streamlit-swipe-ui.md) | Streamlit swipe UI | ✅ Done |
| [004](plans/004-swipe-informed-reranking.md) | Swipe-informed re-ranking + offline eval | 🔨 Queued |

## How this repo is built

Two AI coding agents work this repo with a strict division of labor, coordinated through numbered spec files in [plans/](plans/):

- **Claude Code** — planner and reviewer: writes specs, reviews diffs against acceptance criteria
- **Codex** — implementer: picks up `READY` specs and builds them
- **Me** — product owner: sets direction, relays handoffs, makes final calls

Conventions for both agents live in [docs/CONVENTIONS.md](docs/CONVENTIONS.md).
