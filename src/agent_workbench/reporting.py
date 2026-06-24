"""Render audit and init results."""

from __future__ import annotations

import json

from .models import AuditResult, Finding, FindingLocation, Severity


def audit_to_json(result: AuditResult) -> str:
    return json.dumps(result.as_dict(), indent=2, sort_keys=True)


def audit_to_text(result: AuditResult) -> str:
    lines = [
        f"agent-workbench audit: {result.root}",
        f"status: {'pass' if result.passed else 'fail'}",
        f"errors: {result.error_count}, warnings: {result.warning_count}",
        f"baselined: {result.baselined_count}",
        f"suppressed: {result.suppressed_count}",
        "",
    ]
    for finding in result.findings:
        marker = _marker(finding.severity)
        location = f" [{_display_location(finding)}]" if _display_location(finding) else ""
        baseline = " (baseline)" if finding.baselined else ""
        suppression = f" ({finding.suppression_reason})" if finding.suppressed else ""
        lines.append(f"{marker} {finding.check_id}{location}{baseline}{suppression}: {finding.title}")
        lines.append(f"  {finding.detail}")
        if finding.remediation:
            lines.append(f"  fix: {finding.remediation}")
    return "\n".join(lines)


def audit_to_markdown(result: AuditResult) -> str:
    lines = [
        "# Agent Workbench Audit",
        "",
        f"- Root: `{result.root}`",
        f"- Status: `{'pass' if result.passed else 'fail'}`",
        f"- Errors: `{result.error_count}`",
        f"- Warnings: `{result.warning_count}`",
        f"- Baselined: `{result.baselined_count}`",
        f"- Suppressed: `{result.suppressed_count}`",
        "",
        "| Severity | Check | Path | Baseline | Suppression | Finding |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for finding in result.findings:
        location = _display_location(finding)
        path = f"`{location}`" if location else ""
        detail = finding.detail.replace("|", "\\|")
        remediation = f"<br>Fix: {finding.remediation}" if finding.remediation else ""
        baseline = "yes" if finding.baselined else ""
        suppression = finding.suppression_reason or ""
        lines.append(
            f"| `{finding.severity.value}` | `{finding.check_id}` | {path} | {baseline} | "
            f"{suppression} | "
            f"{finding.title}<br>{detail}{remediation} |"
        )
    return "\n".join(lines)


def audit_to_sarif(result: AuditResult) -> str:
    rules = {}
    sarif_results = []
    for finding in result.findings:
        if finding.severity in (Severity.OK, Severity.INFO) or finding.baselined or finding.suppressed:
            continue
        rules[finding.check_id] = {
            "id": finding.check_id,
            "name": finding.title,
            "shortDescription": {"text": finding.title},
            "fullDescription": {"text": finding.detail},
            "help": {"text": finding.remediation or finding.detail},
        }
        sarif_result = {
            "ruleId": finding.check_id,
            "level": "error" if finding.severity == Severity.ERROR else "warning",
            "message": {"text": finding.detail},
        }
        locations = _finding_locations(finding)
        if locations:
            sarif_result["locations"] = [_sarif_location(location) for location in locations]
        sarif_results.append(sarif_result)

    payload = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "agent-workbench",
                        "informationUri": "https://github.com/hzspyy/codex-cluade-code-practice",
                        "rules": list(rules.values()),
                    }
                },
                "results": sarif_results,
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def render_audit(result: AuditResult, output_format: str) -> str:
    if output_format == "text":
        return audit_to_text(result)
    if output_format == "json":
        return audit_to_json(result)
    if output_format == "markdown":
        return audit_to_markdown(result)
    if output_format == "sarif":
        return audit_to_sarif(result)
    raise ValueError(f"unsupported output format: {output_format}")


def _marker(severity: Severity) -> str:
    return {
        Severity.OK: "OK",
        Severity.INFO: "INFO",
        Severity.WARNING: "WARN",
        Severity.ERROR: "ERR",
    }[severity]


def _finding_locations(finding: Finding) -> tuple[FindingLocation, ...]:
    if finding.locations:
        return finding.locations
    if finding.path:
        return (FindingLocation(path=finding.path),)
    return ()


def _display_location(finding: Finding) -> str:
    locations = _finding_locations(finding)
    if not locations:
        return ""
    if len(locations) == 1:
        location = locations[0]
        return f"{location.path}:{location.line}"
    return f"{locations[0].path}:{locations[0].line} (+{len(locations) - 1} more)"


def _sarif_location(location: FindingLocation) -> dict[str, object]:
    return {
        "physicalLocation": {
            "artifactLocation": {"uri": location.path},
            "region": {"startLine": location.line},
        }
    }
