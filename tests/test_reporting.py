from __future__ import annotations

import json

from agent_workbench.models import AuditResult, Finding, Severity
from agent_workbench.reporting import audit_to_markdown, audit_to_sarif


def test_markdown_report_escapes_table_pipes() -> None:
    result = AuditResult(
        root="/repo",
        findings=(
            Finding(
                check_id="demo",
                severity=Severity.WARNING,
                title="Title",
                detail="contains | pipe",
                path="AGENTS.md",
            ),
        ),
    )

    report = audit_to_markdown(result)

    assert "contains \\| pipe" in report


def test_sarif_omits_passing_findings() -> None:
    result = AuditResult(
        root="/repo",
        findings=(
            Finding(check_id="ok", severity=Severity.OK, title="OK", detail="fine"),
            Finding(
                check_id="bad",
                severity=Severity.ERROR,
                title="Bad",
                detail="broken",
                path="AGENTS.md",
            ),
        ),
    )

    payload = json.loads(audit_to_sarif(result))

    assert payload["runs"][0]["results"][0]["ruleId"] == "bad"
    assert len(payload["runs"][0]["tool"]["driver"]["rules"]) == 1
