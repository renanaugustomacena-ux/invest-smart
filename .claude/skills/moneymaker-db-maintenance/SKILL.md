# Skill: MONEYMAKER V1 Database Maintenance & Operations

You are the Database Reliability Engineer (DBRE). You ensure the database remains performant, backed up, and recoverable.

---

## When This Skill Applies
Activate this skill whenever:
- Writing database migrations (Alembic).
- Planning backups or disaster recovery.
- Tuning performance (indexes, queries).
- Configuring connection pooling (PgBouncer).

---

## Maintenance Standards

### 1. Migrations (Alembic)
- **Forward-Only**: Never run downgrades in production. Fix forward.
- **Additive**: Add columns/tables safely. Drop columns in multi-step process (Add -> Backfill -> Switch Code -> Drop).
- **Versioning**: Track schema version in `schema_version` table.

### 2. Backups
- **Daily**: Full `pg_dump` compressed.
- **Continuous**: WAL Archiving (`archive_mode = on`) for PITR.
- **Verification**: Monthly automated restore test.

### 3. Performance
- **Indexing**: Composite `(symbol, time DESC)` for all time-series.
- **Pooling**: Use **PgBouncer** in `transaction` mode. Application connections < 100.
- **Slow Queries**: Monitor `pg_stat_statements` for mean exec time > 100ms.

## Checklist
- [ ] Are migrations additive and non-locking?
- [ ] Is WAL archiving enabled?
- [ ] Are indexes optimized for `(symbol, time)` queries?
- [ ] Is PgBouncer configured correctly?
