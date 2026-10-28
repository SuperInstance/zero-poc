# Plugins — Adding a New Service

A plugin gives the agent a new capability: a new API it can call through the
vault. Plugins are how this system grows. Each one follows the same three-part
pattern, and each one is documented so that an agent who has never seen the
underlying API can use it correctly on the first try — because that is exactly
what will happen.

## The pattern

The vault worker's code is **outside this repo**. Steps 1–2 describe the
worker's convention as its owner documented it; this tree cannot verify the
names. Step 3 is the client contract, and it is what the code here does.

1. **Secret**: stored in the vault worker as `VAULT_<SERVICE>_TOKEN`
   (Cloudflare dashboard → Workers → vault worker → Settings → Variables and
   Secrets). Never in the repo. Ever.
2. **Handler**: a `proxy<Service>` function in the vault worker, registered in
   the `proxyAction` switch. It takes `(action, params, secret, env)` and
   returns JSON.
3. **Call**: the agent POSTs to the vault `/proxy` endpoint:
   ```json
   {
     "oidc_token": "<github-actions-oidc-jwt, audience=vault>",
     "service": "myservice",
     "action": "do_thing",
     "params": { "key": "value" }
   }
   ```
   The vault verifies the OIDC token, checks the repo/workflow allowlist,
   looks up the secret, runs the handler, and returns
   `{ "success": true, "result": {...} }`. The secret never leaves the worker.
4. **Reach it from the agent**: workflows call `/proxy` with `curl` + `jq`
   (see `telegram.yml`, `react.yml`). The think loop reaches only the
   services it has tools for — `api_github` and `api_cloudflare` pass any
   action through; the LLM is `llm_think()`. A new service needs a new tool
   in `agent.py` (`execute_tool` + a `PERMISSIONS` tier) and a `TOOLS.md`
   row, or the loop cannot call it.

## Worked example: the LLM service

- **Secret**: `VAULT_LLM_TOKEN` — an API key for an LLM provider.
- **Handler**: `proxyLLM` — action `complete`. Supports `anthropic` natively
  and any OpenAI-compatible API via the `openai` provider setting.
- **Config** (plain worker variables, not secrets): `LLM_PROVIDER`
  (`anthropic` or `openai`), `LLM_BASE_URL` (for OpenAI-compatible endpoints),
  `LLM_MODEL` (default model).
- **Call**: `{ "service": "llm", "action": "complete",
  "params": { "messages": [{ "role": "user", "content": "..." }],
  "max_tokens": 500 } }` — telegram.yml's shape. `agent.py` sends
  `"model": "default"` instead of `max_tokens`; react.yml adds a `system`
  param and `max_tokens: 400`.
- **Returns**: `{ "success": true, "result": { "content": "..." } }` — the
  code reads `result.content` and nothing else.

## Worked example: Telegram

Telegram is a plugin with its own small worker (the bridge), not a `/proxy`
service:

- **Secret**: `TELEGRAM_BOT_TOKEN` on the bridge worker *(outside the repo)*.
- **In**: Telegram sends updates to the bridge `/webhook`; the bridge fires a
  `repository_dispatch` (`telegram_message`, payload `text`, `username`,
  `chat_id`) to wake the repo. Needs `VAULT_GITHUB_TOKEN` on the bridge
  worker to dispatch *(outside the repo)*.
- **Out**: telegram.yml POSTs `{ "chat_id": ..., "text": "..." }` to the
  bridge `/send` (URL from the repo variable `TELEGRAM_BRIDGE_URL`, else a
  hardcoded fallback) with no OIDC token; the step fails unless the bridge
  answers `ok: true`. The bridge delivers it via the Telegram API.
- The agent never touches the Telegram API directly.

## Checklist for a new plugin

- [ ] Secret stored in the vault worker as `VAULT_<SERVICE>_TOKEN`
- [ ] `proxy<Service>` handler written, registered in `proxyAction`
- [ ] Vault worker redeployed
- [ ] If the think loop needs it: a tool in `agent.py`, a test, a `TOOLS.md` row
- [ ] This file (or a new doc under `docs/`) updated: what the service does,
      every action, every param, what comes back, and one worked example

## Design notes

- Keep handlers small and explicit: one service, a few named actions, JSON in
  and out.
- Name actions as verbs (`complete`, `send`, `get_repo`), not endpoints.
- The agent reasons about your plugin from its documentation alone. Write the
  doc for a stranger.
- If a plugin needs configuration that is not secret (base URLs, default
  models), use plain worker variables, not secrets.
