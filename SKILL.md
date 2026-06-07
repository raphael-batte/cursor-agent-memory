---
name: agent-memory
description: >
  Single entry for Cursor agent memory. Sync with "sync with agent memory". Routes layers
  by task — handoff (optional), distills with chat links, global context, feedback.
  MEMORY_HOME at install clone memory/. Do NOT load all layers every session.
---

# Agent Memory

**Version:** 0.8.7 — see [VERSIONING.md](VERSIONING.md)

**Full protocol:** [INSTRUCTIONS.md](INSTRUCTIONS.md) · **Overview:** [ARCHITECTURE.md](ARCHITECTURE.md)

### Path variables (clone anywhere — no fixed install folder)

| Variable | Meaning | Resolve order |
|----------|---------|---------------|
| `$FRAMEWORK_ROOT` | Install clone (Cursor symlink target) | `~/.cursor/hooks/agent-memory.env` → `memory/config.json` |
| `$MEMORY_HOME` | `<install>/memory/` (gitignored) | `--memory-home` → env → install hub |

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
2. **Handoff:** use `AGENT_HANDOFF.md` in repos?
   - **No** → `handoff_mode: off`
   - **Yes / not sure** → `optional`
   - **Required** → always read handoff when present

### Step 3 — Run sync (after user confirms)

```bash
python3 "$FRAMEWORK_ROOT/scripts/sync-memory.py" \
  --memory-home "$MEMORY_HOME" \
  --days 90 \
  --limit 38 \
  --handoff-mode optional
```

Optional preview: add `--dry-run` before the real run. Reload Cursor after hooks install.

### Report to user

Always end with:

`Projects in GLOBAL_CONTEXT: N · Chat distills: M · Handoff: off|optional|required · Ready to work.`

---

## Session start (routing)

Read `$MEMORY_HOME/config.json` → `handoff_mode` (`off` | `optional` | `required`).

| Order | Layer | Read |
|-------|-------|------|
| 1 (if mode allows) | Handoff | `<repo>/AGENT_HANDOFF.md` when Next Step is non-empty |
| 2 | Distill | `$MEMORY_HOME/chats/projects/<slug>.md` (latest Recent by date) |
| 3 (if slug unclear) | Global | `$MEMORY_HOME/context/GLOBAL_CONTEXT.md` |

**Do not** invoke separate skills — read files directly. Internal detail: `skills/chat-memory/SKILL.md`, etc.

**If distill lacks detail:** open full chat via markdown link `[title](uuid)` in Recent, or read transcript on demand (never bulk-load raw jsonl).

---

## Layer map

| Question | Read |
|----------|------|
| Who / projects / rules | `$MEMORY_HOME/context/GLOBAL_CONTEXT.md`, `conventions.md`, `infra.md` |
| Where we stopped | handoff (optional) → else distill Recent |
| Past decisions | `$MEMORY_HOME/chats/projects/<slug>.md` → `## Decisions` |
| Wins / fails / style | `$MEMORY_HOME/feedback/{wins,fails}.md`, `preferences.md` |

| Situation | Read |
|-----------|------|
| Continue known repo | handoff (if mode + Next Step) → distill |
| «What did we decide» | distill Decisions |
| Other project mid-chat | distill for that slug + `chats/INDEX.md` |
| Plan / CI / deploy | feedback fails + wins + preferences |

---

## Session end

Distill runs via hooks (`sessionEnd`, `preCompact`, `sessionStart` catch-up). Agent updates only what changed:

- `handoff_mode` not `off` and user asked → `AGENT_HANDOFF.md`
- New cross-repo rule → `conventions.md`
- Curated decisions → semantic-merge from `merge-staging/` (see `skills/semantic-merge/SKILL.md`)
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

Then in chat: **sync with agent memory**. Guide: [MIGRATION.md](MIGRATION.md).
