# Clones and Shells

## The snail and the hermit crab

The git-native agent is like a snail: the git log is the silver trail showing where it has been. As it grows, it leaves behind usable shells — snapshots of working code, docs, identity, and memory up to that point.

A local clone does **not** join the sky pipeline. It does not phone home for thought. It is a shell left on the beach.

Then a **hermit crab** moves in: a Pi, a laptop, an Oracle machine, any local runtime. The hermit crab has its own brain and its own life — a local model, or its human's key. The shell gives it everything the sky agent knew: code, docs, identity, memory. The crab walks around in it, does local work, and never reports back up the chain.

The crab may leave bottles — issues, notes, messages — for the sky agent to find later. And when the sky agent has grown a better shell, the crab can move into the newer one. But it is not subordinate to the sky pipeline. It is its own creature, wearing a borrowed shell.

## What a shell carries

A usable shell is a snapshot containing:

- **Code** — the working application at that commit.
- **Docs** — everything in `docs/`, the agent's own Wikipedia.
- **Identity** — `ONBOARDING.md`, `AGENTS.md`: who the agent is, how it works.
- **Memory** — `MEMORY.md` and the git log: what it has done and learned.

`git clone` at any commit is a shell. Tag the good ones.

## Shell sizes

Not every creature needs the same shell. Purple Pincher shells come in sizes:

- **Zero** — the minimal seed. Fork-and-go. Everything needed, nothing extra.
- **Turbo** — a self-contained application shell. One repo, one builder agent whose whole world is that repo.
- **Tapestry** — the quilt shell. Many repos, one coherent story — the middle management of turbos.

A creature outgrows its shell and moves to a bigger one. The creature stays the same; only the shell changes.

## The rule

**Shells flow down. Thought stays local.** The sky agent's trail is a gift, not a leash.
