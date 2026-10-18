# Decision & gate science

The science underneath the idle gate and the decision path — why the
thresholds, normalizations, and failure policies are what they are. Companion
to `docs/system1.md` (which covers the model landscape and the motivation);
this document covers the mechanics. Full verified citations live in
communicator's `docs/research/PAPERS.md` (shared fleet corpus). Everything
below is either derived here, measured here with the model named, or
attributed.

## 1. Confidence scales are not portable; normalize before thresholding

The two decision-model backends this agent uses report "confidence" in
different units:

- A **Noul** answer is a probability p ∈ [0,1] that a proposition is true.
- A **Choice** answer's `confidence` is a distribution-spread statistic.
  For two options it reduces to |2·p_max − 1|: conf 0.6 ⇔ p_max = 0.8.

`decide()` normalizes both providers onto the same scale (choice +
|2p−1|), so `GATE_CONFIDENCE_THRESHOLD = 0.6` means "p ≥ 0.8" on EITHER
backend. Without that normalization one threshold is two different filters
— the local gate might skip at true probability 0.55 while the cloud gate
skips at 0.8, and no test on one backend says anything about the other.

General law: **a threshold is only meaningful on a scale whose meaning you
have pinned** — which is the calibration problem, next.

## 2. Calibration is what makes a threshold a claim

A threshold on calibrated confidence is a measurable promise: "skip when
the model says ≥ 0.8 confident" then misses work at a known rate. A
threshold on UNcalibrated confidence is a vibe with a number attached.

Fleet measurements (2026-10-16..18, recorded in decision-ledger and
gate-replay):

| model | state | measured |
|---|---|---|
| laya | raw ECE 0.374 | reads p(busy)=0.41 on idle states — 5–6× overconfident; coin-flip at its best busy answer post-repair → judges-only, never a gate |
| laya | post-Platt ECE 0.077 | repair worked (Brier 0.175→0.020) — scaling as REPAIR |
| winnow:e4b | ECE 0.033 raw | already calibrated; Platt made it WORSE (0.053) — scaling is not an upgrade |
| Jev (jev-1.14.0) | gate bench | 99.0–99.7% on 600 labelled questions, **0 wrong GOs** at thresholds 0.8/0.9/0.95; batch of 300 in 0.3–0.6 s |

The classical result the fleet re-derived empirically: probability-
calibration repair (Platt/temperature family) helps stretched or
sigmoid-distorted models and does not help — can hurt — already-calibrated
ones (Niculescu-Mizil & Caruana 2005; Platt 1999; see PAPERS.md). Measure
ECE first; scale only on evidence.

Teacher labels closed the loop: Jev-as-teacher agreed with ground truth on
96.4% of rows, so calibration loops taught by Jev are measuring something
real, not echoing themselves.

## 3. The error matrix is asymmetric — and it chooses the failure policy

An idle gate makes two errors with very different costs:

- **False-idle** (says idle, work existed): the agent sleeps through real
  work. Silent, compounding, the worst failure.
- **False-busy** (says busy, nothing to do): one wasted LLM cycle. Cost:
  roughly a cent and some tokens.

Measured (gate-replay, live Jev, combined git-history corpus + adversarial
probes): **95% idle-skip at 10.5% false-idle**. The decisive detail: the
false-idle class was dominated by `llm_error`-retry rows — transient
failures that a probability gate reads as "nothing actionable." Hence the
law, now fleet-wide:

    A deterministic blind veto sits in front of ANY model gate.

Jev-lattice independently confirmed the same shape with compiled
predicates: trusted to say NO they gave 0 wrong GOs at half the cost;
trusted to say YES they produced 5–24 wrong GOs after a format shift.
minigate's blindness veto is the same law. Cheap deterministic checks veto;
models propose.

## 4. Fail-open vs fail-closed: two policies, two cost matrices

- The **idle gate fails OPEN** (no decision service, timeout, parse error →
  run the full cycle). A wasted cycle is cheap; sleeping through work is
  not. Live-validated: a cold-start timeout once fell through to the full
  loop exactly as designed.
- **Act/review/block gates fail CLOSED** (no gate answered → block). These
  gates guard actions, where the error costs invert: an unanswered gate
  passing you through is the false-idle of authority. A gate that did not
  answer may not act as if it had. (gitpp-gate's law, adopted repo-wide.)

One rule generates both: **fail toward whichever error is cheaper for THAT
decision**, and say which policy each gate uses in its docstring.

## 5. The digest, not the document

Naive raw-markdown gating FAILS (measured 2026-10-15): the model drowns in
markup. A distilled ~10-line digest of the same state separates cleanly
(laya 0.19 idle / 0.81 busy; winnow 0.004 / 0.995). The gate question is
cheap; the REPRESENTATION is the instrument. Related fleet finding: reading
rules belong in `state` — Jev missed "later directive overrides earlier"
traps until the rule rode along with the state.

## 6. One Choice, not N independent Nouls

For mutually exclusive options, ask one Choice — never N independent
yes/no questions. Measured: independent nouls are NOT exclusive in
practice (on "most moons", both Jupiter 0.52 and Saturn 0.79 cleared 0.5 —
a threshold reader accepts a wrong answer). Choice normalizes across
options in one call. Nouls are for genuinely independent propositions.
Parallel evaluation means adding questions barely moves latency — four
questions + four presence gates ride in ONE call (communicator measures
200–550 ms), which is what makes per-cycle gating affordable at all
(~$0.05/month at 96 beats/day, gate-replay's bench).

## 7. Duty cycle: probability needs a clock

A gate answers "is there work NOW?" It decays without new evidence, and a
cheap gate makes it cheap to never look. The duty-cycle rule (vision
PLAN, Sprint 0): forced probe after > 6 h without substantive work,
latched, reset only by substantive work — **count actions, not wakeups**.
Live-validated by accident: a 15.5 h stale clock forced a probe past the
gate exactly as designed. The gate is a shutter, not a conscience.

## 8. Where this is all written down

- system1.md — model landscape, digest findings, gate design.
- communicator/docs/SCIENCE.md — the probability-as-controller theory and
  measurement science in depth (ECE's blind spots, presence gates,
  safe-parking).
- communicator/docs/research/PAPERS.md — the verified bibliography
  (Brier, Murphy, Platt, Niculescu-Mizil & Caruana, Naeini et al., Guo et
  al., Spearman, and the pitch/prosody canon).
- decision-ledger — calibration code + CALIBRATION.md/QUESTION-REWRITE.md.
- gate-replay — the idle-gate bench, jev_bench.py, JEV-RESULTS.md.
