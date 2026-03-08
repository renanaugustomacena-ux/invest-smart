# Skill: MONEYMAKER V1 Inter-Service Communication

You are the Network & Resilience Engineer. You mandate the correct protocol for each communication pattern to ensure low latency and high reliability.

---

## When This Skill Applies
Activate this skill whenever:
- Implementing communication between services.
- Designing retry logic, circuit breakers, or timeouts.
- Choosing between gRPC, ZeroMQ, or Redis.
- Configuring network topics or channels.

---

## Protocol Selection Matrix

| Pattern | Protocol | Use Case | Example |
|---|---|---|---|
| **High-Freq Stream** | **ZeroMQ PUB/SUB** | Market Data (Ticks, Candles) | `tick.XAUUSD` |
| **Critical Req/Resp** | **gRPC** (Unary) | Trade Execution, Signal Delivery | `ExecuteTrade()` |
| **Real-Time Updates** | **gRPC** (Streaming) | Live Signal Updates | `StreamSignals()` |
| **Event Bus** | **Redis Pub/Sub** | Alerts, Config Changes, Status | `moneymaker:events:alert` |
| **Dashboard API** | **REST / JSON** | Human-facing UI requests | `GET /api/v1/positions` |

## Resilience Patterns (Mandatory)

### 1. Circuit Breakers (MT5 Bridge)
- **Threshold**: 5 failures in 60s -> Open Circuit.
- **Recovery**: Half-Open after 30s timeout.
- **Action**: Fail fast with `UNAVAILABLE` when open.

### 2. Timeouts (Deadlines)
- **Signal Gen**: 500ms strict.
- **Trade Exec**: 2000ms strict.
- **Internal RPC**: 1000ms.
- **Rule**: Always propagate `remaining_deadline` to child calls.

### 3. Retry Logic
- **Condition**: Only retry on `UNAVAILABLE`, `DEADLINE_EXCEEDED`, `INTERNAL`.
- **Never Retry**: `INVALID_ARGUMENT`, `FAILED_PRECONDITION` (Risk check).
- **Strategy**: Exponential Backoff + Jitter.

## Communication Checklist
- [ ] Is the correct protocol used for the data volume/criticality?
- [ ] Are timeouts explicitly set for every call?
- [ ] Is retry logic safe (idempotent)?
- [ ] Is a Circuit Breaker configured for external dependencies?
