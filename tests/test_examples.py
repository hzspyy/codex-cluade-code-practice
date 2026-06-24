from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from agent_workbench.audit import audit_repository
from agent_workbench.config import load_config
from agent_workbench.init_repo import init_repository


def test_minimal_example_can_be_bootstrapped(tmp_path: Path) -> None:
    source = Path("examples/minimal-agent-repo")
    target = tmp_path / "minimal-agent-repo"
    shutil.copytree(source, target)
    subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)

    init_repository(target)
    result = audit_repository(target, load_config(target))

    assert result.passed
    assert result.error_count == 0
