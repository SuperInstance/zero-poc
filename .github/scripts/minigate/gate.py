#!/usr/bin/env python3
"""minigate inference — the serverless idle gate. Zero dependencies.

Load gate.json (trained by train.py), read digests (one per line of a
jsonl file, or argv strings), print skip/run per cycle. This file plus
gate.json is the ENTIRE deployment: drop both into a CI runner.

Exit code: 0 always — a gate that blocks work on its own error is worse
than no gate. Unknown/malformed input fails OPEN (run the cycle).
"""
import json
import sys
from train import features, sigmoid, FEATURE_ORDER


def load(path="gate.json"):
    spec = json.load(open(path))
    return spec["weights"], spec.get("threshold", 0.5)


def check(w, threshold, digest):
    # Blindness veto (Sprint-0 law): an issue-fetch failure is a
    # deterministic RUN — never a feature weight, never "zero issues".
    # Matches ONLY the production phrasing (agent.py: "fetch failed,
    # count unknown"); bare "unknown" strings are corpus-replay
    # artifacts, not live blindness (selftest rows 5a/5b enforce this).
    if "fetch failed" in digest:
        return None, False  # None p = blind veto
    f = features(digest)
    p = sigmoid(sum(w[name] * f[name] for name in FEATURE_ORDER))
    return p, p < threshold  # p(busy) < t  ->  skip (idle)


def main():
    w, t = load()
    if len(sys.argv) > 1 and sys.argv[1].endswith(".jsonl"):
        rows = [json.loads(l) for l in open(sys.argv[1])]
        digests = [r["digest"] for r in rows]
    else:
        digests = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else [
            sys.stdin.read().strip()]
    for d in digests:
        p, skip = check(w, t, d)
        if p is None:
            print(f"RUN  (blind) — issue state unknown  | {d[:70]}")
        else:
            print(f"p(busy)={p:.2f}  {'SKIP (idle)' if skip else 'RUN  (work)'}"
                  f"  | {d[:80]}")


if __name__ == "__main__":
    main()
