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
bash scripts/validate.sh
```

Initialize another repository:

```bash
agent-workbench init /path/to/repo
cd /path/to/repo
bash scripts/validate.sh
```

The CLI supports machine-readable output:

```bash
agent-workbench audit --json .
agent-workbench audit --format markdown -o audit.md .
agent-workbench audit --format sarif -o agent-workbench.sarif .
```

JSON and SARIF reports include structured file/line locations for findings that
come from workflow or hook scans, so CI systems can annotate the risky lines
instead of only showing a summary.

For an existing repository, create a committed baseline so CI blocks new
automation risk without demanding a cleanup of every historical warning first:

```bash
agent-workbench audit --write-baseline agent-workbench-baseline.json .
git add agent-workbench-baseline.json
agent-workbench audit --strict --baseline agent-workbench-baseline.json .
```

## Commands

- `agent-workbench audit [path]`: check for repository guidance, CI, hooks,
  executable validation scripts, parseable JSON config, and common secret
  patterns. It also checks for high-risk automation patterns such as broad
  GitHub token permissions, write permissions on pull request workflows,
  `pull_request_target`, credential-persisting checkout steps, unpinned
  third-party actions, download-and-execute shell chains, artifact trust
  boundaries, and risky lifecycle hook commands. Supports `text`, `json`,
  `markdown`, and `sarif` output. Use `--write-baseline` to record current
  warnings and errors, then `--baseline` to keep those accepted findings from
  failing future runs.
- `agent-workbench init [path]`: create missing starter files for an
  agent-ready repository.
- `agent-workbench doctor`: report whether local tools such as `git`, `gh`,
  `codex`, and `claude` are available.

## Configuration

Put `agent-workbench.toml` in a repository root to tune the audit policy:

```toml
[audit]
required_files = ["AGENTS.md", "CLAUDE.md", "LICENSE"]
json_files = [".codex/hooks.json", ".claude/settings.json"]
executable_files = ["scripts/validate.sh", ".githooks/pre-commit"]
ignored_dirs = [".git", ".venv", "__pycache__", "node_modules"]
workflow_files = [".github/workflows/*.yml", "action.yml"]
hook_json_files = [".codex/hooks.json", ".claude/settings.json"]
allowed_unpinned_actions = []
allowed_broad_permission_workflows = []

[guidance]
"AGENTS.md" = ["Review guidelines", "Commands"]
"CLAUDE.md" = ["validate"]
```

Use `--config path/to/file.toml` when the config is not in the repository root.

Allowlist entries should be rare and documented in review. For example, a
release workflow may need `contents: write`, but a pull request workflow usually
should not.

## Repository workflow

For this repository:

```bash
git switch -c codex/my-change
bash scripts/validate.sh
gh pr create --draft --fill
```

## GitHub Action

Use this repository as a composite action:

```yaml
- uses: actions/checkout@v5
- uses: hzspyy/codex-cluade-code-practice@main
  with:
    format: sarif
    output: agent-workbench.sarif
    baseline: agent-workbench-baseline.json
```

See `docs/github-action.md` for a complete workflow, including SARIF upload to
GitHub code scanning.

This repository dogfoods the local action in `.github/workflows/action-self-test.yml`
and the released tag in `.github/workflows/tag-action-smoke.yml`.

## What is included

- `src/agent_workbench/`: the Python CLI package.
- `action.yml`: reusable composite GitHub Action.
- `examples/`: sample config, workflow, output, and a minimal fixture repo.
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

## Releasing

Release artifacts are built from version tags:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

The release workflow builds a source distribution and wheel, uploads them as
artifacts, and creates a GitHub release for tag pushes.
