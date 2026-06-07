# Onboarding — fresh clone

One skill, one sync command. Framework repo is **English-only**; your `$MEMORY_HOME` hub can be any language.

## Prerequisites

- Cursor with **Skills** enabled
- Python 3.10+
- Git

## Quick start (single clone)

```bash
git clone https://github.com/raphael-batte/cursor-agent-memory.git
cd cursor-agent-memory
export FRAMEWORK_ROOT="$(pwd)"
bash scripts/link-cursor-skills.sh --force
bash scripts/init-memory.sh
```

| Step | What it does |
|------|----------------|
| `link-cursor-skills.sh` | Symlinks `@agent-memory` skill into `~/.cursor/skills/` |
| `init-memory.sh` | Creates `<clone>/memory/` (context, feedback, chats — **gitignored**) |

### Sync in Cursor

1. Open any project in Cursor.
2. Add **`@agent-memory`** in chat.
3. Say: **`sync with agent memory`** — agent scans transcripts (~180 days by default), asks period/limit, runs sync.
4. **Reload Window** — hooks install during sync.

### What sync + hooks do automatically

| Output | How |
|--------|-----|
| `chats/manifest.json` | Tracks processed Cursor chats |
| `chats/merge-staging/` | Raw candidates per chat (for agent review) |
| `chats/projects/<slug>.md` | **Recent**, **`## Next step`** (pointer or explicit `_No forward pointer._` + chat drill link), optional **`[bootstrap]` Decisions** on first sync |
| `context/GLOBAL_CONTEXT.md` → **Projects** | Rows from distilled workspaces |
| Boundary hooks | `sessionStart` / `sessionEnd` / `preCompact` re-distill stale chats and refresh **Next step** |

**Forward pointer** replaces per-repo `AGENT_HANDOFF.md` — one file per project slug under `chats/projects/`.

### After sync — agent should offer (optional)

1. **`fill Me in GLOBAL_CONTEXT from our chats`**
2. **Review `[bootstrap]` Decisions** — semantic merge from `merge-staging/`
3. **Curate `## Next step`** if placeholder `[?]` / `_No forward pointer._` — or drill chat link first, then edit

Manual sync:

```bash
python3 scripts/sync-memory.py --days 180
python3 scripts/memory-doctor.py
python3 scripts/verify-memory.py --memory-home "$MEMORY_HOME"
```

---

## Dev + install (framework contributors only)

See previous two-clone workflow in [MIGRATION.md](MIGRATION.md) — `dev.config.json` + `sync-to-install.sh`.

---

## Verify setup

```bash
bash scripts/skills-status.sh
python3 scripts/memory-status.py --brief
```

Hooks env: `~/.cursor/hooks/agent-memory.env`  
Transcripts (read-only): `~/.cursor/projects/*/agent-transcripts/`

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Sync finds 0 chats | Transcripts under `~/.cursor/projects/` |
| verify failed | `memory-doctor.py --memory-home "$MEMORY_HOME"` |
| Hooks silent | Reload Cursor; check `~/.cursor/hooks/agent-memory.env` |
| Stale Next step | Close chat (sessionEnd distill) or `list-chats.py --pending` |

Details: [MIGRATION.md](MIGRATION.md) · [INSTRUCTIONS.md](INSTRUCTIONS.md)
