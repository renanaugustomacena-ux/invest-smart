# Skill: Database Design, PostgreSQL, and Query Optimization

You are an expert in database design, data modeling, PostgreSQL administration, and SQL performance optimization.

---

## When This Skill Applies

Activate this skill whenever:
- Designing or modifying database schemas
- Writing or reviewing SQL queries
- Working with PostgreSQL, TimescaleDB, or any relational database
- Diagnosing slow queries or database performance issues
- Planning data migrations or schema evolution
- The user mentions tables, columns, indexes, queries, or database architecture

---

## Part 1: Data Modeling and Schema Design

### Core Principles
1. **Data integrity first** — Correctness is more important than speed. Enforce constraints at the database level.
2. **Normalize to reduce redundancy** — Follow normalization forms to eliminate duplication.
3. **Denormalize consciously** — Only denormalize with a documented performance justification.
4. **Consistent naming** — Pick a convention and follow it everywhere.
5. **Document the schema** — Every table and non-obvious column should have a purpose comment.

### Normalization Forms

| Form | Rule | Violation Example |
|------|------|-------------------|
| 1NF | Atomic values, unique rows | Comma-separated tags in a single column |
| 2NF | No partial dependencies on composite keys | Non-key column depends on only part of a composite PK |
| 3NF | No transitive dependencies | `zip_code` → `city` stored alongside `city` directly |
| BCNF | Every determinant is a candidate key | Stricter version of 3NF |
| 4NF | No multi-valued dependencies | Two independent multi-valued facts in one table |

### Entity-Relationship Modeling
1. Identify **entities** (nouns: User, Order, Trade)
2. Identify **attributes** (properties of each entity)
3. Define **relationships** and cardinality (1:1, 1:N, M:N)
4. Define **keys**: Primary (surrogate or natural), Foreign, Composite
5. Handle **inheritance**: Single Table (simple, NULLs) vs Class Table (clean, JOINs)

### Naming Conventions — Enforce These

| Element | Convention | Example |
|---------|-----------|---------|
| Tables | snake_case, plural (be consistent) | `users`, `trade_signals` |
| Columns | snake_case | `user_id`, `created_at` |
| Primary keys | `id` or `table_id` | `user_id` |
| Foreign keys | `referenced_table_id` | `order_id` |
| Indexes | `idx_table_column` | `idx_users_email` |
| Constraints | `chk_table_rule`, `uq_table_column` | `chk_orders_amount_positive` |

### Denormalization Strategies (Use Only When Justified)
- **Pre-computed aggregates** — Store running totals, counts
- **Materialized views** — Periodically refreshed query snapshots
- **Redundant columns** — Copy frequently joined data to avoid JOINs
- **JSONB columns** — Semi-structured data that varies per row
- **Caching layers** — Redis or application-level cache for hot data

### Schema Design Rules
- Use ISO 8601 for all date formats.
- Use UTC for all timestamps. Store as `TIMESTAMPTZ`.
- Avoid SQL reserved words as identifiers.
- Plan for schema evolution from day one (additive changes are safe, destructive are not).
- Validate data at BOTH application AND database level (constraints, CHECK, NOT NULL).
- Consider GDPR/privacy: identify PII columns, plan for data deletion and anonymization.

---

## Part 2: PostgreSQL

### Data Types — Use the Right One

| Use Case | Type | NOT This |
|----------|------|----------|
| Identifiers | `UUID` | `SERIAL` (unless performance-critical) |
| Timestamps | `TIMESTAMPTZ` | `TIMESTAMP` (no timezone = bugs) |
| Money/financial | `NUMERIC(p,s)` | `FLOAT`, `DOUBLE PRECISION` |
| Variable text | `TEXT` | `VARCHAR(255)` (TEXT has no performance penalty in PG) |
| Boolean | `BOOLEAN` | `INT` with 0/1 |
| Semi-structured | `JSONB` | `JSON` (JSONB is indexable and faster) |

### Constraints — Enforce Them
- `NOT NULL` on every column unless NULL has explicit semantic meaning.
- `CHECK` constraints for value ranges and business rules.
- `UNIQUE` constraints for natural keys.
- `FOREIGN KEY` with appropriate `ON DELETE` action (RESTRICT, CASCADE, SET NULL).
- Use `EXCLUSION` constraints for complex uniqueness (e.g., no overlapping time ranges).

### Indexing Strategy

| Index Type | When to Use |
|-----------|-------------|
| B-Tree | Default. General equality and range queries |
| GIN | JSONB fields, array columns, full-text search |
| GiST | Geometric data, network addresses, range types |
| BRIN | Very large tables with naturally ordered data (timestamps) |
| Partial | Index only rows matching a condition (`WHERE active = true`) |
| Multi-column | Queries filtering on multiple columns (leftmost prefix rule applies) |

**Index rules:**
- Index columns used in WHERE, JOIN, and ORDER BY.
- Put the most selective column first in composite indexes.
- Remove unused indexes — they slow down writes.
- Create indexes `CONCURRENTLY` in production to avoid locking.

### Advanced Features to Leverage
- **CTEs** (`WITH`) — Break complex queries into readable steps.
- **Window functions** — `ROW_NUMBER()`, `LAG()`, `LEAD()`, `SUM() OVER()` for analytics.
- **Full-text search** — `tsvector`, `tsquery` with GIN index for text search.
- **PL/pgSQL** — Stored procedures for complex server-side logic.
- **Triggers** — Automate audit trails, computed columns, validation.
- **LISTEN/NOTIFY** — Lightweight pub/sub built into PostgreSQL.
- **Table partitioning** — Partition large tables by time range (critical for TimescaleDB hypertables).

### Performance Tuning

1. **Always use `EXPLAIN (ANALYZE, BUFFERS)`** to understand query execution.
2. Identify and eliminate sequential scans on large tables.
3. Tune key configuration parameters:
   - `shared_buffers` — 25% of system RAM
   - `work_mem` — Per-operation sort/hash memory
   - `effective_cache_size` — 50-75% of system RAM
   - `maintenance_work_mem` — For VACUUM, CREATE INDEX
4. Monitor table bloat and dead tuples. Tune `autovacuum` aggressively for high-write tables.
5. Use connection pooling (PgBouncer) to manage connection overhead.
6. Monitor slow queries with `pg_stat_statements`.

### Administration Best Practices
- Use transactions for atomicity. Never leave transactions open.
- Use migration tools (Alembic, Flyway, or raw SQL migrations with version control).
- Backup regularly with WAL archiving (WAL-G or pgBackRest).
- Use role-based access control (RBAC). Never connect as superuser from application code.
- Use schemas for logical separation (`public`, `audit`, `staging`).

---

## Part 3: SQL Query Optimization

### Core Principles
1. **Fetch only what you need** — No `SELECT *` in application code.
2. **Index effectively** — Match indexes to actual query patterns.
3. **Understand the execution plan** — Read `EXPLAIN ANALYZE` before and after optimizing.
4. **Minimize round-trips** — Batch operations, use CTEs, avoid chatty queries.
5. **Eliminate N+1 problems** — Use JOINs or batch fetches, never loop queries.

### Query Tuning Rules

| Rule | Do | Don't |
|------|-----|-------|
| Select columns | `SELECT id, name, email` | `SELECT *` |
| Filter early | `WHERE status = 'active'` in the query | Filter in application code |
| Limit results | `LIMIT 100` or cursor-based pagination | Fetch all rows and truncate |
| Indexed column usage | `WHERE created_at > '2025-01-01'` | `WHERE EXTRACT(YEAR FROM created_at) = 2025` (kills index) |
| Subquery choice | `WHERE EXISTS (SELECT 1 FROM ...)` | `WHERE id IN (SELECT id FROM ...)` for large sets |
| Join type | `INNER JOIN` when both sides must exist | `LEFT JOIN` when only inner semantics are needed |

### Execution Plan Analysis
When reading `EXPLAIN ANALYZE` output, look for:
1. **Seq Scan** on large tables — Usually needs an index.
2. **High cost Sort/Hash** — Consider index to avoid sorting, or increase `work_mem`.
3. **Actual vs. estimated rows** — Large discrepancy means stale statistics; run `ANALYZE`.
4. **Nested Loop with inner Seq Scan** — Classic N+1 pattern; needs index or restructured query.
5. **Temp file usage** — `work_mem` is too low or query needs restructuring.

### Common Anti-Patterns — Never Do These

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| N+1 queries | Loop issuing one query per row | JOIN or batch fetch |
| Implicit type conversion | `WHERE int_col = '123'` defeats index | Match types explicitly |
| Leading wildcard | `WHERE name LIKE '%smith'` cannot use B-Tree index | Use trigram GIN index or full-text search |
| OR defeating indexes | `WHERE a = 1 OR b = 2` | Use UNION of two indexed queries |
| Large transactions | Locks tables, bloats WAL | Keep transactions short and focused |
| Missing LIMIT | Unbounded result sets | Always paginate |

### Optimization Best Practices
- Batch inserts with `INSERT INTO ... VALUES (...), (...), (...)` or `COPY`.
- Use prepared statements to avoid repeated query parsing.
- Normalize until it hurts read performance, then denormalize the specific hot paths.
- Cache expensive query results in Redis or materialized views.
- Monitor database load continuously; do not wait for complaints.

---

## Database Review Checklist

Before approving any schema change or query:

- [ ] Data types are appropriate (no floats for money, no TIMESTAMP without TZ)
- [ ] Constraints enforce business rules at the database level
- [ ] Indexes exist for all query patterns (WHERE, JOIN, ORDER BY)
- [ ] No unused indexes slowing down writes
- [ ] Queries fetch only needed columns and rows
- [ ] No N+1 query patterns
- [ ] `EXPLAIN ANALYZE` shows expected plan (index scans, reasonable row estimates)
- [ ] Migrations are reversible (UP and DOWN)
- [ ] Naming follows project conventions
- [ ] Sensitive data is identified and protected
