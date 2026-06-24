"""Command line interface for agent-workbench."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from . import __version__
from .audit import audit_repository, detect_git_root
from .baseline import apply_baseline, load_baseline, write_baseline
from .changed_lines import apply_changed_lines, git_changed_lines
from .config import load_config
from .init_repo import init_repository
from .reporting import render_audit
from .summary import load_audit_json, summary_to_json, summary_to_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-workbench",
        description="Audit and bootstrap Codex/Claude Code repository automation.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="audit a repository")
    audit.add_argument("path", nargs="?", default=".", help="repository path")
    audit.add_argument(
        "--format",
        choices=("text", "json", "markdown", "sarif"),
        default="text",
        help="output format",
    )
    audit.add_argument("--json", action="store_true", help="emit JSON; shorthand for --format json")
    audit.add_argument("--config", help="path to agent-workbench.toml")
    audit.add_argument("--output", "-o", help="write the report to a file")
    audit.add_argument(
        "--baseline",
        help="path to a committed baseline JSON file; matching findings do not fail the audit",
    )
    audit.add_argument(
        "--write-baseline",
        help="write current warning/error signatures to a baseline JSON file and exit successfully",
    )
    audit.add_argument(
        "--changed-lines",
        action="store_true",
        help="only fail findings that touch lines changed from --base-ref",
    )
    audit.add_argument(
        "--base-ref",
        default="origin/main",
        help="git ref used by --changed-lines; default: origin/main",
    )
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

    summary = subparsers.add_parser("summary", help="summarize audit findings")
    summary.add_argument("path", nargs="?", default=".", help="repository path")
    summary.add_argument(
        "--from-json",
        help="read a saved agent-workbench audit JSON report instead of running an audit",
    )
    summary.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="summary output format",
    )
    summary.add_argument("--config", help="path to agent-workbench.toml")
    summary.add_argument("--output", "-o", help="write the summary to a file")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "audit":
        root = detect_git_root(Path(args.path))
        config = load_config(root, Path(args.config).resolve() if args.config else None)
        result = audit_repository(root, config)
        if args.write_baseline:
            write_baseline(result, Path(args.write_baseline))
        if args.baseline:
            result = apply_baseline(result, load_baseline(Path(args.baseline)))
        if args.changed_lines:
            result = apply_changed_lines(result, git_changed_lines(root, args.base_ref))
        output_format = "json" if args.json else args.format
        rendered = render_audit(result, output_format)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        if args.write_baseline:
            return 0
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

    if args.command == "summary":
        if args.from_json:
            result = load_audit_json(Path(args.from_json))
        else:
            root = detect_git_root(Path(args.path))
            config = load_config(root, Path(args.config).resolve() if args.config else None)
            result = audit_repository(root, config)
        rendered = summary_to_json(result) if args.format == "json" else summary_to_markdown(result)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        return 0 if result.passed else 1

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
