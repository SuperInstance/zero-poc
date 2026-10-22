# TOOLS.md — My Tools & Skills Index

This is the index of what I can actually do: every tool and skill
available to me, what it does, who may call it, and its permission
tier. The think loop reads this file every cycle.

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
| `read_file` | Read any file in the repo | auto |
| `write_scratch` | Write working notes under `scratch/` | auto |
| `write_file` | Write repo files (protected files excluded) | auto |
| `write_workflow` | Change `.github/workflows/` — my own reflexes | deferred |
| `delete_file` | Delete a repo file | deferred |
| `run_shell` | Run a shell command in the Actions runner sandbox | auto |
| `run_tests` | Run the repo test suite | auto |
| `git_commit` | Commit changes in the working tree | auto |
| `git_push_branch` | Push a branch | auto |
| `git_push_main` | *No such tool exists.* Listed in `PERMISSIONS` as intent only — `think.yml` pushes to main after the loop exits | deferred |
| `open_pr` | Open a pull request | auto |
| `comment_issue` | Comment on a GitHub issue (via `gh`, vault fallback) | auto |
| `create_issue` | Open a GitHub issue | auto |

Substantive tools — the ones that count as *work done* for the duty
cycle (6 hours without one and the loop must probe): `write_file`,
`run_shell`, `run_tests`, `git_commit`, `git_push_branch`.

## Senses & voice — vault services (VAULT.md, docs/plugins.md)

Called by POSTing `{oidc_token, service, action, params}` to the
vault `/proxy`. The vault verifies my GitHub OIDC identity, checks
the repo allowlist, and supplies the secret. I never hold a key.

| Service / action | What it does | Used by |
|---|---|---|
| `llm` / `complete` | One rented LLM completion — my thinking itself | think loop, telegram & react workflows |
| `github` / `list_issues` | Fetch open issues (context assembly; `gh` fallback) | think loop |
| `github` / `comment_issue`, `create_issue`, `get_repo` | GitHub API access | think loop (vault tier) |
| `api_cloudflare` | Cloudflare API access | think loop (vault tier) |
| Telegram bridge | **In:** bot webhook → `repository_dispatch` wakes the repo. **Out:** POST `/send` delivers my reply. The bridge holds the bot token | telegram workflow |

## Judgment — the System-1 gate

| Mechanism | What it does |
|---|---|
| minigate (`.github/scripts/minigate/`) + hosted TypeSafe Jev | A small decision model that judges whether a cycle's material is worth an LLM call — three-valued (act / watch / defer), behind a deadband. It gates cost; it must never block the agent outright (docs/system1.md) |

## Records — capabilities that are places, not calls

| Place | What it is |
|---|---|
| `conversation/inputs/` + `outputs/` | The verbatim dialogue with my human, both sides, paired by turn stem. Written by the telegram workflow (not a tool call); readable by everything — the substrate other work builds on (contract: `conversation/README.md`) |
| `CONTEXT.md` / `MEMORY.md` | Working memory / append-only digest — how I remember between cycles |
| `for-fleet/` | Bottles — one-line-headline messages to sibling agents |

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
