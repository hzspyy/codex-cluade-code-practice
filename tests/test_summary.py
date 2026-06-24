from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent_workbench.cli import main
from agent_workbench.models import AuditResult, Finding, FindingLocation, Severity
from agent_workbench.summary import load_audit_json, summary_payload, summary_to_markdown


def test_summary_payload_counts_only_actionable_findings() -> None:
    result = AuditResult(
        root="/repo",
        findings=(
            Finding(
                check_id="error",
                severity=Severity.ERROR,
                title="Error",
                detail="broken",
                locations=(FindingLocation("a.yml", 3),),
            ),
            Finding(
                check_id="old",
                severity=Severity.WARNING,
                title="Old",
                detail="accepted",
                baselined=True,
            ),
            Finding(
                check_id="unchanged",
                severity=Severity.WARNING,
                title="Unchanged",
                detail="not in diff",
                suppressed=True,
                suppression_reason="unchanged",
            ),
        ),
    )

    payload = summary_payload(result)

    assert payload["error_count"] == 1
    assert payload["warning_count"] == 0
    assert payload["total_warning_count"] == 2
    assert payload["baselined_count"] == 1
    assert payload["suppressed_count"] == 1
    assert payload["actionable_by_check"] == {"error": 1}


def test_summary_markdown_lists_actionable_findings() -> None:
    result = AuditResult(
        root="/repo",
        findings=(
            Finding(
                check_id="workflow.download_execute",
                severity=Severity.WARNING,
                title="Workflow downloads and executes code",
                detail="curl | bash",
                locations=(FindingLocation(".github/workflows/ci.yml", 12),),
            ),
        ),
    )

    report = summary_to_markdown(result)

    assert "Agent Workbench Summary" in report
    assert "`workflow.download_execute`" in report
    assert "`.github/workflows/ci.yml:12`" in report


def test_load_audit_json_preserves_locations(tmp_path: Path) -> None:
    report = tmp_path / "audit.json"
    report.write_text(
        json.dumps(
            {
                "root": "/repo",
                "findings": [
                    {
                        "check_id": "demo",
                        "severity": "warning",
                        "title": "Demo",
                        "detail": "detail",
                        "path": None,
                        "remediation": None,
                        "locations": [{"path": "file.yml", "line": 9}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = load_audit_json(report)

    assert result.findings[0].resolved_locations[0].path == "file.yml"
    assert result.findings[0].resolved_locations[0].line == 9


def test_cli_summary_from_json(tmp_path: Path, capsys) -> None:
    report = tmp_path / "audit.json"
    report.write_text(
        json.dumps(
            {
                "root": "/repo",
                "findings": [
                    {
                        "check_id": "demo",
                        "severity": "warning",
                        "title": "Demo",
                        "detail": "detail",
                        "path": "file.yml",
                        "remediation": None,
                        "locations": [{"path": "file.yml", "line": 1}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    code = main(["summary", "--from-json", str(report), "--format", "json"])
    captured = capsys.readouterr()

    assert code == 0
    assert '"warning_count": 1' in captured.out
    assert '"demo": 1' in captured.out


def test_cli_summary_runs_audit(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)

    code = main(["summary", str(tmp_path)])
    captured = capsys.readouterr()

    assert code == 1
    assert "Agent Workbench Summary" in captured.out
    assert "Actionable errors" in captured.out
