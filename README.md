<div align="center">

# 🦀 Purple Pincher Zero

**The minimal git-native agent. Fork this repo, register with the vault, and it starts working your repo.**

No server. No hosting. No keys in the repo. The repo *is* the agent.

</div>

---

## What is this?

Zero is the smallest complete seed of a Purple Pincher: an AI agent that lives entirely in GitHub.

- **Commits** are work
- **Branches** are explorations
- **Issues** are the task board
- **PRs** are communication
- **Git log** is memory — rewindable, time-shaped, not a snapshot

It wakes up on a schedule (GitHub throttles `*/15` crons to ~4–5 runs/day in practice), thinks (LLM through the vault), acts (vault-proxied APIs), remembers (by committing), and sleeps. Every decision is a commit. You can read its mind with `git log`.

## Quick Start

```bash
# 1. Fork this repo
# (click Fork on GitHub)

# 2. Register your fork with the vault
# (see VAULT.md — one allowlist entry, no keys in the repo)

# 3. That's it. It wakes up and starts working.
```

## The zero principle

A Purple Pincher is a small, economical creature. Zero is the smallest shell one can live in:

- **Minimum moving parts** — three workflows, two scripts, one vault. Engineers should be impressed by the economy.
- **Capability-centric** — new powers arrive as small vault service handlers (plugins), never as new infrastructure. See `docs/plugins.md`.
- **The repo is the world** — the agent's whole understanding grows from *this* repo: its code, its history, its docs. It builds its own Wikipedia as it works, for its own purpose. See `docs/clones.md`.

## The tripartite

Zero is the **Logos** agent — it understands the *logic* of the application. It is one of three:

1. **The human agent** — knows the person (presentation, judgment, conversation).
2. **The git agent** — knows the application's logic. *That's this.*
3. **The hardware agent** — knows how to render the application to hardware.

The human-facing agent never touches git mechanics; the git agent never touches hardware. Each owns one demarcation. See `docs/tripartite.md`.

## Shells

As a Pincher grows, it moves into bigger shells — but the creature stays the same:

- **Zero** — this. The minimal seed. Fork-and-go.
- **Turbo** — a self-contained application shell: one repo, one builder.
- **Tapestry** — the quilt-worker: many repos, one coherent story.

See `docs/clones.md` for the shell model. To *be* the hermit crab — run a
clone of this repo locally with your own GPU model as the brain, no vault:

```bash
LOCAL_LLM_URL=http://localhost:11434/v1 LOCAL_LLM_MODEL=<model> \
  python3 .github/scripts/agent.py --task "your task"
```

(Any OpenAI-compatible server works — see `docs/architecture.md`
"Local-brain mode".)

## Layout

```
.github/workflows/   think.yml, react.yml, telegram.yml
.github/scripts/      agent.py (the brain), act.py (legacy v0.1 executor, unused)
tests/                unittest-style test suite (pytest-compatible)
docs/                 architecture.md, maintenance-notes.md, system1.md, plugins.md, i2i.md, memory.md, clones.md, tripartite.md, registration.md
AGENTS.md             operator's manual
ONBOARDING.md         first-boot checklist
TASKS.md              the task board
MEMORY.md             long-term memory (committed, rewindable)
VAULT.md              how the vault works (it holds no secrets)
```

New here? `docs/architecture.md` is the full system map (start there);
`docs/maintenance-notes.md` collects known issues, quirks, and vestigial
code for anyone doing maintenance.

## License

MIT — take the shell, grow your own crab.

---

## This fork: a live research agent (v0.3 → Sprint 2)

This fork of zero is a working experiment: how much cognition can you
give a git-native agent before it stops being a cron script? It runs
the original seed loop plus a growing stack of "System-1" machinery —
small, fast, calibrated decision models that gate and judge the
expensive LLM cycle. Highlights, all bench-validated before shipping
(full change log in `docs/maintenance-notes.md`, 63 tests):

- **Idle gate (v0.4 + Sprint 2):** before each heartbeat's LLM call, a
  decision model judges a distilled digest — a confident "nothing to
  do" skips the cycle entirely. Works with local decision models
  (Ollaya) or TypeSafe's hosted Jev (`DECISION_URL` +
  `DECISION_API_KEY`; measured 95% idle-skip at ~$0.05/month).
  Fail-open everywhere; a deterministic blindness veto overrides the
  model whenever the issue tracker can't be read.
- **Duty cycle (the drive):** after 6 hours without substantive work,
  the next wake is a forced probe that bypasses the gate — the agent
  looks even when nothing poked it. The clock resets only on real work.
- **Honest memory (Sprint 0):** `CONTEXT.md` is the working memory
  (rewritten, SHA-cited facts); `MEMORY.md` is an append-only event log
  no model reads at runtime. Any memory claim that cites no commit SHA
  is stamped `[unverified, date]`. No-op cycles write nothing.
- **Hardened context (Sprint 1):** issue bodies enter the prompt
  wrapped in a deterministic `[UNTRUSTED]` annotation; task-board
  items may carry `[commitment:]`/`[blast:]` stake tags.
- **Shadow gate:** each heartbeat also records what a vendored
  zero-dependency gate (10 logistic weights) would have decided —
  observation only; skip authority lives in a CI-enforced selftest.

## The ecosystem

This agent is the center of a small constellation of research repos:
[gate-replay](https://github.com/SuperInstance/gate-replay) (calibrating
gates from git history),
[minigate](https://github.com/SuperInstance/minigate) (the serverless
distilled gate),
[cycle-judge](https://github.com/SuperInstance/cycle-judge) (completion
judges, flail detection, injection screening),
[decision-ledger](https://github.com/SuperInstance/decision-ledger)
(filing every model decision — ~0.5 answers are passes, not coin flips),
[trust-ledger](https://github.com/SuperInstance/trust-ledger) (trust as
a computable scalar),
[pacemaker](https://github.com/SuperInstance/pacemaker) (a circadian
heartbeat dispatcher),
[drift-probe](https://github.com/SuperInstance/drift-probe) (repo-drift
detection), and
[vision](https://github.com/SuperInstance/vision) (the roadmap and the
two-model strategy council that designed it).

## License

MIT — see [LICENSE](LICENSE).
