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


def default_config() -> AuditConfig:
    return AuditConfig(
        required_files=DEFAULT_REQUIRED_FILES,
        guidance_terms=DEFAULT_GUIDANCE_TERMS,
        json_files=DEFAULT_JSON_FILES,
        executable_files=DEFAULT_EXECUTABLE_FILES,
        ignored_dirs=DEFAULT_IGNORE_DIRS,
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
    guidance_terms = _guidance_terms(guidance, base.guidance_terms)

    return AuditConfig(
        required_files=required_files,
        guidance_terms=guidance_terms,
        json_files=json_files,
        executable_files=executable_files,
        ignored_dirs=ignored_dirs,
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
