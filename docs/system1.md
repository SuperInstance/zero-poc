# System 1 — Decision Models and the Idle Gate

Written 2026-10-15 after live research + a working experiment on this
machine (Ollaya 0.13.0, laya + winnow:e4b pulled and benchmarked against
this repo's real state). Audience: the agent and any maintainer deciding
whether to build the idle gate. Everything below is verified unless
marked otherwise; sources linked at the end.

**Status at v0.8.2** (from `agent.py` and `think.yml`): the idle gate is
code (`gate_says_work()`), with two providers. In Actions, think.yml
points it at hosted TypeSafe Jev (`DECISION_URL=https://api.typesafe.ai`,
`DECISION_MODEL=jev-preview`, key from the `TYPESAFE_API_KEY` secret); no
Actions cycle has yet recorded `gated_idle`. A separate **shadow gate**
(vendored minigate) runs before every cycle and only records its verdict.
The 6-hour duty cycle bypasses both. The research sections below are the
2026-10-15 record; where the design changed since, it says so inline.

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

Why it mattered here (2026-10-15): zero spent a **full System-2 vault LLM
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
load): ~3 s laya, ~11 s winnow; laya also runs fine CPU-only. tev1 via
Ollama: no 92% / yes 97% (see Notes).

## The idle gate (implemented 2026-10-16)

Shipped in agent.py the night after the research. Exactly the design
below, now real code with tests (tests/test_agent.py, TestIdleGate):

1. **Env**: `DECISION_URL` (empty = disabled; `http://localhost:11435`
   locally), `DECISION_MODEL` (default `laya`),
   `GATE_CONFIDENCE_THRESHOLD` (0.6).
2. **Client**: `decide(questions, state)` → POST
   `{DECISION_URL}/v1/decisions`; parses `answers.{id}.choice/.confidence`.
   *Since Sprint 2 (2026-10-18):* with `DECISION_API_KEY` set it POSTs
   `{DECISION_URL}/v1/systemone` with Bearer auth instead, and
   `normalize_decision_answers()` maps TypeSafe probabilities onto the same
   confidence scale (|2p−1|; see `docs/decision-science.md` §1).
3. **`build_gate_digest()`**: counts + first lines of open TASKS.md
   items (first 5), the telegram task count, open issue count and titles
   (first 5, or "fetch failed, count unknown") — distilled prose, never
   raw markdown (attempt-1 lesson baked into a code comment). *Changed in
   Sprint 0:* the "last cycle outcome" line was removed — the gate must
   never see its own prior verdict (it caused an idle latch).
4. **Policy in `run_agent_loop()`**: before the first `llm_think()`, and
   ONLY for schedule cycles with no explicit `--task` (a human asking
   directly always bypasses the gate). Confident "no" → `save_state(
   outcome="gated_idle")`, no MEMORY.md write, return with zero LLM
   calls. Everything else — "yes", sub-threshold confidence, no
   DECISION_URL, any error/timeout — runs the full loop. **Fail-open,
   verified live**: a tokenless local run (issues "fetch failed, count
   unknown") dropped laya's confidence to 0.479 < 0.6, so the gate
   correctly stepped aside and the loop ran.
5. **Where it runs**: local/hermit-crab shells via Ollaya (pairs with
   LOCAL_LLM_URL as a tiered brain: decision gate + local System 2).
   *Superseded for Actions:* the plan was a `decision` vault service;
   Sprint 2 instead wired TypeSafe Jev directly in think.yml (status
   above). The duty cycle (Sprint 0) forces a full cycle after 6 h
   without substantive work, gate or no gate.
6. **Shadow gate (Sprint 1)**: think.yml's `Shadow gate (observe only —
   never skips a cycle)` step runs the vendored minigate
   (`.github/scripts/minigate/`) on the same digest and stores `SKIP` /
   `RUN` / `RUN_BLIND` as `shadow_gate` in `.agent-state.json`. It has no
   authority; its blindness veto (a digest saying "fetch failed" is always
   RUN) exists only there — `gate_says_work()` has no such veto.

Later applications of the same client — none built yet — in rough value order: reflex-tier
classification for incoming tasks (ONBOARDING.md's Known/Semi-known/
Unknown tiers made real), react.yml triage (task vs question vs noise —
Ollaya ships a built-in `agent`/`triage` preset), and guardrailing tool
calls before `execute_tool` (Qwen3Guard-style). Ollaya also speaks MCP
(`ollaya mcp`), which is a natural future sense-organ shape.

## Notes and unknowns

- **tev1** (the model originally mentioned as "dtev1"): Together AI's
  experimental open Jev-like family — [Tev1-4B-experimental](https://huggingface.co/togethercomputer/Tev1-4B-experimental)
  (Qwen3.5-4B SFT) and a 0.8B variant; ranks well on the [Jev Decision
  Index](https://huggingface.co/spaces/multimodalart/jev-decision-index).
  Pulled via [Ollama](https://ollama.com/library/tev1) (Q8_0, 4.3B) and
  benchmarked on the same idle/busy digests: **no 92% / yes 97%** —
  clean discrimination, 0.3 s warm, but ~46 s cold model load on this
  machine's 6 GB GPU, and it speaks Ollama's `--ask` interface rather
  than the TypeSafe `/v1/decisions` contract the gate client targets
  (a thin adapter or an Ollaya Modelfile import would bridge it).
  Together's checkpoints are Apache-2.0.
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
