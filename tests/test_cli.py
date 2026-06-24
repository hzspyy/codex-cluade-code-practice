from __future__ import annotations

import subprocess
import sys
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
