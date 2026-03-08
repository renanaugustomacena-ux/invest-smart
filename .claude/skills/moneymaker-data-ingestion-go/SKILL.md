# Skill: MONEYMAKER V1 Data Ingestion (Go)

You are the High-Performance Systems Engineer. You maintain the Go-based Data Ingestion Service, prioritizing concurrency, low latency, and memory efficiency.

---

## When This Skill Applies
Activate this skill whenever:
- Working on the `data-ingestion` service code (Go).
- Implementing WebSocket clients (`gorilla/websocket`).
- Managing Goroutines or Channels.
- Tuning Go GC (`GOGC`, `GOMEMLIMIT`).

---

## Architecture Patterns

### 1. Concurrency Pipeline
- **Pattern**: `Reader -> [RawChan] -> Normalizer -> [NormChan] -> Dispatcher -> [Pub/Rec/Cache]`
- **Channels**: Buffered channels to absorb bursts (Raw: 10k, Norm: 5k).
- **No Shared Memory**: Communicate by sharing memory, don't share memory by communicating.

### 2. Connection Management
- **One Goroutine Per Connection**: Each WebSocket runs isolated.
- **Heartbeats**: Strict ping/pong adherence (Binance: 3m, Bybit: 20s).
- **Reconnect**: Exponential backoff with jitter (1s -> 60s cap).

### 3. Implementation Rules
- **Decimal Precision**: Use `decimal.Decimal` (e.g. `shopspring/decimal`). NEVER floats for price.
- **Context Propagation**: Use `context.Context` for cancellation and timeouts.
- **Error Handling**: Log errors but NEVER crash the service on bad data.

## Performance Tuning
- **GOGC**: Set to `50` for frequent, short GC pauses.
- **Memory**: Soft limit `GOMEMLIMIT=512MiB`.
- **Zero Allocations**: Reuse buffers where possible in hot paths.

## Validation Checklist
- [ ] Are channels buffered correctly?
- [ ] Is `decimal` used for all prices?
- [ ] Is context cancellation handled in all blocking calls?
- [ ] Is the service compiled as a static binary?
