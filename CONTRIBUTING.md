# Contributing to MONEYMAKER

MONEYMAKER is proprietary software developed and maintained by
**Renan Augusto Macena**. This document describes the development
standards and workflow used in this project.

## Development Workflow

### Branch Strategy

- `main` — stable, production-ready code
- Feature branches — `feat/description`, `fix/description`
- All changes go through the CI pipeline before merge

### Commit Conventions

This project enforces **Conventional Commits** via pre-commit hooks.

Allowed types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`,
`chore`, `ci`, `build`, `style`, `release`

Format:

```
type(scope): short description

Optional longer body explaining the change.
```

Examples:

```
feat(algo-engine): add Keltner channel indicator
fix(mt5-bridge): prevent duplicate order execution
docs(security): add vulnerability disclosure policy
test(algo-engine): fix regime classifier hysteresis tests
```

### Pre-Commit Hooks

Install hooks before starting development:

```bash
pip install pre-commit
pre-commit install
```

Configured hooks:
- **ruff** — Python linting and formatting
- **detect-secrets** — prevents accidental credential commits
- **go-fmt / go-vet** — Go code quality
- **hadolint** — Dockerfile linting
- **conventional-pre-commit** — commit message format enforcement

### Code Style

| Language   | Formatter     | Linter          | Line Length |
|------------|---------------|-----------------|-------------|
| Python     | black + ruff  | ruff + mypy     | 100         |
| Go         | gofmt         | golangci-lint   | default     |
| TypeScript | ESLint        | ESLint          | default     |
| Docker     | —             | hadolint        | —           |

### Testing Requirements

All changes must pass the CI pipeline:

```bash
# Run all tests
cd program && make test

# Run with coverage
cd program && make test-cov

# Lint all code
cd program && make lint
```

**Coverage thresholds** (enforced in CI):
- algo-engine: 70%
- python-common: 25%
- mt5-bridge: 20%
- external-data: 70%
- data-ingestion (Go): 70%

### Security

- **Never commit** `.env` files, API keys, or credentials
- All passwords must be randomly generated (`openssl rand -base64 24`)
- TLS must be enabled in staging and production environments
- See [SECURITY.md](SECURITY.md) for vulnerability reporting
