# Semantic merge — agent prompt (copy into chat)

Use after `distill-merge.py` wrote `chats/merge-staging/<slug>-*.md`.

## Inputs

- Staging: `$MEMORY_HOME/chats/merge-staging/<file>.md`
- Target: `$MEMORY_HOME/chats/<project_rel>` (from staging header or manifest `distilled_to`)
- Language: **preserve original chat language** — do not translate

## Task

1. Read staging `## Raw candidates` — these are **not** decisions.
2. If `## Window summaries (map-reduce)` exists — **reduce** each `[wN]` block into 1–2 Decisions bullets (map-reduce).
3. Read target `## Decisions` — keep existing curated bullets.
4. Write **new** bullets only where a candidate expresses a durable decision, preference, or constraint.
5. Paraphrase; merge duplicates; drop noise, commands, one-off debug, credentials.
6. Update `## Open threads` if staging lists unresolved items.
7. If `## Next step` is placeholder (`_No forward pointer._` / `[?]`) — curate one line using `pointer-curate-prompt.md`.
8. Do **not** paste raw candidate text into Decisions.
9. Run `verify-memory.py`; hooks already updated Recent — do not `--apply` over curated Decisions.

## Output format (Decisions bullets)

- One line per decision; imperative or past-tense fact
- Preserve chat link from staging Recent when present: `[title](full-uuid)`
- Or short ref: `` (`<uuid-prefix>`) ``
- No passwords, tokens, API keys, `.env` values

## Example transform

| Raw candidate | Curated Decision |
|---------------|------------------|
| "fix submit so row creates on real submit only" | **Ghost articles:** create row only on real submit; title required (`43f91e19`) |
| "what is the local admin password" | *(skip — no secret; use .admpassfile locally, not in hub)* |

## Checklist before save

- [ ] No verbatim long user quotes in Decisions
- [ ] Language matches chat (RU/EN mixed OK if source mixed)
- [ ] `verify-memory.py` passes
- [ ] File still ≤ 100 lines (archive older blocks if needed)
