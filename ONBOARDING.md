# Onboarding — fresh clone

One skill, one sync command. Framework repo is **English-only**; your `$MEMORY_HOME` hub can be any language.

## Prerequisites

- Cursor with **Skills** enabled
- Python 3.10+
- Git

## Quick start (single clone)

Most users only need **one** clone — framework + private hub together.

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
3. Say: **`sync with agent memory`** — agent scans transcripts (~180 days by default), asks period + handoff mode, runs sync.
4. **Reload Window** — hooks (`sessionStart`, `sessionEnd`, `preCompact`) install during sync and need a reload.

### What first sync does automatically

| Output | How |
|--------|-----|
| `chats/manifest.json` | Tracks processed Cursor chats |
| `chats/merge-staging/` | Raw candidates per chat (for agent review) |
| `chats/projects/<slug>.md` | **Recent** lines + optional **`[bootstrap]` Decisions** (keyword-tagged user messages, only while Decisions is empty) |
| `context/GLOBAL_CONTEXT.md` → **Projects** | Rows from distilled workspaces |
| Cursor hooks | `~/.cursor/hooks/agent-memory.*` |

Sync does **not** fill **Me** in GLOBAL_CONTEXT — that is personal context (see below).

### After sync — agent should suggest (optional)

The `@agent-memory` agent can offer these follow-ups (user confirms each):

1. **`fill Me in GLOBAL_CONTEXT from our chats`** — role, stack, tools, communication style inferred from distilled history.
2. **Review `[bootstrap]` Decisions** — refine or replace heuristic seeds in `chats/projects/*.md` with curated bullets (semantic merge from `merge-staging/`).
3. **Handoff setup** — if `handoff_mode` is not `off` (see [Handoff](#handoff-optional-per-repo)).

Manual sync (no chat):

```bash
python3 scripts/sync-memory.py --days 180 --handoff-mode optional
python3 scripts/memory-doctor.py
python3 scripts/verify-memory.py --memory-home "$MEMORY_HOME"
```

---

## Handoff (optional, per repo)

**What it is:** `AGENT_HANDOFF.md` in each repo answers *where we stopped* — phase, next step, blockers. Distilled chat memory is history; handoff is **now**.

**When to use:** Multi-session work on the same codebase. Skip (`handoff_mode: off`) if you only need cross-chat memory.

**During sync** the agent asks: use handoff? → sets `memory/config.json` → `handoff_mode`: `off` | `optional` | `required`.

**Enable later in a repo:**

```bash
cp templates/repo-handoff/AGENT_HANDOFF.md /path/to/your-repo/
# optional Cursor rule:
cp templates/cursor-rule/agent-handoff.mdc /path/to/your-repo/.cursor/rules/
```

Fill **Next Step** at session end (agent does this when `handoff_mode` allows). Trendymen-style per-repo `AGENT_HANDOFF.md` is **your** repo file — not shipped inside the memory hub.

---

## Dev + install (framework contributors only)

Keep the **dev** clone free of personal data. Cursor uses a separate **install** clone.

### 1. Clone dev

```bash
git clone https://github.com/raphael-batte/cursor-agent-memory.git cursor-agent-memory-dev
cd cursor-agent-memory-dev
cp dev.config.json.example dev.config.json
# edit dev.config.json → install_root: absolute path to install clone
```

### 2. Clone install

```bash
git clone https://github.com/raphael-batte/cursor-agent-memory.git agent-memory
```

Set `install_root` in dev `dev.config.json` to the install clone path.

### 3. Sync dev → install

```bash
cd cursor-agent-memory-dev
bash scripts/sync-to-install.sh
```

### 4. Link + init (on install only)

```bash
cd agent-memory
export FRAMEWORK_ROOT="$(pwd)"
bash scripts/link-cursor-skills.sh --force
bash scripts/init-memory.sh
```

Hub lives at `<install>/memory/` — **never** in the dev clone.

---

## Verify setup

```bash
bash scripts/skills-status.sh
python3 scripts/memory-status.py --brief
```

Hooks env: `~/.cursor/hooks/agent-memory.env`  
Transcripts (read-only): `~/.cursor/projects/*/agent-transcripts/`

## After onboarding

| Situation | What happens |
|-----------|----------------|
| New chat / window | `sessionStart` catch-up distill for open workspace |
| Close chat | `sessionEnd` distill + optional checklist |
| Context compact | `preCompact` distill + reminder |
| Framework edits in dev | `sync-to-install.sh` then reload Cursor |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Sync finds 0 chats | Transcripts under `~/.cursor/projects/` |
| verify failed | `memory-doctor.py --memory-home "$MEMORY_HOME"` |
| Hooks silent | Reload Cursor; check `~/.cursor/hooks/agent-memory.env` |
| `memory/` in dev clone | Remove it; use `dev.config.json` + install clone |
| Old external hub | `migrate-memory.sh --from … --to "$MEMORY_HOME"` |

Details: [MIGRATION.md](MIGRATION.md) · [INSTRUCTIONS.md](INSTRUCTIONS.md)
