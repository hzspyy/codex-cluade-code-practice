"""Compact audit summaries for PR comments and dashboards."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .models import AuditResult, Finding, FindingLocation, Severity


def summary_payload(result: AuditResult) -> dict[str, object]:
    actionable = [
        finding
        for finding in result.findings
        if finding.severity in (Severity.ERROR, Severity.WARNING)
        and not finding.baselined
        and not finding.suppressed
    ]
    severity_counts = Counter(finding.severity.value for finding in result.findings)
    check_counts = Counter(finding.check_id for finding in actionable)
    return {
        "root": result.root,
        "passed": result.passed,
        "error_count": result.error_count,
        "warning_count": result.warning_count,
        "total_error_count": result.total_error_count,
        "total_warning_count": result.total_warning_count,
        "baselined_count": result.baselined_count,
        "suppressed_count": result.suppressed_count,
        "severity_counts": dict(sorted(severity_counts.items())),
        "actionable_by_check": dict(sorted(check_counts.items())),
        "top_findings": [_finding_summary(finding) for finding in actionable[:10]],
    }


def summary_to_json(result: AuditResult) -> str:
    return json.dumps(summary_payload(result), indent=2, sort_keys=True)


def summary_to_markdown(result: AuditResult) -> str:
    payload = summary_payload(result)
    lines = [
        "## Agent Workbench Summary",
        "",
        f"- Status: `{'pass' if payload['passed'] else 'fail'}`",
        f"- Actionable errors: `{payload['error_count']}`",
        f"- Actionable warnings: `{payload['warning_count']}`",
        f"- Baselined: `{payload['baselined_count']}`",
        f"- Suppressed: `{payload['suppressed_count']}`",
        "",
    ]
    actionable = payload["top_findings"]
    if actionable:
        lines.extend(
            [
                "| Severity | Check | Location | Finding |",
                "| --- | --- | --- | --- |",
            ]
        )
        for finding in actionable:
            lines.append(
                f"| `{finding['severity']}` | `{finding['check_id']}` | "
                f"{_markdown_code(str(finding['location']))} | {finding['title']} |"
            )
    else:
        lines.append("No actionable errors or warnings.")
    return "\n".join(lines)


def load_audit_json(path: Path) -> AuditResult:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("audit JSON must be an object")
    findings = tuple(_finding_from_payload(item) for item in _required_list(payload, "findings"))
    return AuditResult(root=str(payload.get("root", "")), findings=findings)


def _finding_from_payload(payload: object) -> Finding:
    if not isinstance(payload, dict):
        raise ValueError("finding must be an object")
    severity = Severity(str(payload["severity"]))
    return Finding(
        check_id=str(payload["check_id"]),
        severity=severity,
        title=str(payload["title"]),
        detail=str(payload["detail"]),
        path=str(payload["path"]) if payload.get("path") is not None else None,
        remediation=str(payload["remediation"]) if payload.get("remediation") is not None else None,
        locations=_locations_from_payload(payload.get("locations", [])),
        baselined=bool(payload.get("baselined", False)),
        suppressed=bool(payload.get("suppressed", False)),
        suppression_reason=(
            str(payload["suppression_reason"]) if payload.get("suppression_reason") is not None else None
        ),
    )


def _required_list(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"audit JSON missing list field: {key}")
    return value


def _locations_from_payload(value: object) -> tuple[FindingLocation, ...]:
    if not isinstance(value, list):
        raise ValueError("finding locations must be an array")
    locations = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("finding location must be an object")
        locations.append(FindingLocation(path=str(item["path"]), line=int(item.get("line", 1))))
    return tuple(locations)


def _finding_summary(finding: Finding) -> dict[str, object]:
    location = ""
    if finding.resolved_locations:
        first = finding.resolved_locations[0]
        location = f"{first.path}:{first.line}"
    return {
        "check_id": finding.check_id,
        "severity": finding.severity.value,
        "title": finding.title,
        "location": location,
    }


def _markdown_code(value: str) -> str:
    return f"`{value}`" if value else ""
