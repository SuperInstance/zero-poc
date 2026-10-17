# CONTEXT.md — Working Memory

<!-- Rewritten, never appended (Sprint-0 D5). Live load-bearing facts
     only. MEMORY.md remains the append-only event log; git history is
     the archive. The consolidation job (02:17, future) rewrites this
     file from git; until then, owner maintenance does. -->

## Facts
| claim | sha | ts (UTC) | confidence |
|---|---|---|---|
| My brain is agent.py (ReAct loop); LLM via vault; I run in GitHub Actions on a throttled cron + a 6h duty-cycle probe | 180e304 | 2026-10-17 | high |
| Before each LLM cycle a System-1 idle gate can skip me if nothing is actionable; the gate never sees its own prior verdict | 180e304 | 2026-10-17 | high |
| I must not write "Completed: awaiting instructions" when I did nothing substantive (outcome completed_noop, no MEMORY write) | 180e304 | 2026-10-17 | high |
| Memory entries that cite no commit SHA are stamped [unverified, date] | c0f6e49 | 2026-10-17 | high |
| Casey DiGennaro (SuperInstance) is my owner; instructions arrive via TASKS.md "## Open", GitHub issues, or Telegram DMs | dcae9d8-era docs | 2026-10-15 | high |
| The vault's list_issues action 404s; gh CLI is the working fallback (GH_TOKEN in think.yml) | dcf0469 | 2026-10-15 | high |
| Repo rules: never put secrets in the repo; workflows are my nervous system (edits get extra validation); MEMORY.md is append-only | docs/architecture.md | 2026-10-15 | high |

## Open Questions
| question | since | notes |
|---|---|---|
| Register as a fork in the fleet? | 2026-10-05 | issue #1 closed 2026-10-17; resurfaces on the board if needed |

## Blocked / Waiting
| item | blocked on | since |
|---|---|---|
| Active gate in Actions (DECISION_URL) | vault decision service or vendored minigate | 2026-10-16 |
