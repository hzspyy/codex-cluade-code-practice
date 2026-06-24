# Changelog

## v0.3.0

- Added structured finding locations for JSON, text, Markdown, and SARIF output.
- Added deterministic finding signatures and `--write-baseline` / `--baseline`
  support for gradual adoption in repositories with existing findings.
- Added `--changed-lines` / `--base-ref` so pull request workflows can fail only
  on warnings or errors that touch the current diff.
- Added GitHub Action inputs for `baseline`, `changed-lines`, and `base-ref`.
- Expanded automation risk checks for supply-chain-sensitive workflow patterns.

## v0.2.0

- Added automation risk checks for GitHub Actions permissions, unpinned actions,
  privileged PR events, checkout credential persistence, download-and-execute
  shell patterns, artifact trust boundaries, and risky agent hooks.
- Added released-action smoke testing.

## v0.1.0

- Bootstrapped `agent-workbench` as a Python CLI and composite GitHub Action.
- Added repository initialization templates, audit output formats, CI validation,
  git hooks, and Codex/Claude Code guidance files.
