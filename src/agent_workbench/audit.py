"""Audit repositories for agent automation readiness."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from pathlib import Path

from .config import AuditConfig, default_config
from .models import AuditResult, Finding, Severity

REQUIRED_FILE_PURPOSES = {
    "AGENTS.md": "Codex project guidance",
    "CLAUDE.md": "Claude Code project guidance",
    "LICENSE": "open source license",
    ".github/pull_request_template.md": "pull request checklist",
    ".github/workflows/validate.yml": "CI validation workflow",
}

SECRET_PATTERNS = (
    re.compile(r"\bgh[opsu]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:OPENAI|ANTHROPIC|GITHUB|CODEX)_API_KEY\s*=\s*['\"]?[A-Za-z0-9_./+=-]{12,}"),
)


def audit_repository(root: Path, config: AuditConfig | None = None) -> AuditResult:
    root = root.resolve()
    config = config or default_config()
    findings: list[Finding] = []

    findings.extend(_check_git(root))
    findings.extend(_check_required_files(root, config.required_files))
    findings.extend(_check_guidance(root, config.guidance_terms))
    findings.extend(_check_json_configs(root, config.json_files))
    findings.extend(_check_scripts(root, config.executable_files))
    findings.extend(_check_secret_patterns(root, config.ignored_dirs))

    if not any(f.severity == Severity.ERROR for f in findings):
        findings.append(
            Finding(
                check_id="summary.ready",
                severity=Severity.OK,
                title="Repository passes required agent automation checks",
                detail="No blocking errors were found.",
            )
        )

    return AuditResult(root=str(root), findings=tuple(findings))


def _check_git(root: Path) -> list[Finding]:
    git_dir = root / ".git"
    if git_dir.exists():
        return [
            Finding(
                check_id="git.present",
                severity=Severity.OK,
                title="Git repository detected",
                detail="The repository can support branch, PR, and review workflows.",
            )
        ]
    return [
        Finding(
            check_id="git.present",
            severity=Severity.ERROR,
            title="Git repository not detected",
            detail="Agent review panes and PR automation need a git repository.",
            remediation="Run `git init` before using agent-workbench in this directory.",
        )
    ]


def _check_required_files(root: Path, required_files: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    for path in required_files:
        purpose = REQUIRED_FILE_PURPOSES.get(path, "required project file")
        target = root / path
        if target.exists():
            findings.append(
                Finding(
                    check_id=f"file.{path}",
                    severity=Severity.OK,
                    title=f"{path} exists",
                    detail=f"Found {purpose}.",
                    path=path,
                )
            )
        else:
            findings.append(
                Finding(
                    check_id=f"file.{path}",
                    severity=Severity.ERROR,
                    title=f"{path} is missing",
                    detail=f"Missing {purpose}.",
                    path=path,
                    remediation=f"Create {path} or run `agent-workbench init`.",
                )
            )
    return findings


def _check_guidance(root: Path, guidance_checks: dict[str, tuple[str, ...]]) -> list[Finding]:
    findings: list[Finding] = []
    for path, required_terms in guidance_checks.items():
        target = root / path
        if not target.exists():
            continue
        text = target.read_text(encoding="utf-8")
        for term in required_terms:
            if term.lower() in text.lower():
                findings.append(
                    Finding(
                        check_id=f"guidance.{path}.{term}",
                        severity=Severity.OK,
                        title=f"{path} mentions {term}",
                        detail="The guidance includes a durable instruction for this workflow.",
                        path=path,
                    )
                )
            else:
                findings.append(
                    Finding(
                        check_id=f"guidance.{path}.{term}",
                        severity=Severity.WARNING,
                        title=f"{path} does not mention {term}",
                        detail="The file exists but may not guide agents strongly enough.",
                        path=path,
                        remediation=f"Add a concise {term} section to {path}.",
                    )
                )
    return findings


def _check_json_configs(root: Path, json_files: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    for path in json_files:
        target = root / path
        if not target.exists():
            findings.append(
                Finding(
                    check_id=f"json.{path}",
                    severity=Severity.INFO,
                    title=f"{path} is not configured",
                    detail="This is optional, but committed hooks make agent automation easier to audit.",
                    path=path,
                )
            )
            continue
        try:
            json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            findings.append(
                Finding(
                    check_id=f"json.{path}",
                    severity=Severity.ERROR,
                    title=f"{path} is invalid JSON",
                    detail=str(exc),
                    path=path,
                    remediation="Fix the JSON syntax.",
                )
            )
        else:
            findings.append(
                Finding(
                    check_id=f"json.{path}",
                    severity=Severity.OK,
                    title=f"{path} is valid JSON",
                    detail="Configuration can be parsed.",
                    path=path,
                )
            )
    return findings


def _check_scripts(root: Path, executable_files: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    for path in executable_files:
        target = root / path
        if not target.exists():
            findings.append(
                Finding(
                    check_id=f"script.{path}",
                    severity=Severity.WARNING,
                    title=f"{path} is missing",
                    detail="Local validation is harder to run consistently without it.",
                    path=path,
                    remediation=f"Add {path} or run `agent-workbench init`.",
                )
            )
            continue
        mode = target.stat().st_mode
        if mode & stat.S_IXUSR:
            findings.append(
                Finding(
                    check_id=f"script.{path}.executable",
                    severity=Severity.OK,
                    title=f"{path} is executable",
                    detail="The script can be run directly.",
                    path=path,
                )
            )
        else:
            findings.append(
                Finding(
                    check_id=f"script.{path}.executable",
                    severity=Severity.ERROR,
                    title=f"{path} is not executable",
                    detail="Hooks and docs expect this script to be executable.",
                    path=path,
                    remediation=f"Run `chmod +x {path}`.",
                )
            )
    return findings


def _check_secret_patterns(root: Path, ignored_dirs: tuple[str, ...]) -> list[Finding]:
    matches: list[str] = []
    for path in _iter_text_files(root, ignored_dirs):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                matches.append(rel)
                break

    if matches:
        return [
            Finding(
                check_id="secret.patterns",
                severity=Severity.ERROR,
                title="Possible secret material found",
                detail=", ".join(sorted(matches)),
                remediation="Remove secrets from git-tracked files and rotate any exposed credentials.",
            )
        ]

    return [
        Finding(
            check_id="secret.patterns",
            severity=Severity.OK,
            title="No common secret patterns found",
            detail="Scanned text files for common token shapes.",
        )
    ]


def _iter_text_files(root: Path, ignored_dirs: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    ignored = set(ignored_dirs)
    for current_root, dirs, filenames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ignored]
        for filename in filenames:
            path = Path(current_root) / filename
            if path.is_file() and path.stat().st_size <= 1_000_000:
                files.append(path)
    return files


def detect_git_root(path: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return path.resolve()
