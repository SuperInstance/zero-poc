Vendored from SuperInstance/minigate at commit 39eaa841b2ee897763e33a05cf2cbbbfc4efc2f0; re-vendor after retraining.

# Vendored minigate — the serverless idle gate (SHADOW mode)

`gate.py`, `gate.json` and `train.py` are byte-identical copies of upstream.
Do not edit them here: upstream's `scripts/selftest.py` is the suite that
grants and withdraws skip authority, so a local edit would fork the artifact
from the thing that governs it. Re-vendor instead.

**`train.py` is vendored too, and upstream's README is wrong about this.**
`gate.py` line 13 does `from train import features, sigmoid, FEATURE_ORDER` —
an unconditional runtime import, not a training-time-only one. Copying just
`gate.py` + `gate.json` (as upstream's "this file plus gate.json is the
ENTIRE deployment" claims) produces a `ModuleNotFoundError` on every run.
Verified: the two-file deploy fails on the first line of inference.

## SHADOW mode (Sprint 1)

`think.yml` runs this gate **before** the agent and records the verdict in
`.agent-state.json`. It **never skips a cycle.** The verdict is observation
only — no branch, no `if:`, no exit code that can prevent `agent.py` from
running. Authority is not granted here; it is granted upstream, by a passing
selftest. See `.github/scripts/agent.py` (`build_gate_digest`) for the digest
contract the feature parser expects.