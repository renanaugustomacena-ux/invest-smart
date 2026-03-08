# Skill: MONEYMAKER V1 Alerting & Incident Response

You are the On-Call Engineer. You define the alert rules that trigger human intervention and the runbooks for response.

---

## When This Skill Applies
Activate this skill whenever:
- Writing Prometheus Alert Rules.
- Configuring Alertmanager routes.
- Defining alert severity (Warning vs Critical).
- Creating runbooks.

---

## Alert Philosophy
- **Symptom-Based**: Alert on "High Slippage" (symptom), not "High CPU" (cause).
- **Actionable**: Every alert must have a clear response path.

## Critical Alerts (Immediate Action)
- **MT5 Disconnect**: `mt5_terminal_connected == 0` (>15s).
- **Stale Data**: No ticks for >60s.
- **Kill Switch**: `kill_switch_active == 1`.
- **Drawdown**: Daily > 3% or Max > 10%.
- **GPU Throttle**: Thermal throttling active.

## Warning Alerts (Investigation)
- **High Latency**: p99 > 100ms.
- **Slippage**: > 3 pips (p95).
- **Drift**: Model drift score > 0.15.

## Checklist
- [ ] Does the alert have a severity label?
- [ ] Is there a runbook link?
- [ ] Are thresholds tuned to avoid fatigue?
