# VAULT.md — How the Vault Works

zero holds no secrets. All API access goes through the vault.

## The vault
**URL:** https://superinstance-vault.casey-digennaro.workers.dev

A Cloudflare Worker that holds API keys outside GitHub. The agent proves its identity via GitHub OIDC; the vault verifies and proxies API calls.

The worker's code is not in this repo. This file states its client contract (what the workflows and `agent.py` send and read); what happens inside the worker is its stated design, not something this tree can show. The URL above is the fallback in `agent.py`, `react.yml` and `telegram.yml`; the repo variable `VAULT_URL` overrides it.

## How the agent uses it

```yaml
# In a workflow (needs `permissions: id-token: write`). The token passes
# between steps as a step output, as in think/react/telegram.yml — a shell
# variable does not survive into the next step.
- name: Get OIDC token
  id: oidc
  run: |
    OIDC_TOKEN=$(curl -s \
      -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
      "${ACTIONS_ID_TOKEN_REQUEST_URL}&audience=vault" \
      | jq -r '.value')
    echo "token=${OIDC_TOKEN}" >> "$GITHUB_OUTPUT"

- name: Call API via vault
  env:
    OIDC_TOKEN: ${{ steps.oidc.outputs.token }}
  run: |
    curl -s -X POST https://superinstance-vault.casey-digennaro.workers.dev/proxy \
      -H "Content-Type: application/json" \
      -d "{
        \"oidc_token\": \"${OIDC_TOKEN}\",
        \"service\": \"github\",
        \"action\": \"get_repo\",
        \"params\": {\"owner\": \"purplepincher\", \"repo\": \"zero\"}
      }"
```

## For LLM access
The agent calls the LLM through the vault too. The vault holds the model API key; the agent sends prompts and gets completions without ever seeing the key.

```
POST /proxy
{
  "oidc_token": "...",
  "service": "llm",
  "action": "complete",
  "params": {
    "messages": [...],
    "model": "default"
  }
}
→ { "success": true, "result": { "content": "..." } }
```

`agent.py` sends `"model": "default"`, which the vault maps to its configured `LLM_MODEL`; the telegram and react workflows send no model, only `max_tokens` (500 and 400). The code reads `result.content` and nothing else.

## Registration
To use the vault, your fork must be registered. Open an issue titled "Register" in your fork — the fleet coordinator adds your repo to the allowlist. Until then, the vault stays silent.

## Security model
- Repos are public; workflows are visible; anyone can fork
- Forks get nothing until registered — OIDC proves identity, allowlist grants access
- Keys never leave Cloudflare
