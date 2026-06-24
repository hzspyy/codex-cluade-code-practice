from __future__ import annotations

import subprocess
from pathlib import Path

from agent_workbench.cli import main


def test_cli_init_json(tmp_path: Path, capsys) -> None:
    code = main(["init", "--json", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 0
    assert '"created"' in captured.out
    assert (tmp_path / "AGENTS.md").exists()


def test_cli_audit_fails_without_git(tmp_path: Path, capsys) -> None:
    main(["init", str(tmp_path)])

    code = main(["audit", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 1
    assert "Git repository not detected" in captured.out


def test_cli_audit_json_passes_after_git_init(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    main(["init", str(tmp_path)])

    code = main(["audit", "--json", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 0
    assert '"passed": true' in captured.out


def test_cli_writes_markdown_report(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    main(["init", str(tmp_path)])
    output = tmp_path / "audit.md"

    code = main(["audit", "--format", "markdown", "--output", str(output), str(tmp_path)])

    assert code == 0
    assert output.read_text(encoding="utf-8").startswith("# Agent Workbench Audit")


def test_cli_sarif_contains_warning_result(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    main(["init", str(tmp_path)])
    (tmp_path / "AGENTS.md").write_text("# AGENTS.md\n", encoding="utf-8")

    code = main(["audit", "--format", "sarif", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 0
    assert '"version": "2.1.0"' in captured.out
    assert '"ruleId": "guidance.AGENTS.md.Commands"' in captured.out
