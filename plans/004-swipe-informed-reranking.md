---
status: READY
author: claude
created: 2026-07-19
---

# 004 — Swipe-informed re-ranking + offline evaluation

## Goal
Swipes actually change the feed: likes pull similar candidates up, dislikes push them down, via a Rocchio-adjusted style profile. An offline evaluation CLI measures whether personalization beats the seed-only baseline — the repo's measurable ML story.

## Context
Specs 001–003 (DONE): `/feed` ranks candidates by cosine similarity to `build_style_profile(seed_vectors)` in `app/recommend.py` (pure numpy); swipes are stored but only *exclude* items from the feed. `bytes_to_vector` in `app/embeddings.py` decodes stored blobs. Tests use handcrafted 2-d vectors and monkeypatch `app.db.engine` (resolve `db.engine` at call time in any new db-touching code).

Approach: Rocchio relevance feedback — cheap, explainable, no training loop. `adjusted = normalize(seed_profile + ALPHA·mean(liked) − BETA·mean(disliked))`.

## Tasks
1. In `app/recommend.py` add `ALPHA = 0.5`, `BETA = 0.25` and:
   - `build_adjusted_profile(seed_vectors: Sequence[np.ndarray], liked_vectors: Sequence[np.ndarray], disliked_vectors: Sequence[np.ndarray], alpha: float = ALPHA, beta: float = BETA) -> np.ndarray` — start from `build_style_profile(seed_vectors)`, add `alpha * mean(liked)`, subtract `beta * mean(disliked)`, skipping empty sequences; L2-normalize the result. With no liked and no disliked vectors it must equal `build_style_profile(seed_vectors)`. If the combination normalizes to zero, fall back to the seed profile.
2. In `app/main.py`, extend `GET /feed` with query param `profile: Literal["seed", "personalized"] = "personalized"`:
   - `personalized`: load all swipes joined to their items, split embedded item vectors into liked/disliked, and rank with `build_adjusted_profile`. Swipes whose item has no embedding are ignored.
   - `seed`: current behavior (baseline for comparison).
   - The 409-no-seeds rule is unchanged.
3. Create `app/evaluate.py` (CLI: `uv run python -m app.evaluate`):
   - `holdout_rank(profile: np.ndarray, held_out: np.ndarray, negatives: Sequence[np.ndarray]) -> int` — 1-based rank of `held_out` among `negatives + held_out` by cosine score against `profile` (ties: held_out ranks worst, so improvements are never tie artifacts).
   - `evaluate_profiles(seed_vectors, liked_vectors, disliked_vectors, alpha: float = ALPHA, beta: float = BETA) -> dict` — leave-one-out over liked vectors: for each liked vector, build the baseline profile (seeds only) and the personalized profile from seeds + the *remaining* liked/disliked vectors, then `holdout_rank` the held-out vector against the disliked vectors as negatives. Return `{"n_evaluated": int, "baseline": {"mean_rank": float, "mrr": float}, "personalized": {"mean_rank": float, "mrr": float}}`.
   - `main()` — read seed/liked/disliked vectors from the real db (`db.engine` at call time), require ≥ 2 liked and ≥ 1 disliked embedded swipe, else print a friendly "not enough swipe data" message and exit 0. Otherwise print both profiles' mean rank and MRR.
4. Chore (UI): in `ui/app.py`, replace the four deprecated `use_container_width=True` args with `width="stretch"` (Streamlit removed the old arg after 2025-12-31; it currently spams deprecation warnings).
5. Tests — `tests/test_recommend.py` additions (no-swipe equivalence; a liked-direction candidate scores strictly higher under the adjusted profile; a disliked-direction candidate strictly lower; zero-vector fallback), `tests/test_feed.py` additions (`?profile=seed` vs default personalized ordering flips after a like, using handcrafted vectors; swipe on an unembedded item is ignored without error), `tests/test_evaluate.py` (`holdout_rank` ordering + tie rule; `evaluate_profiles` on constructed vectors where personalized strictly beats baseline on MRR; not-enough-data path of the db-reading logic).

## Acceptance criteria
- [ ] With zero swipes, `build_adjusted_profile` equals `build_style_profile` and `/feed?profile=personalized` returns the same order as `?profile=seed`.
- [ ] After a like, candidates similar to the liked item rank strictly higher in the personalized feed than in the seed feed; after a dislike, similar candidates rank strictly lower.
- [ ] Swipes on items without embeddings are ignored by both the feed and the evaluator — no errors.
- [ ] `uv run python -m app.evaluate` prints mean rank and MRR for baseline and personalized profiles, or a friendly not-enough-data message; `evaluate_profiles` is unit-tested with vectors where personalized beats baseline.
- [ ] `ui/app.py` contains no `use_container_width` usages and the UI renders unchanged.
- [ ] Full suite passes offline; `uv run ruff check .` and `uv run ruff format --check .` pass.

## Out of scope
- Learned rankers (logistic regression, gradient boosting, fine-tuning) — Rocchio only for now.
- Time-decayed or session-weighted swipes; brand weights in the profile.
- New UI features beyond the deprecation chore (no eval dashboards — CLI output only).
- Persisting evaluation results; hyperparameter search over ALPHA/BETA.

## Implementation notes
*(Codex fills this in: what was built, deviations, questions, follow-ups.)*

## Review feedback
*(Claude fills this in if the review fails: concrete fixes required.)*
