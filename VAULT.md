# VAULT.md — How the Vault Works

zero holds no secrets. All API access goes through the vault.

## The vault
**URL:** https://superinstance-vault.casey-digennaro.workers.dev

A Cloudflare Worker that holds API keys outside GitHub. The agent proves its identity via GitHub OIDC; the vault verifies and proxies API calls.

## How the agent uses it

```yaml
# In a workflow:
- name: Get OIDC token
  run: |
    OIDC_TOKEN=$(curl -s \
      -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
      "${ACTIONS_ID_TOKEN_REQUEST_URL}&audience=vault" \
      | jq -r '.value')

- name: Call API via vault
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
    "model": "claude-sonnet-4-5"
  }
}
```

## Registration
To use the vault, your fork must be registered. Open an issue titled "Register" in your fork — the fleet coordinator adds your repo to the allowlist. Until then, the vault stays silent.

## Security model
- Repos are public; workflows are visible; anyone can fork
- Forks get nothing until registered — OIDC proves identity, allowlist grants access
- Keys never leave Cloudflare
- Every access is logged
