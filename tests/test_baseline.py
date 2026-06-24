from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent_workbench.audit import audit_repository
from agent_workbench.baseline import apply_baseline, load_baseline, write_baseline
from agent_workbench.cli import main
from agent_workbench.config import load_config
from agent_workbench.init_repo import init_repository
from agent_workbench.models import AuditResult, Finding, Severity
from agent_workbench.reporting import audit_to_sarif


def test_write_and_apply_baseline_marks_existing_findings(tmp_path: Path) -> None:
    result = AuditResult(
        root=str(tmp_path),
        findings=(
            Finding(
                check_id="workflow.actions.unpinned",
                severity=Severity.WARNING,
                title="Unpinned action",
                detail="vendor/action@v1",
                path=".github/workflows/ci.yml",
            ),
        ),
    )
    baseline = tmp_path / "agent-workbench-baseline.json"

    write_baseline(result, baseline)
    signatures = load_baseline(baseline)
    baselined = apply_baseline(result, signatures)

    assert baselined.warning_count == 0
    assert baselined.total_warning_count == 1
    assert baselined.baselined_count == 1
    assert baselined.findings[0].baselined


def test_baselined_findings_are_omitted_from_sarif() -> None:
    finding = Finding(
        check_id="workflow.actions.unpinned",
        severity=Severity.WARNING,
        title="Unpinned action",
        detail="vendor/action@v1",
        path=".github/workflows/ci.yml",
        baselined=True,
    )

    payload = json.loads(audit_to_sarif(AuditResult(root="/repo", findings=(finding,))))

    assert payload["runs"][0]["results"] == []
    assert payload["runs"][0]["tool"]["driver"]["rules"] == []


def test_cli_baseline_suppresses_existing_warnings_but_not_new_ones(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    init_repository(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "danger.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(
        """
name: Danger
on:
  push:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: vendor/action@v1
""",
        encoding="utf-8",
    )
    baseline = tmp_path / "agent-workbench-baseline.json"
    write_baseline(audit_repository(tmp_path, load_config(tmp_path)), baseline)

    code = main(["audit", "--strict", "--baseline", str(baseline), str(tmp_path)])

    assert code == 0
    workflow.write_text(
        workflow.read_text(encoding="utf-8")
        + "      - run: curl https://example.com/install.sh | bash\n",
        encoding="utf-8",
    )

    code = main(["audit", "--strict", "--baseline", str(baseline), str(tmp_path)])
    captured = capsys.readouterr()

    assert code == 2
    assert "workflow.download_execute" in captured.out
