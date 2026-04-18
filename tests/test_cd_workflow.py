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

    assert "Smoke test staging slot by invoking timer function" in content
    assert "az functionapp function list" in content
    assert "/admin/functions/${FUNCTION_NAME}" in content
    assert "-H \"x-functions-key: ${MASTER_KEY}\"" in content
    assert "for attempt in 1 2 3 4 5 6; do" in content

    assert "Swap staging slot to production" in content
    assert "az functionapp deployment slot swap \\" in content
    assert "--slot staging \\" in content
    assert "--target-slot production" in content

    deploy_index = content.index("Deploy zip package to staging slot")
    smoke_index = content.index("Smoke test staging slot by invoking timer function")
    swap_index = content.index("Swap staging slot to production")
    assert deploy_index < smoke_index < swap_index
