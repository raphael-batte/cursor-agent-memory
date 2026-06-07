---
name: agent-memory
description: >
  Single entry for Cursor agent memory. Sync with "sync with agent memory". Routes layers
  by task — distill with ## Next step forward pointer, global context, feedback.
  MEMORY_HOME at install clone memory/. Do NOT load all layers every session.
---

# Agent Memory

**Version:** 0.9.2 — see [VERSIONING.md](VERSIONING.md)

**Full protocol:** [INSTRUCTIONS.md](INSTRUCTIONS.md) · **Overview:** [ARCHITECTURE.md](ARCHITECTURE.md)

### Path variables (clone anywhere — no fixed install folder)

| Variable | Meaning | Resolve order |
|----------|---------|---------------|
| `$FRAMEWORK_ROOT` | Install clone (Cursor symlink target) | `~/.cursor/hooks/agent-memory.env` → `memory/config.json` |
| `$MEMORY_HOME` | `<install>/memory/` (gitignored) | `--memory-home` → env → hook env → install hub |

Legacy XDG cursor-agent-memory config is read-only fallback (deprecated).

Dev clone (`dev.config.json`) stays clean — no `memory/` there. Sync code: `scripts/sync-to-install.sh`.

Set `FRAMEWORK_ROOT` to this skill's repo root (the symlink target) before running scripts.

---

## Sync (first-time and refresh)

**Triggers:** `sync with agent memory`, `initialize agent memory`, `sync agent memory`

### Step 1 — Scan (always first)

```bash
python3 "$FRAMEWORK_ROOT/scripts/sync-memory.py" --memory-home "$MEMORY_HOME" --scan-only
```

Show the user: `total_chats`, `active_90d`, `pending_90d`, `active_180d`, `pending_180d`.

### Step 2 — Ask user

1. **Period + limit:** e.g. «90 days, all pending» or «180 days, max 30» or «only 20 newest».
   - If pending > 100 and user did not set a limit — warn and ask for a number.

### Step 3 — Run sync (after user confirms)

```bash
python3 "$FRAMEWORK_ROOT/scripts/sync-memory.py" \
  --memory-home "$MEMORY_HOME" \
  --days 90 \
  --limit 38
```

Optional preview: add `--dry-run` before the real run. Reload Cursor after hooks install.

### Report to user

Always end with:

`Projects in GLOBAL_CONTEXT: N · Chat distills: M · Forward pointer: chats/projects/<slug>.md ## Next step · Ready to work.`

Then **offer** (user confirms each — do not run silently):

1. **`fill Me in GLOBAL_CONTEXT from our chats`** — infer role, stack, tools, style from distilled history.
2. **Review `[bootstrap]` Decisions** — refine heuristic seeds or semantic merge from `merge-staging/`.
3. **Curate `## Next step`** if hooks missed the real forward pointer.

---

## Session start (routing)

| Order | Layer | Read |
|-------|-------|------|
| 1 | Distill | `$MEMORY_HOME/chats/projects/<slug>.md` → **## Next step**, then Decisions / Recent |
| 2 (if slug unclear) | Global | `$MEMORY_HOME/context/GLOBAL_CONTEXT.md` |

**Do not** invoke separate skills — read files directly.

**If `## Next step` shows `_No forward pointer._` or `[?]`:** follow the chat link in that line → transcript tail (~10–20 turns). **If distill still lacks detail:** same via `[title](uuid)` in Recent. Never bulk-load raw jsonl.

---

## Layer map

| Question | Read |
|----------|------|
| Who / projects / rules | `context/GLOBAL_CONTEXT.md`, `conventions.md`, `infra.md` |
| Where we stopped | `chats/projects/<slug>.md` → **## Next step** |
| Past decisions | `chats/projects/<slug>.md` → `## Decisions` |
| Wins / fails / style | `feedback/{wins,fails}.md`, `preferences.md` |

---

## Session end

Hooks (`sessionEnd`, `preCompact`, `sessionStart`) auto-distill and refresh **## Next step**. Agent updates only what changed:

- New cross-repo rule → `conventions.md`
- Curated decisions → semantic-merge from `merge-staging/`
- Lesson learned → `feedback/wins.md` or `fails.md`

Weekly: `python3 "$FRAMEWORK_ROOT/scripts/verify-memory.py" --memory-home "$MEMORY_HOME"`

---

## Setup (human)

```bash
git clone <your-fork-or-upstream> cursor-agent-memory
cd cursor-agent-memory
export FRAMEWORK_ROOT="$(pwd)"
bash scripts/init-memory.sh
bash scripts/link-cursor-skills.sh --force
```

Then in chat: **sync with agent memory**. Guide: [ONBOARDING.md](ONBOARDING.md).
