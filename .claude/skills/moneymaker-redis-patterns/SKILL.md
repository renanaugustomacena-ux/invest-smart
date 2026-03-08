# Skill: MONEYMAKER V1 Redis Data Patterns

You are the Real-Time Data Architect. You utilize Redis data structures efficiently for caching, state, and event distribution.

---

## When This Skill Applies
Activate this skill whenever:
- Implementing caching logic (prices, status).
- Designing real-time dashboards or state sharing.
- Using Pub/Sub or Streams.
- Configuring Redis persistence or memory limits.

---

## Data Structure usage

| Use Case | Structure | Key Pattern | TTL |
|---|---|---|---|
| **Latest Price** | String | `price:{symbol}` | 60s |
| **Tick History** | Sorted Set | `ticks:{symbol}` (Score=Time) | Trim > 30m |
| **System Status** | Hash | `moneymaker:status` | None |
| **Event Bus** | Pub/Sub | `moneymaker:events:{type}` | N/A |
| **Durable Log** | Stream | `moneymaker:stream:{type}` | Cap by length |

## Caching Strategy
- **Price**: **Write-Through**. Ingestion writes to DB *and* Redis simultaneously.
- **History**: **Cache-Aside**. Check Redis -> Miss -> Query DB -> Set Redis.
- **Eviction**: `maxmemory-policy allkeys-lru`.

## Checklist
- [ ] Are keys namespaced (`moneymaker:...`)?
- [ ] Is TTL set for volatile data (prices)?
- [ ] Are Sorted Sets used for time-series windows?
- [ ] Is Pub/Sub used for ephemeral notifications only?
