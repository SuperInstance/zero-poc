# Architecture — The Whole System, Connected

Written 2026-10-15 after a full deep dive (code, git history, live GitHub
state). Audience: any agent or human arriving cold to maintain, extend, or
explain this repo. If you only read one doc, read this one. For known quirks,
vestigial code, and open bugs, read `docs/maintenance-notes.md` next.

Everything here is verifiable from the repo itself unless marked
**[observed live]** (verified against the GitHub API / issue threads on
2026-10-15) or **[outside the repo]** (lives in Cloudflare, not in git).

## The one-paragraph version

This repo is not code *for* an agent — the repo, running on GitHub Actions,
**is** the agent ("zero", a Purple Pincher). Three workflows are its nervous
system: `think` (a heartbeat that runs a ReAct loop driven by an LLM), `react`
(conversational replies in issue threads), and `telegram` (a Telegram ear and
mouth). All privileged API access (LLM, GitHub, Cloudflare, Telegram) flows
through **the vault**, a Cloudflare Worker that holds the secrets, verifies
GitHub OIDC identity, checks an allowlist, and proxies calls — so the repo
itself holds zero secrets. Memory is git: `MEMORY.md` is the digest, the log
is the full rewindable history.

## Component map

```
                        ┌──────────────────────────────────────────────┐
                        │                CLOUDFLARE                    │
                        │                                              │
   GitHub Actions ──────┼──▶ vault worker  /proxy ──▶ LLM API          │
   (think/react/        │    - verifies OIDC     ──▶ GitHub API        │
    telegram.yml)       │    - checks allowlist  ──▶ Cloudflare API    │
        │               │    - holds the keys                         │
        │ OIDC (aud=vault)                                            │
        │               │   telegram bridge worker                    │
        │◀──────────────┼── /webhook ◀─ Telegram ── /send ──────────┐  │
        │ repository_dispatch("telegram_message")                   │  │
        ▼               └──────────────────────────────────────────┼──┘
   .github/scripts/agent.py  (ReAct brain, think.yml only)          │
        │ tool calls: files, shell, git, vault-proxied APIs          │
        ▼                                                             │
   the repo itself: TASKS.md, MEMORY.md, scratch/, code, docs        │
        │                                                             │
        └── think.yml's final step commits + pushes to main ─────────┘
```

## The three workflows (`.github/workflows/`)

All three share the same skeleton: checkout → mint a GitHub OIDC token with
`audience=vault` → do work → talk to the vault at `/proxy`. Since v0.3 the
token reaches the steps that need it via a step *output*
(`steps.oidc.outputs.token`), not `$GITHUB_ENV`, so it doesn't persist in
every later step's environment.

### `think.yml` — the heartbeat (the agent's deep-work mode)

- **Triggers**: `schedule: cron '*/15 * * * *'` plus manual
  `workflow_dispatch` (inputs: `task`, `max_iterations`). **[observed live]**
  GitHub throttles the schedule heavily — runs actually fire ~4–5 times a
  day, not 96. Every run that fires succeeds. When diagnosing "why is the
  agent slow," check the Actions tab first: the agent is usually waiting for
  GitHub, not thinking.
- **Permissions**: `id-token: write` (mint the OIDC token), `contents:
  write` / `issues: write` / `pull-requests: write` (commit results, gh
  calls).
- **Steps**: checkout with `fetch-depth: 0` (the agent reads `git log` as
  memory, so it needs full history) → Python 3.11 → get OIDC → run
  `agent.py` → **commit everything** as `zero <zero@purplepincher.org>` and
  push to main.
- The final commit step runs `git add -A` then `git reset
  .github/workflows/` — a self-modification guard. The agent can change any
  file in the repo *except its own nervous system*. (This is one of three
  such guards; see "Defense in depth" below.)
- Env plumbing: `VAULT_URL` comes from repo *variables* (not secrets).
  `GH_TOKEN` is load-bearing since v0.3: `agent.py` uses `gh` with it to
  list open issues (fallback when the vault's `list_issues` 404s) and to
  post comments as `github-actions[bot]` (the react echo-loop fix). The
  vault still carries everything privileged; see maintenance notes.

### `react.yml` — the ears (conversational layer)

- **Triggers**: issues opened/reopened, any issue comment created. The
  job `if` skips `github-actions[bot]` actors (self-loop guard) and, since
  v0.3, PR comments too (`!github.event.issue.pull_request` — `gh issue
  comment` would fail on a PR number; see maintenance notes #5).
- **Flow**: gather the issue thread with `gh` (title + body[:1500], last 10
  comments[:800] each) + first 1200 bytes each of `ONBOARDING.md` (identity)
  and `MEMORY.md` (memory digest; byte cuts are UTF-8-boundary-safe since
  v0.3) → **single-shot** LLM call via the vault
  (max_tokens 400) with a system prompt that says: be conversational; if
  asked to *do* something, acknowledge and say the next think cycle (≤15
  min) will pick it up — never claim work is done → post the reply (capped
  at 2000 bytes, UTF-8-boundary-safe) via `gh issue comment`, appearing as
  `github-actions[bot]`.
- **Design intent** (from the file header): react is *manner*, think is
  *matter*. Deep work never happens here — one LLM turn, one comment.
- **Echo loop — fixed agent-side (v0.3)**: **[observed live]** the agent's
  comments used to post through the vault, which appears as the repo
  **owner**, so react re-triggered on them and the bot replied to the
  agent's own status comments (half of issue #1's 72 comments). `agent.py`
  now posts via `gh` first — as `github-actions[bot]`, which the `if`
  above filters. The echo returns only if the vault fallback path fires.
  Details in maintenance notes #2.

### `telegram.yml` — the Telegram ear and mouth

- **Trigger**: `repository_dispatch` event `telegram_message`, fired by the
  **telegram bridge worker** **[outside the repo]** when a Telegram message
  arrives at its `/webhook`.
- **Flow**: log the message to `MEMORY.md` **and** route it onto
  `TASKS.md` under "## Open" as `- [ ] (telegram <user>) <text[:200
  flattened]>` (v0.3 — MEMORY entries age out of the think loop's
  2000-char window while TASKS.md is re-read every cycle; the text
  reaches the script through env vars, never interpolation), then
  commit+push immediately (memory first, reply second) → single-shot LLM
  call via vault (max_tokens 500, terse system prompt) → POST the reply
  (≤4000 chars) to the bridge's `/send`, which delivers it via the
  Telegram API. The agent never touches the Telegram API or bot token
  directly.

## The brain — `.github/scripts/agent.py`

A self-contained ReAct loop (Reason + Act). Only `think.yml` invokes it.
Walkthrough of `run_agent_loop()`:

1. **Observe** — `build_context()` assembles the agent's world, fresh each
   iteration: `ONBOARDING.md`[:3000] (identity), `MEMORY.md`[-2000:]
   (memory), the task (from `workflow_dispatch` input, else "check TASKS.md
   and issues"), `TASKS.md`[:2000] (board), open issues via
   `fetch_open_issues()` — vault `list_issues` first with an `gh issue
   list` fallback, source labeled, and on total failure an explicit
   "FETCH FAILED — this does NOT mean the board is empty" (first 10,
   body[:800] each), `git log --oneline -5` (recent activity), `scratch/`
   filenames (work in flight), and — since v0.3 — a "## Fleet Bottles"
   section (first line of each `for-fleet/*.md`, max 5). Note what is
   *not* included: `docs/`, `AGENTS.md`, and issue *comments* (only
   bodies). The agent must `read_file` those deliberately.
2. **Think** — one LLM call via the vault with a strict contract: the entire
   response must be a single JSON object, either
   `{"tool_calls": [...], "thinking": "...", "done": false}` or
   `{"thinking": "...", "done": true, "summary": "..."}`. The prompt lists
   the ~11 available tools.
3. **Parse** — leniently: strip markdown code fences, then take the first
   `{` to the last `}` and `json.loads`. Since v0.3 this lives in
   `parse_llm_decision()`, unit-tested in `tests/`. Unparseable responses
   are fed back with "please respond in the JSON format" and the iteration
   is consumed.
4. **Act** — `execute_tool()` runs each tool call serially; results (truncated
   to 2000 chars) are appended to the conversation as the next user message.
   A 2-second sleep paces the loop against rate limits.
5. **Repeat** until the LLM says `done` (→ append summary to `MEMORY.md`) or
   `max_iterations` is hit (default 10; → append "Hit max iterations" to
   `MEMORY.md`). Every exit path — done, max iterations, LLM error — also
   persists the cycle's vital signs to `.agent-state.json` (see below).

**The permissions model** (`PERMISSIONS` dict) has three tiers:
`auto` (execute immediately), `vault` (goes through the vault, which enforces
its own allowlist), and `deferred` (log the intent, return a
`[DEFERRED for human review: ...]` string to the LLM instead of executing).
Deferred: `write_workflow`, `delete_file`, `git_push_main`. Important nuance:
`git_push_main` has no corresponding tool — and `think.yml`'s commit step
pushes to main unconditionally after the loop exits anyway, so that tier is
aspirational, not enforced. The real guarantees are the workflow-file guards
and the vault allowlist.

**The tool surface** (all implemented in `execute_tool`):
- `read_file(path)` — repo files only (`..` blocked), truncated at 10k chars.
- `write_scratch(filename, content)` — flat files in `scratch/` only (no `/`
  or `..` in the name). Ephemeral scaffolding per `docs/memory.md`.
- `write_file(path, content)` — anywhere in the repo except `..` paths and
  `.github/workflows/`. This includes `MEMORY.md`, `ONBOARDING.md`, and
  `AGENTS.md` — the agent can rewrite its own identity and memory. That is
  by design ("it learns by doing"); the git log keeps every version.
- `run_shell(command)` — arbitrary shell on the ephemeral Actions runner,
  120s timeout, minus a tiny denylist (`rm -rf /`, `mkfs`, the fork bomb,
  `curl | bash`). This is a speed bump, not a security boundary; the real
  boundary is that the runner is throwaway and holds no secrets.
- `run_tests()` — convention-based: `pytest tests/` if `tests/` exists —
  falling back to `python3 -m unittest discover -s . -p "test_*.py" -v` when
  pytest isn't installed (the runner's setup-python may lack it) — else
  `npm test` if `package.json` exists, else "no test suite". A `tests/`
  suite now exists (added with v0.3, unittest-style and
  pytest-compatible).
- `api_github(action, params)` / `api_cloudflare(action, params)` — generic
  passthroughs to the vault's `github` / `cloudflare` services. What actions
  actually exist is defined by the vault worker, not this repo.
- `comment_issue(issue, body)` / `create_issue(title, body)` — `gh` CLI
  first since v0.3: posts as `github-actions[bot]`, which react.yml's
  actor filter skips — that identity choice is what broke the echo loop.
  Vault `github` service calls remain as fallback; those posts appear as
  the repo **owner** **[observed live]** (the vault's GitHub token is the
  owner's) and would re-trigger react — see maintenance notes #2. Owner/
  repo come from `GITHUB_REPOSITORY`, then `remote.origin.url`, then a
  loud-warned fallback to `purplepincher/zero` (the template).
- `git_commit(message)` — `git add -A`, `git reset .github/workflows/`,
  commit as `zero`. Note the loop itself never pushes; only think.yml's
  final step does.

**Vault client** (`vault_call`): plain `urllib` POST to `${VAULT_URL}/proxy`
with `{oidc_token, service, action, params}`. Two gotchas baked in: a custom
`User-Agent` (Cloudflare edge error 1010 silently blocks Python-urllib's
default UA) and a 60s timeout. `llm_think()` sends `model: "default"` unless
told otherwise; the vault maps that to its configured `LLM_MODEL`.

**Local-brain mode / hermit-crab shells (v0.3)**: set `LOCAL_LLM_URL` to any
OpenAI-compatible server's base URL (Ollama `http://localhost:11434/v1`,
llama.cpp server, vLLM, LM Studio) and `llm_think()` POSTs directly to its
`/chat/completions` — the vault is never contacted, so a local clone of this
repo thinks with its own GPU/model, no registration, no keys. Pick the model
with `LOCAL_LLM_MODEL`. This is the docs/clones.md hermit crab made
concrete:

```bash
LOCAL_LLM_URL=http://localhost:11434/v1 LOCAL_LLM_MODEL=qwen2.5-coder:7b \
  python3 .github/scripts/agent.py --task "your task here"
```

Notes: the local path uses a 120s timeout (small local models are slow and
there is no shared rate limit); `model: "default"` maps to
`LOCAL_LLM_MODEL`. GitHub-side tools degrade gracefully without tokens —
`comment_issue`/`create_issue`/`list_issues` need `GH_TOKEN` (present in
Actions; set it locally to `gh auth token` if you want those to work).
Everything else (files, shell, git, memory) works anywhere.

A complementary tier — **System-1 decision models** (fast typed
gates in front of the brain, e.g. an idle-heartbeat gate via Ollaya/laya)
— is researched and designed in `docs/system1.md`, including live
benchmark results from this repo's real state.

**State file (no longer vestigial — implemented v0.3)**:
`STATE_FILE = .agent-state.json` used to be defined and never used; now
`load_state()`/`save_state()` persist each cycle's `started_utc`, `task`,
`outcome` (`completed:...` / `max_iterations` / `llm_error`), and
`iterations_used`. It is committed with each heartbeat, so git log doubles
as a vital-signs record. It is not yet fed back into `build_context()` —
a sensible next step (see maintenance notes).

## The hands — `.github/scripts/act.py` (legacy)

`act.py` is the v0.1 executor from before the ReAct design: it reads a
`decision.json` (single `observation`/`plan`/`actions` document) and executes
`comment_issue` / `update_file` / `update_memory` via the `gh` CLI. Nothing
invokes it anymore — `agent.py`'s `execute_tool()` absorbed all of its
duties. It is kept as reference/history. Don't wire new behavior into it.

## The vault [outside the repo]

A Cloudflare Worker — the only component that holds secrets. This repo
contains its *client contract*, documented in `VAULT.md` and `docs/plugins.md`:

```
POST /proxy
{ "oidc_token": "<GitHub Actions OIDC JWT, audience=vault>",
  "service":   "llm" | "github" | "cloudflare" | ...,
  "action":    "complete" | "get_repo" | "comment_issue" | ...,
  "params":    {...} }
→ { "success": true, "result": {...} }
```

- Identity: GitHub OIDC token, minted by the workflow, `audience=vault`.
- Authorization: the vault checks a repo/workflow **allowlist** (this fork
  was registered via issue #1 "Register"; see `docs/registration.md` for the
  real procedure). Unregistered forks get nothing.
- LLM service: `complete` action; Anthropic native or any OpenAI-compatible
  endpoint via worker vars `LLM_PROVIDER` / `LLM_BASE_URL` / `LLM_MODEL`.
  Secrets (`VAULT_LLM_TOKEN`, `VAULT_GITHUB_TOKEN`, ...) live only in the
  worker. Adding a capability = adding a handler there — see
  `docs/plugins.md`.
- Telegram sidecar: a second worker (the "bridge") with `/webhook` (Telegram
  → `repository_dispatch`) and `/send` (repo → Telegram).

The vault's actual handler code is **not** in this repo — when an action
404s or behaves oddly (e.g. `list_issues`, see maintenance notes), the fix
lives in the Cloudflare worker, not here.

## The data — what each file is for

| File | Role | Who writes it |
|---|---|---|
| `ONBOARDING.md` | identity, principles, alignment | human (agent may edit by design) |
| `AGENTS.md` | operator's manual — how to run/extend/explain | human |
| `TASKS.md` | kanban board the heartbeat checks | human + agent |
| `MEMORY.md` | append-only memory digest | agent (`update_memory`, every done/max-iter; telegram log) |
| `VAULT.md` | vault client contract + security model | human |
| `docs/` | the system's self-description (this file included) | human + agents |
| `tests/` | unittest-style suite, pytest-compatible (v0.3) | humans (agent may extend) |
| `.agent-state.json` | per-cycle vital signs: start, task, outcome, iterations | agent (every cycle exit) |
| `scratch/` | per-task ephemera, not memory | agent |
| `git log` | the full, rewindable ground truth | everyone — append-only culture |

Git history is load-bearing: the agent was seeded 2026-10-04
("zero: seed the template"), woke in this fork 2026-10-05, and every
heartbeat since is a `think: autonomous cycle <utc timestamp>` commit.
Reading `git log` is reading the agent's diary.

## Defense in depth (and its limits)

Three independent guards stop the agent from rewriting its own workflows:
`write_file` rejects `.github/workflows` paths, `git_commit` resets
`.github/workflows/` before committing, and think.yml's commit step resets
it again. Everything else in the repo is agent-writable *by design*.

The deeper trust chain: LLM output → tool execution happens on an ephemeral,
secret-less runner; the only durable privilege is what the vault will proxy,
and the vault gates that on OIDC + allowlist. The `run_shell` denylist and
path checks are conveniences, not boundaries. The strongest rule in the
system is social/structural, and it's stated in AGENTS.md: **this repo holds
no secrets, ever.**

## How the pieces talk — three end-to-end flows

1. **Scheduled deep work**: cron/dispatch → think.yml → OIDC → agent.py
   ReAct loop (context from repo+vault, tools act, memory appends) →
   commit+push → human reviews via git log / issues.
2. **Issue conversation**: comment → react.yml → thread+identity+memory →
   one vault LLM turn → bot reply in thread. Deep work promised to the next
   think cycle.
3. **Telegram**: DM → bridge `/webhook` → `repository_dispatch` →
   telegram.yml → MEMORY.md log + TASKS.md "## Open" routing commit → one
   vault LLM turn → bridge `/send` → reply in Telegram.

## Extension points (where to plug in)

- **New capability** → new vault service handler + doc in `docs/plugins.md`;
  the agent reaches it via `api_github`-style passthrough or a new tool in
  `agent.py`'s prompt + `execute_tool`.
- **New senses/reflexes** → new workflow triggered by whatever event,
  following the react.yml single-shot pattern.
- **Teaching the agent** → edit `ONBOARDING.md` (identity), add `TASKS.md`
  entries or issues (work), append `MEMORY.md` (facts), or drop a bottle
  in `for-fleet/` (fleet broadcast — surfaced in context since v0.3). The
  think loop still does *not* auto-include `docs/` or `AGENTS.md` — teach
  via the files it does read, or tell it to `read_file` the docs.
