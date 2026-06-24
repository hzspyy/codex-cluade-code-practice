# Contributing

Agent Workbench should stay small, auditable, and useful to real repositories.

## Development

```bash
python3 -m pip install -e .
bash scripts/validate.sh
```

Before cutting a release, run:

```bash
./scripts/check-package.py
```

## Design rules

- Prefer standard-library Python unless a dependency removes substantial
  complexity.
- Keep checks explainable. Every failing audit item should include a concrete
  remediation.
- Avoid network calls in core audit logic.
- Treat secret-handling regressions as high severity.
- Update tests when changing audit behavior.

## Pull requests

Open draft PRs until local validation passes. Include:

- what changed
- why it helps agent-enabled repositories
- validation output
