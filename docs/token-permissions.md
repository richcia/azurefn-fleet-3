# GitHub PAT write access for `richcia/azurefn-fleet-3`

When you use a Personal Access Token (PAT), write access is not assigned directly to the token name (`copilot-token`). Access comes from:

- the PAT type and scopes/permissions, and
- the PAT owner's access to the repository.

## Fine-grained PAT (recommended over classic PAT)

In **GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens**:

1. Edit/create the token.
2. Under **Repository access**, choose:
   - **Only select repositories** and include `richcia/azurefn-fleet-3`, or
   - **All repositories** (if appropriate for your use case).
3. Under **Repository permissions**, set at least:
   - **Contents: Read and write**
4. Add other permissions only if needed by your workflow, for example:
   - **Pull requests: Read and write**
   - **Workflows: Read and write**

## Classic PAT

Classic PATs use scopes instead of per-repo permission selection.

- For private repositories, include the `repo` scope.
- For public-only operations, use the appropriate public scopes.
- The PAT can only do what its owner can do in `richcia/azurefn-fleet-3` (for example, no write if the owner has read-only access).

## Verify write access safely

Do not paste tokens into chat, code, scripts, or checked-in files.

```bash
GH_TOKEN=YOUR_PAT gh api repos/richcia/azurefn-fleet-3 --jq '.permissions'
```

Expected write indicator:

- `"push": true` means the token has repository write (push) access.

Optional single-value check:

```bash
GH_TOKEN=YOUR_PAT gh api repos/richcia/azurefn-fleet-3 --jq '.permissions.push'
```

## Automation recommendation

For automation, prefer short-lived credentials where possible:

- **GitHub Actions `GITHUB_TOKEN`** (for workflows in this repository), or
- **GitHub App installation tokens** (for cross-repo/service automation),

instead of long-lived PATs.
