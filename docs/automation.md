# Automation Notes

## Codex

Codex reads repository guidance from `AGENTS.md`. Keep durable repository rules,
verification commands, and review guidance there.

Project-local Codex hooks are configured in `.codex/hooks.json`. Codex requires
local hooks to be reviewed and trusted before they run. Use `/hooks` in Codex to
inspect and trust changed hooks.

Codex GitHub code review is a hosted repository setting. After Codex cloud and
code review are enabled for the GitHub repository, request a review with:

```text
@codex review
```

Automatic reviews can be enabled in Codex code review settings for the
repository.

## Claude Code

Claude Code reads project guidance from `CLAUDE.md`. Project settings and hooks
live under `.claude/`.

Use `/hooks` in Claude Code to inspect configured hooks. Project settings are
committed in `.claude/settings.json`; local machine-only settings should stay in
`.claude/settings.local.json` and should not be committed.

## Git

Enable committed git hooks with:

```bash
./scripts/install-git-hooks.sh
```

The pre-commit hook runs `./scripts/validate.sh`.
