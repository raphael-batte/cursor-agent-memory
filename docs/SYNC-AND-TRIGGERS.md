# Sync and boundary triggers

Technical reference for distill-first memory with **forward pointer** (`## Next step`).

## Design goals

1. **Distill-first** — `chats/projects/<slug>.md` is primary history and forward pointer.
2. **Chat links** — Recent lines include `[title](uuid)` when transcript jsonl exists.
3. **One skill** — `agent-memory` routes all layers.
4. **Event-driven** — distill on session boundaries; `apply=True` updates Recent + Next step.

## Hub config

`$MEMORY_HOME/config.json`:

```json
{
  "framework_root": "",
  "memory_home": ""
}
```

## Triggers

| Cursor event | Script | Action |
|--------------|--------|--------|
| `sessionStart` | `agent-memory-session-start.sh` | Catch-up distill (≤5 chats, 180d, current workspace) |
| `sessionEnd` | `agent-memory-boundary.sh` | Distill + apply → Recent + **Next step** |
| `sessionEnd` | `agent-memory-session-end.sh` | Checklist log |
| `preCompact` | `agent-memory-boundary.sh` | Distill + reminder |
| `afterFileEdit` | `agent-memory-after-edit.sh` | Log chats hub edits |

## sync-memory.py

1. `init-memory.sh` (idempotent)
2. `install-memory-hooks.sh`
3. List pending chats in `--days` window
4. `distill-merge` each with `apply=True`, `bootstrap_decisions=True` on first sync
5. Bootstrap `GLOBAL_CONTEXT.md` Projects table
6. `verify-memory.py`

CLI: `--scan-only`, `--dry-run`, `--no-hooks`, `--days`, `--limit`.

## Forward pointer

`lib/forward_pointer.py` — heuristics on transcript tail with **confidence** tier. Hooks write `## Next step` mechanically; on placeholder or low confidence, `sessionEnd` emits `user_message` pointing to `pointer-curate-prompt.md` for **agent curation** (regex = fallback only).

## Distill freshness (v0.10+)

- **Watermark** — `manifest.json` stores `watermark_user_count` + `watermark_tail_hash`; redistill when ≥2 new user messages or tail changes (not mtime alone).
- **Debounce** — same chat within 30s on `preCompact`/`sessionEnd` → one distill.
- **Metrics** — `logs/agent-memory-metrics.jsonl`; `memory-health.py` tracks pointer hit-rate vs rolling baseline in `logs/health-baseline.json`.

## Modules

| Module | Role |
|--------|------|
| `lib/forward_pointer.py` | Next step extraction |
| `lib/distill_links.py` | `[title](uuid)` in Recent |
| `lib/pending_chats.py` | Pending/stale scan |
| `lib/boundary_hooks.py` | Hook dispatch + apply |
| `lib/global_context_bootstrap.py` | Projects table |
