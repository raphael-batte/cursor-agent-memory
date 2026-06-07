# Changelog

All notable changes to **cursor-agent-memory** (framework). Format [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning [SemVer](https://semver.org/).

Data hub (`$MEMORY_HOME`) is **not** versioned with this file.

## [Unreleased]

## [0.9.0] - 2026-06-07

### Removed

- **Per-repo handoff layer** — `AGENT_HANDOFF.md`, `handoff_mode`, `templates/repo-handoff/`, `agent-handoff.mdc`

### Added

- **`## Next step`** forward pointer in `chats/projects/<slug>.md` — auto-extracted on every boundary distill (`lib/forward_pointer.py`)
- Boundary hooks use `apply=True` — Recent + Next step written on `sessionEnd` / `preCompact` / catch-up

### Changed

- Session routing: distill **Next step** first (no repo handoff files)
- `sync-memory.py` — no `--handoff-mode`; SKILL / INSTRUCTIONS / ONBOARDING updated

## [0.8.9] - 2026-06-07

### Added

- First sync seeds **`[bootstrap]` Decisions** from keyword-tagged user messages when `## Decisions` is empty
- ONBOARDING: post-sync agent offers (fill Me, review bootstrap, handoff setup); handoff section

### Changed

- `sync-memory.py` applies distills to `chats/projects/*.md` (`Recent` + bootstrap Decisions)
- `templates/feedback/fails.md` — no placeholder `_superseded § <heading>` (verify passes on fresh hub)
- README / GitHub description copy tightened

## [0.8.8] - 2026-06-07

### Changed

- Tests, fixtures, and docs use generic project names (`example-app`, `other-app`) — no real workspace names
- `tests/test_no_hardcoded_paths.py` — skip scanning itself (forbidden-pattern literals)

## [0.8.7] - 2026-06-07

### Changed

- **No hardcoded install paths** — removed `DEFAULT_INSTALL_ROOT`; install via `dev.config.json` / env / hook env only
- **Projects table paths** — decode Cursor workspace folder to real path; manifest stores `workspace_path`
- Docs/templates: `$MEMORY_HOME` / `$FRAMEWORK_ROOT` only — no legacy global config writes
- `tests/test_no_hardcoded_paths.py` — expanded forbidden path patterns

## [0.8.6] - 2026-06-07

### Added

- **Dev vs install split** — `dev.config.json` (gitignored) points dev clone at install root
- `scripts/sync-to-install.sh` — rsync framework dev → install; excludes `memory/`, `.git`, `dev.config.json`

### Changed

- **Clean dev repo** — scripts never create or use `<dev>/memory/` when `dev.config.json` exists
- `init-memory.sh`, `link-cursor-skills.sh`, `install-memory-hooks.sh` target install root + `<install>/memory/`
- Docs: [ONBOARDING.md](ONBOARDING.md), [ARCHITECTURE.md](ARCHITECTURE.md) — two-clone workflow

## [0.8.5] - 2026-06-07

### Changed

- **In-repo hub only** — default `$MEMORY_HOME` is `<clone>/memory/` (gitignored); no external hub or legacy global paths
- Framework scripts **do not write** legacy global config (read-only if present)
- `memory/config.json` holds `framework_root`, `memory_home`, `handoff_mode`
- Cursor hooks get `MEMORY_HOME` via `~/.cursor/hooks/agent-memory.env` (Cursor integration only)

## [0.8.4] - 2026-06-07

### Added

- `scripts/lib/hook_env.sh` — resolve framework clone path in Cursor hooks (no `$HOME/agent-memory` fallback)
- `persist_framework_root()` — writes real clone path to global + hub config on init/link/sync
- `tests/test_no_hardcoded_paths.py` — guard against fixed install directory in repo

### Changed

- Clone anywhere — paths resolved from config/env/script location
- Hook templates source `agent-memory.env` first; fail gracefully if framework unknown
- Restored root `SKILL.md` with `$FRAMEWORK_ROOT` / `$MEMORY_HOME` contract
- Docs: use `scripts/...` from repo root or `"$FRAMEWORK_ROOT/scripts/..."`

## [0.8.3] - 2026-06-07

### Added

- `lib/timestamps.py` — ISO `distilled_at`, mtime comparison, legacy `YYYY-MM-DD` compat

### Changed

- Re-distill when transcript **mtime** > `distilled_at` (same-day updates work)
- `manifest` / `_Last updated_` / staging use full ISO timestamps
- `collect_projects_from_manifest` keeps summary from latest `distilled_at`
- `filter_by_slugs` — exact slug match (no substring false positives)
- `sessionStart` catch-up — drop duplicate skip pass (`needs_distill` only in list)
- `_load_distill_modules()` — module-level cache
- `list-chats` STALE flag uses mtime vs `distilled_at`
- `verify-memory` rejects unparseable `distilled_at`

## [0.8.2] - 2026-06-06

### Added

- `sync-memory.py --scan-only` — fast inventory (`total_chats`, `active_90d/180d`, `pending_90d/180d`)
- Sync report fields: `distills_planned`, `truncated`, `candidates` (total before limit)

### Changed

- Sync flow: scan → user picks `--days` + `--limit` → run (documented in SKILL + ONBOARDING)
- `--dry-run` no longer reports fake `distills` count; uses `distills_planned`
- `sessionStart` catch-up skips when `workspace_roots` empty (no cross-project distill)

## [0.8.1] - 2026-06-06

### Added

- [ONBOARDING.md](ONBOARDING.md) — fresh clone walkthrough (one skill + sync)
- [docs/SYNC-AND-TRIGGERS.md](docs/SYNC-AND-TRIGGERS.md) — hooks and sync technical reference

### Changed

- INSTRUCTIONS, MIGRATION, ARCHITECTURE, README — distill-first, single skill, `handoff_mode`
- `session-end` hook checklist respects `handoff_mode: off`
- `memory-doctor.py` reports `handoff_mode`
- `init-memory.sh` next steps point to sync

## [0.8.0] - 2026-06-06

### Added

- **Distill-first core** — chat links `[title](uuid)` in staging/Recent when transcript exists
- `scripts/sync-memory.py` — init, hooks, batch distill (default 180 days), GLOBAL_CONTEXT bootstrap
- `handoff_mode` in hub config (`off` | `optional` | `required`)
- `sessionStart` catch-up distill (replaces handoff inject)
- Lib: `distill_links`, `pending_chats`, `memory_routing`, `global_context_bootstrap`
- Tests: `test_distill_links`, `test_pending_chats`, `test_memory_routing`, `test_sync_memory`, `test_global_context_bootstrap`

### Changed

- **Single skill onboarding** — `link-cursor-skills.sh` defaults to `agent-memory` only; expanded root `SKILL.md` with Sync protocol
- `preCompact` user_message references distills, not handoff
- `templates/config.json` — default `handoff_mode: optional`

### Removed

- `sessionStart` handoff `additional_context` inject (use distill + optional handoff read)

## [0.6.0] - 2026-06-06

### Added

- **Boundary hooks** — `sessionStart` injects `AGENT_HANDOFF.md` excerpt; `preCompact` / `sessionEnd` auto-distill pending chats
- `scripts/boundary-hooks.py`, `scripts/lib/boundary_hooks.py`
- Cursor templates: `agent-memory-session-start.sh`, `agent-memory-boundary.sh`
- `tests/test_boundary_hooks.py`

### Changed

- `install-memory-hooks.sh` — installs four hook scripts; merges `sessionStart`, `preCompact`, dual `sessionEnd` entries

## [0.5.1] - 2026-06-06

### Added

- [ARCHITECTURE.md](ARCHITECTURE.md) — human-oriented system overview (layers, routing, distill pipeline)

### Changed

- README — hero, layer diagram, inventory, docs map (closes gap vs INSTRUCTIONS depth)
- SKILL.md — version sync + link to ARCHITECTURE

## [0.5.0] - 2026-06-06

### Added

- **Release workflow** — `release.yml` on tag `v*`; guard tag == VERSION; GitHub Release from CHANGELOG section
- `scripts/extract-changelog.py` — extract one version block for release notes
- `.gitleaks.toml` — allowlist for test fixtures; pinned `GITLEAKS_VERSION` in CI

### Changed

- CI reusable via `workflow_call` (release job reuses test + gitleaks)
- `cross_layer_warnings` — document-frequency filter + bigram overlap; domain stopwords in `defaults.py`
- `gitleaks_scan` — auto `--config .gitleaks.toml` when present
- `--apply` no longer fills empty `## Summary` with raw `first_query` (agent/semantic-merge only)

## [0.4.3] - 2026-06-06

### Fixed

- CHANGELOG: English-only entry (CI `test_no_cyrillic_in_framework_repo`)

## [0.4.2] - 2026-06-06

### Fixed

- CI: `actions/setup-python@v6` (Node 24 native) — remove remaining setup-python deprecation warning

## [0.4.1] - 2026-06-06

### Fixed

- CI: `actions/checkout@v5`, `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` — silence Node 20 deprecation warnings

## [0.4.0] - 2026-06-06

### Added

- **semantic-merge** skill + `templates/chats/semantic-merge-prompt.md` — agent workflow for Raw candidates → Decisions
- Cursor rule `agent-memory-session-end.mdc` — checklist from `agent-memory-session.log`
- `lib/cross_layer_warnings.py` — keyword overlap fails ↔ conventions (+ superseded substring hints)
- **Generic transcript adapter** `lib/transcript_generic.py` + unified `lib/transcript.py`; hub path `$MEMORY_HOME/transcripts/<uuid>.jsonl`
- Extract field `transcript_adapter`: `cursor` | `generic`

### Changed

- `verify-memory` uses cross-layer warnings; `link-cursor-skills` includes semantic-merge
- `distill-extract` / `distill-merge` use unified transcript router

## [0.3.3] - 2026-06-06

### Fixed

- CI gitleaks job: install from versioned release asset (`gitleaks_*_linux_x64.tar.gz`)

## [0.3.2] - 2026-06-06

### Fixed

- `--apply` bookkeeping only: updates Recent≤3 + empty Summary — **does not** write raw user messages into `## Decisions`
- `--apply` target: `manifest.distilled_to` primary `projects/*.md` (not workspace slug); `--project` override
- Staging section renamed to `## Raw candidates (review — not Decisions)`

### Changed

- Hook templates aligned with `hooks.json`: `agent-memory-session-end.sh`, `agent-memory-after-edit.sh`
- Session hook logs to `~/.cursor/hooks/agent-memory-session.log` + stdout/stderr for visibility
- `gitleaks_scan`: prefers `gitleaks dir` (8.19+), falls back to `detect --no-git`

### Added

- GitHub Actions CI: `tests/run-tests.sh` + gitleaks adapter smoke on push/PR
- MIGRATION: multi-machine hub sync (private git repo)
- `primary_project_rel()` in `lib/chats_manifest.py`

## [0.3.1] - 2026-06-06

### Added

- `distill-merge.py --apply` — merge extract into `chats/projects/<slug>.md` (append Decisions, Recent≤3; secrets scan before write)
- `lib/project_merge.py` — project file merge helpers
- Hook v2: `afterFileEdit` template + `lib/hooks_config.py`; `install-memory-hooks.sh` installs sessionEnd + afterFileEdit
- `weekly-verify.sh` — cron helper (doctor + verify, strict secrets + gitleaks); `--dry-run`
- `lib/gitleaks_scan.py`; `verify-memory --gitleaks` / `--gitleaks-required`; `memory-doctor --gitleaks`
- `memory-doctor --fix` / `--fix-dry-run` — align global/hub `config.json`, relink skills (`lib/doctor_fix.py`)

### Tests

- `test_project_merge`, `test_hooks_config`, `test_gitleaks_scan`, `test_doctor_fix`; extended distill-merge, verify, doctor, shell suites

## [0.3.0] - 2026-06-06

### Added

- `distill-merge.py` — auto manifest `distilled_at`, extracts + `merge-staging/` (preserve chat language)
- `memory-doctor.py` — one-shot hub health (paths, chats, verify, skills)
- `lib/transcript_cursor.py` — Cursor jsonl adapter + `TranscriptSchemaError` + cached `find_transcript`
- `lib/chats_manifest.py`, `lib/defaults.py` — shared manifest/thresholds
- Cursor hooks template + `install-memory-hooks.sh` (sessionEnd reminder)
- `verify-memory --strict-secrets` — optional entropy scan (best-effort)
- Duplicate-lesson warnings in verify; path resolution documented in memory-doctor

### Changed

- `memory-status.py` — direct imports (no subprocess stdout regex)
- `list-chats.py` — `chat_counts()` API; cached transcript index
- Secrets docs: safety net wording (not a guarantee)
- INSTRUCTIONS: preserve chat language; distill-merge workflow

### Tests

- `test_distill_merge`, `test_transcript_cursor`, `test_memory_doctor`, `test_list_chats`, `test_defaults`, `test_chats_manifest`; updated existing suites

## [0.2.5] - 2026-06-06

### Added

- `lib/secrets_guard.py` — detect/redact secrets in distill; scan hub in `verify-memory`
- `distill-extract.py` — sanitizes user messages; JSON field `secrets_redacted`
- `verify-memory.py` — check `no secrets in hub` (context/feedback/chats)
- Tests: `test_secrets_guard.py`, `test_english_only.py`; docs: hard secrets policy in INSTRUCTIONS, MIGRATION, chat-memory skill
- English-only policy: removed Cyrillic from framework; agent prompts in MIGRATION.md translated

## [0.2.4] - 2026-06-06

### Fixed

- add MIGRATION.md setup and agent prompts guide

## [0.2.3] - 2026-06-06

### Fixed

- distill-extract --strategy spread/auto for long chats

## [0.2.2] - 2026-06-06

### Fixed

- add distill-extract.py for chat distill without raw jsonl

## [0.2.1] - 2026-06-06

### Fixed

- add unittest/shell tests; fix fails_open, --list exit code, migrate --to

## [0.2.0] - 2026-06-06

### Added

- v0.2: memory-status, config.json, skills-status, selective link, migrate

## [0.1.4] - 2026-06-06

### Fixed

- Neutral default paths: generic clone example, `$MEMORY_HOME` under clone or config

## [0.1.3] - 2026-06-06

### Added

- `scripts/publish-github.sh`

### Changed

- README: Feedback layer section; GitHub topics

## [0.1.2] - 2026-06-06

### Fixed

- Remove personal project paths and CI examples from framework docs
- `verify-memory.py`: conventions check is generic (sections), not coverage/staging keywords

## [0.1.1] - 2026-06-06

### Fixed

- Pre-commit: exempt doc-only paths (README, docs/, templates/)

## [0.1.0] - 2026-06-06

### Added

- Five memory layers: context, preferences, feedback, chats, handoff
- Skills: `agent-memory`, `global-context`, `chat-memory`, `agent-handoff`, `feedback-memory`
- `INSTRUCTIONS.md` — routing Flows A–E, session start/end, rotation
- Templates for context, feedback, chats, repo-handoff, cursor-rule
- `scripts/init-memory.sh`, `link-cursor-skills.sh`, `list-chats.py`
- `scripts/verify-memory.py` — weekly integrity checks (7 rules)
- `scripts/session-smoke.md` — session self-check + drift detection
- `_superseded → conventions.md § <heading>` format (not line numbers)
- SemVer: `VERSION`, this changelog, git pre-commit hook
