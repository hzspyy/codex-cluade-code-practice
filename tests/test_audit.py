from __future__ import annotations

import stat
import subprocess
from pathlib import Path

from agent_workbench.audit import audit_repository
from agent_workbench.config import load_config
from agent_workbench.init_repo import init_repository
from agent_workbench.models import Severity


def test_init_then_audit_passes(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)

    result = init_repository(tmp_path)

    assert "AGENTS.md" in result.created
    audit = audit_repository(tmp_path)
    errors = [finding for finding in audit.findings if finding.severity == Severity.ERROR]
    assert errors == []
    assert (tmp_path / "agent-workbench.toml").exists()


def test_invalid_json_is_error(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    init_repository(tmp_path)
    (tmp_path / ".codex").mkdir(exist_ok=True)
    (tmp_path / ".codex" / "hooks.json").write_text("{not json", encoding="utf-8")

    audit = audit_repository(tmp_path)

    assert any(finding.check_id == "json..codex/hooks.json" for finding in audit.findings)
    assert audit.error_count >= 1


def test_secret_pattern_is_error(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    init_repository(tmp_path)
    fake_secret = "OPENAI_API_KEY=" + "sk-" + "thisLooksLikeARealSecretValue"
    (tmp_path / "leak.txt").write_text(fake_secret, encoding="utf-8")

    audit = audit_repository(tmp_path)

    assert any(finding.check_id == "secret.patterns" and finding.severity == Severity.ERROR for finding in audit.findings)


def test_init_makes_scripts_executable(tmp_path: Path) -> None:
    init_repository(tmp_path)

    for rel in ("scripts/validate.sh", ".githooks/pre-commit"):
        mode = (tmp_path / rel).stat().st_mode
        assert mode & stat.S_IXUSR


def test_config_can_require_custom_guidance(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    init_repository(tmp_path)
    (tmp_path / "agent-workbench.toml").write_text(
        """
[audit]
required_files = ["AGENTS.md"]
json_files = []
executable_files = []
ignored_dirs = [".git"]

[guidance]
"AGENTS.md" = ["nonexistent project phrase"]
""",
        encoding="utf-8",
    )

    config = load_config(tmp_path)
    audit = audit_repository(tmp_path, config)

    assert audit.error_count == 0
    assert any(finding.severity == Severity.WARNING for finding in audit.findings)
