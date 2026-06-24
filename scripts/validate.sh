#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

fail() {
  printf 'validate: %s\n' "$*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "missing required file: $1"
}

require_file AGENTS.md
require_file CLAUDE.md
require_file README.md
require_file .codex/hooks.json
require_file .claude/settings.json
require_file .githooks/pre-commit
require_file .github/workflows/validate.yml
require_file .github/codex/prompts/review.md

git diff --check

python3 -m json.tool .codex/hooks.json >/dev/null
python3 -m json.tool .claude/settings.json >/dev/null

bash -n scripts/validate.sh
bash -n scripts/install-git-hooks.sh
bash -n .githooks/pre-commit

while IFS= read -r script; do
  [[ -x "$script" ]] || fail "script is not executable: $script"
done < <(find scripts .githooks -type f | sort)

if rg -n --hidden --glob '!.git/**' --glob '!AGENTS.md' --glob '!scripts/validate.sh' \
  'OPENAI_API_KEY=|ANTHROPIC_API_KEY=|gho_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{20,}' .; then
  fail "possible secret found"
fi

mkdir -p .agent-state
date -u '+%Y-%m-%dT%H:%M:%SZ' > .agent-state/validated

printf 'validate: ok\n'
