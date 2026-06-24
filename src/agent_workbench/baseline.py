"""Baseline support for gradual audit adoption."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from .models import AuditResult, Finding, Severity

BASELINE_VERSION = 1


def load_baseline(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("baseline must be a JSON object")
    if payload.get("version") != BASELINE_VERSION:
        raise ValueError(f"unsupported baseline version: {payload.get('version')}")
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise ValueError("baseline findings must be an array")

    identities: set[str] = set()
    for item in findings:
        if not isinstance(item, dict):
            raise ValueError("baseline entries must be objects")
        fingerprint = item.get("fingerprint")
        signature = item.get("signature")
        if isinstance(fingerprint, str):
            identities.add(fingerprint)
        elif isinstance(signature, str):
            identities.add(signature)
        else:
            raise ValueError("baseline entries must include a string fingerprint or signature")
    return identities


def apply_baseline(result: AuditResult, identities: set[str]) -> AuditResult:
    findings = tuple(_apply_to_finding(finding, identities) for finding in result.findings)
    return AuditResult(root=result.root, findings=findings)


def baseline_payload(result: AuditResult) -> dict[str, object]:
    findings = [
        {
            "signature": finding.signature,
            "fingerprint": finding.fingerprint,
            "check_id": finding.check_id,
            "severity": finding.severity.value,
            "title": finding.title,
            "locations": [location.as_dict() for location in finding.resolved_locations],
        }
        for finding in result.findings
        if finding.severity in (Severity.ERROR, Severity.WARNING)
    ]
    return {
        "version": BASELINE_VERSION,
        "findings": sorted(findings, key=lambda item: str(item["signature"])),
    }


def write_baseline(result: AuditResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = baseline_payload(result)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _apply_to_finding(finding: Finding, identities: set[str]) -> Finding:
    if finding.severity not in (Severity.ERROR, Severity.WARNING):
        return finding
    if finding.fingerprint not in identities and finding.signature not in identities:
        return finding
    return replace(finding, baselined=True)
