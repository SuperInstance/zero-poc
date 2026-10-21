To switch from using a static token to OIDC for authentication in the `think.yml` workflow, the following changes need to be made:

1. **Remove Static Token**: Eliminate any references to static tokens such as `GH_TOKEN` in the workflow configuration.
2. **Configure OIDC Token**: Update the workflow to request an OIDC token with the necessary permissions. This involves configuring the `id-token` permission and ensuring that the workflow requests the token.
3. **Update Vault Configuration**: Modify the workflow to use the OIDC token when interacting with the vault. This may include setting environment variables or modifying the steps that interact with the vault.
4. **Test the Workflow**: After making the changes, run the workflow to ensure that it can successfully authenticate using OIDC and interact with the vault.