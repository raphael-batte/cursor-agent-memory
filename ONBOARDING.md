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

## Second machine (same hub, new Mac)

1. `git clone` / `git pull` your framework clone (any path)
2. `bash scripts/link-cursor-skills.sh --force`
3. `bash scripts/install-memory-hooks.sh` — writes `~/.cursor/hooks/agent-memory.env`
4. `python3 scripts/memory-doctor.py --fix` — repairs `memory/config.json` paths

Sync the hub separately: private git / Syncthing / iCloud on `memory/` only.

Do **not** use the legacy XDG config directory — read-only fallback (deprecated; see hook env).

### Optional: session-start rule (per workspace)

After first sync, install a thin always-on rule with resolved paths:

```bash
bash scripts/init-project-rules.sh --project /path/to/your/workspace
# if slug differs from repo folder name:
bash scripts/init-project-rules.sh --project /path/to/workspace --slug <name-from-chats/projects>
```

Check distills: `ls memory/chats/projects/`

---

## Contributors

See [CONTRIBUTING.md](CONTRIBUTING.md) — branch → PR → CI → merge to `main`.

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
| Wrong paths after hub sync | `memory-doctor.py --fix`; check `~/.cursor/hooks/agent-memory.env` |
| Rule reads wrong distill | `init-project-rules.sh --slug <name-from-chats/projects>` |

Details: [MIGRATION.md](MIGRATION.md) · [INSTRUCTIONS.md](INSTRUCTIONS.md)
