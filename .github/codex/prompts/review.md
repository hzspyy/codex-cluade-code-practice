# Codex Pull Request Review

Review this pull request for serious issues only.

Focus on:

- automation that can run unexpectedly or mutate files without clear intent
- secret exposure, token-like strings, or private transcript leakage
- disagreement between `AGENTS.md`, `CLAUDE.md`, hooks, CI, and scripts
- missing validation for changed automation
- PR changes that make agent behavior harder to audit

Ignore purely stylistic comments unless they create a concrete maintenance risk.
