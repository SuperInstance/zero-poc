# Maintenance Notes — Quirks, Known Issues, Open Questions

Written 2026-10-15 after a deep dive over code, full git history, and the
live repo state (GitHub API: workflow runs, issue #1's 72 comments). This is
the file for coder agents jumping in to fix or improve things: every entry
says where to look and what the evidence is. Companion to
`docs/architecture.md` (the system map).

## Verified live behavior (as of 2026-10-15)

- The fork **SuperInstance/zero-poc** is a live, registered agent. Parent
  template: `purplepincher/zero`. Heartbeat commits every run GitHub fires.
- All scheduled think runs succeed; the bottleneck is GitHub, not the code
  (see next section).
- Since ~2026-10-08 the agent is in an "awaiting instructions" steady
  state: each cycle it finds no tasks, comments on issue #1, appends one
  line to `MEMORY.md`, commits. That's correct behavior for an empty board —
  but note how much noise it generates (see the echo loop below).
- Since seed, the agent has modified exactly three files: `MEMORY.md`,
  `TASKS.md`, and `docs/registration.md` (which it wrote wrong — see
  "Dangerous doc" below). All code is still the human's seed, untouched.

## Known issues (ranked by impact)

### 1. `list_issues` through the vault 404s every cycle
**Evidence**: every MEMORY.md entry for days says "attempted to list open
GitHub issues but received a '404 Not Found' error, suggesting there are no
open issues" — yet issues #1 and #2 are open. `build_context()`
(`agent.py:295-305`) calls `vault_call("github", "list_issues", ...)` and on
failure appends "(could not fetch: ...)".
**Impact**: the agent's context claims issues can't be fetched; the LLM then
*concludes* there are no open issues and says so in comments — confidently
wrong, every cycle. It also never sees issue #2 ("Write your first journal
entry") as open work.
**Where to fix**: the vault worker's `github` service (Cloudflare, outside
this repo) — either the `list_issues` action is missing from the
`proxyAction` switch, or `VAULT_GITHUB_TOKEN` lacks read scope on this repo.
Alternatively harden `agent.py` to distinguish "fetch failed" from "empty"
in the prompt text so the LLM stops guessing.

### 2. react.yml echoes the agent's own comments (self-talk loop)
**Evidence**: issue #1 has 72 comments in a strict pattern — agent comments
as `SuperInstance` (OWNER) at e.g. 05:04:24, `github-actions[bot]` replies
at 05:04:47 (~24s later, react.yml runtime) restating the same status.
**Cause**: `react.yml` skips only `github-actions[bot]` actors
(`if: github.actor != 'github-actions[bot]'`). Comments the agent posts via
the vault's `VAULT_GITHUB_TOKEN` appear as the repo **owner**, so they
trigger react.yml, which LLM-replies to them. One echo per agent comment;
each echo costs an Actions run + an LLM call and doubles the thread noise.
**Where to fix**: either post agent comments as a dedicated bot identity
(vault-side), or have react.yml ignore comments whose body matches the
agent's status format, or gate on `github.event.comment.user.id` of the
owner when the actor is the vault's identity. Any of these is a small patch
to `react.yml`'s `if:` or the vault's `comment_issue`.

### 3. `docs/registration.md` is hallucinated and dangerous
**Evidence**: the doc instructs forks to "update the repository secrets with
the vault credentials" and "modify configuration files (e.g. `.env`,
`config.yaml`) to include the vault credentials" — a direct violation of the
system's one rule (AGENTS.md: "This repo holds NO secrets"). It was written
by the agent early in its life (git blame: appears in the only agent-made
docs commit) and describes a registration flow that doesn't exist.
**Where to fix**: the real procedure is: open an issue titled "Register" in
your fork; the fleet coordinator adds the repo to the vault allowlist
(VAULT.md "Registration" section). **This doc was rewritten on 2026-10-15**
to match reality; if you find a fork still carrying the old text, fix it
there too.

### 4. Cron says every 15 minutes; GitHub fires ~4–5 runs/day
**Evidence**: `think.yml` has had `cron: '*/15 * * * *'` since the seed
commit (43a5375, unchanged since). The Actions API shows scheduled runs at
e.g. 00:24, 05:04, 09:59, 14:54, 19:00 on 2026-10-15 — every ~5h, all
`conclusion=success`.
**Interpretation**: GitHub throttles/delays scheduled workflows on shared
runners; a */15 cron on a quiet repo reliably degrades to a few runs a day.
Not a bug in this repo, but it changes the product: "wakes every 15 minutes"
(README/AGENTS.md) overpromises. react/telegram remain event-driven and fast.
**If 15-min cadence matters**: `workflow_dispatch` from an external pinger,
or consolidate the heartbeat to fewer, longer cycles by design.

### 5. react.yml breaks on PR comments
**Evidence**: `issue_comment` fires for comments on PRs too;
`github.event.issue.number` is then the PR number, and
`gh issue comment <pr-number>` fails ("no issues found") — the workflow run
errors after paying for checkout + OIDC.
**Where to fix**: early-exit `if: github.event.issue.pull_request == ''` in
react.yml.

## Quirks and sharp edges (know before you edit)

- **`act.py` is dead code** — v0.1 single-decision executor; nothing invokes
  it (README's "the hands" description is historical). Change `agent.py`, not
  `act.py`.
- **`.agent-state.json` (`STATE_FILE`) is vestigial** — defined at
  `agent.py:31`, never read or written. Safe to delete or implement
  (loop-persistence across cycles is the obvious use).
- **`GH_TOKEN` is passed to agent.py but never read** — all GitHub traffic
  goes through the vault by design. Harmless; confusing. (`react.yml` and
  `telegram.yml` *do* use `gh` + `GH_TOKEN` directly.)
- **Vault URL is hardcoded in four places** — `agent.py:28`,
  `react.yml` (fallback), `telegram.yml` (fallback), `VAULT.md` — with the
  repo variable `vars.VAULT_URL` as the intended override. Move the vault →
  update all four (or rely on the variable, set it, and the fallbacks never
  matter). Same for the telegram bridge URL fallback in `telegram.yml`.
- **Hardcoded fallback identity** — `get_repo()` returns
  `("purplepincher", "zero")` (the template) if the remote can't be parsed.
  In a registered fork that fallback would target the wrong repo; failures
  here should probably be loud, not defaulted.
- **Context is rebuilt from disk every iteration** (`build_context()` inside
  the loop) — deliberate: the agent re-reads MEMORY/TASKS/issues each turn,
  so its own mid-loop writes are visible to itself next iteration. Tool
  *results* accumulate only in `conversation`. Keep this split in mind when
  refactoring.
- **JSON parsing is brace-span, not strict** — first `{` to last `}` after
  fence-stripping (`agent.py:405-427`). If the LLM's `thinking` contains
  braces around the JSON, parsing breaks and the iteration is spent
  re-asking. Lenient by design; don't make it stricter without also
  tightening the prompt.
- **Truncation budget** — file reads 10k, tool results 2k, issue bodies
  800, react replies 2000 **bytes** (can cut mid-UTF-8-character; cosmetic),
  react context files 1200 bytes each. These silently shape what the LLM
  knows; adjust with care.
- **`run_shell` denylist is cosmetic** — four literal substrings. Fine: the
  runner is ephemeral and secret-less; the vault is the boundary. Don't
  treat the denylist as a control.
- **`git_push_main` "deferred" is not enforced** — no such tool exists, and
  think.yml's final step pushes to main regardless. The permission tier
  documents intent; the workflow enforces reality.
- **The think loop never reads `docs/`, `AGENTS.md`, or `for-fleet/`** —
  `build_context()` includes only ONBOARDING.md, MEMORY.md, TASKS.md, open
  issue bodies, `git log -5`, and `scratch/` names. I2I bottles dropped in
  `for-fleet/` (per `docs/i2i.md`) are invisible until something teaches the
  agent to look. If you rely on bottles, add them to `build_context()` or
  to ONBOARDING.md's standing instructions.
- **Telegram messages are memory-logged but not task-routed** — telegram.yml
  appends to MEMORY.md and replies conversationally; it never creates
  TASKS/issues, so Telegram instructions only become work if a later think
  cycle notices them in the memory digest (last 2000 chars — old Telegram
  entries age out of context quickly). Casey's Oct 4–10 messages mostly
  evaporated this way.
- **Identity of vault-posted content** — `comment_issue`/`create_issue`
  appear as the repo owner (the vault holds the owner's token). Anything
  the LLM writes lands with the owner's name on it; review accordingly.
- **react.yml's system prompt has one load-bearing line** — "do NOT claim
  you have done it" (acknowledge, defer to next think cycle). It's what
  keeps the conversational layer honest; preserve it when editing.

## Open questions (unresolved at time of writing)

- Does the vault's `github` service implement anything beyond
  `get_repo`/`comment_issue`/`create_issue` — and what exactly does its
  allowlist check (repo? workflow? actor)? The worker source isn't public;
  only behavior can tell. `list_issues` 404ing suggests the switch is
  smaller than `agent.py`'s tool prompt implies.
- Why did the first think cycles see "minimal docs" (first journal entry,
  26e7b7a) when the seed had full docs — early context truncation, or
  something else? Low stakes; noted for honesty.
- Issue #2 ("Write your first journal entry") is open with zero comments
  while the journal has been written many times — the agent can't see it
  (issue #1's 404 sibling) and no one closed it. Close it or fix
  `list_issues` first.

## Hardening ideas (if you want them, in impact order)

1. Fix `list_issues` in the vault (or context wording in agent.py) — kills
   the confidently-wrong "no open issues" claims.
2. Break the react echo loop — halves issue-thread noise and Actions spend.
3. Add `if: github.event.issue.pull_request == ''` to react.yml.
4. Route Telegram instructions into TASKS.md so they survive the 2000-char
   memory window.
5. Implement or delete `STATE_FILE`; delete or clearly deprecate `act.py`.
6. Teach `build_context()` about `for-fleet/` bottles.
