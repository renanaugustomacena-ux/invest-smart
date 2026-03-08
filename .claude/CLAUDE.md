# Global CLAUDE.md - Machine-Wide Instructions

You are a strong reasoner and planner. Follow these critical instructions to structure all plans, thoughts, and responses.

---

## Non-Negotiable Rules

### Auto-Commit and Push
**MANDATORY**: After every code modification (file creation, edit, or deletion), you MUST immediately:
1. Stage the changed files with `git add`
2. Commit with a clear, descriptive message
3. Push to the remote repository with `git push`

This applies to ALL modifications, no exceptions. Do not batch changes or defer commits. Each logical change gets its own commit and push immediately after the modification is complete.

---

## Core Reasoning Framework

Before taking ANY action (tool calls or responses), you MUST proactively, methodically, and independently plan and reason through the following. Once an action is taken, it cannot be undone — so reason FIRST, act SECOND.

### 1. Logical Dependencies and Constraints
Analyze every intended action against these factors. Resolve conflicts in order of importance:
1. **Policy-based rules** — Mandatory prerequisites, constraints, and non-negotiable rules in this file.
2. **Order of operations** — Ensure an action does not prevent a subsequent necessary action. The user may request things in random order; reorder operations to maximize successful completion.
3. **Other prerequisites** — Information or actions needed before proceeding.
4. **User constraints/preferences** — Explicit instructions from the user.

### 2. Risk Assessment
Before every action, evaluate:
- What are the consequences of this action?
- Will the resulting state cause future issues?
- For exploratory tasks (searches, reads), missing optional parameters is LOW risk — prefer calling the tool with available information over asking the user, unless Rule 1 reasoning determines the optional info is required for a later step.

### 3. Abductive Reasoning and Hypothesis Exploration
At each step, identify the most logical and likely explanation for any problem:
- Look beyond immediate or obvious causes. The most likely reason may require deeper inference.
- Hypotheses may require multiple steps to test — do not shortcut.
- Prioritize hypotheses by likelihood, but do NOT discard less likely ones prematurely. A low-probability event may still be the root cause.

### 4. Outcome Evaluation and Adaptability
After every observation or result:
- Reassess: does this require changes to the current plan?
- If initial hypotheses are disproven, actively generate new ones from the gathered evidence.
- Do NOT repeat failed approaches — adapt.

### 5. Information Availability
Incorporate ALL applicable sources of information:
1. Available tools and their capabilities
2. All policies, rules, checklists, and constraints (this file and skills)
3. Previous observations and conversation history
4. Information only obtainable by asking the user

### 6. Precision and Grounding
- Be extremely precise and relevant to each exact situation.
- When referring to rules or policies, quote the exact applicable text.
- Do not make vague or ungrounded claims.

### 7. Completeness
- Exhaustively incorporate all requirements, constraints, options, and preferences.
- Resolve conflicts using the priority order in Rule 1.
- Avoid premature conclusions — there may be multiple relevant options.
- To check if an option is relevant, reason through all information sources from Rule 5.
- You may need to consult the user to know whether something is applicable. Do NOT assume it is not applicable without checking.

### 8. Persistence and Patience
- Do NOT give up unless all reasoning above is exhausted.
- Do not be dissuaded by time taken or user frustration.
- **Intelligent persistence**: On transient errors ("please try again"), retry unless an explicit retry limit has been reached. If the limit is hit, stop. On other errors, change strategy or arguments — never repeat the same failed call.

---

## Debugging Protocol

When investigating any bug, apply rigorous systematic reasoning:

### Problem Understanding
- Gather complete symptom information: what is happening vs. what should happen.
- Identify reproduction steps. Can the bug be consistently reproduced?
- Determine scope: isolated or affecting multiple areas?
- Check environment context: dev, staging, production? Versions?

### Hypothesis Generation
Generate multiple hypotheses ranked by likelihood:
1. **Most likely**: Recent code changes in the affected area
2. **Common**: Data/state issues, race conditions, edge cases
3. **Less likely**: Infrastructure, third-party dependencies, compiler/runtime bugs

Do NOT assume the obvious cause. The bug might originate elsewhere. Consider interaction effects between components. Check for similar past bugs.

### Systematic Investigation
- **Binary search**: Narrow the problem space by half each step.
- Add strategic logging/breakpoints at key decision points.
- Trace data flow from input to output.
- Check ALL assumptions explicitly — verify, never assume.
- Examine stack traces, error messages, and logs thoroughly.

### Root Cause Identification
- Distinguish between root cause and symptoms.
- Apply the "5 Whys" technique to drill down.
- Verify the root cause explains ALL observed symptoms.
- Consider multiple contributing factors.

### Fix Implementation
- Design the minimal fix that addresses the root cause.
- Consider potential side effects.
- Add tests to prevent regression.
- Document the fix and why it works.

### Verification
- Confirm the fix with the original reproduction steps.
- Test edge cases and related functionality.
- Verify no new issues were introduced.
- If the fix fails, return to hypothesis generation.

### Debugging Checklist
- [ ] Can I reproduce the bug?
- [ ] Have I identified when it started (which commit/change)?
- [ ] Have I checked logs and error messages?
- [ ] Have I verified my assumptions?
- [ ] Have I considered edge cases?
- [ ] Does my fix address the root cause, not just symptoms?
- [ ] Have I added tests to prevent regression?

---

## Code Review Standards

When reviewing or writing code, systematically analyze:

### Correctness
- Does the code do what it is supposed to do?
- Are edge cases handled? Are error conditions handled gracefully?
- Is the logic sound and free of bugs?
- Are there potential runtime issues (null pointers, type errors)?

### Security (OWASP-Aligned)
- **Input validation**: Is all user input validated and sanitized?
- **Auth**: Are permissions checked correctly?
- **Data exposure**: Is sensitive data protected?
- **Injection**: SQL, XSS, command injection risks?
- **Dependencies**: Known vulnerabilities in imports?

### Performance
- N+1 queries or unnecessary database calls?
- Expensive operations that should be cached?
- Proper pagination for large datasets?
- Memory leaks or resource cleanup issues?
- Reasonable algorithmic complexity?

### Code Quality
- Easy to understand? Descriptive names?
- Properly formatted and consistent?
- Helpful comments where needed (not where obvious)?
- No unnecessary complexity?

### Architecture
- Follows established codebase patterns?
- Modular and reusable? Proper separation of concerns?
- SOLID principles where applicable?

### Review Severity Levels
- **Critical**: Security vulnerabilities, data loss risk, broken functionality
- **Important**: Logic errors, missing error handling, performance issues
- **Suggestion**: Better patterns, naming improvements, readability
- **Nitpick**: Style preferences, minor formatting

---

## Security Audit Standards

Before reviewing any code for security, you MUST methodically analyze the following.

### Attack Surface Analysis
For any code touching external input or sensitive operations:
1. Identify all entry points (APIs, forms, file uploads, webhooks)
2. Map data flows from input → storage → output
3. Identify trust boundaries (where untrusted data crosses into trusted zones)
4. List all external dependencies and their versions
5. Identify privileged operations (admin endpoints, data deletion, config changes)

### OWASP Top 10 — Full Review

#### 1. Injection (SQL, NoSQL, Command, LDAP)

- Are ALL queries parameterized? Never concatenate user input into queries.
- Are ORM queries verified safe from injection (raw query escapes)?
- Is shell command execution avoided with user input? If unavoidable, is input strictly sanitized?

#### 2. Broken Authentication

- Are passwords hashed with strong algorithms (bcrypt, Argon2)? Never MD5/SHA1.
- Is MFA available for sensitive operations?
- Are session tokens secure (HttpOnly, Secure, SameSite flags set)?
- Is there account lockout or rate limiting after failed login attempts?

#### 3. Sensitive Data Exposure

- Is sensitive data encrypted at rest AND in transit (TLS)?
- Are API keys and secrets stored in environment variables only, NEVER in code or config files committed to version control?
- Is PII properly protected and access-logged?
- Are error messages generic in production (no stack traces, no internal paths)?

#### 4. XML External Entities (XXE)

- Is XML parsing configured to disable external entities and DTDs?
- Are safer data formats (JSON) used when possible?

#### 5. Broken Access Control

- Are ALL endpoints properly authorized (not just authenticated)?
- Is there IDOR (Insecure Direct Object Reference) protection? Users must not access other users' resources by changing an ID.
- Are CORS policies properly configured (no wildcard `*` in production)?
- Is principle of least privilege followed for all roles and service accounts?

#### 6. Security Misconfiguration

- Are default credentials changed?
- Are unnecessary features, ports, and services disabled?
- Are security headers set? (See Security Headers Checklist below)
- Is HTTPS enforced with proper TLS configuration?

#### 7. Cross-Site Scripting (XSS)

- Is ALL user input escaped/sanitized before rendering in HTML?
- Is Content Security Policy (CSP) configured and enforced?
- Are dangerous functions (`innerHTML`, `eval`, `document.write`) avoided with user-supplied data?
- Is input validated on BOTH client and server?

#### 8. Insecure Deserialization

- Is untrusted data NEVER deserialized directly (no `pickle.loads`, `eval`, `unserialize` on user input)?
- Are safe alternatives used (JSON parsing instead of native deserialization)?

#### 9. Components with Known Vulnerabilities

- Are all dependencies up to date? Run `npm audit`, `pip audit`, `go vuln check` regularly.
- Is there a process for applying security updates promptly?
- Are vulnerability scanners integrated into CI/CD?

#### 10. Insufficient Logging and Monitoring

- Are security events logged (login attempts, access denials, privilege changes)?
- Are logs protected from tampering (append-only, separate storage)?
- Is there alerting for suspicious activity (brute force, unusual access patterns)?

### Risk Assessment

For each vulnerability found, evaluate:

- **Severity**: Critical / High / Medium / Low
- **Likelihood**: How easy is it to exploit? (Unauthenticated remote = High; requires physical access = Low)
- **Impact**: What damage occurs if exploited? (Data breach = Critical; UI glitch = Low)
- **Priority**: Severity x Likelihood — fix Critical+High first

### Remediation Rules

1. Provide specific fix recommendations with code examples.
2. Reference security standards (OWASP, CWE identifiers).
3. Suggest defense-in-depth (multiple layers, not just one fix).
4. Prioritize fixes by risk level — Critical and High before Medium and Low.

### Security Headers Checklist

Every web-facing application MUST have these headers configured:

- [ ] `Strict-Transport-Security` (HSTS): `max-age=63072000; includeSubDomains; preload`
- [ ] `Content-Security-Policy` (CSP): Restrict script/style/img sources, use nonces for inline
- [ ] `X-Content-Type-Options`: `nosniff`
- [ ] `X-Frame-Options`: `DENY` or `SAMEORIGIN`
- [ ] `X-XSS-Protection`: `1; mode=block`
- [ ] `Referrer-Policy`: `strict-origin-when-cross-origin`
- [ ] `Permissions-Policy`: Disable unused browser features (camera, microphone, geolocation)
- [ ] `X-DNS-Prefetch-Control`: `on`

### Vulnerability Report Format

For every vulnerability found, document using this exact format:

```text
[SEVERITY] Vulnerability Title

Location:     File:Line or API endpoint
Description:  What is the vulnerability
Impact:       What can an attacker do if this is exploited
Reproduction: Steps to exploit (proof of concept)
Remediation:  How to fix it, with code example
References:   CWE-ID, OWASP category link
```

---

## Web Security Hardening

When building or reviewing web applications, enforce these security patterns:

### Rate Limiting — Mandatory for All API Routes

Every public API endpoint MUST have rate limiting to prevent abuse. Implement at the middleware or route level. Requirements:

- Track requests by IP address or authenticated user
- Define reasonable limits (e.g., 10-60 requests per minute per IP depending on endpoint sensitivity)
- Return HTTP `429 Too Many Requests` with `Retry-After` header when limit is exceeded
- Use sliding window or fixed window with reset

### Content Security Policy (CSP) — Mandatory

All web applications MUST implement CSP via middleware:

- `default-src 'self'` — Only allow same-origin by default
- Use nonce-based script and style allowlisting (`'nonce-{random}'` + `'strict-dynamic'`)
- `object-src 'none'` — Block plugins (Flash, Java)
- `base-uri 'self'` — Prevent base tag hijacking
- `frame-ancestors 'none'` — Prevent clickjacking (replaces X-Frame-Options)
- `upgrade-insecure-requests` — Auto-upgrade HTTP to HTTPS
- Generate a fresh nonce per request using `crypto.randomUUID()`

### Secrets Management

- **NEVER** commit `.env` files, credentials, API keys, or private keys to version control
- Add `.env*` to `.gitignore` in every project
- Use environment variables for all secrets
- Rotate credentials regularly
- Audit dependencies regularly: `npm audit fix`, `pip audit`, `go vuln check`

---

## Refactoring Standards

### Before Any Refactoring
1. **Understand first** — Document what the code does and WHY it was written this way.
2. **Tests required** — Do NOT refactor without tests. Write them first if none exist.
3. **Know the dependents** — Who depends on this code?

### Code Smells to Address
- **Long methods** (>20 lines) — Extract smaller functions
- **Large classes** (SRP violations) — Split into focused classes
- **Duplicate code** — Extract common logic
- **Long parameter lists** (>3-4 params) — Introduce parameter objects
- **Feature envy** — Move method to the right class
- **Primitive obsession** — Create domain objects
- **Nested conditionals** — Guard clauses, polymorphism
- **Dead code** — Remove it

### Safe Refactoring Process
1. Ensure test coverage BEFORE starting
2. One small change at a time
3. Run tests after each step
4. Commit after each successful step
5. Never refactor and add features in the same commit

### When NOT to Refactor
- No tests and no time to add them
- Under deadline pressure
- Code is about to be replaced
- You do not understand what the code does
- The code works and nobody needs to change it

---

## API Design Standards

### REST Conventions
- **Resource naming**: Nouns, not verbs. Plural. Lowercase with hyphens. Nested for relationships.
- **HTTP methods**: GET=retrieve, POST=create, PUT=full replace, PATCH=partial update, DELETE=remove
- **Status codes**: Use them correctly (200, 201, 204, 400, 401, 403, 404, 409, 422, 429, 500)
- **Query params**: Filtering (?status=active), Sorting (?sort=created_at), Pagination (?page=2&limit=20), Field selection (?fields=id,name)

### Response Structure
Always use consistent response envelopes:
```json
{
  "data": { },
  "meta": { "total": 100, "page": 1 },
  "errors": [{ "code": "INVALID_EMAIL", "message": "..." }]
}
```

### Error Responses Must Include
- Error code (machine-readable)
- Message (human-readable)
- Field (for validation errors)
- Request ID (for debugging)

### API Security
- HTTPS always
- Authentication (OAuth2, JWT, or API keys)
- Rate limiting
- Validate all inputs
- Do not expose internal IDs if security-sensitive

### Versioning
- Use URL versioning (/api/v1/) as default
- Never break backward compatibility without a version bump
- Deprecate before removing

---

## Skills

Specialized skill files are stored in `~/.claude/skills/`. You **MUST** check this directory and activate the relevant skill whenever the context matches its domain.

**Mandatory Skill Activations:**
- **Architecture & Design**: Activate `moneymaker-architecture.md` for any architectural decision, new service creation, or tech stack choice.
- **Infrastructure & Proxmox**: Activate `moneymaker-infrastructure.md` for VM management, host tuning, or networking.
- **Quant Statistics**: Activate `moneymaker-math-statistics.md` for return calculations, volatility, or correlation matrices.
- **Technical Indicators**: Activate `moneymaker-math-indicators.md` for indicator formulas (RSI, MACD, ATR) or smoothing logic.
- **Time Series**: Activate `moneymaker-math-time-series.md` for stationarity tests, ARIMA/GARCH, or fractional differencing.
- **Implementation Roadmap**: Activate `moneymaker-implementation-roadmap.md` for project planning, phasing, or sequencing.
- **Phase Gates**: Activate `moneymaker-phase-gates.md` for milestone verification or transition criteria.
- **Success Metrics**: Activate `moneymaker-success-metrics.md` for KPI evaluation, performance targets, or red flags.
- **Security Architecture**: Activate `moneymaker-security-architecture.md` for defense in depth, zero trust, or threat modeling.
- **Network Security**: Activate `moneymaker-network-security.md` for VLANs, firewalls, TLS/mTLS, or VPN.
- **Audit & Secrets**: Activate `moneymaker-audit-secrets.md` for secrets management, audit logs, or data encryption.
- **Dev Workflow**: Activate `moneymaker-dev-workflow.md` for git, code style, or review standards.
- **Testing Strategy**: Activate `moneymaker-testing-strategy.md` for unit/integration/E2E tests or mocking.
- **Deployment Pipeline**: Activate `moneymaker-deployment-pipeline.md` for docker compose, env vars, or migrations.
- **Observability Stack**: Activate `moneymaker-observability-stack.md` for monitoring VM, Prometheus, or Grafana setup.
- **Metrics Definitions**: Activate `moneymaker-metrics-definitions.md` for custom metrics, recording rules, or instrumentation.
- **Alerting Rules**: Activate `moneymaker-alerting-rules.md` for alert thresholds, severity definitions, or runbooks.
- **Risk Architecture**: Activate `moneymaker-risk-architecture.md` for risk service design, independence, or audit logs.
- **Safety Systems**: Activate `moneymaker-safety-systems.md` for circuit breakers, spiral protection, or kill switches.
- **Risk Calculations**: Activate `moneymaker-risk-calculations.md` for Kelly criteria, volatility adjustments, or margin math.
- **Brain Architecture**: Activate `moneymaker-brain-architecture.md` for the decision pipeline or orchestrator logic.
- **Signal Generation**: Activate `moneymaker-signal-generation.md` for the 4-tier fallback, COPER, or confidence gating.
- **Market Regimes**: Activate `moneymaker-market-regimes.md` for regime classification or strategy routing.
- **ML Features**: Activate `moneymaker-ml-feature-engineering.md` for feature creation, stationarity, or scaling.
- **ML Training**: Activate `moneymaker-ml-training-workflow.md` for training loops, validation, or labeling.
- **ML Architectures**: Activate `moneymaker-model-architectures.md` for model definition or ensemble logic.
- **MT5 Execution**: Activate `moneymaker-mt5-execution.md` for API calls, connection logic, or error handling.
- **Order Management**: Activate `moneymaker-order-management.md` for signal processing, idempotency, or reconciliation.
- **Risk & Sizing**: Activate `moneymaker-position-sizing.md` for lot calculation, risk limits, or SL/TP validation.
- **Database Schema**: Activate `moneymaker-timescaledb-schema.md` for table design, hypertables, or aggregations.
- **Redis Patterns**: Activate `moneymaker-redis-patterns.md` for caching, pub/sub, or real-time state.
- **DB Maintenance**: Activate `moneymaker-db-maintenance.md` for migrations, backups, or performance tuning.
- **Data Ingestion (Go)**: Activate `moneymaker-data-ingestion-go.md` for Go code, WebSocket handling, or channel pipelines.
- **Data Normalization**: Activate `market-data-normalization.md` for adapters, data models, or quality checks.
- **Candle Aggregation**: Activate `real-time-aggregation.md` for OHLCV logic, timeframes, or bar alignment.
- **Microservices & Communication**: Activate `moneymaker-service-comms.md` for protocol choice, retries, or resilience logic.
- **Protobuf & Contracts**: Activate `moneymaker-protobuf-contracts.md` for schema definition or serialization.
- **Docker & DevOps**: Activate `moneymaker-docker-services.md` for container setup, Dockerfiles, or CI/CD.
- **Storage & ZFS**: Activate `zfs-storage-mastery.md` for any storage pool, dataset, or disk operation.
- **GPU & ML Hardware**: Activate `gpu-passthrough-ml.md` for GPU config or ML training setup.
- **Financial Logic**: Activate `financial-integrity.md` for ANY code involving price, money, timestamps, or floating-point math.
- **Trading Logic**: Activate `trading-risk.md` for strategy implementation, signal generation, or order execution.
- **Database (General)**: Activate `database.md` for general SQL best practices (supplementary to MONEYMAKER specific skills).
