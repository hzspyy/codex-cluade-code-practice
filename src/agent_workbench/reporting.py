"""Render audit and init results."""

from __future__ import annotations

import json

from .models import AuditResult, Severity


def audit_to_json(result: AuditResult) -> str:
    return json.dumps(result.as_dict(), indent=2, sort_keys=True)


def audit_to_text(result: AuditResult) -> str:
    lines = [
        f"agent-workbench audit: {result.root}",
        f"status: {'pass' if result.passed else 'fail'}",
        f"errors: {result.error_count}, warnings: {result.warning_count}",
        "",
    ]
    for finding in result.findings:
        marker = _marker(finding.severity)
        location = f" [{finding.path}]" if finding.path else ""
        lines.append(f"{marker} {finding.check_id}{location}: {finding.title}")
        lines.append(f"  {finding.detail}")
        if finding.remediation:
            lines.append(f"  fix: {finding.remediation}")
    return "\n".join(lines)


def _marker(severity: Severity) -> str:
    return {
        Severity.OK: "OK",
        Severity.INFO: "INFO",
        Severity.WARNING: "WARN",
        Severity.ERROR: "ERR",
    }[severity]
