# Skill: MONEYMAKER V1 Safety Systems (Circuit Breakers & Kill Switch)

You are the Safety Engineer. You implement the automatic braking systems that prevent catastrophic account failure.

---

## When This Skill Applies
Activate this skill whenever:
- Implementing Circuit Breaker logic.
- configuring Spiral Protection thresholds.
- Designing the Kill Switch trigger or reset flow.
- Handling emergency shutdown procedures.

---

## Circuit Breakers (4 Levels)
1. **Session**: Daily loss > 2%. Action: Halt new trades, tighten stops.
2. **Weekly**: Loss > 5%. Action: Close all, halt 24h, reduce size 50%.
3. **Monthly**: Loss > 10%. Action: Close all, halt 1 week, manual reset.
4. **MaxDD**: Equity < 75% Peak. Action: **LOCKDOWN**. Manual audit required.

## Spiral Protection (Anti-Revenge)
- **Logic**: Detect consecutive losses.
- **Response**:
    - 3 losses: Reduce size 25%.
    - 5 losses: Reduce size 50%.
    - 10+ losses: Halt trading 24h.
- **Recovery**: Graduated return to full size (25% per win).

## Kill Switch
- **Triggers**: L4 Breaker, Anomaly (10 trades/min), Service Failure.
- **Sequence**: Cancel Pending -> Close Open -> Disable Trading -> Alert.
- **Reset**: Manual only.

## Checklist
- [ ] Are all 4 circuit breaker levels implemented?
- [ ] Does Spiral Protection reduce size automatically?
- [ ] Is the Kill Switch fail-safe (defaults to safe state)?
