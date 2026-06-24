# AGENTS.md

This repository is a small lab for exploring Codex, Claude Code, and agentic
software automation. Treat the repo itself as an automation artifact: keep the
instructions, hooks, prompts, and verification scripts reviewable in git.

## Working agreements

- Start by reading this file, then inspect the current git state before editing.
- Prefer small, reviewable changes on `codex/*` branches.
- Use `rg`/`rg --files` for repository search.
- Keep generated automation deterministic where possible; avoid hidden global
  state unless a setup step documents it.
- Do not commit secrets, access tokens, session dumps, or private transcripts.
- When adding an agent workflow, include the command that verifies it.
- When behavior depends on a hosted product setting, document the setting and
  keep a local fallback that still works in this repository.

## Commands

- `./scripts/validate.sh` checks repository structure, shell scripts, markdown
  basics, and agent configuration JSON.
- `./scripts/install-git-hooks.sh` enables the committed git hooks by setting
  `core.hooksPath=.githooks`.
- `git diff --check` catches whitespace errors before commit.

Run `./scripts/validate.sh` before opening or updating a pull request.

## Automation surfaces

- `AGENTS.md` is the durable Codex project guidance. Nested `AGENTS.md` files
  may add narrower rules for future subdirectories.
- `CLAUDE.md` mirrors the high-level repo guidance for Claude Code.
- `.codex/hooks.json` wires Codex lifecycle hooks to scripts under
  `.codex/hooks/`. Project-local Codex hooks must be reviewed and trusted in
  Codex before they run.
- `.claude/settings.json` wires Claude Code hooks to scripts under
  `.claude/hooks/`.
- `.githooks/pre-commit` runs the local validation script for ordinary git
  commits.
- `.github/workflows/validate.yml` runs the same validation in GitHub Actions.
- `.github/codex/prompts/review.md` is the prompt for optional Codex Action
  review workflows or manual `codex exec` review runs.

## Review guidelines

- Treat missing validation for changed automation as a P1 issue.
- Treat committed secrets, token-looking strings, or private transcript content
  as a P1 issue.
- Treat hooks that execute network commands, mutate files unexpectedly, or rely
  on global machine state without documentation as a P1 issue.
- Prefer findings about concrete behavioral risk over style-only comments.
- Check whether `AGENTS.md`, `CLAUDE.md`, hooks, CI, and scripts still agree
  when one of them changes.

## Pull request checklist

- The branch name describes the automation change.
- `./scripts/validate.sh` passes locally.
- The PR body explains what changed, why, and how it was checked.
- If Codex GitHub code review is enabled for the repository, request it with
  `@codex review` or rely on the repository's automatic review setting.
