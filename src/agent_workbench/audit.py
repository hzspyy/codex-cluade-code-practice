"""Audit repositories for agent automation readiness."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import AuditConfig, default_config
from .models import AuditResult, Finding, FindingLocation, Severity

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

NETWORK_COMMAND_PATTERN = re.compile(r"\b(curl|wget|nc|ncat|ssh|scp|rsync)\b")
DESTRUCTIVE_COMMAND_PATTERN = re.compile(r"\b(rm\s+-rf|chmod\s+-R\s+777|git\s+reset\s+--hard)\b")
UNPINNED_ACTION_PATTERN = re.compile(r"uses:\s*([^\s#]+)")
DOWNLOAD_EXEC_PATTERN = re.compile(
    r"\b(curl|wget)\b.*(\|\s*(bash|sh|python|ruby)|\b(bash|sh|python|ruby)\b)",
)


@dataclass(frozen=True)
class LineMatch:
    path: str
    line_number: int
    line: str


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
    findings.extend(
        _check_workflow_risks(
            root,
            config.workflow_files,
            config.allowed_unpinned_actions,
            config.allowed_write_permission_workflows,
            config.allowed_broad_permission_workflows,
            config.allowed_ungated_privileged_workflows,
        )
    )
    findings.extend(_check_hook_risks(root, config.hook_json_files))

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


def _check_workflow_risks(
    root: Path,
    workflow_patterns: tuple[str, ...],
    allowed_unpinned_actions: tuple[str, ...],
    allowed_write_permission_workflows: tuple[str, ...],
    allowed_broad_permission_workflows: tuple[str, ...],
    allowed_ungated_privileged_workflows: tuple[str, ...],
) -> list[Finding]:
    findings: list[Finding] = []
    workflow_files = _expand_patterns(root, workflow_patterns)
    if not workflow_files:
        return [
            Finding(
                check_id="workflow.present",
                severity=Severity.INFO,
                title="No workflow files found",
                detail="No GitHub Actions or composite action files matched the configured patterns.",
            )
        ]

    unpinned = []
    broad_permissions = []
    pull_request_writes = []
    pull_request_target = []
    checkout_credentials = []
    download_exec = []
    artifact_boundary = []
    ungated_privileged = []
    for path in workflow_files:
        rel = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        action_refs = _action_references(lines)
        for index, line in enumerate(lines, start=1):
            stripped = line.strip()
            permission_key = stripped.split(":", 1)[0] if ":" in stripped else ""
            if rel not in allowed_broad_permission_workflows:
                if stripped == "permissions: write-all" or stripped == "write-all":
                    broad_permissions.append(LineMatch(rel, index, stripped))
                if re.search(r":\s*write\b", stripped):
                    broad_permissions.append(LineMatch(rel, index, stripped))
            match = UNPINNED_ACTION_PATTERN.search(stripped)
            if (
                match
                and _is_unpinned_third_party_action(match.group(1))
                and match.group(1).split("@", 1)[0] not in allowed_unpinned_actions
            ):
                unpinned.append(LineMatch(rel, index, stripped))
            if DOWNLOAD_EXEC_PATTERN.search(stripped):
                download_exec.append(LineMatch(rel, index, stripped))

        if (
            rel not in allowed_write_permission_workflows
            and _mentions_event(lines, "pull_request")
            and _has_write_permission(lines)
        ):
            pull_request_writes.extend(_event_matches(rel, lines, "pull_request"))
        pull_request_target.extend(_event_matches(rel, lines, "pull_request_target"))
        for match in _checkout_without_persist_false(lines):
            checkout_credentials.append(LineMatch(rel, match.line_number, match.line))
        if "actions/upload-artifact" in action_refs and "actions/download-artifact" in action_refs:
            artifact_boundary.extend(_artifact_action_matches(rel, lines))
        if (
            rel not in allowed_ungated_privileged_workflows
            and _is_privileged_workflow(lines, action_refs)
            and not _has_environment_gate(lines)
        ):
            ungated_privileged.extend(_privileged_workflow_matches(rel, lines, action_refs))

    if unpinned:
        findings.append(
            Finding(
                check_id="workflow.actions.unpinned",
                severity=Severity.WARNING,
                title="Third-party GitHub Actions are not pinned to commit SHAs",
                detail=_format_line_matches(unpinned),
                remediation="Pin third-party actions to a full commit SHA when the workflow handles sensitive code or secrets.",
                locations=_locations_from_matches(unpinned),
            )
        )
    else:
        findings.append(
            Finding(
                check_id="workflow.actions.pinned",
                severity=Severity.OK,
                title="No unpinned third-party action references detected",
                detail="Workflow action references are local, first-party, or pinned to commit-like refs.",
            )
        )

    if broad_permissions:
        findings.append(
            Finding(
                check_id="workflow.permissions.broad",
                severity=Severity.WARNING,
                title="Broad GitHub token permissions detected",
                detail=_format_line_matches(broad_permissions),
                remediation="Prefer least-privilege permissions such as `contents: read` unless writes are required.",
                locations=_locations_from_matches(broad_permissions),
            )
        )
    else:
        findings.append(
            Finding(
                check_id="workflow.permissions.narrow",
                severity=Severity.OK,
                title="No broad GitHub token permissions detected",
                detail="Workflow permission declarations avoid obvious broad write patterns.",
            )
        )

    if pull_request_writes:
        findings.append(
            Finding(
                check_id="workflow.pull_request.write_permissions",
                severity=Severity.WARNING,
                title="Pull request workflows request write permissions",
                detail=_format_line_matches(pull_request_writes),
                remediation="Avoid write permissions on `pull_request` workflows unless the write path is carefully constrained.",
                locations=_locations_from_matches(pull_request_writes),
            )
        )
    else:
        findings.append(
            Finding(
                check_id="workflow.pull_request.permissions",
                severity=Severity.OK,
                title="No pull_request workflow with write permissions detected",
                detail="Pull request workflows do not show obvious write-token permission use.",
            )
        )

    if pull_request_target:
        findings.append(
            Finding(
                check_id="workflow.pull_request_target",
                severity=Severity.WARNING,
                title="pull_request_target workflow detected",
                detail=_format_line_matches(pull_request_target),
                remediation="Use `pull_request_target` only when untrusted PR code is never checked out or executed with privileged tokens.",
                locations=_locations_from_matches(pull_request_target),
            )
        )
    else:
        findings.append(
            Finding(
                check_id="workflow.pull_request_target.absent",
                severity=Severity.OK,
                title="No pull_request_target workflows detected",
                detail="No workflow uses the privileged pull_request_target event.",
            )
        )

    if checkout_credentials:
        findings.append(
            Finding(
                check_id="workflow.checkout.persist_credentials",
                severity=Severity.WARNING,
                title="actions/checkout does not disable persisted credentials",
                detail=_format_line_matches(checkout_credentials),
                remediation="Set `persist-credentials: false` when later steps run untrusted code or do not need git push credentials.",
                locations=_locations_from_matches(checkout_credentials),
            )
        )
    else:
        findings.append(
            Finding(
                check_id="workflow.checkout.credentials",
                severity=Severity.OK,
                title="No risky actions/checkout credential persistence detected",
                detail="Checkout steps either avoid obvious risk contexts or set `persist-credentials: false`.",
            )
        )

    if download_exec:
        findings.append(
            Finding(
                check_id="workflow.download_execute",
                severity=Severity.WARNING,
                title="Workflow downloads and executes code in one shell step",
                detail=_format_line_matches(download_exec),
                remediation="Download, verify integrity, and execute in separate reviewed steps; avoid `curl | bash` patterns.",
                locations=_locations_from_matches(download_exec),
            )
        )
    else:
        findings.append(
            Finding(
                check_id="workflow.download_execute.absent",
                severity=Severity.OK,
                title="No download-and-execute shell pattern detected",
                detail="Workflow run steps avoid obvious curl/wget execution chains.",
            )
        )

    if artifact_boundary:
        findings.append(
            Finding(
                check_id="workflow.artifact.boundary",
                severity=Severity.WARNING,
                title="Workflow both uploads and downloads artifacts",
                detail=_format_line_matches(artifact_boundary),
                remediation="Treat downloaded artifacts as untrusted unless producer and consumer jobs are constrained and verified.",
                locations=_locations_from_matches(artifact_boundary),
            )
        )
    else:
        findings.append(
            Finding(
                check_id="workflow.artifact.boundary",
                severity=Severity.OK,
                title="No same-workflow upload/download artifact boundary detected",
                detail="No workflow combines upload-artifact and download-artifact actions.",
            )
        )

    if ungated_privileged:
        findings.append(
            Finding(
                check_id="workflow.privileged.environment",
                severity=Severity.WARNING,
                title="Privileged workflow has no environment gate",
                detail=_format_line_matches(ungated_privileged),
                remediation="Add a GitHub Environment to privileged jobs and configure required reviewers or deployment protections.",
                locations=_locations_from_matches(ungated_privileged),
            )
        )
    else:
        findings.append(
            Finding(
                check_id="workflow.privileged.environment",
                severity=Severity.OK,
                title="Privileged workflows declare environment gates or are absent",
                detail="Workflows with obvious publish/write privileges reference a GitHub Environment or no privileged workflow was detected.",
            )
        )

    return findings


def _check_hook_risks(root: Path, hook_json_files: tuple[str, ...]) -> list[Finding]:
    risky: list[LineMatch] = []
    for rel in hook_json_files:
        path = root / rel
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for command in _walk_commands(payload):
            if NETWORK_COMMAND_PATTERN.search(command) or DESTRUCTIVE_COMMAND_PATTERN.search(command):
                risky.append(LineMatch(rel, 1, command))

    if risky:
        return [
            Finding(
                check_id="hooks.commands.risky",
                severity=Severity.WARNING,
                title="Hook commands contain network or destructive shell patterns",
                detail=_format_line_matches(risky),
                remediation="Keep lifecycle hooks deterministic and local; move network or destructive behavior behind explicit user review.",
                locations=_locations_from_matches(risky),
            )
        ]

    return [
        Finding(
            check_id="hooks.commands.local",
            severity=Severity.OK,
            title="No risky hook command patterns detected",
            detail="Configured hook commands avoid common network and destructive shell patterns.",
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


def _expand_patterns(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file() and path not in seen:
                paths.append(path)
                seen.add(path)
    return sorted(paths)


def _is_unpinned_third_party_action(reference: str) -> bool:
    if reference.startswith("./") or reference.startswith("../"):
        return False
    if "@" not in reference:
        return True
    name, ref = reference.rsplit("@", 1)
    if name.startswith("actions/") or name.startswith("github/"):
        return False
    return not re.fullmatch(r"[a-fA-F0-9]{40}", ref)


def _action_references(lines: list[str]) -> set[str]:
    refs: set[str] = set()
    for line in lines:
        match = UNPINNED_ACTION_PATTERN.search(line.strip())
        if match:
            refs.add(match.group(1).split("@", 1)[0])
    return refs


def _event_matches(path: str, lines: list[str], event: str) -> list[LineMatch]:
    matches: list[LineMatch] = []
    event_pattern = re.compile(rf"(^|\s|-\s*){re.escape(event)}\s*:")
    bracket_pattern = re.compile(rf"\[[^\]]*\b{re.escape(event)}\b[^\]]*\]")
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if event_pattern.search(line) or bracket_pattern.search(line):
            matches.append(LineMatch(path, index, stripped))
    return matches


def _artifact_action_matches(path: str, lines: list[str]) -> list[LineMatch]:
    matches: list[LineMatch] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        match = UNPINNED_ACTION_PATTERN.search(stripped)
        if not match:
            continue
        action = match.group(1).split("@", 1)[0]
        if action in {"actions/upload-artifact", "actions/download-artifact"}:
            matches.append(LineMatch(path, index, stripped))
    return matches


def _checkout_without_persist_false(lines: list[str]) -> list[LineMatch]:
    matches: list[LineMatch] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        match = UNPINNED_ACTION_PATTERN.search(stripped)
        if not match or match.group(1).split("@", 1)[0] != "actions/checkout":
            continue
        window = "\n".join(lines[index : min(len(lines), index + 8)])
        if "persist-credentials: false" not in window:
            matches.append(LineMatch("", index, stripped))
    return matches


def _mentions_event(lines: list[str], event: str) -> bool:
    event_pattern = re.compile(rf"(^|\s|-\s*){re.escape(event)}\s*:")
    bracket_pattern = re.compile(rf"\[[^\]]*\b{re.escape(event)}\b[^\]]*\]")
    return any(event_pattern.search(line) or bracket_pattern.search(line) for line in lines)


def _has_write_permission(lines: list[str]) -> bool:
    for line in lines:
        stripped = line.strip()
        if stripped == "permissions: write-all" or stripped == "write-all":
            return True
        if re.search(r":\s*write\b", stripped):
            return True
    return False


def _has_environment_gate(lines: list[str]) -> bool:
    return any(line.strip().startswith("environment:") for line in lines)


def _is_privileged_workflow(lines: list[str], action_refs: set[str]) -> bool:
    return (
        _has_write_permission(lines)
        or _mentions_event(lines, "pull_request_target")
        or "softprops/action-gh-release" in action_refs
        or _has_release_command(lines)
    )


def _has_release_command(lines: list[str]) -> bool:
    return any("gh release" in line or "npm publish" in line or "twine upload" in line for line in lines)


def _privileged_workflow_matches(path: str, lines: list[str], action_refs: set[str]) -> list[LineMatch]:
    matches: list[LineMatch] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "permissions: write-all" or stripped == "write-all" or re.search(r":\s*write\b", stripped):
            matches.append(LineMatch(path, index, stripped))
        if "pull_request_target" in stripped:
            matches.append(LineMatch(path, index, stripped))
        if "gh release" in stripped or "npm publish" in stripped or "twine upload" in stripped:
            matches.append(LineMatch(path, index, stripped))
        match = UNPINNED_ACTION_PATTERN.search(stripped)
        if match and match.group(1).split("@", 1)[0] == "softprops/action-gh-release":
            matches.append(LineMatch(path, index, stripped))
    if not matches and action_refs:
        matches.append(LineMatch(path, 1, "privileged workflow"))
    return matches


def _walk_commands(value: object) -> list[str]:
    commands: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key == "command" and isinstance(nested, str):
                commands.append(nested)
            else:
                commands.extend(_walk_commands(nested))
    elif isinstance(value, list):
        for item in value:
            commands.extend(_walk_commands(item))
    return commands


def _format_line_matches(matches: list[LineMatch]) -> str:
    return "; ".join(f"{match.path}:{match.line_number}: {match.line}" for match in matches)


def _locations_from_matches(matches: list[LineMatch]) -> tuple[FindingLocation, ...]:
    return tuple(FindingLocation(path=match.path, line=match.line_number) for match in matches)


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
