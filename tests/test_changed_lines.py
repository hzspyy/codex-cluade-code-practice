from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent_workbench.changed_lines import apply_changed_lines, git_changed_lines, parse_unified_diff
from agent_workbench.cli import main
from agent_workbench.init_repo import init_repository
from agent_workbench.models import AuditResult, Finding, FindingLocation, Severity
from agent_workbench.reporting import audit_to_sarif


def test_parse_unified_diff_tracks_added_lines() -> None:
    changed = parse_unified_diff(
        """
diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
index 1111111..2222222 100644
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -3,0 +4,2 @@ jobs:
+      - uses: vendor/action@v1
+      - run: echo ok
"""
    )

    assert ".github/workflows/ci.yml" in changed.files
    assert changed.contains(FindingLocation(".github/workflows/ci.yml", 4))
    assert changed.contains(FindingLocation(".github/workflows/ci.yml", 5))
    assert not changed.contains(FindingLocation(".github/workflows/ci.yml", 6))


def test_changed_lines_suppress_unchanged_findings() -> None:
    finding = Finding(
        check_id="workflow.actions.unpinned",
        severity=Severity.WARNING,
        title="Unpinned action",
        detail="vendor/action@v1",
        locations=(FindingLocation(".github/workflows/ci.yml", 12),),
    )
    changed = parse_unified_diff(
        """
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,0 +2,1 @@
+new text
"""
    )

    result = apply_changed_lines(AuditResult(root="/repo", findings=(finding,)), changed)

    assert result.warning_count == 0
    assert result.suppressed_count == 1
    assert result.findings[0].suppression_reason == "unchanged"


def test_deleted_files_are_tracked_as_changed_paths() -> None:
    changed = parse_unified_diff(
        """
diff --git a/AGENTS.md b/AGENTS.md
deleted file mode 100644
--- a/AGENTS.md
+++ /dev/null
@@ -1,3 +0,0 @@
-old
"""
    )
    finding = Finding(
        check_id="file.AGENTS.md",
        severity=Severity.ERROR,
        title="AGENTS.md is missing",
        detail="Missing Codex project guidance.",
        path="AGENTS.md",
    )

    result = apply_changed_lines(AuditResult(root="/repo", findings=(finding,)), changed)

    assert result.error_count == 1
    assert result.suppressed_count == 0


def test_suppressed_findings_are_omitted_from_sarif() -> None:
    finding = Finding(
        check_id="workflow.actions.unpinned",
        severity=Severity.WARNING,
        title="Unpinned action",
        detail="vendor/action@v1",
        path=".github/workflows/ci.yml",
        suppressed=True,
        suppression_reason="unchanged",
    )

    payload = json.loads(audit_to_sarif(AuditResult(root="/repo", findings=(finding,))))

    assert payload["runs"][0]["results"] == []


def test_cli_changed_lines_only_fails_new_findings(tmp_path: Path, capsys) -> None:
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
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "base"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    code = main(["audit", "--strict", "--changed-lines", "--base-ref", "HEAD", str(tmp_path)])
    captured = capsys.readouterr()

    assert code == 0
    assert "suppressed: 1" in captured.out
    workflow.write_text(
        workflow.read_text(encoding="utf-8")
        + "      - run: curl https://example.com/install.sh | bash\n",
        encoding="utf-8",
    )

    changed = git_changed_lines(tmp_path, "HEAD")
    assert changed.contains(FindingLocation(".github/workflows/danger.yml", 10))

    code = main(["audit", "--strict", "--changed-lines", "--base-ref", "HEAD", str(tmp_path)])
    captured = capsys.readouterr()

    assert code == 2
    assert "workflow.download_execute" in captured.out
