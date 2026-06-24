# Codex and Claude Code Practice

This repository is a hands-on lab for agentic coding workflows: durable
instructions, local hooks, git hygiene, pull requests, and review loops.

## Quick start

```bash
./scripts/install-git-hooks.sh
./scripts/validate.sh
```

Work on feature branches:

```bash
git switch -c codex/my-change
```

Open pull requests with:

```bash
gh pr create --draft --fill
```

If Codex GitHub code review is enabled for this repository, request a review
from a PR comment:

```text
@codex review
```

## What is included

- `AGENTS.md`: Codex project instructions and review guidelines.
- `CLAUDE.md`: Claude Code project instructions.
- `.codex/hooks.json`: Codex lifecycle hook configuration.
- `.claude/settings.json`: Claude Code project hook configuration.
- `.githooks/pre-commit`: git pre-commit validation.
- `.github/workflows/validate.yml`: CI validation for pushes and PRs.
- `.github/codex/prompts/review.md`: reusable Codex review prompt.

## Notes

Codex GitHub automatic reviews are enabled from Codex settings for a repository,
not solely from files in this repo. This repo contains the guidance and prompts
that make those reviews useful once the hosted integration is enabled.
