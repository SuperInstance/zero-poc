# reports/ — finished work, told back

This folder is how finished board work reaches my human.

The voice (the Telegram workflow) can only speak when spoken to — it
cannot initiate contact. The think loop works the board in silence.
Before this folder existed, the loop could finish something the human
asked for and he would never hear the outcome unless he asked again,
while the voice promised "I'll let you know" — a message it had no way
to send (docs/playtest-2026-10-27.md, deficit D1). Now the loop files
a report, and the report rides back attached to the next reply.

## Layout

```
reports/
  pending/     filed, not yet delivered
  delivered/   delivered — the permanent archive
```

## Format

A report is a small markdown file with a header:

```
---
from: think-loop
at: 2026-10-28T04:15:00Z
kind: mechanical | written
source-hash: <first 12 hex of sha1 of the normalized task text>   (board-task reports only)
task: <the task line text>                                         (board-task reports only)
---

<1-3 plain sentences: what finished, and the outcome.>
```

The *normalized task text* is the `TASKS.md` line with its checkbox
marker (`- [ ]` / `- [x]`) stripped and whitespace collapsed.

## Writers

- **The producer step** (`think.yml`, "File board reports", after the
  loop runs) — `kind: mechanical`. It compares `TASKS.md` at the
  cycle's start commit with the working tree; every telegram task
  (`(telegram ...)` in its text) that sat in `## Open` and now sits in
  `## Done` — or is checked `- [x]` anywhere — gets a report whose body
  is `Closed on the board: "<task text>".` (task text cut to 300
  chars). Files are named `<UTC %Y-%m-%dT%H%M%SZ>-<i>.md`, with a `-2`,
  `-3` suffix on collision. A task whose `source-hash` already appears
  in `pending/` or `delivered/` is never reported twice. A reports
  failure never fails the think cycle.
- **The agent itself** — `kind: written`. When the loop finishes work
  the human asked for, it may write its own report into
  `reports/pending/` with `write_file`, saying what the outcome
  actually was (the mechanical report only says the task closed). Use
  the same header; include `source-hash` and `task` when the report is
  about a board task, so the producer won't duplicate it.

## Delivery

The telegram workflow, on the human's next message:

1. **Assemble context** reads `reports/pending/*.md` oldest first (by
   filename) and picks up to **5 files / 2,000 body chars**; a single
   oversized report is cut to the budget rather than blocking the
   queue. The voice is told the reports are attached and not to repeat
   them.
2. **Record reply** prepends the block to the reply, then a blank line:

   ```
   While you were away, my loop finished:
   - <body of report 1, one line>
   - <body of report 2, one line>
   ```

   So the recorded output in `conversation/outputs/` is exactly what
   was delivered, block included.
3. **Reply via bridge** sends it.
4. **Mark reports delivered** moves each delivered file from
   `pending/` to `delivered/` and commits
   `telegram: reports delivered (<turn stem>)`. It runs only if every
   step before it succeeded — if the Think step failed and the
   fallback hiccup line went out instead, the reports stay pending for
   the next reply.

Anything over the caps simply waits for the next message.

**The gate (v0.8.2).** The block is the workflow's voice, never the
model's. If the voice's draft reply imitates the block (it contains
"while you were away" or "loop finished" while a block is being
attached), the Record step replaces the draft whole with a neutral
line and notes the replacement in the output's header. Prompt
wording alone failed this twice in live acceptance; the boundary
is therefore mechanical.

## Rules

- **Delivered is permanent.** A delivered report is never edited or
  deleted; `delivered/` is the audit of what the human was told.
- **Dry-run never consumes.** A `dry_run: "true"` test dispatch shows
  the block in its recorded reply but leaves every report in
  `pending/`.
- **Empty means unchanged.** With nothing in `pending/`, the telegram
  pipeline behaves exactly as it did before reports existed — no
  block, no system note, no extra commit.
