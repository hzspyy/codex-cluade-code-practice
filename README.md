# Agent Workbench

Agent Workbench is a small, zero-runtime-dependency CLI for bootstrapping and
auditing repositories that use Codex, Claude Code, GitHub pull requests, and
local hooks as part of an agentic software workflow.

The project started as a practice repository, but its goal is broader: make
agent-enabled repositories easier to review, safer to automate, and less
dependent on undocumented machine-local state.

## Why this exists

Agent coding tools are most useful when their operating rules are visible in
the repo:

- durable guidance in `AGENTS.md` and `CLAUDE.md`
- repeatable validation in scripts and CI
- auditable hooks instead of hidden global shell snippets
- pull request templates that make review expectations explicit
- secret hygiene before automation runs on public branches

Agent Workbench checks for that baseline and can generate starter files for new
repositories.

## Quick start

```bash
python3 -m pip install -e .
agent-workbench doctor
agent-workbench audit .
./scripts/install-git-hooks.sh
./scripts/validate.sh
```

Initialize another repository:

```bash
agent-workbench init /path/to/repo
cd /path/to/repo
./scripts/validate.sh
```

The CLI supports machine-readable output:

```bash
agent-workbench audit --json .
```

## Commands

- `agent-workbench audit [path]`: check for repository guidance, CI, hooks,
  executable validation scripts, parseable JSON config, and common secret
  patterns.
- `agent-workbench init [path]`: create missing starter files for an
  agent-ready repository.
- `agent-workbench doctor`: report whether local tools such as `git`, `gh`,
  `codex`, and `claude` are available.

## Repository workflow

For this repository:

```bash
git switch -c codex/my-change
./scripts/validate.sh
gh pr create --draft --fill
```

## What is included

- `src/agent_workbench/`: the Python CLI package.
- `tests/`: unit tests for audit and init behavior.
- `AGENTS.md` and `CLAUDE.md`: project instructions for Codex and Claude Code.
- `.codex/hooks.json` and `.claude/settings.json`: local lifecycle hook
  examples.
- `.githooks/pre-commit`: committed git pre-commit validation.
- `.github/workflows/validate.yml`: CI validation for pushes and PRs.
- `.github/codex/prompts/review.md`: reusable Codex review prompt.

## Codex review

Codex GitHub automatic reviews are enabled from Codex settings for a repository,
not solely from files in this repo. This repo contains the guidance and prompts
that make those reviews useful once the hosted integration is enabled.

To request a review manually from a PR comment:

```text
@codex review
```

## License

MIT. See `LICENSE`.
