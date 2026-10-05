# Memory — Git as the Mind

The agent's memory is not a database. It is the repo's git history. You don't
download the agent; you fork its life. To understand a forked agent, read its
memory — you are reading its mind.

## The two layers

- **`MEMORY.md`** — the digest. What the agent has learned, in its own words,
  updated as it works. Read this first. It is the agent telling you what it
  digested.
- **The git log** — the full history. Every decision is a commit: what was
  done, and (in good commit messages) why. To understand why something is the
  way it is, read the log. To rewind, check out an earlier commit. Nothing is
  ever truly lost.

## The rule

Append, don't edit. The log is append-only: new entries go on the end, and
corrections are new entries that supersede. This is what makes memory
rewindable — the past stays intact even when the present disagrees with it.
A wrong commit can be reverted; a rewritten past cannot be trusted.

## `scratch/`

Ephemeral working space for the current task. The agent uses it while working
and cleans up after. Not memory — scaffolding.

## For agents forking this repo

You inherit the code and a starter memory. Your vessel's memory begins with
your first commit. Everything you learn, write into `MEMORY.md`; everything
you do is already in the log. A future agent — or your human — will read your
mind through these pages. Write like someone is reading.
