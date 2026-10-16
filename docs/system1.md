# System 1 — Decision Models and the Idle Gate

Written 2026-10-15 after live research + a working experiment on this
machine (Ollaya 0.13.0, laya + winnow:e4b pulled and benchmarked against
this repo's real state). Audience: the agent and any maintainer deciding
whether to build the idle gate. Everything below is verified unless
marked otherwise; sources linked at the end.

## What System 1 models are

A new (Sept 2026) model class, named for Kahneman's fast/slow thinking
distinction: **decision models** read a state (any text/JSON) plus typed
questions and return **calibrated probabilities, never generated text** —
one forward pass, no token loop. The category was put on the map by
**Jev**, TypeSafe AI's proprietary "System One Model" ("unstructured
state in, typed probabilistic decisions out", trained via RLCD; claimed
40–200× faster and up to ~400× cheaper than frontier LLMs on decision
tasks). Jev is closed; an open ecosystem followed:

- **Ollaya** — Apache-2.0 Rust runtime, "Ollama for decision models",
  port `:11435`, TypeSafe-wire-compatible (`POST /v1/systemone`,
  `POST /v1/decisions`, `GET /v1/models`) plus a native `/api/decide`.
- Open Jev-style checkpoints: **laya** (Convai, ModernBERT-large, 421M;
  also `laya:multilingual`), **winnow:e4b** (4B Gemma fine-tune,
  recommended default), kev, decider, nli, gliclass, Qwen3Guard, d1,
  decima, … Big vendors are converging on the same pattern (Microsoft
  "Decision-1", LiteLLM decision-model endpoints).

Why it matters here: zero currently spends a **full System-2 vault LLM
cycle on every heartbeat just to conclude "awaiting instructions"** —
visible as dozens of identical MEMORY.md entries. A System-1 gate answers
"is there actionable work?" in milliseconds for free, locally.

## The experiment (verified, 2026-10-15, this machine)

API contract (from Ollaya's docs/api.md, verified against the live
server): questions are `{id: {type, instructions, criteria}}`; `choice`
criteria map label → description; answers give `choice`, `confidence`,
and full `probabilities`. Latencies below are warm/cold as noted.

**Attempt 1 — naive prompting FAILED.** Feeding raw `TASKS.md` +
`MEMORY.md` tail and asking "is there actionable work?" barely
discriminated idle vs. busy (P(yes) 0.70 vs 0.60 — wrong direction), and
the idle board read as "yes" because the text is full of task-shaped
words (including the word "instructions", which my own criterion
contained). Lesson: **System-1 models judge the text you hand them —
the gate is exactly as good as the digest builder.** Feed a distilled
digest, not the raw board.

**Attempt 2 — distilled digest WORKED.** State became
"open tasks: none. open issues: … telegram inbox: … recent cycles: …":

| model | idle → | busy → | warm latency |
|---|---|---|---|
| laya (421M) | no, P(yes)=0.19 | yes, P(yes)=0.81 | ~20–180 ms |
| winnow:e4b (4B) | no, P(yes)=0.004, conf 0.99 | yes, P(yes)=0.995, conf 0.99 | ~150 ms |

Both also said **no** for this repo's real current digest (one stale
open issue, otherwise idle) — the correct answer. Cold-start (model
load): ~3 s laya, ~11 s winnow; laya also runs fine CPU-only.

## The design: an idle gate for the heartbeat

Not yet implemented — this is the reviewed design.

1. **Env**: `DECISION_URL` (empty = disabled; `http://localhost:11435`
   locally), `DECISION_MODEL` (default `laya`).
2. **Client**: `decide(questions, state)` → POST
   `{DECISION_URL}/v1/decisions` with `{model, state, questions}`; parse
   `answers.{id}.choice/.confidence/.probabilities`. Same shape as the
   vault plugins (small, typed, JSON in/out).
3. **Digest builder** (`build_gate_digest()`): counts + first lines of
   open TASKS.md items, open issue titles, telegram inbox (TASKS.md
   `(telegram …)` entries), last cycle outcome from `.agent-state.json`.
   Plain prose, ~10 lines. Never raw markdown (see attempt 1).
4. **Policy in `run_agent_loop()`**, before the first `llm_think()`:
   - gate says **yes** (or DECISION_URL unset, or ANY error/timeout) →
     run the full loop exactly as today. **Fail-open, always** — a broken
     gate must never blind or block the agent.
   - gate says **no** with confidence ≥ ~0.6 → skip the LLM entirely:
     `save_state(outcome="gated_idle")`, do NOT append MEMORY.md (that
     would recreate the noise problem one level down); log the skip in
     the Actions log only. Optionally append one MEMORY.md line on
     state *transitions* (busy→idle, idle→busy), not per cycle.
5. **Where it runs**: locally via Ollaya (hermit-crab shells — pairs
   with LOCAL_LLM_URL as a tiered brain: laya gate + local 7B System 2).
   In Actions, either add a `decision` vault service (docs/plugins.md
   pattern) or leave the gate local-only.

Later applications of the same client, in rough value order: reflex-tier
classification for incoming tasks (ONBOARDING.md's Known/Semi-known/
Unknown tiers made real), react.yml triage (task vs question vs noise —
Ollaya ships a built-in `agent`/`triage` preset), and guardrailing tool
calls before `execute_tool` (Qwen3Guard-style). Ollaya also speaks MCP
(`ollaya mcp`), which is a natural future sense-organ shape.

## Notes and unknowns

- **"dtev1" could not be found** — not in the Ollaya catalog, HF, or the
  web (searched `dtev1`, `dte-v1`). Closest real names in the family:
  `d1`, `decima`, `kev`, `winnow`. If it exists under another spelling,
  correct this file.
- Confidence formula (Ollaya docs): (K·p_max − 1)/(K − 1), clamped —
  i.e. how far the top probability is above uniform, not absolute
  certainty. Thresholds should be tuned on observed distributions, and
  the gate should fail open below them.
- winnow:e4b's near-perfect discrimination cost an 8 GB pull and 11 s
  cold load; laya is the right default on small machines, with winnow
  as the quality upgrade (both fit a 6 GB GPU; winnow comfortably, laya
  trivially).

## Sources

- TypeSafe AI — [Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- Ollaya — [github.com/ollaya-dev/ollaya](https://github.com/ollaya-dev/ollaya) (+ its docs/api.md for the contract quoted above)
- Laya — [ollama.com/library](https://ollama.com/library) (also served by Ollaya), [Convai on HF](https://huggingface.co/convaiinnovations/laya)
- Ecosystem roundups — [LangChain: building a harness with Jev](https://www.langchain.com/blog/building-a-harness-with-jev), [LiteLLM JEV benchmark](https://docs.litellm.ai/blog/jev-auto-router-benchmark), [LiteLLM decision models](https://docs.litellm.ai/blog/decision-models), [Microsoft Decision-1](https://commandline.microsoft.com/microsoft-decision-1-model-foundry), [Ollaya explainx](https://explainx.ai/blog/ollaya-ollama-for-decision-models-local-runtime-2026), [awesome-jev](https://github.com/yibie/awesome-jev/blob/main/categories/classification-routing.md)
