#!/usr/bin/env python3
"""Claude Code stop hook that mirrors the Codex validation hint."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=False)


def main() -> int:
    root = run(["git", "rev-parse", "--show-toplevel"])
    if root.returncode != 0:
        return 0

    repo = Path(root.stdout.strip())
    status = run(["git", "status", "--porcelain"])
    if status.returncode != 0 or not status.stdout.strip():
        return 0

    marker = repo / ".agent-state" / "validated"
    if marker.exists():
        return 0

    print(
        "claude hook: working tree has changes. Run ./scripts/validate.sh before PR.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
