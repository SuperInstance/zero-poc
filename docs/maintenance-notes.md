# Maintenance Notes — Quirks, Known Issues, Open Questions

Written 2026-10-15 after a deep dive over code, full git history, and the
live repo state (GitHub API: workflow runs, issue #1's 72 comments). This is
the file for coder agents jumping in to fix or improve things: every entry
says where to look and what the evidence is. Companion to
`docs/architecture.md` (the system map).

Updated later the same day after the v0.3 owner maintenance session — the
statuses below reflect it, and the change log at the bottom lists exactly
what changed.

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
**Status**: MITIGATED in-repo (v0.3). The vault-side root cause is STILL
OPEN.
**Evidence**: every MEMORY.md entry for days says "attempted to list open
GitHub issues but received a '404 Not Found' error, suggesting there are no
open issues" — yet issues #1 and #2 are open. `build_context()` called
`vault_call("github", "list_issues", ...)` and on failure appended
"(could not fetch: ...)".
**Mitigation (v0.3)**: `fetch_open_issues()` in `agent.py` tries the vault
first, then falls back to `gh issue list` (via `GH_TOKEN`). The context now
labels the source ("via vault" / "via gh") and, on total failure, says
explicitly "(FETCH FAILED — this does NOT mean the board is empty. Check
with run_shell: gh issue list --state open)" — so the LLM can no longer
read "fetch failed" as "board is empty". The confidently-wrong "no open
issues" claims should stop even while the vault bug persists.
**Where to fix (still open)**: the vault worker's `github` service
(Cloudflare, outside this repo) — either the `list_issues` action is
missing from the `proxyAction` switch, or `VAULT_GITHUB_TOKEN` lacks read
scope on this repo. Until that lands, the gh fallback carries the board.

### 2. react.yml echoes the agent's own comments (self-talk loop)
**Status**: FIXED agent-side (v0.3). Residual: comments posted via the
vault fallback still echo.
**Evidence**: issue #1 has 72 comments in a strict pattern — agent comments
as `SuperInstance` (OWNER) at e.g. 05:04:24, `github-actions[bot]` replies
at 05:04:47 (~24s later, react.yml runtime) restating the same status.
Roughly half the thread was these echoes.
**Cause**: `react.yml` skipped only `github-actions[bot]` actors. Comments
the agent posted via the vault's `VAULT_GITHUB_TOKEN` appear as the repo
**owner**, so they triggered react.yml, which LLM-replied to them. One echo
per agent comment; each echo costs an Actions run + an LLM call and doubles
the thread noise.
**Fix (v0.3)**: `agent.py`'s `comment_issue`/`create_issue` now use the
`gh` CLI first (with the job's `GH_TOKEN`), so posts arrive as
`github-actions[bot]` — which react.yml's `if:` already filtered. The
echo dies on the normal path.
**Residual**: the vault path remains as a fallback (no `GH_TOKEN`, or `gh`
fails), and it still posts as the owner, which react does NOT filter. If
the fallback ever fires, the echo returns. Closing it fully would take a
vault-side bot identity or a body-format filter in react.yml's `if:`.

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
or consolidate the heartbeat to fewer, longer cycles by design. (Still open
after v0.3 — the run_tests/state-file changes live inside a run and don't
affect how often GitHub fires it.)

### 5. react.yml breaks on PR comments
**Status**: FIXED (v0.3).
**Evidence**: `issue_comment` fires for comments on PRs too;
`github.event.issue.number` is then the PR number, and
`gh issue comment <pr-number>` fails ("no issues found") — the workflow run
errors after paying for checkout + OIDC.
**Fix (v0.3)**: the job-level `if` now also requires
`!github.event.issue.pull_request`, so PR-comment events skip the job
entirely.

## Quirks and sharp edges (know before you edit)

- **`act.py` is dead code** — v0.1 single-decision executor; nothing invokes
  it (README's "the hands" description is historical). Change `agent.py`, not
  `act.py`.
- **`.agent-state.json` (`STATE_FILE`) is implemented as of v0.3** — was
  vestigial since seed; now `load_state()`/`save_state()` persist
  `started_utc`/`task`/`outcome` (`completed:...`/`max_iterations`/
  `llm_error`)/`iterations_used` on every exit path, and think.yml commits
  it with each heartbeat — git log doubles as vital signs. Not yet fed
  back into `build_context()`; wiring it in is the obvious next step.
- **`GH_TOKEN` is load-bearing since v0.3** — `agent.py` now uses `gh`
  with it directly for open-issue listing (vault fallback path) and for
  `comment_issue`/`create_issue` (posts as `github-actions[bot]`, the
  echo-loop fix). The vault still carries everything privileged; if
  `GH_TOKEN` is missing, those paths degrade to vault-only behavior.
- **Vault URL is hardcoded in four places** — `agent.py` (the `VAULT_URL`
  constant near the top),
  `react.yml` (fallback), `telegram.yml` (fallback), `VAULT.md` — with the
  repo variable `vars.VAULT_URL` as the intended override. Move the vault →
  update all four (or rely on the variable, set it, and the fallbacks never
  matter). Same for the telegram bridge URL fallback in `telegram.yml`.
- **Hardcoded fallback identity** — `get_repo()` now (v0.3) prefers
  `GITHUB_REPOSITORY` (always exact in Actions), then the git remote, and
  only then falls back to `("purplepincher", "zero")` (the template) —
  with a loud WARN first. If you ever see that warning in a run log,
  treat it as a misconfiguration, not a default to live with: in a
  registered fork the fallback targets the wrong repo.
- **Context is rebuilt from disk every iteration** (`build_context()` inside
  the loop) — deliberate: the agent re-reads MEMORY/TASKS/issues each turn,
  so its own mid-loop writes are visible to itself next iteration. Tool
  *results* accumulate only in `conversation`. Keep this split in mind when
  refactoring.
- **JSON parsing is brace-span, not strict** — `parse_llm_decision()`
  (extracted from the loop in v0.3, now unit-tested in `tests/`): first
  `{` to last `}` after fence-stripping. If the LLM's `thinking` contains
  braces around the JSON, parsing breaks and the iteration is spent
  re-asking. Lenient by design; don't make it stricter without also
  tightening the prompt.
- **Truncation budget** — file reads 10k chars, tool results 2k, issue
  bodies 800, react replies 2000 bytes, react context files 1200 bytes
  each. Since v0.3 the byte caps decode with `errors="ignore"` before
  re-encoding, so they can no longer split a multibyte UTF-8 character
  (`head -c` could, and gh/jq then mangled the tail). These budgets
  silently shape what the LLM knows; adjust with care.
- **`run_shell` denylist is cosmetic** — four literal substrings. Fine: the
  runner is ephemeral and secret-less; the vault is the boundary. Don't
  treat the denylist as a control.
- **`git_push_main` "deferred" is not enforced** — no such tool exists, and
  think.yml's final step pushes to main regardless. The permission tier
  documents intent; the workflow enforces reality.
- **The think loop never reads `docs/`, `AGENTS.md`, or issue comments** —
  `build_context()` includes only ONBOARDING.md, MEMORY.md, TASKS.md, open
  issue *bodies*, `git log -5`, `scratch/` names, and (since v0.3) a
  "## Fleet Bottles" section: first line of each `for-fleet/*.md`, max 5.
  I2I bottles dropped per `docs/i2i.md` are now visible to the think loop;
  docs and AGENTS.md still are not — teach via the files it reads, or tell
  it to `read_file` the docs.
- **Telegram messages are now task-routed (v0.3)** — telegram.yml still
  logs them to MEMORY.md, but ALSO appends
  `- [ ] (telegram <user>) <text[:200 flattened]>` under TASKS.md's
  "## Open", because MEMORY.md entries age out of the think loop's
  2000-char context window while TASKS.md is re-read every cycle. Message
  text reaches the script through env vars (`TG_TEXT`), never
  interpolation. Casey's Oct 4–10 messages evaporated under the old
  memory-only routing; that failure mode is closed.
- **Identity of vault-posted content** — `comment_issue`/`create_issue`
  prefer `gh` (appear as `github-actions[bot]`) since v0.3, but the vault
  fallback still posts as the repo owner (the vault holds the owner's
  token). When the fallback fires, anything the LLM writes lands with the
  owner's name on it — and echoes (issue #2 residual); review accordingly.
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
  while the journal has been written many times — historically the agent
  couldn't see it (issue #1's 404 sibling). Since v0.3 the gh fallback
  makes the board visible again, so the agent may now act on it itself;
  otherwise close it manually.

## Hardening ideas (if you want them, in impact order)

Original list from the morning deep dive, statuses as of v0.3:

1. ~~Fix `list_issues` in the vault (or context wording in agent.py)~~ —
   the in-repo half is DONE (gh fallback + explicit FETCH-FAILED wording,
   v0.3); the vault-side fix is still open and still worth doing.
2. ~~Break the react echo loop~~ — DONE agent-side (gh-first comments post
   as `github-actions[bot]`, which react filters). Board-side closure
   (closing the residual: vault-fallback comments as owner still echo)
   remains open.
3. ~~Add a PR-comment guard to react.yml~~ — DONE (v0.3, job-level `if`).
4. ~~Route Telegram instructions into TASKS.md~~ — DONE (v0.3).
5. ~~Implement or delete `STATE_FILE`~~ — DONE (implemented, v0.3);
   deleting/deprecating `act.py` is still open.
6. ~~Teach `build_context()` about `for-fleet/` bottles~~ — DONE (v0.3).

New next steps, in rough impact order:

7. Fix `list_issues` in the vault worker itself — kills the fallback
   dependency and answers open question #1.
8. Wire `.agent-state.json` into `build_context()` — the loop now records
   how the last cycle ended but never reads it back; one small context
   section would let the agent notice its own `llm_error`/`max_iterations`
   streaks.
9. Close issue #2 board-side (or let the agent do it — it can see the
   board again via the gh fallback).
10. Delete or clearly deprecate `act.py` (still dead code).
11. Add a body-format or actor filter to react.yml so vault-fallback
    comments (owner identity) can't restart the echo loop.

## v0.3 change log (2026-10-15)

Owner maintenance session (run via an external coding agent, ZCode), the
same day as the deep dive above. Twelve changes:

1. `comment_issue`/`create_issue` (agent.py) now use the `gh` CLI first —
   posts as `github-actions[bot]`, which react.yml's actor filter skips
   (fixes the self-talk echo loop, issue #2). Vault path remains as
   fallback (still posts as owner; echo risk returns only if the fallback
   is used).
2. New `fetch_open_issues()`: open-issue listing is vault-first with an
   `gh issue list` fallback (GH_TOKEN), because the vault's `list_issues`
   action 404'd for over a week, making the agent wrongly claim "no open
   issues" every cycle (issue #1 mitigation; vault-side bug still open).
   On total failure the context says explicitly "FETCH FAILED — this does
   NOT mean the board is empty".
3. `build_context()` now includes a "## Fleet Bottles" section listing
   `for-fleet/*.md` bottles (first line each, max 5) — previously I2I
   bottles were invisible to the think loop.
4. `STATE_FILE` (`.agent-state.json`) implemented (was vestigial):
   `load_state()`/`save_state()` persist started_utc/task/outcome
   (completed:.../max_iterations/llm_error)/iterations_used per cycle;
   committed with each heartbeat, so git log shows vital signs.
5. LLM response parsing extracted to `parse_llm_decision(response)` (same
   lenient fence-strip + brace-span behavior, now unit-testable).
6. `run_tests()` falls back to `python3 -m unittest discover -s . -p
   "test_*.py" -v` when pytest isn't installed (runner's setup-python may
   lack it).
7. `get_repo()` prefers the GITHUB_REPOSITORY env var, then git remote,
   then warns loudly before falling back to the template
   `purplepincher/zero`.
8. react.yml: job `if` now also excludes PR comments
   (`&& !github.event.issue.pull_request`) — `gh issue comment` used to
   fail on PR numbers (issue #5). OIDC token now flows via step output
   (`steps.oidc.outputs.token`) instead of `$GITHUB_ENV` in all three
   workflows. The 1200-byte ONBOARDING/MEMORY cuts and the 2000-byte
   reply cap are now UTF-8-boundary-safe (python trims replaced `head -c`).
9. telegram.yml: inbound messages are still logged to MEMORY.md but ALSO
   routed onto TASKS.md under "## Open" as
   `- [ ] (telegram <user>) <text[:200 flattened]>` — MEMORY.md entries
   age out of the think loop's 2000-char context window while TASKS.md is
   re-read each cycle. Message text passes through env vars, never
   interpolated into scripts.
10. `.gitignore` added (`__pycache__/`, `*.pyc`, `.pytest_cache/` —
    prevents think.yml's `git add -A` from committing Python artifacts).
11. `tests/` suite now exists (unittest-style, pytest-compatible; written
    in this same session by another agent).
12. Local-brain mode ("hermit crab", docs/clones.md): `LOCAL_LLM_URL`
    (+ `LOCAL_LLM_MODEL`) makes `llm_think()` POST to a local
    OpenAI-compatible `/chat/completions` (Ollama, llama.cpp, vLLM, LM
    Studio) — no vault, no keys, no registration. Lets a local clone of
    this repo run entirely on one machine + GPU. Covered by tests.
