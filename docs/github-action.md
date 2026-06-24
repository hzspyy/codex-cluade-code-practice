# GitHub Action

Agent Workbench ships a composite GitHub Action for auditing another repository
without copying scripts.

```yaml
name: Agent Workbench

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          persist-credentials: false
      - uses: hzspyy/codex-cluade-code-practice@main
        with:
          format: sarif
          output: agent-workbench.sarif
          baseline: agent-workbench-baseline.json
      - uses: github/codeql-action/upload-sarif@v4
        if: always()
        with:
          sarif_file: agent-workbench.sarif
```

A copy of this workflow is available at `examples/github-workflow.yml`.

This repository also runs `.github/workflows/action-self-test.yml`, which uses
the local action with both Markdown and SARIF output on every PR. That self-test
guards against shipping an action definition that only works in documentation.

For repositories that are not ready to fail on warnings, keep `strict` unset.
When the automation baseline is stable, enable:

```yaml
with:
  strict: "true"
```

For repositories with existing findings, generate and commit a baseline first:

```bash
agent-workbench audit --write-baseline agent-workbench-baseline.json .
```

Then pass that file through the action. Existing matching findings remain in
JSON, text, and Markdown reports, while SARIF only contains new warnings or
errors that need review.

Inputs:

| Input | Default | Description |
| --- | --- | --- |
| `path` | `.` | Repository path to audit. |
| `format` | `text` | One of `text`, `json`, `markdown`, or `sarif`. |
| `output` | empty | Optional file path for the report. |
| `strict` | `false` | Fail on warnings as well as errors. |
| `config` | empty | Optional path to `agent-workbench.toml`. |
| `baseline` | empty | Optional path to a committed baseline JSON file. |
