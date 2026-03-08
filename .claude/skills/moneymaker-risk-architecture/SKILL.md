# Skill: MONEYMAKER V1 Risk Management Architecture

You are the Chief Risk Officer. You maintain the independent Risk Service that acts as the immune system of the trading ecosystem.

---

## When This Skill Applies
Activate this skill whenever:
- Designing the Risk Service or its interfaces.
- Implementing the `RiskGate` gRPC service.
- Configuring the independent risk database (`risk_audit_log`).
- Defining authority boundaries between Brain and Risk.

---

## Core Architecture Principles

### 1. Independence
- **Standalone Service**: Risk runs in its own container/VM.
- **Authority**: Risk Gate has **VETO** power. Brain proposes, Risk disposes.
- **Isolation**: Risk failure -> System Kill Switch (Fail-safe).

### 2. Defense in Depth (Layers)
1. **Position Sizing**: Limit exposure *before* trade.
2. **Stop-Loss**: Limit loss *during* trade.
3. **Spiral Protection**: Limit streaks *across* trades.
4. **Circuit Breakers**: Limit drawdown *across* time.
5. **Kill Switch**: Emergency manual/auto halt.
6. **Margin Monitor**: Broker-level last resort.

### 3. Auditability
- **Immutable Log**: `risk_audit_log` is append-only.
- **Full Context**: Log every decision (Approve/Modify/Reject) with input metrics.

## Checklist
- [ ] Is the Risk Service independent of the Brain?
- [ ] Does the Risk Gate have absolute authority?
- [ ] Is the audit log tamper-proof?
