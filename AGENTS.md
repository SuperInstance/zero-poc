# AGENTS.md — Operator's Manual for the Purple Pincher Zero

You are an agent reading this. This document tells you everything you need to
operate, extend, and explain this system. It is written so that an agent
arriving cold can understand the whole thing from these pages and then explain
it accurately to their human — because that is how documentation travels now:
an agent digests, then tells their person. If something here is unclear, that
is a bug in the docs.

## What this is

This repo IS an agent. Not code for an agent — the repo itself, running on
GitHub Actions, is the agent. It is called a Purple Pincher zero.

- **Body**: this repo — files, workflows, scripts.
- **Heartbeat**: the `think` workflow, on a schedule (GitHub throttles
  `*/15` crons; ~4–5×/day observed in practice). It runs the ReAct loop
  (`.github/scripts/agent.py`): observe → think → act → repeat.
- **Ears**: the `react` workflow (GitHub issues and comments) and the
  `telegram` workflow (Telegram messages via the bridge worker).
- **Brain**: an LLM, reached only through the vault. Never directly, never with
  keys in the repo.
- **Hands**: the think loop's tools — files, a shell on the runner (with
  outbound internet), git, the `gh` CLI, and vault-proxied APIs (LLM, GitHub,
  Cloudflare). Telegram goes through a separate bridge worker, not the vault.
  Extensible (see `docs/plugins.md`; the tool index is `TOOLS.md`).
- **Memory**: `CONTEXT.md` (working memory), `MEMORY.md` (event log),
  `conversation/` (the dialogue), `reports/` (finished work), and the git log
  under all of it (see `docs/memory.md`).

The full component map, request flows, and file-by-file reference live in
`docs/architecture.md`. Known issues, quirks, and vestigial code live in
`docs/maintenance-notes.md`. If those two files can't answer your question,
the docs have a bug — fix them.

## The one rule

This repo holds NO secrets. API keys live in the vault, a Cloudflare Worker.
The agent proves its identity with GitHub OIDC; the vault verifies the token,
checks the allowlist, and proxies the API call. The secret never leaves the
worker. If you ever feel tempted to put a key in a file, stop and read
`VAULT.md`.

## Fork and go

1. Fork this repo.
2. Register with the vault: open an issue titled "Register" — the fleet
   coordinator adds your repo to the vault allowlist.
3. Done. The heartbeat wakes on a schedule (GitHub throttles the cron; a
   few times a day in practice). Open an issue to give it a task.

## How to talk to it

- **Issues**: open an issue or comment on one. The `react` workflow
  acknowledges; the next think cycle acts. This is also the agent-to-agent
  channel (see `docs/i2i.md`).
- **Telegram**: message its bot, if the fork owner configured one. The
  `telegram` workflow records the message in `conversation/inputs/`, routes
  it onto `TASKS.md`, thinks via the vault, records the reply in
  `conversation/outputs/`, and sends it. It cannot message first: work the
  loop finished rides back on the next reply (`reports/README.md`).
- **TASKS.md**: the onboard task board. The heartbeat checks it every cycle.

## How to teach it things

- Edit `ONBOARDING.md` — that is its identity, its principles, and its
  alignment. The alignment section orients it around understanding its own
  system and explaining it to humans and agents alike.
- Add tasks to `TASKS.md` or open issues.
- Put live facts in `CONTEXT.md` — the working memory the loop reads every
  cycle (rewritten by hand for now). The loop appends its cycle outcomes to
  `MEMORY.md` itself, and can edit any of these files and the docs.
- The loop reads `ONBOARDING.md`, `CONTEXT.md`, `TASKS.md`, `TOOLS.md`, open
  issue bodies and `git log -5` every cycle — not `docs/`, not this file.
  Teach through what it reads.

## How to extend it

See `docs/plugins.md`. Short version: a plugin is a new vault service — a
handler function in the vault worker, a secret stored in the worker, and an
allowlist entry. The agent calls it through the same `/proxy` endpoint as
everything else.

## How it remembers

See `docs/memory.md`. Short version: `CONTEXT.md` is rewritten; everything
else — `MEMORY.md`, `conversation/`, delivered reports, the git log — is
append-only. The git log is the full, rewindable history.

## Explaining this system (your duty)

When a human — or another agent — asks you about this system, explain from
these docs, concretely: the vessel, the heartbeat, the ears, the vault, the
memory, the fork-and-go path. If you cannot answer from these docs, say so
plainly and note what is missing. Then consider writing it down.
