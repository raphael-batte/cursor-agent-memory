# Onboarding — fresh clone

One skill, one sync command. Framework repo is English-only; your `$MEMORY_HOME` hub can be any language.

## Prerequisites

- Cursor with **Skills** enabled
- Python 3.10+
- Git

## Recommended: dev + install (clean GitHub repo)

Keep the **dev** clone free of user files. Cursor uses a separate **install** clone.

### 1. Clone dev (framework work)

```bash
git clone https://github.com/raphael-batte/cursor-agent-memory.git
cd cursor-agent-memory
cp dev.config.json.example dev.config.json
# edit dev.config.json → install_root: absolute path to install clone
```

### 2. Clone install (Cursor-connected)

```bash
git clone https://github.com/raphael-batte/cursor-agent-memory.git <install-clone>
```

Set `install_root` in dev `dev.config.json` to `<install-clone>`.

### 3. Sync dev → install

```bash
cd cursor-agent-memory
bash scripts/sync-to-install.sh
```

### 4. Link skill + init hub (on install)

```bash
cd <install-clone>
export FRAMEWORK_ROOT="$(pwd)"
bash scripts/link-cursor-skills.sh --force
bash scripts/init-memory.sh
```

Creates `<install-clone>/memory/` only — **not** in the dev clone.

### 5. Sync in chat

Open any project in Cursor. With `@agent-memory`:

```text
sync with agent memory
```

### 6. Reload Cursor

Hooks install during sync. **Reload Window** so `sessionStart` / `sessionEnd` / `preCompact` activate.

---

## Alternative: single clone

```bash
git clone https://github.com/raphael-batte/cursor-agent-memory.git
cd cursor-agent-memory
export FRAMEWORK_ROOT="$(pwd)"
bash scripts/link-cursor-skills.sh --force
bash scripts/init-memory.sh
```

Hub: `<clone>/memory/` (gitignored).

---

## Manual sync

```bash
python3 "$FRAMEWORK_ROOT/scripts/sync-memory.py" --days 180 --handoff-mode off
python3 "$FRAMEWORK_ROOT/scripts/memory-doctor.py"
```

Preview: `--dry-run`.

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
| Sync finds 0 chats | Transcripts under `~/.cursor/projects/` (read-only) |
| verify failed | `memory-doctor.py --memory-home "$MEMORY_HOME"` |
| Hooks silent | Reload Cursor; check `~/.cursor/hooks/agent-memory.env` |
| `memory/` in dev clone | Remove it; use `dev.config.json` + install clone |
| Old external hub | `migrate-memory.sh --from … --to "$MEMORY_HOME"` |

Details: [MIGRATION.md](MIGRATION.md) · [INSTRUCTIONS.md](INSTRUCTIONS.md)
