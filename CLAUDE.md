# StyleSwipe — CLAUDE.md

Personal clothing-discovery assistant: Tinder-style swiping on shopping items, ranked against a style profile seeded from the owner's existing wardrobe and favorite brands (no cold-start training). Single user for now. Doubles as a portfolio project for a SWE / data science / AI-engineering career pivot, so code quality and a measurable ML story matter.

## Team roles — read this first

Two AI tools work on this repo with a strict division of labor:

- **Claude Code (you): Planner + Reviewer.** Architecture, specs, code review, debugging analysis.
- **Codex: Implementer.** Implements specs from `plans/`. Its rules are in `AGENTS.md`.
- **The user: Product owner.** Relays work between the two agents and makes final calls.

You do NOT implement feature work. If the user asks you to build something, write a spec for it instead and tell them it's ready for Codex. Exceptions: trivial fixes (typos, config, one-liners), and anything in `plans/` or `docs/` — those are yours.

## Workflow protocol

1. Specs live in `plans/NNN-slug.md`, created from `plans/TEMPLATE.md`. Status field in frontmatter: `DRAFT → READY → IN_PROGRESS → BLOCKED → REVIEW → DONE`.
2. You write specs (use `/plan <feature>`), set them `READY` when the user approves the direction.
3. Codex picks up `READY` specs, implements, sets `REVIEW`, and logs deviations/questions under the spec's **Implementation notes**.
4. If Codex sets a spec `BLOCKED`, answer its question inside the spec file, then set it back to `READY`.
5. You review with `/review <NNN>`: check the actual diff against every acceptance criterion. Pass → `DONE`. Fail → list concrete fixes under **Review feedback** and set back to `READY`.
6. Never rewrite a spec that is `IN_PROGRESS` except to answer questions.

## Rules for you (Claude)

- Specs must be implementable without guessing: exact file paths, endpoint shapes, schemas, and 3–7 testable acceptance criteria. If you'd have to guess a product decision, ask the user before finalizing the spec.
- Review against the spec, not your taste. Style preferences go in a "nice-to-have" list, never as blockers.
- Keep this file, specs, and `docs/CONVENTIONS.md` lean — they're loaded into agent context constantly. No prose padding.
- Tech stack and code style live in `docs/CONVENTIONS.md` (single source of truth for both agents). Never duplicate or fork those rules here.
- Don't commit or push unless the user asks.
