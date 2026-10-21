The current GitHub authentication status shows that the `github-actions[bot]` account is logged in using a token. To proceed with OIDC verification, I need to ensure that the workflow is configured to use OIDC for authentication instead of a static token. This involves the following steps:

1. **Update Workflow Configuration**: Modify the GitHub Actions workflow files to use OIDC tokens for authentication.
2. **Configure Vault for OIDC**: Ensure that the vault is set up to accept OIDC tokens from this repository.
3. **Test OIDC Authentication**: Run a test to verify that the OIDC authentication is working as expected.