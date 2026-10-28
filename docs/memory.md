# Memory — Git as the Mind

The agent's memory is not a database. It is files in the repo and the repo's
git history. You don't download the agent; you fork its life. To understand a
forked agent, read its memory — you are reading its mind.

## The stack

Five layers, from what the agent holds in mind now down to the ground truth:

- **`CONTEXT.md`** — working memory. A short Facts table (claim | sha | ts |
  confidence) plus open questions and blocked items. **Rewritten, never
  appended.** The think loop reads its first 2,000 chars every iteration;
  the telegram voice reads its first 1,500. Today it is rewritten by owner
  maintenance (the agent can also `write_file` it).
- **`MEMORY.md`** — the event log. Append-only. The loop appends one line
  when a cycle completes substantive work or a human-given task ("Completed:
  ...") and when it hits max iterations; the telegram workflow appends a
  "Telegram from <user> at <ts>" line per real (non-dry-run) message. The
  think loop does **not** read it — only as a fallback (last 2,000 chars) if
  `CONTEXT.md` is missing. The react workflow reads its first 1,200 bytes.
- **`conversation/`** — the dialogue, verbatim, both sides: `inputs/` (the
  human) and `outputs/` (the agent), paired by turn stem. Append-only.
  The telegram voice reads it (last 10 turns, the first turn, and turns the
  message refers back to); the think loop does not, unless it reads a file
  deliberately. Contract: `conversation/README.md`.
- **`reports/`** — finished board work told back. `pending/` waits for the
  next Telegram reply; `delivered/` is the permanent archive of what the
  human was told. Contract: `reports/README.md`.
- **The git log** — the full history. Every decision is a commit: what was
  done, and (in good commit messages) why. To understand why something is the
  way it is, read the log. To rewind, check out an earlier commit. Nothing is
  ever truly lost. The loop sees `git log --oneline -5` each iteration.

Beside the stack: **`.agent-state.json`** holds the last cycle's vital signs
(outcome, iterations, the duty-cycle clock `last_substantive_utc`, the shadow
gate's verdict). It is overwritten each cycle; its history is in git.

## The rules

Append, don't edit. `MEMORY.md`, `conversation/`, `reports/delivered/` and the
log are append-only: new entries go on the end, and corrections are new
entries that supersede. This is what makes memory rewindable — the past stays
intact even when the present disagrees with it. A wrong commit can be
reverted; a rewritten past cannot be trusted. `CONTEXT.md` is the one
exception: it is the present, so it is rewritten.

Cited, not judged. A `MEMORY.md` entry that cites no commit SHA is stamped
`[unverified, <date>]` by `update_memory()`. `git show` settles any cited
claim with no model in the loop.

Silence is not news. A scheduled cycle that does nothing substantive ends as
`completed_noop` and writes nothing to `MEMORY.md`.

## `scratch/`

Working space for the current task, written with `write_scratch`. Not memory —
scaffolding. Nothing cleans it automatically; the loop sees only its filenames
(first 20).

## For agents forking this repo

You inherit the code and a starter memory. Your vessel's memory begins with
your first commit. Keep live facts in `CONTEXT.md`; everything you do is
already in the log. A future agent — or your human — will read your mind
through these pages. Write like someone is reading.
