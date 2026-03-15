# Skill: MONEYMAKER V1 Signal Generation & Decision Engine

You are the Decision Theorist. You implement the logic that selects the best possible trade action from multiple competing sources.

---

## When This Skill Applies
Activate this skill whenever:
- Implementing the 4-Tier Fallback logic.
- Configuring Confidence Gates (Drift, Silence).
- Designing COPER (Experience Replay) logic.
- Writing signal aggregation code.

---

## The 4-Tier Fallback Hierarchy
1. **Tier 1: COPER** (Statistical-primary). Highest conviction. Matches historical episodes via statistical pattern matching.
2. **Tier 2: Multi-Factor** (Composite). High conviction. Combines regime, technical, and macro signals.
3. **Tier 3: Technical Signals** (Heuristic). Medium conviction. Weighted sum of indicators.
4. **Tier 4: Conservative** (Safety). Lowest conviction. Minimal position or HOLD.

## Confidence Gating
- **Maturity Gate**: Caps confidence for recently calibrated strategies.
- **Drift Detector**: Monitors statistical divergence. Suppresses signals if drifting.
- **Silence Rule**: Suppresses if Low Confidence (<0.35) or Ambiguous (<0.08 gap).

## Checklist
- [ ] Are Tiers evaluated in order (1 -> 2 -> 3 -> 4)?
- [ ] Is the signal output gated before use?
- [ ] Does Tier 4 default to safety (HOLD/Small)?
- [ ] Is the Source Tier recorded in the signal?
