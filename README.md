# Cursor Agent Memory

**Version:** 0.12.1 — see [VERSIONING.md](VERSIONING.md)
Created by [raphaelbatte](https://github.com/raphael-batte) · [raphbatte.com](https://raphbatte.com)

## What this is

**Cursor forgets between sessions.** One `@agent-memory` skill, a private `memory/` hub, and routed layers — not a notes dump.

- **Global context** — who you are, which projects, cross-repo rules, infra
- **Feedback** — what worked (+) and what to stop proposing (−)
- **Chat memory** — distilled transcripts + **`## Next step`** forward pointer (auto on hooks; explicit placeholder + chat drill link when none)

Agents load **one layer per task** (INDEX-first), not everything every time. Weak pointer → drill transcript tail via `[title](uuid)` in distill (never bulk jsonl). Scripts verify hub integrity; hooks refresh on session boundaries.

**Cursor plugin** — code in the bundle; your hub and anchor live **outside** it (survives updates). MIT license.

→ **Setup:** [ONBOARDING.md](ONBOARDING.md)

→ **System design:** [ARCHITECTURE.md](ARCHITECTURE.md) · **Agent protocol:** [INSTRUCTIONS.md](INSTRUCTIONS.md) · **Human setup:** [MIGRATION.md](MIGRATION.md)

## How layers connect

```mermaid
flowchart TB
  subgraph hub ["$MEMORY_HOME (private hub)"]
    GC[GLOBAL_CONTEXT + conventions + infra]
    FB[feedback wins/fails + preferences]
    CH["chats/projects/slug.md\n## Next step · Recent · Decisions"]
    MF[manifest.json]
  end
  TR[Cursor transcripts jsonl read-only]
  AG[Agent session start]

  TR -->|boundary distill apply| CH
  TR -->|track distilled_at| MF
  CH -->|pointer or placeholder + uuid link| AG
  AG -->|_No forward pointer_ or ?| TR
  GC -->|route by task| FB
  GC -->|route by task| CH
  FB -->|before proposing plans| CH
```

**Drill-down:** `## Next step` → `[title](uuid)` in same file → transcript tail (~10–20 turns). Placeholders: `_No forward pointer._` or `[?] _Not refreshed._`.

| Layer | Answers | Location |
|-------|---------|----------|
| Global context | Who? Rules? Projects? Hosts? | `$MEMORY_HOME/context/` |
| Feedback | What +/− worked? How user thinks? | `feedback/`, `preferences.md` |
| Chat memory | History + **next step now** | `chats/projects/<slug>.md` (`## Next step`) |

## Who reads what

| You are… | Start here |
|----------|------------|
| **Human** setting up for the first time | [ONBOARDING.md](ONBOARDING.md) → Quick start below |
| **Human** understanding the design | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Agent** in Cursor | [INSTRUCTIONS.md](INSTRUCTIONS.md) + `@agent-memory` skill |
| **Contributor** to this framework | [CONTRIBUTING.md](CONTRIBUTING.md) · [VERSIONING.md](VERSIONING.md) |

## What is in this repo

| Area | Contents |
|------|----------|
| **Skill** (1 default) | `agent-memory` — internal docs under `skills/*/` |
| **Scripts** | distill, `sync-memory`, verify, doctor, hooks installer |
| **Templates** | Empty hub scaffolds: context, feedback, chats, Cursor hooks |
| **CI** | Tests + version-check + gitleaks on PR; GitHub Release on `v*` tag |
| **Tests** | 130+ unit/shell checks including sync, forward pointer, placeholders, routing, secrets |

Distill flow: `distill-merge.py <uuid>` → review `merge-staging/` → **semantic-merge** skill for Decisions → hooks/sync `--apply` (Recent + **## Next step**).

## Quick start

```bash
git clone https://github.com/raphael-batte/cursor-agent-memory.git
cd cursor-agent-memory
bash scripts/install-local.sh    # symlink → ~/.cursor/plugins/local/agent-memory
```

**Reload Cursor**, then:

```bash
bash scripts/init-memory.sh      # hub + anchor (idempotent)
```

In Cursor: add `@agent-memory`, then say **sync with agent memory**.

Manual sync:

```bash
python3 scripts/sync-memory.py --days 180
```

### Three locations

| Entity | Path | On plugin update |
|--------|------|------------------|
| **Bundle** (code) | `~/.cursor/plugins/local/agent-memory/` | replaced |
| **Anchor** | `~/.cursor/agent-memory/config.json` | survives |
| **Hub** (data) | from anchor (default `~/.cursor/agent-memory/`) | survives |

`MEMORY_HOME` resolution: CLI `--memory-home` → env → anchor → default.

### Config

| File | Purpose |
|------|---------|
| `~/.cursor/agent-memory/config.json` | anchor — `memory_home` only |
| `$MEMORY_HOME/config.json` | `plugin_root`, `memory_home` (hub-local) |

**Never** store secrets in `$MEMORY_HOME`. Distill redacts known patterns; `verify-memory.py` scans the hub.

Sync bootstraps Projects in GLOBAL_CONTEXT from distills. Hooks keep **## Next step** fresh (heuristic pointer or explicit placeholder with drill link).

## Migration, skills, status

```bash
bash scripts/migrate-memory.sh --from /path/to/old-hub --to "$MEMORY_HOME"
python3 scripts/memory-doctor.py --fix
python3 scripts/memory-status.py --brief
```

**Legacy:** if you used `link-cursor-skills.sh` or global `~/.cursor/hooks.json` entries, remove them after plugin install to avoid double distill — see [MIGRATION.md](MIGRATION.md).

## Docs map

| File | Audience |
|------|----------|
| [ONBOARDING.md](ONBOARDING.md) | **Humans** — fresh clone, one skill, sync command |
| [ARCHITECTURE.md](ARCHITECTURE.md) | **Humans** — layers, routing, distill pipeline |
| [docs/SYNC-AND-TRIGGERS.md](docs/SYNC-AND-TRIGGERS.md) | **Humans/devs** — hooks, sync pipeline |
| [MIGRATION.md](MIGRATION.md) | **Humans** — migrate hub, advanced workflows |
| [INSTRUCTIONS.md](INSTRUCTIONS.md) | **Agents** — session start/end, rotation, secrets |
| [CONTRIBUTING.md](CONTRIBUTING.md) | **Contributors** — PR workflow, CI |
| [VERSIONING.md](VERSIONING.md) | SemVer, tags, releases |
| [SKILL.md](SKILL.md) | Cursor `@agent-memory` entry |
| [templates/](templates/) | Empty scaffolds |

## Scripts (common)

```bash
python3 scripts/list-chats.py --pending
python3 scripts/distill-extract.py <uuid> --strategy auto
python3 scripts/distill-merge.py <uuid> --strategy auto --memory-home "$MEMORY_HOME"
python3 scripts/distill-merge.py <uuid> --apply --memory-home "$MEMORY_HOME"
python3 scripts/verify-memory.py --memory-home "$MEMORY_HOME"
bash scripts/weekly-verify.sh --dry-run
```

**Tests:** `bash tests/run-tests.sh`

## License

[MIT](LICENSE) — clone, fork, modify freely. [Contributing](CONTRIBUTING.md): PR → `main`.
