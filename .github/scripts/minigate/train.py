#!/usr/bin/env python3
"""Train minigate: distill the gate-replay corpus into a logistic model.

The whole point is the deployment shape: no server, no network, no deps.
Feature extraction mirrors the digest structure agent.py builds (stable by
construction), the model is plain logistic regression trained by gradient
descent (pure stdlib), and the result serializes to gate.json — a dict of
~10 weights. Inference (gate.py) is a regex parse plus a dot product, so
this runs in any CI runner, container, or tiny box that has python3.

Usage: python3 train.py ../gate-replay/corpus.jsonl
"""
import json
import math
import random
import re
import sys

STALE_RE = re.compile(r"2026-\d\d-\d\d|\d+ weeks? ago|\d+ days? ago")


def features(digest):
    """Structured features from a gate digest (see agent.py build_gate_digest)."""
    n_tasks = 0
    m = re.search(r"open tasks: (\d+)", digest)
    if m:
        n_tasks = int(m.group(1))
    task_lines = re.findall(r"task: (.+?)(?=\s{2,}|open |unread |last |$)", digest)
    n_telegram = 0
    m = re.search(r"unread user messages via telegram: (\d+)", digest)
    if m:
        n_telegram = int(m.group(1))
    issues_unknown = ("open issues: unknown" in digest
                      or "fetch failed" in digest)
    n_issues = 0
    if not issues_unknown:
        m = re.search(r"open issues: (\d+)", digest)
        if m:
            n_issues = int(m.group(1))
    issue_lines = len(re.findall(r"issue #\d+", digest))
    stale_task = any(STALE_RE.search(t) for t in task_lines)
    outcome_idle = ("awaiting" in digest.lower()
                    or "gated_idle" in digest.lower())  # informational only
    outcome_error = bool(re.search(r"llm_error|outcome.{0,20}error|after \d+ attempts",
                                   digest.lower()))
    return {
        "bias": 1.0,
        "n_tasks": float(n_tasks),
        "has_task": 1.0 if task_lines else 0.0,
        "n_telegram": float(n_telegram),
        "n_issues": float(n_issues),
        "has_issue": 1.0 if issue_lines else 0.0,
        "issues_unknown": 1.0 if issues_unknown else 0.0,
        "stale_task": 1.0 if stale_task else 0.0,
        "outcome_error": 1.0 if outcome_error else 0.0,
    }


# outcome_idle is DELIBERATELY absent (Sprint-0 law: no self-feedback).
# The gate must never consume its own prior verdict — that created the
# idle latch (one gated_idle flipped a visible issue from RUN to SKIP).
FEATURE_ORDER = [
    "bias", "n_tasks", "has_task", "n_telegram", "n_issues", "has_issue",
    "issues_unknown", "stale_task", "outcome_error",
]


def sigmoid(z):
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def train(rows, epochs=4000, lr=0.35, l2=0.01, seed=7):
    random.seed(seed)
    xs = [[features(r["digest"])[k] for k in FEATURE_ORDER] for r in rows]
    ys = [1.0 if r["label"] == "busy" else 0.0 for r in rows]
    w = [0.0] * len(FEATURE_ORDER)
    for _ in range(epochs):
        grad = [0.0] * len(w)
        for x, y in zip(xs, ys):
            p = sigmoid(sum(wi * xi for wi, xi in zip(w, x)))
            err = p - y
            for j in range(len(w)):
                grad[j] += err * x[j]
        for j in range(len(w)):
            w[j] -= lr * (grad[j] / len(xs) + l2 * w[j])
    return w


def predict(w, digest):
    f = features(digest)
    return sigmoid(sum(wi * f[k] for wi, k in zip(w, FEATURE_ORDER)))


def main():
    rows = [json.loads(l) for l in open(sys.argv[1])]
    real = [r for r in rows if not r["synthetic"]]
    w = train(rows)  # synthetic busy cases included: they carry real signal

    # Leave-one-out CV on REAL rows only — the honest generalization number.
    correct, false_idle = 0, 0
    for i, held in enumerate(real):
        w_cv = train([r for j, r in enumerate(real) if j != i])
        p = predict(w_cv, held["digest"])
        pred_busy = p >= 0.5
        if pred_busy == (held["label"] == "busy"):
            correct += 1
        if held["label"] == "busy" and not pred_busy:
            false_idle += 1
        held["_p"] = round(p, 3)

    acc, fi = correct / len(real), false_idle / sum(
        1 for r in real if r["label"] == "busy")
    weights = {k: round(v, 4) for k, v in zip(FEATURE_ORDER, w)}
    json.dump({"features": FEATURE_ORDER, "weights": weights,
               "threshold": 0.5},
              open("gate.json", "w"), indent=1)

    print(f"LOO accuracy on {len(real)} real cycles: {acc:.1%}")
    print(f"false-idle rate (busy predicted idle): {fi:.1%}")
    for r in real:
        if r["label"] == "busy" or r["_p"] >= 0.5:
            print(f"  {r['cycle']} label={r['label']:4} p(busy)={r['_p']}")
    print("\nweights:", json.dumps(weights))


if __name__ == "__main__":
    main()
