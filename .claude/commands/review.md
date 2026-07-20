---
description: Review Codex's implementation of a spec against its acceptance criteria
---
Review the implementation of spec: $ARGUMENTS (a number like 001, or the newest spec with status REVIEW if not given).

1. Read the spec, including Codex's **Implementation notes**.
2. Read the actual diff/code it produced — every file the spec names plus anything Implementation notes mentions. Run `uv run pytest` and `uv run ruff check .` yourself; don't trust claims.
3. Verify each acceptance criterion against the real code, checking them off in the spec.
4. Verdict:
   - **Pass:** set status DONE, tick remaining boxes, tell the user it's done and what was verified.
   - **Fail:** write numbered, concrete fixes under **Review feedback** (file + what's wrong + what correct looks like), set status READY, and tell the user it's back in Codex's queue.

Style preferences that don't violate `docs/CONVENTIONS.md` are nice-to-haves — list them separately, never as blockers. Do not fix Codex's code yourself unless the user asks.
