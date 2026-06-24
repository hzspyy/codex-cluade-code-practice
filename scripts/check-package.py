#!/usr/bin/env python3
"""Check package metadata without requiring external build tools."""

from __future__ import annotations

import configparser
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> int:
    print(f"check-package: {message}", file=sys.stderr)
    return 1


def main() -> int:
    pyproject = ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project", {})

    required = {
        "name": "agent-workbench",
        "version": None,
        "description": None,
        "readme": "README.md",
        "requires-python": ">=3.11",
    }
    for key, expected in required.items():
        value = project.get(key)
        if not value:
            return fail(f"missing project.{key}")
        if expected is not None and value != expected:
            return fail(f"project.{key} expected {expected!r}, got {value!r}")

    scripts = project.get("scripts", {})
    if scripts.get("agent-workbench") != "agent_workbench.cli:main":
        return fail("missing agent-workbench console script")

    license_file = project.get("license", {}).get("file")
    if license_file != "LICENSE" or not (ROOT / license_file).exists():
        return fail("license file is not configured correctly")

    for path in ("README.md", "src/agent_workbench/cli.py", "src/agent_workbench/__main__.py"):
        if not (ROOT / path).exists():
            return fail(f"missing package file: {path}")

    action = ROOT / "action.yml"
    for line_number, line in enumerate(action.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("description: ") and stripped.count(":") > 1:
            value = stripped.removeprefix("description: ").strip()
            if not (value.startswith('"') or value.startswith("'")):
                return fail(f"quote action.yml description with colon on line {line_number}")

    print("check-package: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
