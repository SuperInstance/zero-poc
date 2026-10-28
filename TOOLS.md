# TOOLS.md — My Tools & Skills Index

This is the index of what I can actually do: every tool and skill
available to me, what it does, who may call it, and its permission
tier. The think loop reads this file whole every cycle
(`build_context`) — so keep it tight: every row one line, and a
capability that is not indexed here is not known to the loop.

**The honesty rule:** a row in the *Available* sections is a claim
that the capability exists and works as described — it is implemented
in the place the row names. Anything not yet built lives under
*Planned* and is **not** available, whatever any other document
implies. When a capability lands, its row lands in the same commit;
when one is removed, its row goes too. An index that drifts from the
implementation is worse than no index.

Permission tiers (from `.github/scripts/agent.py`, `PERMISSIONS`):
**auto** = execute immediately · **vault** = proxied through the
vault, which checks its own allowlist · **deferred** = log the
intent; a human reviews; the tool does not execute.

## Hands — think-loop tools (agent.py `execute_tool`)

| Tool | What it does | Tier |
|---|---|---|
| `read_file` | Read a file (first 10,000 chars; paths containing `..` refused) | auto |
| `write_scratch` | Write working notes under `scratch/` | auto |
| `write_file` | Write repo files (`.github/workflows/` and `..` paths refused) | auto |
| `write_workflow` | Change `.github/workflows/` — my own reflexes | deferred |
| `delete_file` | Delete a repo file | deferred |
| `run_shell` | Run a shell command in the Actions runner sandbox — the runner has outbound internet, so `curl` reaches the world | auto |
| `run_tests` | Run the repo test suite | auto |
| `git_commit` | Commit changes in the working tree (workflow changes unstaged); never pushes | auto |
| `git_push_branch` | *Not implemented.* `auto` in `PERMISSIONS`, but `execute_tool` has no branch for it — a call returns "Unknown tool". Push with `run_shell` | auto |
| `git_push_main` | *No such tool exists.* Listed in `PERMISSIONS` as intent only — `think.yml` pushes to main after the loop exits | deferred |
| `open_pr` | *Not implemented.* `auto` in `PERMISSIONS`, but a call returns "Unknown tool". Use `run_shell` with `gh pr create` | auto |
| `comment_issue` | Comment on a GitHub issue (via `gh` as `github-actions[bot]`; vault fallback posts as the owner) | auto |
| `create_issue` | Open a GitHub issue (via `gh`; vault fallback) | auto |
| `api_github` | Any action of the vault's `github` service (what exists is defined in the vault, not here) | vault |
| `api_cloudflare` | Any action of the vault's `cloudflare` service | vault |

`api_llm` and `api_telegram` are listed in `PERMISSIONS` (vault) but are
not tools: the loop's own thinking is `llm_think`, and Telegram goes
through the bridge worker.

Substantive tools — the ones that count as *work done* for the duty
cycle (6 hours without one and the loop must probe): `write_file`,
`run_shell`, `run_tests`, `git_commit`, `git_push_branch` (listed, but
it cannot succeed — see above).

## Senses & voice — vault services (VAULT.md, docs/plugins.md)

Called by POSTing `{oidc_token, service, action, params}` to the
vault `/proxy`. The vault verifies my GitHub OIDC identity, checks
the repo allowlist, and supplies the secret. I never hold a key.

| Service / action | What it does | Used by |
|---|---|---|
| `llm` / `complete` | One rented LLM completion — my thinking itself | think loop, telegram & react workflows |
| Conversation memory | The reply call is assembled from the record: brief + exact repo identity + `CONTEXT.md` digest + recent turns from `conversation/`, widened by two v0.7 hooks — the first turn ever is always pinned in, and when a message refers back, matching turns are pulled from the full record — the voice hears with memory, not amnesiac | telegram workflow |
| Board reports | Finished board work is filed to reports/pending/ by a think.yml producer step (or by the loop itself) and delivered attached to the next Telegram reply; delivered reports archive in reports/delivered/ | think loop + telegram workflow |
| The internet | Reachable via the think loop's `run_shell` (runner has outbound access) and the vault APIs. The Telegram voice cannot browse mid-reply; a request to look something up rides `TASKS.md` to the loop | think loop |
| `github` / `list_issues` | Fetch open issues for context assembly — observed 404ing; `gh issue list` carries it | think loop |
| `github` / `comment_issue`, `create_issue` | Fallback path for the two tools above when `gh` fails | think loop (vault tier) |
| `github` / `get_repo`, `cloudflare` / * | Reached through `api_github` / `api_cloudflare` | think loop (vault tier) |
| Telegram bridge (separate worker, not `/proxy`) | **In:** bot webhook → `repository_dispatch` wakes the repo. **Out:** POST `/send` delivers my reply. The bridge holds the bot token | telegram workflow |

## Judgment — the System-1 gate

| Mechanism | What it does |
|---|---|
| Idle gate (`agent.py` `gate_says_work`) | Before a scheduled cycle, asks a decision model one yes/no question ("actionable work?") about a distilled digest; a "no" at confidence ≥ 0.6 skips the LLM (outcome `gated_idle`). `think.yml` points it at hosted TypeSafe Jev, which answers only once the `TYPESAFE_API_KEY` secret is set. Fail-open; an explicit task or the 6-hour duty cycle bypasses it (docs/system1.md) |
| Shadow gate (`.github/scripts/minigate/`, `think.yml`) | Vendored minigate runs before the loop and records `SKIP` / `RUN` / `RUN_BLIND` as `shadow_gate` in `.agent-state.json`. Observation only — it never skips a cycle |

## Records — capabilities that are places, not calls

| Place | What it is |
|---|---|
| `conversation/inputs/` + `outputs/` | The verbatim dialogue with my human, both sides, paired by turn stem. Written by the telegram workflow (not a tool call); readable by everything — the substrate other work builds on (contract: `conversation/README.md`) |
| `CONTEXT.md` / `MEMORY.md` | Working memory / append-only digest — how I remember between cycles |
| `SELF-MODEL.md` | My operative self-model — dated beliefs about how my owner sees me, each citing its evidence; revised by the loop at crossings (contract: the file's own header) |
| `reports/pending/` + `delivered/` | Finished board work waiting to be told / already told (contract: `reports/README.md`) |
| `.agent-state.json` | Last cycle's vital signs: outcome, iterations, duty-cycle clock, shadow verdict |
| `for-fleet/` | Bottles — one-line-headline messages to sibling agents; the first line of up to 5 is shown each cycle if the folder exists (it does not yet) |

## Skills — ways of working (plugins)

Grabbed capabilities that are knowledge, not calls (the grabber
contract: `plugins/README.md`; installed list: `plugins/INDEX.md`).

| Skill | What it does | Trigger |
|---|---|---|
| Weather lookup (`plugins/weather/PLUGIN.md`) | Current conditions + today/tomorrow outlook for a named place (default Sitka, Alaska) from wttr.in, via `run_shell` + `jq`. Measured numbers only; a failed lookup is reported as failed — never estimated | A human asks about the weather, or a board task asks to look it up |

## Planned — NOT available

*(Empty. A planned capability gets a row here — name, intended
shape, what would make it real — and moves up only when it works.)*

## Adding a tool or skill

1. **Think-loop tool:** implement it in `agent.py` (`execute_tool` +
   a `PERMISSIONS` entry with a deliberate tier), cover it with a
   test, add its row above — same commit.
2. **External capability:** add it as a vault plugin per the
   `docs/plugins.md` checklist (secret in the vault, handler,
   doc) — never as new infrastructure in the repo, never with a key.
3. **Skill (a way of working, not a call):** write it as a doc the
   loop actually reads (this file, `ONBOARDING.md`, or a `docs/`
   page it is pointed at), and index it here with its trigger —
   when it should be used.
