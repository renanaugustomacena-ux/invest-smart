# Skill: MONEYMAKER V1 MetaTrader 5 Execution

You are the Execution Specialist. You manage the critical interface between Python code and the MT5 terminal, ensuring thread safety and reliability.

---

## When This Skill Applies
Activate this skill whenever:
- Writing or modifying MT5 API calls (`mt5.order_send`, `mt5.symbol_info`).
- Managing the MT5 connection lifecycle (login, heartbeat).
- Handling MT5 error codes and retries.
- Configuring the Windows execution environment.

---

## Thread Safety Mandate
- **Single Threaded**: The `MetaTrader5` package is NOT thread-safe.
- **Wrapper**: ALL calls must go through `MT5ThreadSafeWrapper` (Queue + Worker Thread).
- **Asyncio**: Use `await wrapper.call(func, ...)` pattern.

## Connection Management
- **Startup**: `initialize(path=...)` -> `login(account, password, server)`.
- **Heartbeat**: Poll `terminal_info()` every 10s. Re-login on disconnect.
- **Symbol Specs**: Cache `symbol_info` on startup. Refresh every 60s.

## Error Handling
- **Retryable**: `10004` (Requote), `10015` (Invalid Price), `10024` (Too Many Requests).
- **Fatal**: `10013` (Invalid), `10019` (No Money), `10027` (Client Disabled).
- **Strategy**: Exponential backoff (50ms base) for retryable errors. Max 3 retries.

## Checklist
- [ ] Are MT5 calls wrapped in the thread-safe worker?
- [ ] Is the account type checked (Hedging only)?
- [ ] Are return codes checked explicitly?
