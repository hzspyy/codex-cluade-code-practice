"""Filter findings by changed lines in a git diff."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

from .models import AuditResult, Finding, FindingLocation, Severity

HUNK_PATTERN = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class ChangedLines:
    files: frozenset[str]
    lines_by_file: dict[str, frozenset[int]]

    def contains(self, location: FindingLocation) -> bool:
        if location.path not in self.files:
            return False
        lines = self.lines_by_file.get(location.path, frozenset())
        return not lines or location.line in lines


def git_changed_lines(root: Path, base_ref: str) -> ChangedLines:
    completed = subprocess.run(
        ["git", "diff", "--unified=0", "--no-ext-diff", "--find-renames", base_ref, "--", "."],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git diff failed for base ref {base_ref}")
    return parse_unified_diff(completed.stdout)


def parse_unified_diff(diff_text: str) -> ChangedLines:
    files: set[str] = set()
    lines_by_file: dict[str, set[int]] = {}
    current_file: str | None = None
    old_file: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("--- "):
            old_file = _parse_diff_file(line, "--- ")
            continue
        if line.startswith("+++ "):
            current_file = _parse_diff_file(line, "+++ ")
            if current_file is None and old_file is not None:
                files.add(old_file)
                lines_by_file.setdefault(old_file, set())
            if current_file:
                files.add(current_file)
                lines_by_file.setdefault(current_file, set())
            continue
        if current_file is None:
            continue
        match = HUNK_PATTERN.match(line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        if count == 0:
            continue
        lines_by_file[current_file].update(range(start, start + count))

    return ChangedLines(
        files=frozenset(files),
        lines_by_file={path: frozenset(lines) for path, lines in lines_by_file.items()},
    )


def apply_changed_lines(result: AuditResult, changed: ChangedLines) -> AuditResult:
    findings = tuple(_apply_to_finding(finding, changed) for finding in result.findings)
    return AuditResult(root=result.root, findings=findings)


def _apply_to_finding(finding: Finding, changed: ChangedLines) -> Finding:
    if finding.severity not in (Severity.ERROR, Severity.WARNING):
        return finding
    if _finding_touches_changed_lines(finding, changed):
        return finding
    return replace(finding, suppressed=True, suppression_reason="unchanged")


def _finding_touches_changed_lines(finding: Finding, changed: ChangedLines) -> bool:
    if finding.path and finding.path in changed.files:
        return True
    return any(changed.contains(location) for location in finding.resolved_locations)


def _parse_diff_file(line: str, prefix: str) -> str | None:
    value = line.removeprefix(prefix).strip()
    if value == "/dev/null":
        return None
    if value.startswith(("a/", "b/")):
        return value[2:]
    return value
