---
status: READY
author: claude
created: 2026-07-19
---

# 003 — Streamlit swipe UI

## Goal
A local Streamlit app where the owner swipes through the ranked `/feed` one card at a time — image, brand/title, score, Like/Dislike — completing the end-to-end product loop on top of the spec-002 backend.

## Context
Backend (specs 001–002, DONE) exposes: `GET /feed?limit=` (ranked unswiped candidates; 409 with detail `"no embedded seed items; POST /embed first"` when no embedded seeds), `POST /swipes` `{"item_id", "liked"}` (201; 404 unknown; 409 duplicate), `POST /embed` (`{"embedded": int, "failed": [...]}`), `GET /items?source=`. Item images are local files at `image_path`. Conventions: UI lives in `ui/`, run with `uv run streamlit run ui/app.py`, calls the FastAPI backend over HTTP (assume it's already running — the UI never starts it).

Keep Streamlit code thin: all HTTP logic goes in a plain module (`ui/api_client.py`) so it's unit-testable with a mocked httpx transport; the Streamlit script itself is glue and is not unit-tested.

## Tasks
1. Move `httpx` from the dev group to runtime dependencies; add `streamlit` (runtime).
2. Create `ui/__init__.py` (empty) and `ui/api_client.py`:
   - `DEFAULT_API_URL = "http://127.0.0.1:8000"`; `get_api_url() -> str` reads env `STYLESWIPE_API_URL`, falls back to default.
   - `class NoSeedsError(Exception)` — raised when `/feed` returns 409.
   - `get_feed(client: httpx.Client, limit: int = 20) -> list[dict]` — GET `/feed`; raise `NoSeedsError` on 409; `raise_for_status()` otherwise.
   - `post_swipe(client: httpx.Client, item_id: int, liked: bool) -> dict` — POST `/swipes`; treat 409 (already swiped) as success and return `{}` so a double-click can't crash the UI; `raise_for_status()` otherwise.
   - `post_embed(client: httpx.Client) -> dict` — POST `/embed`, return the JSON summary.
   - All functions take the `httpx.Client` as first arg (tests inject `httpx.Client(transport=httpx.MockTransport(...), base_url=...)`; the app builds a real one with `base_url=get_api_url()`).
3. Create `ui/app.py` (Streamlit):
   - Session state: `queue: list[dict]` of feed items. On empty queue, fetch `get_feed(limit=20)`; when the user exhausts it, refetch. If the refetch is also empty, show "No more candidates — ingest more or come back later."
   - Card view for `queue[0]`: `st.image(image_path)` if the file exists, else a "missing image" caption; brand + title (fall back to the filename); score displayed to 3 decimals.
   - 👍 Like / 👎 Dislike buttons side by side: call `post_swipe`, pop the item, `st.rerun()`.
   - `NoSeedsError` → onboarding screen (no crash): explain the two commands — `uv run python -m app.ingest <folder> --source seed` then the Embed button/`POST /embed`.
   - Backend unreachable (`httpx.ConnectError`) → friendly error telling the user to start the backend (`uv run uvicorn app.main:app --reload`).
   - Sidebar: swipe counts (likes/dislikes via `GET /items` is wrong — there is no swipe-list endpoint; instead track this session's counts in session state), and an **Embed pending items** button calling `post_embed`, showing `embedded`/`failed` counts.
4. Create `tests/test_ui_client.py` using `httpx.MockTransport` (no network, no Streamlit import): feed success, feed 409 → `NoSeedsError`, swipe success, swipe 409 → `{}` without raising, embed summary passthrough, and `get_api_url` env override (monkeypatch `STYLESWIPE_API_URL`).
5. Add the UI run command (`uv run streamlit run ui/app.py`) to the `README.md` quickstart block. Leave the roadmap table alone — Claude maintains it.

## Acceptance criteria
- [ ] `uv run streamlit run ui/app.py` against a running backend shows the top feed card (image, brand/title, score) and Like/Dislike buttons that record a swipe and advance to the next card.
- [ ] With no embedded seed items, the UI shows the onboarding instructions instead of an error trace.
- [ ] With the backend down, the UI shows a "start the backend" message instead of an exception.
- [ ] The sidebar Embed button triggers `POST /embed` and displays the embedded/failed counts.
- [ ] `tests/test_ui_client.py` covers all `api_client` functions with a mocked transport; full suite passes offline; no test imports Streamlit.
- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass.

## Out of scope
- React/Vite frontend (later spec per conventions — do not start it).
- New backend endpoints (e.g., swipe stats, undo). If the UI wants data the API lacks, log it in Implementation notes.
- Swipe-informed re-ranking (spec 004), keyboard shortcuts, animations, image cropping.
- Auth, deployment, mobile layout.

## Implementation notes
*(Codex fills this in: what was built, deviations, questions, follow-ups.)*

## Review feedback
*(Claude fills this in if the review fails: concrete fixes required.)*
