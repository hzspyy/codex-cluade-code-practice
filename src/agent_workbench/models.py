"""Data structures used by agent-workbench."""

from __future__ import annotations

import hashlib
import json
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
    baselined: bool = False
    suppressed: bool = False
    suppression_reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "severity": self.severity.value,
            "title": self.title,
            "detail": self.detail,
            "path": self.path,
            "remediation": self.remediation,
            "locations": [location.as_dict() for location in self.resolved_locations],
            "signature": self.signature,
            "fingerprint": self.fingerprint,
            "baselined": self.baselined,
            "suppressed": self.suppressed,
            "suppression_reason": self.suppression_reason,
        }

    @property
    def resolved_locations(self) -> tuple[FindingLocation, ...]:
        if self.locations:
            return self.locations
        if self.path:
            return (FindingLocation(path=self.path),)
        return ()

    @property
    def signature(self) -> str:
        payload = {
            "check_id": self.check_id,
            "severity": self.severity.value,
            "title": self.title,
            "path": self.path,
            "locations": [location.as_dict() for location in self.resolved_locations],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @property
    def fingerprint(self) -> str:
        payload = {
            "check_id": self.check_id,
            "title": self.title,
            "path": self.path,
            "locations": [location.as_dict() for location in self.resolved_locations],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class AuditResult:
    root: str
    findings: tuple[Finding, ...]

    @property
    def error_count(self) -> int:
        return sum(
            1
            for finding in self.findings
            if finding.severity == Severity.ERROR and not finding.baselined and not finding.suppressed
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1
            for finding in self.findings
            if finding.severity == Severity.WARNING and not finding.baselined and not finding.suppressed
        )

    @property
    def total_error_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == Severity.ERROR)

    @property
    def total_warning_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == Severity.WARNING)

    @property
    def baselined_count(self) -> int:
        return sum(1 for finding in self.findings if finding.baselined)

    @property
    def suppressed_count(self) -> int:
        return sum(1 for finding in self.findings if finding.suppressed)

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def as_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "total_error_count": self.total_error_count,
            "total_warning_count": self.total_warning_count,
            "baselined_count": self.baselined_count,
            "suppressed_count": self.suppressed_count,
            "findings": [finding.as_dict() for finding in self.findings],
        }
