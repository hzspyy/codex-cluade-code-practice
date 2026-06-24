"""Data structures used by agent-workbench."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    OK = "ok"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class FindingLocation:
    path: str
    line: int = 1

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
        }


@dataclass(frozen=True)
class Finding:
    check_id: str
    severity: Severity
    title: str
    detail: str
    path: str | None = None
    remediation: str | None = None
    locations: tuple[FindingLocation, ...] = ()

    def as_dict(self) -> dict[str, object]:
        locations = self.locations
        if not locations and self.path:
            locations = (FindingLocation(path=self.path),)
        return {
            "check_id": self.check_id,
            "severity": self.severity.value,
            "title": self.title,
            "detail": self.detail,
            "path": self.path,
            "remediation": self.remediation,
            "locations": [location.as_dict() for location in locations],
        }


@dataclass(frozen=True)
class AuditResult:
    root: str
    findings: tuple[Finding, ...]

    @property
    def error_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == Severity.WARNING)

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def as_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "findings": [finding.as_dict() for finding in self.findings],
        }
