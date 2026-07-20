---
description: Summarize the plan queue and what each team member should do next
---
Give the user a project status report:

1. List every spec in `plans/` with its number, title, and status (read frontmatter only — don't load full spec bodies for DONE items).
2. Flag anything stuck: BLOCKED specs (quote the question), REVIEW specs waiting on Claude, READY specs waiting on Codex.
3. End with a one-line "next action" for each of: the user, Codex, Claude.
