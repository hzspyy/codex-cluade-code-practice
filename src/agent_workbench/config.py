"""Configuration loading for agent-workbench."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AuditConfig:
    required_files: tuple[str, ...]
    guidance_terms: dict[str, tuple[str, ...]]
    json_files: tuple[str, ...]
    executable_files: tuple[str, ...]
    ignored_dirs: tuple[str, ...]
    workflow_files: tuple[str, ...]
    hook_json_files: tuple[str, ...]
    allowed_unpinned_actions: tuple[str, ...]
    allowed_write_permission_workflows: tuple[str, ...]
    allowed_broad_permission_workflows: tuple[str, ...]
    allowed_ungated_privileged_workflows: tuple[str, ...]
    severity_overrides: dict[str, str]


DEFAULT_REQUIRED_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "LICENSE",
    ".github/pull_request_template.md",
    ".github/workflows/validate.yml",
)

DEFAULT_GUIDANCE_TERMS = {
    "AGENTS.md": ("Review guidelines", "Commands"),
    "CLAUDE.md": ("validate",),
}

DEFAULT_JSON_FILES = (
    ".codex/hooks.json",
    ".claude/settings.json",
)

DEFAULT_EXECUTABLE_FILES = (
    "scripts/validate.sh",
    ".githooks/pre-commit",
)

DEFAULT_IGNORE_DIRS = (
    ".git",
    ".agent-state",
    ".codex-log",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
)

DEFAULT_WORKFLOW_FILES = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    "action.yml",
    "action.yaml",
)

DEFAULT_HOOK_JSON_FILES = (
    ".codex/hooks.json",
    ".claude/settings.json",
)

DEFAULT_ALLOWED_UNPINNED_ACTIONS: tuple[str, ...] = ()
DEFAULT_ALLOWED_WRITE_PERMISSION_WORKFLOWS: tuple[str, ...] = ()
DEFAULT_ALLOWED_BROAD_PERMISSION_WORKFLOWS: tuple[str, ...] = ()
DEFAULT_ALLOWED_UNGATED_PRIVILEGED_WORKFLOWS: tuple[str, ...] = ()
DEFAULT_SEVERITY_OVERRIDES: dict[str, str] = {}


def default_config() -> AuditConfig:
    return AuditConfig(
        required_files=DEFAULT_REQUIRED_FILES,
        guidance_terms=DEFAULT_GUIDANCE_TERMS,
        json_files=DEFAULT_JSON_FILES,
        executable_files=DEFAULT_EXECUTABLE_FILES,
        ignored_dirs=DEFAULT_IGNORE_DIRS,
        workflow_files=DEFAULT_WORKFLOW_FILES,
        hook_json_files=DEFAULT_HOOK_JSON_FILES,
        allowed_unpinned_actions=DEFAULT_ALLOWED_UNPINNED_ACTIONS,
        allowed_write_permission_workflows=DEFAULT_ALLOWED_WRITE_PERMISSION_WORKFLOWS,
        allowed_broad_permission_workflows=DEFAULT_ALLOWED_BROAD_PERMISSION_WORKFLOWS,
        allowed_ungated_privileged_workflows=DEFAULT_ALLOWED_UNGATED_PRIVILEGED_WORKFLOWS,
        severity_overrides=DEFAULT_SEVERITY_OVERRIDES,
    )


def load_config(root: Path, config_path: Path | None = None) -> AuditConfig:
    base = default_config()
    target = config_path or root / "agent-workbench.toml"
    if not target.exists():
        return base

    data = tomllib.loads(target.read_text(encoding="utf-8"))
    audit = data.get("audit", {})
    guidance = data.get("guidance", {})

    required_files = _string_tuple(audit.get("required_files"), base.required_files)
    json_files = _string_tuple(audit.get("json_files"), base.json_files)
    executable_files = _string_tuple(audit.get("executable_files"), base.executable_files)
    ignored_dirs = _string_tuple(audit.get("ignored_dirs"), base.ignored_dirs)
    workflow_files = _string_tuple(audit.get("workflow_files"), base.workflow_files)
    hook_json_files = _string_tuple(audit.get("hook_json_files"), base.hook_json_files)
    allowed_unpinned_actions = _string_tuple(
        audit.get("allowed_unpinned_actions"),
        base.allowed_unpinned_actions,
    )
    allowed_write_permission_workflows = _string_tuple(
        audit.get("allowed_write_permission_workflows"),
        base.allowed_write_permission_workflows,
    )
    allowed_broad_permission_workflows = _string_tuple(
        audit.get("allowed_broad_permission_workflows"),
        base.allowed_broad_permission_workflows,
    )
    allowed_ungated_privileged_workflows = _string_tuple(
        audit.get("allowed_ungated_privileged_workflows"),
        base.allowed_ungated_privileged_workflows,
    )
    guidance_terms = _guidance_terms(guidance, base.guidance_terms)
    severity_overrides = _severity_overrides(audit.get("severity_overrides"), base.severity_overrides)

    return AuditConfig(
        required_files=required_files,
        guidance_terms=guidance_terms,
        json_files=json_files,
        executable_files=executable_files,
        ignored_dirs=ignored_dirs,
        workflow_files=workflow_files,
        hook_json_files=hook_json_files,
        allowed_unpinned_actions=allowed_unpinned_actions,
        allowed_write_permission_workflows=allowed_write_permission_workflows,
        allowed_broad_permission_workflows=allowed_broad_permission_workflows,
        allowed_ungated_privileged_workflows=allowed_ungated_privileged_workflows,
        severity_overrides=severity_overrides,
    )


def _string_tuple(value: object, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("configuration values must be arrays of strings")
    return tuple(value)


def _guidance_terms(value: object, default: dict[str, tuple[str, ...]]) -> dict[str, tuple[str, ...]]:
    if value is None:
        return default
    if not isinstance(value, dict):
        raise ValueError("guidance configuration must be a table")

    merged = dict(default)
    for path, terms in value.items():
        if not isinstance(path, str):
            raise ValueError("guidance file names must be strings")
        if not isinstance(terms, list) or not all(isinstance(term, str) for term in terms):
            raise ValueError("guidance terms must be arrays of strings")
        merged[path] = tuple(terms)
    return merged


def _severity_overrides(value: object, default: dict[str, str]) -> dict[str, str]:
    if value is None:
        return default
    if not isinstance(value, dict):
        raise ValueError("severity_overrides must be a table")
    allowed = {"ok", "info", "warning", "error"}
    overrides: dict[str, str] = {}
    for check_id, severity in value.items():
        if not isinstance(check_id, str):
            raise ValueError("severity override check IDs must be strings")
        if not isinstance(severity, str) or severity not in allowed:
            raise ValueError("severity override values must be one of: ok, info, warning, error")
        overrides[check_id] = severity
    return overrides
