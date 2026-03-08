# AUDIT_05: Reporting & Observability — Task Aperte

**Ultimo aggiornamento:** 2026-02-28

---

## P2: Aggiungere PII Scrubbing a Sentry

**File:** `program/services/algo-engine/src/algo_engine/observability/sentry_setup.py`

**Cosa manca:**
1. Funzione `_scrub_pii(value: str) -> str` — rimuove user home paths dalle stringhe
2. Callback `_before_send(event, hint) -> dict | None` che sanitizza:
   - `server_name` → `"moneymaker-node"` (redact hostname)
   - Stacktrace `filename`/`abs_path` scrubbing
   - Breadcrumb `message` e `data` scrubbing
3. Gate pytest: `if "pytest" in sys.modules: return False`
4. Collegare `before_send=_before_send` a `sentry_sdk.init()`

**Stima:** ~30 LOC
