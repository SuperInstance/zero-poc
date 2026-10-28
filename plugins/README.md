# Plugins — the grabber (plug #0)

The agent is born minimal on purpose. The birth minimum is
three things: a residual self image, a starter memory, and
**the grabber** — the ability to acquire new capabilities
after birth. This folder is where grabbed
capabilities live, and this file is the contract for how they
get here. An agent that can grab plugins can become anything
the shelf holds; an agent that cannot is frozen at whatever it
was born with.

## What a plugin is here

A plugin is a folder, `plugins/<name>/`, containing `PLUGIN.md`
plus any recipe files it needs. `PLUGIN.md` states:

- what the plugin does, in one paragraph;
- its **kind** (below);
- the exact recipe — commands, endpoints, parsing — written so
  an agent that has never seen the underlying API succeeds on
  the first try, because that is exactly what will happen;
- its failure modes, and the honest fallback for each (report
  the failure; never invent the result);
- the exact `TOOLS.md` row the plugin adds (see "Installed"
  below).

Two kinds:

- **skill** — knowledge the think loop executes with tools it
  already has (shell, files, git). The plugin is pure
  documentation-plus-recipe; grabbing it is the whole install.
  Example: `plugins/weather/`.
- **vault-service** — a new capability behind the vault (a
  secret + a handler in the vault worker), following
  docs/plugins.md. That kind ALSO needs the handler deployed,
  which is human/out-of-repo work — so a vault-service grab is
  only complete when the handler exists and answers. The folder
  documents the service either way; until the handler is live,
  the plugin is *documented, not available* (the TOOLS.md
  honesty rule).

## Installed means three things, in one commit

A plugin counts as installed iff all three land together, in a
single commit with subject `plugin: grab <name>`:

1. its folder is at `plugins/<name>/`;
2. it has a row in `plugins/INDEX.md` (name, kind, date, source);
3. its row is in `TOOLS.md` (the index of what the agent HAS).

The TOOLS.md checklist rule applies: the row lands in the same
commit as the capability — documented later is undocumented,
and undocumented is unknown to the next cycle.

## Grabbing

**Grabbing** = copying a plugin folder from an approved source
into `plugins/`, plus the INDEX.md row and the TOOLS.md row,
in that one commit.

Approved sources — the loop may grab from these on its own,
when a task calls for the capability:

- **SuperInstance/xero-lab, folder `plugins/`** — the lab
  shelf. Plugins are authored and proven in the lab first; this
  repo grabs what it needs, whole and unedited.

Any other source is a **deferred** action (same posture as
`write_workflow`): the loop files an issue naming the plugin,
its source, and what it would add, and a human reviews before
anything lands. Capability from the shelf is trusted because
the shelf is ours and its contents are proven; capability from
the wild is reviewed because it runs with the agent's hands.

## Dropping

A grab is reversible: remove the folder, the INDEX.md row, and
the TOOLS.md row in one commit, `plugin: drop <name>`. For a
vault-service plugin, also note in the commit whether the
vault handler was left in place (harmless) or removed.

## The shelf improves first

A grabbed copy is a snapshot. Fixes and improvements land on
the shelf (xero-lab) first, get proven there, and are then
re-grabbed; a local edit to a grabbed copy that never reaches
the shelf is drift, and the next re-grab silently reverts it.
