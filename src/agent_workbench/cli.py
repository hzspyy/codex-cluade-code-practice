"""Command line interface for agent-workbench."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .audit import audit_repository, detect_git_root
from .init_repo import init_repository
from .reporting import audit_to_json, audit_to_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-workbench",
        description="Audit and bootstrap Codex/Claude Code repository automation.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="audit a repository")
    audit.add_argument("path", nargs="?", default=".", help="repository path")
    audit.add_argument("--json", action="store_true", help="emit JSON")
    audit.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero on warnings as well as errors",
    )

    init = subparsers.add_parser("init", help="create missing automation files")
    init.add_argument("path", nargs="?", default=".", help="repository path")
    init.add_argument("--force", action="store_true", help="overwrite existing template files")
    init.add_argument("--json", action="store_true", help="emit JSON")

    doctor = subparsers.add_parser("doctor", help="check local tool availability")
    doctor.add_argument("--json", action="store_true", help="emit JSON")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "audit":
        root = detect_git_root(Path(args.path))
        result = audit_repository(root)
        print(audit_to_json(result) if args.json else audit_to_text(result))
        if result.error_count:
            return 1
        if args.strict and result.warning_count:
            return 2
        return 0

    if args.command == "init":
        root = Path(args.path).resolve()
        result = init_repository(root, force=args.force)
        if args.json:
            print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        else:
            print(f"agent-workbench init: {result.root}")
            for path in result.created:
                print(f"created: {path}")
            for path in result.skipped:
                print(f"skipped: {path}")
        return 0

    if args.command == "doctor":
        result = _doctor()
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print("agent-workbench doctor")
            for item in result["tools"]:
                status = "ok" if item["available"] else "missing"
                print(f"{status}: {item['name']} {item.get('version', '')}".rstrip())
        return 0 if all(item["available"] for item in result["tools"]) else 1

    parser.error(f"unknown command: {args.command}")
    return 2


def _doctor() -> dict[str, object]:
    tools = []
    for name, version_args in {
        "git": ["--version"],
        "gh": ["--version"],
        "python3": ["--version"],
        "codex": ["--version"],
        "claude": ["--version"],
    }.items():
        path = shutil.which(name)
        item: dict[str, object] = {"name": name, "available": bool(path), "path": path}
        if path:
            completed = subprocess.run(
                [name, *version_args],
                text=True,
                capture_output=True,
                check=False,
            )
            output = (completed.stdout or completed.stderr).splitlines()
            if output:
                item["version"] = output[0]
        tools.append(item)
    return {"tools": tools}


if __name__ == "__main__":
    raise SystemExit(main())
