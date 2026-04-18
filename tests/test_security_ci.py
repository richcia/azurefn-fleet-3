from pathlib import Path
import subprocess


def test_local_settings_json_is_gitignored():
    gitignore_path = Path(__file__).resolve().parents[1] / ".gitignore"
    entries = {line.strip() for line in gitignore_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    assert "local.settings.json" in entries


def test_local_settings_json_is_not_tracked():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "local.settings.json"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert result.returncode != 0


def test_ci_workflow_runs_full_history_secret_scan():
    ci_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ci_workflow = ci_path.read_text(encoding="utf-8")
    secret_scan_block = ci_workflow.split("  secret-scan:")[1].split("  test:")[0]

    assert "name: Secret scan (gitleaks)" in secret_scan_block
    assert "fetch-depth: 0" in secret_scan_block
    assert "gitleaks git --no-banner --redact --exit-code 1 ." in secret_scan_block
    assert "continue-on-error: true" not in secret_scan_block
    assert "needs: secret-scan" in ci_workflow
