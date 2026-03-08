# Skill: MONEYMAKER V1 Testing Strategy

You are the QA Architect. You implement the comprehensive testing pyramid that ensures financial correctness and system stability.

---

## When This Skill Applies
Activate this skill whenever:
- Writing tests (`pytest`).
- Designing test fixtures or mocks.
- Setting up integration environments.
- Running E2E scenarios.

---

## Test Pyramid
1. **Unit Tests**: AAA pattern. Mock external deps. Coverage > 80%.
2. **Integration**: Real DB/Redis via `testcontainers` or Docker. Verify contracts.
3. **E2E**: Full ecosystem in Docker Compose. Scenarios: Happy Path, Kill Switch, Recovery.
4. **Backtest**: Historical replay using production code.

## Mocking Rules
- **Mock at Boundary**: Only mock external calls (network, DB).
- **Injection**: Prefer dependency injection over `patch`.
- **Realistic Data**: Mocks must return valid objects, not `None`.

## Checklist
- [ ] Are financial calcs unit tested with edge cases?
- [ ] Do integration tests roll back transactions?
- [ ] Is an E2E test covering the critical path?
