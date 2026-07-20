---
status: READY
author: claude
created: 2026-07-19
---

# 006 — Automatic candidate discovery via Google Shopping (SerpAPI)

## Goal
The feed refills itself: a "Discover" action searches Google Shopping (via SerpAPI) for a query like "streetwear hoodie", pulls real products — image, title, store, buy link — from retailers like Nordstrom/SSENSE/Farfetch, and adds them as candidate items. No more manual-only sourcing.

## Context
Builds on spec 005's importer plumbing (`download_image`, `ProductImportError`, `IMPORT_DIR`) — implement 005 first. SerpAPI (`https://serpapi.com/search.json`) with `engine=google_shopping` returns JSON whose `shopping_results` array has per-product: `title`, `source` (store name, e.g. "Nordstrom"), `product_link` (fall back to `link`), `thumbnail` (image URL — small, but FashionCLIP resizes to 224px anyway, so thumbnails are fine). Auth is an `api_key` query param.

The key is user-specific: `SERPAPI_KEY`, loaded from `.env` (gitignored per conventions). The suite must never require a real key or the network.

## Tasks
1. Add `python-dotenv` (runtime). Create `app/config.py`: call `load_dotenv()` once at import; `get_serpapi_key() -> str | None` returning `os.getenv("SERPAPI_KEY")`.
2. Create `app/discovery.py`:
   - `@dataclass ProductResult`: `title: str`, `store: str | None`, `product_url: str`, `image_url: str`.
   - `search_products(client: httpx.Client, api_key: str, query: str, limit: int = 40, stores: Sequence[str] | None = None) -> list[ProductResult]` — GET SerpAPI google_shopping; skip results missing `thumbnail` or a product link; when `stores` is given, keep only results whose `source` contains any entry (case-insensitive substring, so "nordstrom" matches "Nordstrom Rack" too); non-200 or SerpAPI `"error"` key in body → raise `ProductImportError` with the message.
3. In `app/main.py` add `POST /discover`:
   - Body `DiscoverRequest`: `{"query": str, "max_results": int = 20, "stores": list[str] | None = None}` (`max_results` 1–40; `stores` passed through to `search_products`).
   - No `SERPAPI_KEY` configured → 503 with detail `"SERPAPI_KEY not set; add it to .env (see README)"`.
   - For each `ProductResult`: skip if an item with that `product_url` exists (dedupe); else `download_image` the thumbnail to `IMPORT_DIR` and create a candidate `Item` (`brand=store`, `title`, `product_url`, `image_path`). A single failed download skips that product, doesn't abort the batch.
   - Response `DiscoverResult`: `{"added": int, "skipped": int, "failed": int}`. `ProductImportError`/`httpx.HTTPError` from the search itself → 502 with detail.
   - Same monkeypatchable client pattern as spec 005 (`_import_client()` factory or equivalent).
4. UI: sidebar "Discover new items" — `st.text_input` for the query (default `"streetwear"`), a second optional `st.text_input` "Only these stores (comma-separated)" (e.g. `ssense, nordstrom, farfetch`; blank = all stores), + button; `ui/api_client.py` gets `discover(client: httpx.Client, query: str, max_results: int = 20, stores: list[str] | None = None) -> dict` (503/502/422 → `UiImportError(detail)`). Success shows added/skipped/failed counts and reminds the user to click **Embed pending items**; errors render with `st.error`, no crashes.
5. `README.md`: add a "Live discovery setup" note — create free SerpAPI account, put `SERPAPI_KEY=...` in `.env` at repo root.
6. Tests — `tests/test_discovery.py` (MockTransport with a realistic `shopping_results` fixture: parsing, missing-thumbnail skip, store-filter keeps only matching sources case-insensitively, error-body raise), `tests/test_discover_endpoint.py` (monkeypatched key + client + `IMPORT_DIR`: 201-path adds items with downloaded files, dedupe on rerun reports skipped, per-item download failure counts as failed without aborting, missing key → 503, search failure → 502), `tests/test_ui_client.py` addition (discover success + 503 → `UiImportError`).

## Acceptance criteria
- [ ] With a mocked SerpAPI response, `POST /discover` creates candidate items with local image files, title, store-as-brand, and product URL; re-running the same discovery adds nothing and reports them as skipped.
- [ ] Without `SERPAPI_KEY`, `/discover` returns 503 with the friendly detail; a SerpAPI error returns 502; a single bad thumbnail download is counted in `failed` without aborting the batch. No path 500s.
- [ ] Discovered items flow through the existing `/embed` + `/feed` pipeline like any candidate.
- [ ] Passing `stores` (API or UI) keeps only results from matching stores, case-insensitively.
- [ ] The UI Discover box reports added/skipped/failed on success and shows readable errors otherwise.
- [ ] `.env` loading works: setting `SERPAPI_KEY` via environment or `.env` is picked up; the key never appears in any committed file.
- [ ] Full suite passes offline with zero real network calls; `uv run ruff check .` and `uv run ruff format --check .` pass.

## Out of scope
- Scheduled/automatic background pulls (manual button first; cron later if wanted).
- Price storage or filtering — `Item` has no price field yet; log in notes if it feels missing.
- Per-store connectors (eBay, ASOS/RapidAPI — parked as future specs).
- Pagination beyond the first results page; query history; saved searches.

## Implementation notes
*(Codex fills this in: what was built, deviations, questions, follow-ups.)*

## Review feedback
*(Claude fills this in if the review fails: concrete fixes required.)*
