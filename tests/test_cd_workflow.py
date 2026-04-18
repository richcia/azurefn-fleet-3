from pathlib import Path


def test_cd_workflow_implements_test_deploy_smoke_swap_with_oidc():
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "cd.yml"
    content = workflow_path.read_text(encoding="utf-8")

    assert "push:" in content and "- main" in content
    assert "id-token: write" in content
    assert "uses: azure/login@v2" in content
    assert "client-id: ${{ secrets.AZURE_CLIENT_ID }}" in content
    assert "tenant-id: ${{ secrets.AZURE_TENANT_ID }}" in content
    assert "subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}" in content

    assert "python -m pytest tests/ -v" in content

    assert "Deploy zip package to staging slot" in content
    assert "slot-name: staging" in content

    assert "Smoke test staging slot endpoint" in content
    assert 'STAGING_URL="https://${{ secrets.AZURE_FUNCTIONAPP_NAME }}-staging.azurewebsites.net"' in content

    assert "Swap staging slot to production" in content
    assert "az functionapp deployment slot swap \\" in content
    assert "--slot staging \\" in content
    assert "--target-slot production" in content
