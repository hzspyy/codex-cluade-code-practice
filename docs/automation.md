# Automation Notes

Agent Workbench is both a tool and a reference implementation for keeping
agentic coding automation visible in git.

## CLI

Install in editable mode while developing:

```bash
python3 -m pip install -e .
```

Useful commands:

```bash
agent-workbench doctor
agent-workbench audit .
agent-workbench audit --json .
agent-workbench audit --format markdown -o audit.md .
agent-workbench audit --format sarif -o agent-workbench.sarif .
agent-workbench audit --write-baseline agent-workbench-baseline.json .
agent-workbench audit --strict --baseline agent-workbench-baseline.json .
agent-workbench audit --strict --changed-lines --base-ref origin/main .
agent-workbench summary --from-json agent-workbench-audit.json -o summary.md
agent-workbench init /path/to/another/repo
```

`audit` returns non-zero when blocking errors are found. `--strict` also returns
non-zero for warnings.

Use `--write-baseline` when adopting Agent Workbench in a repository that
already has known warnings or errors. Commit the generated JSON file, then pass
it with `--baseline`; matching findings remain visible in text, Markdown, and
JSON output but do not affect the exit code. SARIF output omits baselined
findings so code-scanning annotations stay focused on new risk.

Use `--changed-lines` in pull request workflows when you want the same gradual
adoption behavior without maintaining a baseline file. The audit still scans
the whole repository, but warnings and errors outside the `git diff` from
`--base-ref` are marked as `unchanged` and do not affect the exit code. SARIF
omits those unchanged findings so code scanning annotates only the lines touched
by the branch.

The SARIF output can be uploaded to GitHub code scanning. Keep it focused on
warnings and errors so public PR feedback remains actionable.

Findings include structured locations where the scanner can identify a concrete
file and line. SARIF consumers can use those locations for inline annotations.

Use `summary` when you want a compact artifact for PR comments, release notes,
or agent handoffs. It can run an audit directly, or read a saved JSON audit with
`--from-json` and emit Markdown or JSON.

## Risk rules

Agent Workbench now checks for several automation risks:

- third-party GitHub Actions referenced by tags or branches instead of full
  commit SHAs
- broad GitHub token permissions such as `write-all` or `contents: write`
- `pull_request` workflows that request write permissions
- privileged `pull_request_target` workflows
- checkout steps that do not set `persist-credentials: false`
- shell steps that download and immediately execute code
- workflows that both upload and download artifacts, which can blur artifact
  trust boundaries
- privileged workflows that publish releases, request write permissions, or use
  `pull_request_target` without a GitHub Environment gate
- Codex or Claude lifecycle hook commands containing common network or
  destructive shell patterns

Some workflows legitimately need write access. Configure those exceptions in
`agent-workbench.toml`:

```toml
[audit]
allowed_broad_permission_workflows = [".github/workflows/release.yml"]
allowed_unpinned_actions = ["owner/action-name"]
allowed_ungated_privileged_workflows = []
```

Prefer fixing the workflow over allowlisting. When allowlisting is necessary,
keep the entry narrow and explain it in the pull request.

For release or deployment workflows, prefer adding `environment: release` or a
similarly named environment to the privileged job, then configure protection
rules such as required reviewers in GitHub repository settings.

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

The pre-commit hook runs `bash scripts/validate.sh`.

## Reusable action

This repository includes `action.yml`, so another repository can run:

```yaml
- uses: hzspyy/codex-cluade-code-practice@main
  with:
    format: markdown
    output: agent-workbench-audit.md
```

Use `format: sarif` when you want GitHub code scanning integration.
