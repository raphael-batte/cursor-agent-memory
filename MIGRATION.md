# Migration & AI workflow

Move an existing memory hub to this framework, wire Cursor skills, and distill chats.

**Framework (git):** `$FRAMEWORK_ROOT` — install clone Cursor points at.  
**Data hub (never git):** `$MEMORY_HOME` — default `<install>/memory/` (gitignored).

Setup: [ONBOARDING.md](ONBOARDING.md)

---

## 1. Fresh machine

```bash
git clone https://github.com/raphael-batte/cursor-agent-memory.git <install-clone>
cd <install-clone>
export FRAMEWORK_ROOT="$(pwd)"
bash scripts/link-cursor-skills.sh --force
bash scripts/init-memory.sh
```

In Cursor with `@agent-memory`: **sync with agent memory**. Reload window after sync.

Manual:

```bash
python3 scripts/sync-memory.py --days 180
```

Paths are written to `$MEMORY_HOME/config.json` on init/link/sync — no `~/.config` files created.

Example `$MEMORY_HOME/config.json`:

```json
{
  "framework_root": "/path/to/install-clone",
  "memory_home": "/path/to/install-clone/memory"
}
```

---

## 2. Migrate from an old hub

Copies **missing** files only (`rsync --ignore-existing`).

```bash
bash "$FRAMEWORK_ROOT/scripts/migrate-memory.sh" \
  --from /path/to/old-hub \
  --to "$MEMORY_HOME"
```

Then:

```bash
bash "$FRAMEWORK_ROOT/scripts/link-cursor-skills.sh" --force
python3 "$FRAMEWORK_ROOT/scripts/memory-doctor.py" --fix
```

---

## 3. Dev + install split

If you edit framework in a **dev** clone:

```bash
cp dev.config.json.example dev.config.json   # set install_root
bash scripts/sync-to-install.sh
```

Dev clone stays clean — no `memory/` there.

---

## 4. Secrets (hard requirement)

**Never** put passwords, tokens, API keys, JWT, private keys, or `.env` values into `$MEMORY_HOME`.

```bash
python3 "$FRAMEWORK_ROOT/scripts/verify-memory.py" --memory-home "$MEMORY_HOME"
```

---

## 5. Chat distill workflow

**Do not** paste raw `.jsonl` into chat.

```bash
python3 "$FRAMEWORK_ROOT/scripts/list-chats.py" --memory-home "$MEMORY_HOME" --pending
python3 "$FRAMEWORK_ROOT/scripts/distill-merge.py" "$UUID" --strategy auto --memory-home "$MEMORY_HOME"
python3 "$FRAMEWORK_ROOT/scripts/distill-merge.py" "$UUID" --apply --memory-home "$MEMORY_HOME"
python3 "$FRAMEWORK_ROOT/scripts/verify-memory.py" --memory-home "$MEMORY_HOME" --strict-secrets
```

Transcripts (read-only): `~/.cursor/projects/*/agent-transcripts/`

### Sync hub across machines

Use a **private git repo** for `$MEMORY_HOME` only, or Syncthing/iCloud on the hub directory.  
Framework: `git pull` in `$FRAMEWORK_ROOT` separately. Never push secrets — run `verify-memory.py` first.

---

## 6. Forward pointer (replaces handoff)

`chats/projects/<slug>.md` **## Next step** is updated automatically on boundary distills (`lib/forward_pointer.py`). Legacy `AGENT_HANDOFF.md` in repos is ignored by the framework — migrate next-step text into distill or delete handoff files.

---

## 7. Agent prompts

**First-time:** `sync with agent memory`

**After session:** distill via `distill-merge.py` — no raw jsonl, verify must pass.

**Weekly:**

```bash
bash "$FRAMEWORK_ROOT/scripts/weekly-verify.sh"
```

**Repair:**

```bash
python3 "$FRAMEWORK_ROOT/scripts/memory-doctor.py" --memory-home "$MEMORY_HOME" --fix
```

---

## 8. Troubleshooting

| Problem | Fix |
|---------|-----|
| Scripts can't find hub | `dev.config.json` install_root, or `--memory-home`, or `memory-doctor --fix` |
| Second Mac / synced hub | [ONBOARDING → Second machine](ONBOARDING.md#second-machine-same-hub-new-mac) |
| Legacy XDG config | Read-only — migrate to hook env + `memory/config.json` |
| Skills point to old path | `link-cursor-skills.sh --force` from install clone |
| `list-chats` STALE | Re-distill when transcript mtime > `distilled_at` |
| verify fails | Remove secrets; fix manifest/GLOBAL_CONTEXT |

```bash
cd "$FRAMEWORK_ROOT" && git pull
bash scripts/link-cursor-skills.sh --force
bash tests/run-tests.sh
```
