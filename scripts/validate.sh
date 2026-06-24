#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

PYTHON_BIN="${AGENT_WORKBENCH_PYTHON:-python3}"
if [[ -x .venv/bin/python && "${AGENT_WORKBENCH_PYTHON:-}" == "" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

fail() {
  printf 'validate: %s\n' "$*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "missing required file: $1"
}

step() {
  printf 'validate: %s\n' "$*" >&2
}

step "checking required files"
require_file AGENTS.md
require_file CLAUDE.md
require_file README.md
require_file agent-workbench.toml
require_file action.yml
require_file .codex/hooks.json
require_file .claude/settings.json
require_file .githooks/pre-commit
require_file .github/workflows/validate.yml
require_file .github/workflows/action-self-test.yml
require_file .github/workflows/release.yml
require_file .github/workflows/tag-action-smoke.yml
require_file .github/codex/prompts/review.md

step "checking git diff whitespace"
git diff --check

step "checking JSON and shell syntax"
"$PYTHON_BIN" -m json.tool .codex/hooks.json >/dev/null
"$PYTHON_BIN" -m json.tool .claude/settings.json >/dev/null

bash -n scripts/validate.sh
bash -n scripts/install-git-hooks.sh
bash -n .githooks/pre-commit

step "checking package metadata"
"$PYTHON_BIN" scripts/check-package.py

step "compiling Python files"
"$PYTHON_BIN" -m compileall -q src tests

step "checking executable scripts"
while IFS= read -r script; do
  [[ -x "$script" ]] || fail "script is not executable: $script"
done < <(find scripts .githooks -type f | sort)

step "scanning for common secret patterns"
if rg -n --hidden \
  --glob '!.git/**' \
  --glob '!.venv/**' \
  --glob '!AGENTS.md' \
  --glob '!scripts/validate.sh' \
  --glob '!tests/**' \
  'OPENAI_API_KEY=|ANTHROPIC_API_KEY=|gho_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{20,}' .; then
  fail "possible secret found"
fi

step "running agent-workbench audit"
PYTHONPATH=src "$PYTHON_BIN" -m agent_workbench audit --strict .

if "$PYTHON_BIN" - <<'PY'
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("pytest") else 1)
PY
then
  step "running pytest"
  PYTHONPATH=src "$PYTHON_BIN" -m pytest -q
else
  printf 'validate: pytest not installed; skipped unit tests\n' >&2
fi

mkdir -p .agent-state
date -u '+%Y-%m-%dT%H:%M:%SZ' > .agent-state/validated

printf 'validate: ok\n'
