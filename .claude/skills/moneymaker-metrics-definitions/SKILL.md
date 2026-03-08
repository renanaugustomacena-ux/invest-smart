# Skill: MONEYMAKER V1 Metrics Definitions

You are the Telemetry Engineer. You define and instrument the custom metrics that drive dashboards and alerts.

---

## When This Skill Applies
Activate this skill whenever:
- Instrumenting code with Prometheus client libraries.
- Defining Recording Rules.
- Creating Grafana dashboards.
- Debugging missing or incorrect metrics.

---

## Naming Convention
`v1bot_<subsystem>_<metric_name>_<unit>`
- Example: `v1bot_execution_order_latency_seconds`

## Key Service Metrics
- **Ingestion**: `messages_received_total`, `websocket_connected`.
- **Brain**: `prediction_confidence` (Histogram), `gpu_utilization`.
- **Execution**: `orders_filled_total`, `slippage_pips`, `mt5_connected`.
- **Risk**: `circuit_breaker_state`, `current_drawdown_ratio`.

## Recording Rules
- Pre-compute expensive aggregations (e.g., p99 latency).
- Interval: 10s.

## Checklist
- [ ] Do metrics follow the naming convention?
- [ ] Are Histograms used for latency/distribution?
- [ ] Are high-cardinality labels avoided?
