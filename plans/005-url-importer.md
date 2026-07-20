---
status: READY
author: claude
created: 2026-07-19
---

# 005 — Product URL importer

## Goal
Paste any product-page URL (Nordstrom, SSENSE, Farfetch, anywhere) into the UI and it becomes a candidate item: image downloaded locally, title/brand/product link stored. The feed fills with real, buyable clothes instead of only local folders.

## Context
Specs 001–004 (DONE). Items need a **local** image file: `embed_image` opens `image_path` from disk and the UI renders it with `st.image`. So importing = fetch the page, read its Open Graph meta tags (`og:image`, `og:title`, `og:site_name` — the same tags link previews use), download the image into `data/` (gitignored), then the existing `/embed` + `/feed` flow takes over untouched.

`httpx` is already a runtime dep. Tests use `httpx.MockTransport` (see `tests/test_ui_client.py`) — no test may touch the network. Resolve `db.engine` at call time in any new db code.

## Tasks
1. Add `beautifulsoup4` (runtime) for meta-tag parsing.
2. Create `app/importer.py`:
   - `IMPORT_DIR = Path("data") / "images" / "imported"`; `USER_AGENT` constant set to a current desktop-browser string (some shops block default client UAs).
   - `class ImportError_(Exception)` with a human-readable message (name avoids shadowing the builtin; pick a better name if you have one — e.g. `ProductImportError`).
   - `fetch_product(client: httpx.Client, url: str) -> ProductMeta` — GET the URL (follow redirects, UA header), parse with BeautifulSoup; `ProductMeta` is a small dataclass: `title: str | None` (og:title, else `<title>`), `brand: str | None` (og:site_name, else registrable domain like "ssense.com"), `image_url: str` (og:image; if absent raise `ProductImportError("no product image found on page")`).
   - `download_image(client: httpx.Client, image_url: str, dest_dir: Path) -> Path` — stream to `dest_dir/<sha1(image_url)[:16]><ext>` (ext from URL path or content-type, default `.jpg`); verify content-type starts with `image/`, else raise `ProductImportError`.
3. In `app/main.py` add `POST /items/import`:
   - Body `ImportRequest`: `{"url": str}`. Always creates `source="candidate"`.
   - 409 if an item with this `product_url` already exists.
   - Build one `httpx.Client` per request (module-level factory `_import_client()` so tests can monkeypatch it), call `fetch_product` then `download_image(IMPORT_DIR)`, create the item (`image_path=str(downloaded path)`, `product_url=url`, title/brand from meta), return 201 with `ItemRead`.
   - `ProductImportError` and `httpx.HTTPError` → 422 with the message as detail. No embedding here — `/embed` stays the one place embeddings happen.
4. UI (`ui/api_client.py` + `ui/app.py`):
   - `import_item(client: httpx.Client, url: str) -> dict` — POST `/items/import`; on 409 or 422 raise a `UiImportError(detail)` the app can show; `raise_for_status()` otherwise.
   - Sidebar section "Add product by URL": `st.text_input` + button → success shows the imported title (or "Imported!") and reminds "click Embed pending items next"; `UiImportError`/connect errors show `st.error` with the detail — no crashes.
5. Tests — `tests/test_importer.py` (MockTransport: full og page happy path; missing og:image → error; non-image content-type → error; brand falls back to domain; filename is deterministic hash), `tests/test_import_endpoint.py` (monkeypatch `app.main._import_client` to a MockTransport client + `importer.IMPORT_DIR` to tmp_path: 201 creates item with downloaded file on disk; duplicate URL → 409; fetch failure → 422 with detail; imported item appears in `/feed` after inserting a fake embedding directly), `tests/test_ui_client.py` additions (import success + 422 → `UiImportError`).

## Acceptance criteria
- [ ] `POST /items/import` with a page exposing og:image/og:title creates a candidate item whose `image_path` is a real downloaded file under the import directory, with title, brand, and `product_url` populated (mocked transport in tests).
- [ ] Duplicate `product_url` → 409; unreachable page, missing og:image, or non-image download → 422 with a human-readable detail. The API never 500s on a bad URL.
- [ ] An imported item flows through the existing pipeline: after embedding it appears in `/feed` ranked like any other candidate.
- [ ] The UI sidebar import box adds an item on success and shows the error detail on failure, without crashing.
- [ ] All new logic is covered by offline MockTransport tests; the suite makes zero real network calls.
- [ ] `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .` all pass.

## Out of scope
- Bulk/catalog scraping, sitemap crawling, or scheduled store polling.
- Aggregator/affiliate APIs (ShopStyle etc.) — possible spec 006 after the user signs up.
- Site-specific parsers (price extraction, size/color variants) — og tags only in v1.
- Auto-embedding on import; retrying failed downloads; image resizing.

## Implementation notes
*(Codex fills this in: what was built, deviations, questions, follow-ups.)*

## Review feedback
*(Claude fills this in if the review fails: concrete fixes required.)*
