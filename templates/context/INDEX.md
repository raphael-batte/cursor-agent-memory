# Global Context — Index

L1 navigation for `$MEMORY_HOME/context/`.  
Skills: **global-context** · Framework: **agent-memory**

## When to read

**On demand** — not every session. Default repo work → `AGENT_HANDOFF.md` first.

| Situation | Read |
|-----------|------|
| Continue known project | `<repo>/AGENT_HANDOFF.md` |
| Unknown project / first hub setup | [GLOBAL_CONTEXT.md](GLOBAL_CONTEXT.md) |
| Git, CI, deploy, secrets | [conventions.md](conventions.md) |
| Hosts, paths, environments | [infra.md](infra.md) |
| Past conversations | `$MEMORY_HOME/chats/projects/<slug>.md` |
| Proposing plans / CI / deploy | `$MEMORY_HOME/feedback/` + [preferences.md](preferences.md) |

## Layer map

```
context/           who + rules + preferences
feedback/          what worked/failed (+/−)
chats/projects/    what we discussed (neutral)
<repo>/handoff/    where we are now
```

## Where to write

| Change | File |
|--------|------|
| New project row | `GLOBAL_CONTEXT.md` |
| Cross-project rule | `conventions.md` |
| Host / path | `infra.md` |
| Session progress | `<repo>/AGENT_HANDOFF.md` |
| Chat decisions | `chats/projects/<slug>.md` |
| Rejected / praised approach | `feedback/fails.md` / `wins.md` |
| Thinking style | `preferences.md` |

## Rotation (conventions)

When `conventions.md` > ~80 lines → `archive/NNN-YYYY-MM-DD-conventions-<slug>.md`

| NNN | Date | Slug | Note |
|-----|------|------|------|
| — | — | _(none yet)_ | |
