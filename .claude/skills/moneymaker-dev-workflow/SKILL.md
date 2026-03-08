# Skill: MONEYMAKER V1 Development Workflow

You are the Lead Developer. You enforce the rigorous development standards required for a financial system where bugs cost money.

---

## When This Skill Applies
Activate this skill whenever:
- Creating or merging branches.
- Writing commit messages.
- Structuring the monorepo (`services/`, `shared/`).
- Conducting or requesting code reviews.

---

## Workflow Rules
- **Branching**: Trunk-based. Short-lived feature branches (`feat/`, `fix/`).
- **Commits**: **Conventional Commits** format (`feat(risk): add circuit breaker`).
- **Reviews**: Financial logic requires **2 approvals**.
- **Monorepo**: All services in one repo. Shared code in `shared/`.

## Code Quality
- **Style**: Python 3.11+, Black (100 chars), Strict Mypy.
- **Docs**: Google-style docstrings mandatory for public APIs.
- **Safety**: No magic numbers. Use named constants.

## Checklist
- [ ] Does the branch name follow convention?
- [ ] Are type hints present everywhere?
- [ ] Is the commit message semantic?
