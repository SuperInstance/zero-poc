# Installed plugins

What this agent has grabbed, under the contract in
plugins/README.md. A plugin is installed iff it appears here,
its folder is in `plugins/`, and its row is in `TOOLS.md` —
all three from the same `plugin: grab <name>` commit.

| Plugin | Kind | Grabbed | Source | What it does |
|---|---|---|---|---|
| weather | skill | 2026-10-28 | SuperInstance/xero-lab `plugins/weather/` | Current conditions + today/tomorrow outlook for a named place (default Sitka, Alaska) from wttr.in — measured numbers via recipe, failures reported, never estimated. |
