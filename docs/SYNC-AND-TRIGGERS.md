# Sync and boundary triggers

Technical reference for v0.8+ distill-first memory.

## Design goals

1. **Distill-first** — `chats/projects/<slug>.md` is primary history; handoff is optional.
2. **Chat links** — Recent lines include `[title](uuid)` when transcript jsonl exists.
3. **One skill** — `agent-memory` routes all layers; read files directly, no `@` skill chain.
4. **Event-driven** — distill on session boundaries, not timers.

## Hub config

`$MEMORY_HOME/config.json`:

```json
{
  "framework_root": "",
  "handoff_mode": "optional"
}
```

| `handoff_mode` | Session start |
|----------------|---------------|
| `off` | Distill only |
| `optional` | Handoff if Next Step filled, else distill |
| `required` | Handoff when file exists, then distill |

## Triggers

| Cursor event | Script | Action |
|--------------|--------|--------|
| `sessionStart` | `agent-memory-session-start.sh` | Catch-up distill (≤5 chats, 180d, current workspace) |
| `sessionEnd` | `agent-memory-boundary.sh` | Distill current chat if stale |
| `sessionEnd` | `agent-memory-session-end.sh` | Checklist log (handoff step if mode ≠ off) |
| `preCompact` | `agent-memory-boundary.sh` | Distill + `user_message` reminder |
| `afterFileEdit` | `agent-memory-after-edit.sh` | Log handoff/chats edits |

## sync-memory.py

Pipeline:

1. `init-memory.sh` (idempotent)
2. Write `handoff_mode`
3. `install-memory-hooks.sh`
4. List pending chats in `--days` window
5. `distill-merge` each (up to `--limit`)
6. Bootstrap `GLOBAL_CONTEXT.md` Projects table
7. `verify-memory.py`

CLI flags: `--scan-only` (step 1), `--dry-run`, `--no-hooks`, `--handoff-mode`, `--days`, `--limit` (user choice after scan).

## Agent sync protocol

Triggers: `sync with agent memory`, `initialize agent memory`.

Agent asks days (default 180) and handoff mode, then runs `sync-memory.py` and prints the report template from [SKILL.md](../SKILL.md).

## Modules

| Module | Role |
|--------|------|
| `lib/distill_links.py` | `[title](uuid)` in Recent |
| `lib/pending_chats.py` | Pending/stale scan, day filter |
| `lib/boundary_hooks.py` | Hook dispatch |
| `lib/memory_routing.py` | `handoff_mode` read order |
| `lib/global_context_bootstrap.py` | Projects table from manifest |

## Internal skill docs

Files under `skills/*/SKILL.md` remain for deep dives. Agents read them on demand — they are **not** symlinked to `~/.cursor/skills/` by default.
