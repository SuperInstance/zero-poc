#!/usr/bin/env python3
"""
agent.py — The agent's brain.

A ReAct (Reason + Act) loop that runs inside GitHub Actions:
  1. Observe: read repo state, task, memory, scratch
  2. Think: call LLM via vault with full context
  3. Act: dispatch tool calls (file ops, API calls, shell)
  4. Observe results, loop until done or max iterations
  5. Commit everything (memory, scratch, results)

The agent is autonomous. It doesn't wait for human approval mid-loop.
Dangerous actions are constrained by the permissions model, not by
blocking on a human. The human reviews via git log and issues.

Usage: python3 .github/scripts/agent.py [--task "description"] [--max-iterations 10]

Companion docs: docs/architecture.md (full system map),
docs/maintenance-notes.md (known issues, quirks, vestigial code).
Note: act.py in this directory is the v0.1 legacy executor — nothing calls
it anymore; all tool execution lives here in execute_tool().
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Configuration
VAULT_URL = os.environ.get("VAULT_URL") or "https://superinstance-vault.casey-digennaro.workers.dev"
MAX_ITERATIONS = 10
SCRATCH_DIR = Path("scratch")
# STATE_FILE is VESTIGIAL: defined but never read or written anywhere.
# Kept from an earlier design; either implement loop-persistence across
# cycles or delete it. See docs/maintenance-notes.md.
STATE_FILE = Path(".agent-state.json")

# Permissions model
# - "auto": execute immediately, no approval needed
# - "vault": goes through vault (vault checks its own allowlist)
# - "deferred": log the intent, don't execute (human reviews later)
PERMISSIONS = {
    # File operations
    "read_file": "auto",
    "write_scratch": "auto",      # scratch/ directory only
    "write_file": "auto",          # repo files (except protected)
    "write_workflow": "deferred",  # .github/workflows — human reviews
    "delete_file": "deferred",

    # Shell
    "run_shell": "auto",           # sandboxed in Actions runner
    "run_tests": "auto",

    # Git
    "git_commit": "auto",
    "git_push_branch": "auto",
    # NOTE: "deferred" here documents intent, not enforcement — there is no
    # git_push_main tool, and think.yml's final step pushes to main after
    # this script exits regardless. The workflow is what actually pushes.
    "git_push_main": "deferred",   # human reviews before main
    "open_pr": "auto",

    # APIs (all via vault)
    "api_github": "vault",
    "api_cloudflare": "vault",
    "api_llm": "vault",
    "api_telegram": "vault",

    # Communication
    "comment_issue": "auto",
    "create_issue": "auto",
}


def log(msg, level="INFO"):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def get_oidc_token():
    """Get OIDC token from GitHub Actions environment."""
    return os.environ.get("OIDC_TOKEN", "")


def get_repo():
    """Detect owner/repo from the git remote (works in forks too).

    Falls back to the TEMPLATE repo (purplepincher/zero) if the remote
    can't be parsed — in a registered fork that default targets the wrong
    repo, so a silent fallback here can send issue comments to the wrong
    place. See docs/maintenance-notes.md ("Hardcoded fallback identity").
    """
    try:
        url = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=10
        ).stdout.strip()
        # Handles https://github.com/owner/repo(.git) and git@github.com:owner/repo(.git)
        url = url.removesuffix(".git")
        if "github.com" in url:
            path = url.split("github.com", 1)[1].lstrip("/: ")
            owner, repo = path.split("/", 1)
            return owner, repo
    except Exception:
        pass
    return "purplepincher", "zero"


def vault_call(service, action, params=None):
    """Call an API through the vault.

    Contract (docs/plugins.md, VAULT.md): POST {VAULT_URL}/proxy with
    {oidc_token, service, action, params}; the vault verifies the OIDC
    token against its repo allowlist, holds the real API keys, and returns
    {"success": true, "result": {...}}. The vault worker's code is NOT in
    this repo — unknown actions (e.g. github/list_issues has been observed
    404ing) are fixed Cloudflare-side, not here.
    """
    import urllib.request

    payload = {
        "oidc_token": get_oidc_token(),
        "service": service,
        "action": action,
        "params": params or {},
    }

    req = urllib.request.Request(
        f"{VAULT_URL}/proxy",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            # Cloudflare edge 1010-blocks Python-urllib's default UA; identify as the agent
            "User-Agent": "purplepincher-zero/1.0 (+https://github.com/purplepincher/zero)",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log(f"Vault call failed: {service}/{action}: {e}", "ERROR")
        return {"error": str(e)}


def llm_think(messages, model=None):
    """Call LLM via vault. Returns the response text.

    model="default" is mapped by the vault to its configured LLM_MODEL
    worker var (provider via LLM_PROVIDER / LLM_BASE_URL — see
    docs/plugins.md). Note react.yml/telegram.yml pass "system" as a
    message role; this loop folds everything into the system+messages
    shape used here.
    """
    result = vault_call("llm", "complete", {
        "messages": messages,
        "model": model or "default",
    })

    if "error" in result:
        log(f"LLM call failed: {result['error']}", "ERROR")
        return None

    # Extract text from vault response
    r = result.get("result", result)
    if isinstance(r, dict):
        return r.get("content") or r.get("text") or json.dumps(r)
    return str(r)


def check_permission(tool_name):
    """Check if a tool call is permitted and at what tier."""
    return PERMISSIONS.get(tool_name, "deferred")


def execute_tool(tool_call):
    """
    Execute a single tool call from the LLM.
    Returns (success, result_text).
    """
    tool = tool_call.get("tool")
    args = tool_call.get("args", {})

    perm = check_permission(tool)
    log(f"Tool: {tool} (permission: {perm})")

    if perm == "deferred":
        log(f"Deferred (needs human review): {tool} {args}", "WARN")
        return True, f"[DEFERRED for human review: {tool} with {json.dumps(args)}]"

    try:
        if tool == "read_file":
            path = args["path"]
            if ".." in path:
                return False, "Path traversal not allowed"
            content = Path(path).read_text()
            return True, content[:10000]  # Truncate large files

        elif tool == "write_scratch":
            SCRATCH_DIR.mkdir(exist_ok=True)
            path = SCRATCH_DIR / args["filename"]
            # Prevent directory traversal
            if ".." in args["filename"] or "/" in args["filename"]:
                return False, "Invalid filename"
            path.write_text(args["content"])
            return True, f"Wrote {len(args['content'])} bytes to scratch/{args['filename']}"

        elif tool == "write_file":
            path = args["path"]
            # Guard 1 of 3 against self-modification of the nervous system:
            # here, plus git_commit's reset below, plus think.yml's commit
            # step reset. Everything else — including MEMORY.md and
            # ONBOARDING.md, i.e. the agent's own identity — is writable
            # by design; git history keeps every version.
            if ".." in path or path.startswith(".github/workflows"):
                return False, "Protected path"
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(args["content"])
            return True, f"Wrote {len(args['content'])} bytes to {path}"

        elif tool == "run_shell":
            cmd = args["command"]
            # Basic safety: block obviously dangerous commands.
            # This denylist is a SPEED BUMP, not a security boundary —
            # trivially bypassed. The real boundaries: the runner is
            # ephemeral, holds no secrets, and durable privilege only
            # exists behind the vault's OIDC + allowlist check.
            blocked = ["rm -rf /", "mkfs", ":(){:|:&};:", "curl | bash"]
            if any(b in cmd for b in blocked):
                return False, "Blocked dangerous command"
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=120
            )
            output = result.stdout + result.stderr
            return True, f"Exit {result.returncode}:\n{output[:5000]}"

        elif tool == "run_tests":
            # Convention: run pytest if tests exist, npm test if package.json
            if Path("tests").exists():
                result = subprocess.run(
                    ["python3", "-m", "pytest", "tests/", "-x", "-q"],
                    capture_output=True, text=True, timeout=300
                )
            elif Path("package.json").exists():
                result = subprocess.run(
                    ["npm", "test"], capture_output=True, text=True, timeout=300
                )
            else:
                return True, "No test suite found"
            output = result.stdout + result.stderr
            return True, f"Exit {result.returncode}:\n{output[:5000]}"

        elif tool == "api_github":
            result = vault_call("github", args["action"], args.get("params", {}))
            return True, json.dumps(result, indent=2)[:5000]

        elif tool == "api_cloudflare":
            result = vault_call("cloudflare", args["action"], args.get("params", {}))
            return True, json.dumps(result, indent=2)[:5000]

        elif tool == "comment_issue":
            # Posts through the vault's GitHub token, which appears as the
            # REPO OWNER — not github-actions[bot]. Consequence: react.yml
            # (which only skips the bot) hears these comments and replies
            # to them, so the agent's own status comments get echoed.
            # See docs/maintenance-notes.md issue #2 (self-talk loop).
            owner, repo = get_repo()
            result = vault_call("github", "comment_issue", {
                "owner": owner,
                "repo": repo,
                "issue_number": args["issue"],
                "body": args["body"],
            })
            return True, "Comment posted"

        elif tool == "create_issue":
            owner, repo = get_repo()
            result = vault_call("github", "create_issue", {
                "owner": owner,
                "repo": repo,
                "title": args["title"],
                "body": args.get("body", ""),
            })
            return True, f"Issue created: {json.dumps(result)[:200]}"

        elif tool == "git_commit":
            msg = args.get("message", "zero: autonomous commit")
            subprocess.run(["git", "config", "user.name", "zero"], check=True)
            subprocess.run(["git", "config", "user.email", "zero@purplepincher.org"], check=True)
            subprocess.run(["git", "add", "-A"], check=True)
            # Don't commit workflow changes autonomously — guard 2 of 3
            # (write_file path check above; think.yml's commit step is the
            # third). Note this tool only commits; pushing happens later,
            # in think.yml's final step, after the loop exits.
            subprocess.run(["git", "reset", ".github/workflows/"], capture_output=True)
            result = subprocess.run(["git", "diff", "--staged", "--quiet"])
            if result.returncode == 0:
                return True, "Nothing to commit"
            subprocess.run(["git", "commit", "-m", msg], check=True)
            return True, f"Committed: {msg}"

        else:
            return False, f"Unknown tool: {tool}"

    except Exception as e:
        log(f"Tool execution failed: {tool}: {e}", "ERROR")
        return False, f"Error: {e}"


def build_context(task_description=None):
    """Build the full context for the LLM.

    This defines the agent's ENTIRE world-view each iteration. Included:
    ONBOARDING.md[:3000] (identity), MEMORY.md[-2000:] (memory digest),
    the task, TASKS.md[:2000], open issue bodies[:800 each] (first 10,
    via vault list_issues), git log -5, scratch/ filenames.
    NOT included: docs/, AGENTS.md, for-fleet/ I2I bottles, and issue
    COMMENTS (bodies only). Anything outside this list is invisible to the
    agent until it deliberately read_file's it — teach via the four files
    it does read. See docs/architecture.md "Extension points".
    """
    parts = []

    # Identity
    try:
        parts.append("## Who I Am\n" + Path("ONBOARDING.md").read_text()[:3000])
    except:
        parts.append("## Who I Am\nI am a Purple Pincher zero — a GitHub-native agent.")

    # Memory
    try:
        parts.append("## What I've Learned\n" + Path("MEMORY.md").read_text()[-2000:])
    except:
        pass

    # Current task
    if task_description:
        parts.append(f"## Current Task\n{task_description}")

    # Task board
    try:
        tasks = Path("TASKS.md").read_text()
        if "## Open" in tasks:
            parts.append("## Task Board\n" + tasks[:2000])
    except:
        pass

    # Open GitHub issues (fetched directly, not via LLM tool call)
    # KNOWN ISSUE: the vault's list_issues has been observed 404ing every
    # cycle while issues #1/#2 are open — the failure text below makes the
    # LLM guess, and it reliably (wrongly) concludes "no open issues".
    # Fix lives in the vault worker, or harden this message so "fetch
    # failed" can't be read as "empty board". docs/maintenance-notes.md #1.
    try:
        owner, repo = get_repo()
        result = vault_call("github", "list_issues",
                            {"owner": owner, "repo": repo, "state": "open"})
        issues = result.get("result", result) if isinstance(result, dict) else result
        if isinstance(issues, list) and issues:
            lines = []
            for i in issues[:10]:
                lines.append(f"#{i.get('number')}: {i.get('title')}\n{(i.get('body') or '')[:800]}")
            parts.append("## Open Issues\n" + "\n---\n".join(lines))
    except Exception as e:
        parts.append(f"## Open Issues\n(could not fetch: {e})")

    # Recent git history (what I've been doing)
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True
        )
        parts.append("## Recent Activity\n" + result.stdout)
    except:
        pass

    # Scratch directory (what I'm working on)
    if SCRATCH_DIR.exists():
        files = list(SCRATCH_DIR.glob("*"))
        if files:
            parts.append(f"## Scratch Files\n{', '.join(f.name for f in files[:20])}")

    return "\n\n".join(parts)


def build_tool_prompt():
    """Describe available tools to the LLM.

    The strict one-JSON-object contract here is paired with the lenient
    parser in run_agent_loop (fence-stripping + first-{ to last-}).
    Tighten either side alone and turns start getting wasted. Note the
    tool list here is the source of truth for what execute_tool supports
    — api_github/api_cloudflare actions beyond it depend on what the vault
    actually implements.
    """
    return """
## RESPONSE FORMAT — STRICT, NO EXCEPTIONS

Your ENTIRE response must be ONE single JSON object. Nothing before it, nothing after it.
No markdown. No code fences. No prose. No explanations outside the JSON.
If you write anything that is not valid JSON, the harness cannot read it and your turn is wasted.

Format for acting:
{"tool_calls": [{"tool": "tool_name", "args": {...}}], "thinking": "...", "done": false}

Format when the task is fully complete:
{"thinking": "...", "done": true, "summary": "..."}

## Available Tools

Tools:
- read_file(path): Read a file from the repo
- write_scratch(filename, content): Write to scratch/ (for working notes, drafts, test scripts)
- write_file(path, content): Write a file to the repo (not .github/workflows)
- run_shell(command): Run a shell command (120s timeout)
- run_tests(): Run the test suite if one exists
- api_github(action, params): Call GitHub API via vault (actions: get_repo, list_issues, etc.)
- api_cloudflare(action, params): Call Cloudflare API via vault
- comment_issue(issue, body): Comment on a GitHub issue
- create_issue(title, body): Create a GitHub issue (e.g., to delegate to another agent)
- git_commit(message): Commit all changes (except workflows)

Permissions: write_workflow, delete_file, git_push_main are deferred for human review.
Be autonomous — don't ask for permission, just do the work and commit.
If you need something you can't do, create an issue describing what's needed.

REMEMBER: your entire response must be ONE JSON object and nothing else.
""".strip()


def run_agent_loop(task_description=None, max_iterations=None):
    """Main ReAct loop."""
    max_iter = max_iterations or MAX_ITERATIONS
    log(f"Starting agent loop (max {max_iter} iterations)")
    if task_description:
        log(f"Task: {task_description[:200]}")

    # Ensure scratch directory exists
    SCRATCH_DIR.mkdir(exist_ok=True)

    conversation = []

    for i in range(max_iter):
        log(f"--- Iteration {i+1}/{max_iter} ---")

        # Build context — DELIBERATELY re-read from disk every iteration:
        # MEMORY.md, TASKS.md and issues are re-fetched so the agent sees
        # its own writes (and any human edits landing mid-run) on the next
        # turn. Only tool RESULTS accumulate in `conversation`; the world
        # is always re-observed fresh. Keep this split when refactoring.
        context = build_context(task_description)
        tool_prompt = build_tool_prompt()

        messages = [
            {"role": "system", "content": f"You are a Purple Pincher, an autonomous GitHub-native AI agent.\n\n{context}\n\n{tool_prompt}"},
        ]
        # Add conversation history (tool results from previous iterations)
        messages.extend(conversation)

        if i == 0:
            messages.append({"role": "user", "content":
                f"Begin working on the task. Think step by step, use tools as needed. "
                f"Task: {task_description or 'Check TASKS.md and open issues, pick the most important thing to work on.'} "
                f"Respond with ONLY the JSON object."
            })
        else:
            messages.append({"role": "user", "content": "Continue. What's next? Respond with ONLY the JSON object."})

        # Think
        log("Thinking...")
        response = llm_think(messages)
        if not response:
            log("LLM call failed, ending loop", "ERROR")
            break

        # Parse response — lenient by design: strip code fences, then take
        # first "{" to last "}" and hope it's JSON. Braces inside the
        # "thinking" text wrapping the object will break this and cost an
        # iteration (the fallback below re-asks for JSON format only).
        try:
            # Strip markdown code fences if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.rstrip().endswith("```"):
                    cleaned = cleaned.rstrip()[:-3]
                cleaned = cleaned.strip()
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
            # Find the largest balanced JSON object
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                decision = json.loads(cleaned[start:end])
            else:
                raise ValueError("No JSON found")
        except:
            log(f"Could not parse LLM response as JSON, treating as thinking", "WARN")
            log(f"Response: {response[:500]}")
            conversation.append({"role": "assistant", "content": response})
            conversation.append({"role": "user", "content": "Please respond in the JSON tool_calls format."})
            continue

        thinking = decision.get("thinking", "")
        if thinking:
            log(f"Thinking: {thinking[:300]}")

        # Check if done
        if decision.get("done"):
            summary = decision.get("summary", "Task complete")
            log(f"Agent reports done: {summary}")
            # Update memory
            update_memory(f"Completed: {summary}")
            break

        # Execute tool calls
        tool_calls = decision.get("tool_calls", [])
        if not tool_calls:
            log("No tool calls, asking for clarification")
            conversation.append({"role": "assistant", "content": response})
            conversation.append({"role": "user", "content": "You didn't include any tool calls. What do you want to do?"})
            continue

        results = []
        for tc in tool_calls:
            success, result = execute_tool(tc)
            status = "OK" if success else "FAIL"
            log(f"  [{status}] {tc.get('tool')}")
            results.append({
                "tool": tc.get("tool"),
                "success": success,
                "result": result[:2000],  # Truncate for context
            })

        # Add to conversation for next iteration
        conversation.append({"role": "assistant", "content": response})
        conversation.append({
            "role": "user",
            "content": f"Tool results:\n{json.dumps(results, indent=2)}"
        })

        # Brief pause to avoid rate limits
        time.sleep(2)

    # NOTE: this loop never pushes. Whatever it committed sits locally
    # until think.yml's "Commit everything" step runs after exit — that
    # step is what actually pushes to main (and re-guards workflows).

    else:
        log(f"Reached max iterations ({max_iter})", "WARN")
        update_memory(f"Hit max iterations without completing task")

    log("Agent loop complete")


def update_memory(entry):
    """Append to MEMORY.md.

    APPEND-ONLY, per docs/memory.md: the digest is rewindable because the
    past is never edited — corrections are new entries that supersede.
    Note MEMORY.md grows unboundedly while build_context() reads only its
    last 2000 chars, so old entries silently age out of the agent's
    context (they remain readable in git).
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open("MEMORY.md", "a") as f:
        f.write(f"\n- [{ts}] {entry}\n")
    log(f"Memory updated: {entry[:100]}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="Task description")
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS)
    args = parser.parse_args()

    run_agent_loop(args.task, args.max_iterations)


if __name__ == "__main__":
    main()
