# CLAUDE.md

This repository is an automation and programming exploration lab for Codex and
Claude Code.

Follow the same repository rules as `AGENTS.md`:

- Inspect git state before editing.
- Keep changes small and reviewable.
- Run `bash scripts/validate.sh` before opening or updating a pull request.
- Do not commit secrets, tokens, local transcripts, or machine-private state.
- Keep hooks and automation scripts committed, documented, and easy to audit.

Claude Code project settings live in `.claude/settings.json`. Project hooks
should call scripts committed under `.claude/hooks/` or `scripts/` rather than
embedding large shell snippets in JSON.
