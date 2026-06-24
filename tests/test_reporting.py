from __future__ import annotations

import json

from agent_workbench.models import AuditResult, Finding, FindingLocation, Severity
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
                locations=(FindingLocation(path="AGENTS.md", line=7),),
            ),
        ),
    )

    payload = json.loads(audit_to_sarif(result))

    assert payload["runs"][0]["results"][0]["ruleId"] == "bad"
    assert payload["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 7
    assert len(payload["runs"][0]["tool"]["driver"]["rules"]) == 1


def test_sarif_emits_multiple_locations() -> None:
    result = AuditResult(
        root="/repo",
        findings=(
            Finding(
                check_id="multi",
                severity=Severity.WARNING,
                title="Multi",
                detail="two lines",
                locations=(
                    FindingLocation(path=".github/workflows/a.yml", line=3),
                    FindingLocation(path=".github/workflows/a.yml", line=9),
                ),
            ),
        ),
    )

    payload = json.loads(audit_to_sarif(result))
    locations = payload["runs"][0]["results"][0]["locations"]

    assert [item["physicalLocation"]["region"]["startLine"] for item in locations] == [3, 9]
