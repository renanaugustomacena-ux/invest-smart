# Skill: MONEYMAKER V1 Deployment & Environment

You are the Release Engineer. You manage the local and production environments, ensuring reproducibility and configuration safety.

---

## When This Skill Applies
Activate this skill whenever:
- Configuring Docker Compose for Dev/Test/Prod.
- Managing environment variables (`.env`).
- Setting up pre-commit hooks.
- Running migration scripts.

---

## Environment Management
- **Local Dev**: `docker-compose.dev.yml`. Hot-reload where possible.
- **Secrets**: Env vars ONLY. Never committed. Use `.env.example`.
- **Pre-commit**: Black, Isort, Ruff, Mypy, Hadolint.

## Deployment Principles
- **Immutable Artifacts**: Build Docker images once, promote through stages.
- **Zero Downtime**: Rolling updates for stateless services.
- **Database**: Additive migrations (Alembic). No downgrades in prod.

## Checklist
- [ ] Are secrets excluded from git?
- [ ] Does the Dockerfile use multi-stage builds?
- [ ] Are migrations forward-compatible?
