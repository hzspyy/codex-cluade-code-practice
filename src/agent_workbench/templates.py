"""Template files used by `agent-workbench init`."""

from __future__ import annotations

TEMPLATES: dict[str, str] = {
    "agent-workbench.toml": """[audit]
required_files = [
  "AGENTS.md",
  "CLAUDE.md",
  "LICENSE",
  ".github/pull_request_template.md",
  ".github/workflows/validate.yml"
]
json_files = [".codex/hooks.json", ".claude/settings.json"]
executable_files = ["scripts/validate.sh", ".githooks/pre-commit"]
workflow_files = [".github/workflows/*.yml", "action.yml"]
hook_json_files = [".codex/hooks.json", ".claude/settings.json"]
ignored_dirs = [".git", ".venv", "__pycache__", "node_modules", "dist", "build"]
allowed_unpinned_actions = []
allowed_broad_permission_workflows = []
allowed_write_permission_workflows = []
allowed_ungated_privileged_workflows = []

[guidance]
"AGENTS.md" = ["Review guidelines", "Commands"]
"CLAUDE.md" = ["validate"]
""",
    "LICENSE": """MIT License

Copyright (c) YEAR OWNER

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""",
    "AGENTS.md": """# AGENTS.md

## Repository expectations

- Inspect git state before editing.
- Keep changes small and reviewable.
- Run `./scripts/validate.sh` before opening a pull request.
- Do not commit secrets, private transcripts, or local machine state.

## Commands

- `./scripts/validate.sh` validates this repository's agent automation setup.

## Review guidelines

- Treat committed secrets as P1 issues.
- Treat missing validation for changed automation as P1.
- Focus on concrete behavioral risk over style-only comments.
""",
    "CLAUDE.md": """# CLAUDE.md

Follow the repository expectations in `AGENTS.md`.

- Run `./scripts/validate.sh` before opening a pull request.
- Keep hooks and automation scripts committed, documented, and auditable.
""",
    "scripts/validate.sh": """#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

python3 -m agent_workbench audit --strict .
""",
    ".githooks/pre-commit": """#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

bash scripts/validate.sh
""",
    ".github/pull_request_template.md": """## Summary

-

## Validation

- [ ] `./scripts/validate.sh`
""",
    ".github/workflows/validate.yml": """name: Validate

on:
  pull_request:
  push:
    branches:
      - main
      - "codex/**"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          persist-credentials: false
      - name: Validate repository automation
        run: ./scripts/validate.sh
""",
}
