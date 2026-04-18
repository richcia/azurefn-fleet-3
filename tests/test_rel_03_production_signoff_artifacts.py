from pathlib import Path


def test_rel_03_signoff_checklist_contains_acceptance_criteria():
    checklist = (
        Path(__file__).resolve().parents[1]
        / "results"
        / "REL-03-production-signoff-checklist.md"
    ).read_text(encoding="utf-8")

    assert "Production Deployment and Monitoring Activation Sign-off" in checklist
    assert "Production slot swap completed via GitHub Actions pipeline" in checklist
    assert "First nightly execution at 2:00 AM UTC writes blob successfully" in checklist
    assert "All three alert rules active in production Application Insights" in checklist
    assert "Failure alert test (deliberate exception) fires within 5 minutes in production" in checklist
    assert "All spec success criteria checked off and documented in release notes" in checklist
    assert "verify blob by 2:15 AM UTC" in checklist


def test_rel_03_evidence_template_contains_required_fields():
    evidence = (
        Path(__file__).resolve().parents[1]
        / "results"
        / "REL-03-production-signoff-evidence.json"
    ).read_text(encoding="utf-8")

    assert '"production_slot_swap_completed"' in evidence
    assert '"slot_swap_workflow_run_url"' in evidence
    assert '"first_nightly_execution"' in evidence
    assert '"production_alert_rules_active"' in evidence
    assert '"deliberate_failure_alert_minutes"' in evidence
    assert '"release_notes_path"' in evidence
    assert '"spec_success_criteria_checked"' in evidence


def test_rel_03_release_notes_template_contains_spec_success_criteria():
    release_notes = (
        Path(__file__).resolve().parents[1]
        / "results"
        / "REL-03-release-notes.md"
    ).read_text(encoding="utf-8")

    assert "Spec Success Criteria Checklist" in release_notes
    assert "All functional requirements implemented" in release_notes
    assert "All acceptance criteria met (including known player assertions: Mattingly, Winfield, Henderson)" in release_notes
    assert "Code review completed and approved" in release_notes
    assert "Unit tests cover prompt validation, response schema parsing, and blob write logic" in release_notes
    assert "Integration test verifies known players appear in blob output" in release_notes
    assert "Deployed to production via GitHub Actions with staging slot swap" in release_notes
    assert "Monitoring and alerting active (failure alert + duration alert + data quality metric)" in release_notes
    assert "Documentation complete (README includes local dev setup, TRAPI auth instructions, and blob naming convention)" in release_notes
