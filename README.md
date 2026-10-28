<div align="center">

# 🦀 Purple Pincher Zero

**The minimal git-native agent. Fork this repo, register with the vault, and it starts working your repo.**

No server. No hosting. No keys in the repo. The repo *is* the agent.

</div>

---

## What is this?

Zero is the smallest complete seed of a Purple Pincher: an AI agent that lives entirely in GitHub.
This repo (`SuperInstance/zero-poc`) is the running instance and the home of its production line, at **v0.8.2**.

- **Commits** are work
- **Issues** and **`TASKS.md`** are the task board
- **Telegram** is the conversation; both sides are recorded in `conversation/`
- **Git log** is memory — rewindable, time-shaped, not a snapshot

It wakes up on a schedule (GitHub throttles `*/15` crons to ~4–5 runs/day in practice), thinks (LLM through the vault), acts (shell, files, git, vault-proxied APIs), remembers (by committing), and sleeps. Every decision is a commit. You can read its mind with `git log`.

## What v0.8.2 does

- **Think loop** (`think.yml` → `.github/scripts/agent.py`): a ReAct loop over
  `ONBOARDING.md`, `CONTEXT.md`, `TASKS.md`, `TOOLS.md`, open issues and the
  recent git log. Up to 10 iterations; commits and pushes at the end.
- **Voice** (`telegram.yml`): every message is recorded in full in
  `conversation/inputs/`, routed onto `TASKS.md`, answered by one vault LLM
  call that sees `CONTEXT.md`, the last 10 turns (up to 12,000 chars), the
  first turn ever, and up to 3 older turns that match the message (3,000
  chars). The reply is committed to `conversation/outputs/` before it is
  sent (cap 4,000 chars).
- **Board reports** (v0.8): when the loop closes a Telegram task, a report is
  filed in `reports/pending/` (5 per cycle) and attached to the next reply
  (5 per message, 2,000 chars), then moved to `reports/delivered/` after a
  successful send. The voice never initiates contact. Since v0.8.2 a reply
  that imitates the reports block is replaced mechanically.
- **Issue replies** (`react.yml`): one conversational LLM reply per issue or
  comment; the work itself waits for the think loop.
- **Idle gate + duty cycle:** a decision model may skip an idle heartbeat.
  `think.yml` points it at TypeSafe Jev; it can only answer once the
  `TYPESAFE_API_KEY` secret is set, and any error runs the cycle (fail-open).
  No Actions cycle has recorded a skip (`gated_idle`) yet. After 6 hours
  without substantive work the next cycle bypasses the gate. See
  `docs/system1.md`.
- **Honest memory:** `CONTEXT.md` is rewritten working memory; `MEMORY.md` is
  an append-only log; entries citing no commit SHA are stamped
  `[unverified, date]`; no-op cycles write nothing to `MEMORY.md`. See
  `docs/memory.md`.

## Quick Start

```bash
# 1. Fork this repo
# (click Fork on GitHub)

# 2. Register your fork with the vault
# (see VAULT.md — open an issue titled "Register"; no keys in the repo)

# 3. That's it. It wakes on the think schedule. Give it work by
#    opening an issue or adding a "- [ ]" line under "## Open" in TASKS.md.

# Run the test suite (63 tests, all for agent.py; no pytest? use
#   python3 -m unittest discover -s . -p "test_*.py"):
python3 -m pytest tests/
```

## When it breaks

Telegram failures are loud: a failed step, or a send the bridge rejects,
fails the run in the Actions tab. The think loop is quieter: an LLM failure
ends the cycle as `llm_error` in `.agent-state.json` and the run passes.
Replies are committed to `conversation/` before sending; undelivered reports
stay in `reports/pending/`. If the Think step fails, a fallback records and
sends a "brain hiccuped" line. Failure log: `docs/maintenance-notes.md` and
the workflow header notes — the v0.5.1 silence bug (an apostrophe broke the
Think step) and v0.8's voice imitating the reports block (the v0.8.2 gate).

## The zero principle

A Purple Pincher is a small, economical creature. Zero is the smallest shell one can live in:

- **Minimum moving parts** — three workflows, one brain script, one vault (plus the Telegram bridge worker). Engineers should be impressed by the economy.
- **Capability-centric** — new powers arrive as small vault service handlers (plugins), never as new infrastructure. See `docs/plugins.md`.
- **The repo is the world** — the agent's whole understanding grows from *this* repo: its code, its history, its docs. It builds its own Wikipedia as it works, for its own purpose. See `docs/clones.md`.

## The tripartite

*Vision, not mechanism: only the git agent exists, in this repo; the other two are not built.*

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

*Turbo and Tapestry are vision; only Zero and the local hermit-crab mode below are shipped.*

See `docs/clones.md` for the shell model. To *be* the hermit crab — run a
clone of this repo locally with your own GPU model as the brain, no vault
for thinking:

```bash
LOCAL_LLM_URL=http://localhost:11434/v1 LOCAL_LLM_MODEL=<model> \
  python3 .github/scripts/agent.py --task "your task"
```

(Any OpenAI-compatible server works — see `docs/architecture.md`
"Local-brain mode".)

## Layout

```
.github/workflows/   think.yml, react.yml, telegram.yml
.github/scripts/     agent.py (the brain), minigate/ (shadow idle gate, vendored), act.py (legacy v0.1 executor, unused)
tests/               unittest-style test suite (pytest-compatible, 63 tests)
docs/                architecture.md, maintenance-notes.md, memory.md, system1.md, decision-science.md, plugins.md, i2i.md, clones.md, tripartite.md, registration.md, playtest-2026-10-27.md
AGENTS.md            operator's manual
ONBOARDING.md        identity and mechanism (read by the think loop every cycle)
TASKS.md             the task board
TOOLS.md             my tools & skills index (read by the think loop every cycle)
CONTEXT.md           working memory (rewritten, never appended)
MEMORY.md            append-only event log
conversation/        the dialogue itself — inputs/ (the human) and outputs/ (the agent), paired by turn stem
reports/             finished board work — pending/ (not yet told) and delivered/ (the archive)
scratch/             the loop's working notes
.agent-state.json    last cycle's vital signs
VAULT.md             how the vault works (it holds no secrets)
scripts/, issues.json, open_issues.json
                     files the loop wrote during its own cycles; nothing in the pipeline runs or reads them
```

New here? `docs/architecture.md` is the full system map (start there);
`docs/maintenance-notes.md` collects known issues, quirks, and vestigial
code for anyone doing maintenance.

---

## History

Dated (UTC), for orientation; the change log is in
`docs/maintenance-notes.md` and the workflow headers. v0.3 (2026-10-15)
fixed the echo loop and issue blindness, routed Telegram onto the board, and
added local-brain mode. The idle gate shipped 2026-10-16 (its commit says
`feat(v0.4)`, a label later reused for the conversation record). Sprint 0/1
(2026-10-17) added the duty cycle, `CONTEXT.md`, `[unverified]` stamps, the
`[UNTRUSTED]` marker on issue bodies, stake tags on the board, and the shadow
gate (vendored minigate, observe-only — it never skips a cycle). Sprint 2
(2026-10-18) wired the TypeSafe Jev cloud gate. v0.4–v0.7 (2026-10-22 →
10-28) built the conversation record, the self-model in
`ONBOARDING.md`/`TOOLS.md`, the voice's memory and its corpus hooks.
v0.8–v0.8.2 (2026-10-28) added board reports and the gate on the voice.

## The ecosystem

Sibling research repos, outside this tree (not audited here; `vision` is
private): [gate-replay](https://github.com/SuperInstance/gate-replay) (the
idle-gate bench), [minigate](https://github.com/SuperInstance/minigate) (the
gate vendored in `.github/scripts/minigate/`),
[cycle-judge](https://github.com/SuperInstance/cycle-judge) (the
injection-screening eval behind the `[UNTRUSTED]` marker),
[decision-ledger](https://github.com/SuperInstance/decision-ledger)
(calibration; see `docs/decision-science.md`),
[trust-ledger](https://github.com/SuperInstance/trust-ledger),
[pacemaker](https://github.com/SuperInstance/pacemaker),
[drift-probe](https://github.com/SuperInstance/drift-probe), and
[vision](https://github.com/SuperInstance/vision) (the roadmap; source of
the Sprint 0/1 plan).

## License

MIT — take the shell, grow your own crab. See [LICENSE](LICENSE).
