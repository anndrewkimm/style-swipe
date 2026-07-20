# Next session — pick-up checklist (written 2026-07-19)

Where things stand: specs 001–004 DONE and pushed. 005 (URL importer) is IN_PROGRESS with Codex. 006 (Google Shopping discovery, with store filter) is READY behind it.

## Owner (you)
1. Sign up free at https://serpapi.com (email only; ShopStyle is dead, this is the replacement).
2. Create `.env` in the repo root containing: `SERPAPI_KEY=your_key_here` (gitignored — never commits).

## Codex
3. Finish spec 005 → set REVIEW.
4. Implement spec 006 → set REVIEW. (Both fully testable offline; the key is only needed at runtime.)

## Claude
5. `/review 005`, then `/review 006`; commit + push each pass.

## First real use (after 005 + 006 land)
```sh
uv run python -m app.ingest <folder-of-your-wardrobe-photos> --source seed
uv run uvicorn app.main:app --reload      # terminal 1
uv run streamlit run ui/app.py            # terminal 2
```
Then in the UI: **Embed pending items** → **Discover** (query: e.g. `streetwear`, stores: `ssense, nordstrom, farfetch`) → Embed again → swipe.

## After ~a week of real swiping
- Run `uv run python -m app.evaluate` — does personalization beat the baseline on your real data? (Portfolio metric.)
- Decide next spec: React/Vite UI, eBay resale source, or price field + filtering.

*Delete this file once the checklist is done.*
