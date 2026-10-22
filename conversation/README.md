# conversation/ — the dialogue itself

This folder is the conversation, as a first-class thing in the repo.

`MEMORY.md` is a digest. `TASKS.md` is a routing board. Neither is the
conversation — and before this folder existed, the repo recorded only
the human's side of it (a timestamp line and a flattened task copy),
while the agent's replies lived only in Telegram and in an ephemeral
runner's `/tmp`. A repo that holds one side of its own conversation
cannot build on the conversation. Now it holds both.

## Layout

```
conversation/
  inputs/    one file per message the human sent
  outputs/   one file per reply the agent sent
```

## The pairing rule

A turn has a **stem**: the UTC second the input arrived, formatted
`YYYY-MM-DDTHHMMSSZ` (a `-2`, `-3` suffix if two inputs land in the
same second). The input is `inputs/<stem>.md`; the reply to it is
`outputs/<stem>.md` — **same stem, so a turn pairs by filename**, and
each output also names its input in an `in-reply-to` field.

## Format

Each file is markdown with a small header:

```
---
from: Casey            (inputs)  /  zero  (outputs)
at: 2026-10-22T19:33:06Z
via: telegram
turn: 2026-10-22T193306Z
in-reply-to: inputs/<stem>.md      (outputs only)
---

<the message text, in full>
```

Inputs record the message **in full** — the 200-char flattening in
`TASKS.md` is a routing copy, not the record.

## Rules

- **Append-only.** A recorded turn is never edited. A correction is a
  new turn.
- **Writers:** only the telegram workflow writes turns (v0.4). The
  record step commits the output *before* the bridge delivers it —
  memory-first, symmetric with the inbound log: the record is
  primary, the send is delivery.
- **Provenance is stated, not implied.** Machine-recorded turns are
  the default. Anything else says so in its header — the seed turn
  below is marked `recorded: owner-reported` because its reply
  predates this folder and was never machine-recorded.

## Why it exists

So that other processes — the think loop, skills, tools not yet
written — can read the dialogue as their substrate and work *because
of* it: summarize it, file it, learn from it, answer it better. The
conversation is the input everything else in this repo is ultimately
for. It gets a folder of its own, inputs and outputs, like anything
else that matters here.

## Genesis

The first recorded turn is `2026-10-22T193306Z` — the owner asked
"are you awake?" and the agent answered in Telegram. Its input is
verbatim (recovered from the `TASKS.md` routing copy); its output is
owner-reported, marked as such in the file, because at the time it
was sent no machine record was kept. That gap is the reason this
folder exists. Every turn after it is recorded whole, both sides,
by the workflow itself.
