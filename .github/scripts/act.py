#!/usr/bin/env python3
"""
act.py — Execute the agent's decisions. [LEGACY — v0.1, NOT WIRED UP]

Reads the LLM's JSON decision and performs the actions:
- comment_issue: post a comment on a GitHub issue
- update_file: write content to a file in the repo
- update_memory: append an entry to MEMORY.md

STATUS (2026-10-15): nothing invokes this script anymore. It is the v0.1
single-decision executor (one LLM turn → one decision.json → this file),
from before agent.py grew its own ReAct loop. agent.py's execute_tool()
absorbed all of these duties and more (it also goes through the vault for
GitHub calls, while this file uses the gh CLI + GITHUB_TOKEN directly).
README.md still describes it as "the hands" — that's historical.

Kept as reference. Do NOT wire new behavior into this file; extend
agent.py instead. See docs/architecture.md and docs/maintenance-notes.md.
"""
import json
import os
import subprocess
import sys


def run_gh(*args):
    """Run gh CLI with the GitHub token."""
    env = {**os.environ}
    result = subprocess.run(
        ["gh", *args],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        print(f"gh error: {result.stderr}", file=sys.stderr)
    return result


def comment_issue(issue_number, body):
    print(f"Commenting on issue #{issue_number}")
    run_gh("issue", "comment", str(issue_number), "--body", body)


def update_file(path, content):
    print(f"Updating file: {path}")
    # Safety: only allow writes within the repo, not to .github/workflows
    if path.startswith(".github/workflows"):
        print(f"Refusing to modify workflow: {path}", file=sys.stderr)
        return
    if ".." in path:
        print(f"Refusing path traversal: {path}", file=sys.stderr)
        return
    with open(path, "w") as f:
        f.write(content)


def update_memory(entry):
    from datetime import datetime, timezone
    print("Updating MEMORY.md")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open("MEMORY.md", "a") as f:
        f.write(f"\n- {entry}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: act.py <decision.json>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        decision = json.load(f)

    print(f"Observation: {decision.get('observation', 'none')}")
    print(f"Plan: {decision.get('plan', 'none')}")

    for action in decision.get("actions", []):
        action_type = action.get("type")

        if action_type == "comment_issue":
            comment_issue(action["issue"], action["body"])
        elif action_type == "update_file":
            update_file(action["path"], action["content"])
        elif action_type == "update_memory":
            update_memory(action["entry"])
        else:
            print(f"Unknown action type: {action_type}", file=sys.stderr)

    print("Done." if not decision.get("done") else "Nothing to do.")


if __name__ == "__main__":
    main()
