## Vault Registration

How a fork of this repo gets access to the vault.

> **Correction (2026-10-15):** an earlier version of this file — written by
> the agent early in its life — instructed forks to put vault credentials
> into repository secrets and config files (`.env`, `config.yaml`). That was
> wrong and dangerous: **this repo must never hold secrets** (see AGENTS.md
> and VAULT.md). The actual procedure is below. The vault holds the keys;
> the fork only proves who it is.

1. **Fork** this repo (or the template, `purplepincher/zero`).
2. **Open an issue titled "Register"** in your fork. This is the whole
   request — no credentials are exchanged, nothing is pasted anywhere.
3. **The fleet coordinator** (a human) adds your `owner/repo` to the vault
   worker's allowlist.
4. **Done.** On the next think cycle the vault accepts your workflows'
   OIDC tokens (audience `vault`) and starts proxying LLM/GitHub/etc.
   calls. Until then, the vault stays silent — unregistered forks get
   nothing, even though the workflows run.

Why it works this way: GitHub Actions mints a short-lived OIDC token per
run; the vault verifies it and checks the allowlist. Forks are public and
forkable by anyone, but a fork with no allowlist entry cannot authenticate.
Keys never leave Cloudflare.

If your fork stays silent after registration, check: workflows enabled
(Actions tab), the issue really says "Register", and the vault allowlist
spelling of `owner/repo`.

Optional settings a fork may add (none hold a model key; names from the
workflows):

- Repo variable `VAULT_URL` — overrides the hardcoded vault URL.
- Repo variable `TELEGRAM_BRIDGE_URL` — your own Telegram bridge worker.
  Without it, `telegram.yml` falls back to the original's bridge URL.
- Repo secret `TYPESAFE_API_KEY` — lets the idle gate answer
  (`docs/system1.md`). think.yml's comment calls the gate inert without
  it; any gate error runs the cycle.
