# Safety First — Paper Trading Design

**Autore**: Claude + Renan
**Data**: 2026-02-28
**Obiettivo**: Portare MONEYMAKER dal 70% al 100% per paper trading rule-based
**Approccio**: Bottom-Up Sequenziale (fix bug → feature safety → monitoring → paper trade)
**Ambiente**: Windows PC con Docker Desktop (Proxmox in futuro)
**Equity iniziale**: $1,000

---

## Contesto

L'architettura MONEYMAKER è al 70% per il paper trading rule-based. L'esplorazione del codice ha rivelato:

- **3 bug critici** che impediscono il corretto funzionamento dei safety systems
- **2 feature mancanti** (spiral protection, margin check)
- **1 interfaccia mancante** (kill switch manuale)
- **1 gap di observability** (alert rules Prometheus)
- **1 miglioramento necessario** (dynamic position sizing per equity $1k)

---

## Bug Critici Scoperti

### Bug 1: Daily Loss Mai Resettata

**File**: `program/services/algo-engine/src/algo_engine/portfolio.py`
**Severità**: CRITICA
**Impatto**: Una volta che la daily loss supera il limite (2%), il sistema smette di tradare **per sempre** — non solo per il giorno corrente.

**Causa root**: `PortfolioStateManager._daily_loss_pct` viene aggiornata tramite `update_daily_loss()` ma non esiste nessun codice che la resetti a mezzanotte. La persistenza Redis usa chiave `moneymaker:daily_loss:{today}` (con data), ma in memoria il valore sopravvive tra i giorni.

**Fix**: Aggiungere `_last_reset_date` e un controllo lazy in `get_state()`:

```python
def __init__(self, ...):
    ...
    self._last_reset_date: str = datetime.date.today().isoformat()

def _check_daily_reset(self) -> None:
    """Resetta la daily loss se il giorno è cambiato."""
    today = datetime.date.today().isoformat()
    if today != self._last_reset_date:
        logger.info("Daily loss reset", old_date=self._last_reset_date, new_date=today)
        self._daily_loss_pct = ZERO
        self._last_reset_date = today

def get_state(self) -> dict:
    self._check_daily_reset()
    return { ... }
```

### Bug 2: Kill Switch auto_check() Mai Funzionato

**File**: `program/services/algo-engine/src/algo_engine/main.py` (riga 1159)
**Severità**: CRITICA
**Impatto**: Il kill switch automatico **non ha mai funzionato** — crasherebbe con `TypeError` a runtime.

**Causa root**: Il metodo `auto_check()` richiede 4 parametri (`daily_loss_pct`, `max_daily_loss_pct`, `drawdown_pct`, `max_drawdown_pct`) ma la chiamata in `main.py` ne passa solo 2.

**Fix**:
```python
await kill_switch.auto_check(
    daily_loss_pct=portfolio_manager.get_state()["daily_loss_pct"],
    max_daily_loss_pct=settings.brain_max_daily_loss_pct,
    drawdown_pct=portfolio_manager.get_state()["current_drawdown_pct"],
    max_drawdown_pct=settings.brain_max_drawdown_pct,
)
```

### Bug 3: Docker depends_on Errato

**File**: `program/infra/docker/docker-compose.yml` (riga 167-168)
**Severità**: BASSA
**Impatto**: Algo Engine può partire prima che Data Ingestion sia pronto. ZMQ troverà un socket vuoto.

**Causa root**: `algo-engine` dipende da `data-ingestion` con `condition: service_started` invece di `condition: service_healthy`. Data Ingestion ha già un healthcheck definito (porta 8081).

**Fix**: Cambiare `service_started` → `service_healthy` (riga 168).

---

## Feature Nuove

### Feature 1: Spiral Protection

**Nuovo file**: `program/services/algo-engine/src/algo_engine/signals/spiral_protection.py`

**Concetto**: Dopo N loss consecutive, il sistema riduce progressivamente il position size. Dopo M loss, ferma il trading per un periodo di cooldown.

**Interfaccia**:
```python
class SpiralProtection:
    def __init__(
        self,
        consecutive_loss_threshold: int = 3,       # Dopo 3 loss: riduce 50%
        max_consecutive_loss: int = 5,              # Dopo 5 loss: cooldown
        cooldown_minutes: int = 60,                 # Pausa di 1 ora
        size_reduction_factor: Decimal = Decimal("0.5"),  # Fattore di riduzione
    ): ...

    def record_trade_result(self, is_win: bool) -> None:
        """Registra esito trade. Win resetta contatore, loss lo incrementa."""

    def get_sizing_multiplier(self) -> Decimal:
        """Restituisce il moltiplicatore corrente: 1.0, 0.5, 0.25, 0.0"""

    def is_in_cooldown(self) -> bool:
        """True se in pausa forzata dopo troppe loss."""

    def reset(self) -> None:
        """Reset manuale (es. nuovo giorno o dopo intervento operatore)."""
```

**Tabella sizing**:
| Loss consecutive | Multiplier | Effetto su $1,000 (1% risk) |
|-----------------|------------|------------------------------|
| 0-2 | 1.0 | $10 risk per trade |
| 3 | 0.5 | $5 risk per trade |
| 4 | 0.25 | $2.50 risk per trade |
| 5+ | 0.0 (cooldown) | Trading sospeso 1 ora |

**Integrazione**:
- `portfolio.py`: chiama `spiral.record_trade_result()` in `record_trade_result()`
- `main.py`: moltiplica `maturity_sizing` per `spiral.get_sizing_multiplier()`
- `validator.py`: aggiunge check `spiral.is_in_cooldown()`

### Feature 2: Margin Check

**File**: `program/services/algo-engine/src/algo_engine/signals/validator.py`

Aggiunge un nuovo controllo tra gli esistenti (prima della correlation, Controllo 8 attuale):

```python
# Controllo: Margine sufficiente
equity = Decimal(str(portfolio_state.get("equity", "0")))
if equity > ZERO:
    used_margin = Decimal(str(portfolio_state.get("used_margin", "0")))
    estimated_margin = self._estimate_margin(signal, leverage)
    available_margin = equity - used_margin
    if estimated_margin > available_margin * Decimal("0.8"):  # 80% buffer
        return False, f"Margine insufficiente: richiesto {estimated_margin}, disponibile {available_margin}"
```

**Stima margine**: `margin = (lots × contract_size × price) / leverage`
- Leverage default: 100 (configurabile in config.py)
- Contract size: 100,000 per Forex, 100 oz per Gold

**Integrazione**:
- `portfolio.py`: aggiungere `_equity`, `_used_margin` a get_state()
- `config.py`: aggiungere `brain_default_leverage: int = 100`

### Feature 3: Kill Switch Manuale

**Due interfacce parallele** che usano Redis come backend condiviso:

**3a. REST API** (aggiunte al health server esistente in `main.py`):
```
POST /kill-switch/activate    body: {"reason": "motivo"}
POST /kill-switch/deactivate
GET  /kill-switch/status       → {"active": bool, "reason": str}
```

**3b. Console CLI** (in `moneymaker_console.py`):
```bash
moneymaker kill activate "motivo"
moneymaker kill deactivate
moneymaker kill status
```

Non serve gRPC — Redis è già il bus di stato condiviso. Il kill switch esistente (`kill_switch.py`) supporta già `activate()`, `deactivate()`, `is_active()`.

### Feature 4: Dynamic Position Sizing

**File**: `program/services/algo-engine/src/algo_engine/signals/position_sizer.py`

Attualmente usa `_default_equity` statico ($10,000 — da cambiare a $1,000). Aggiungere:

1. **Equity passata come parametro** (non più solo default)
2. **Drawdown scaling** (riduzione proporzionale):

| Drawdown | Sizing Factor |
|----------|--------------|
| 0-2% | 1.0 (100%) |
| 2-4% | 0.5 (50%) |
| 4-5% | 0.25 (25%) |
| >5% | 0.0 (kill switch) |

3. **Spiral factor** integrato dal SpiralProtection

Formula finale:
```
effective_risk = base_risk × drawdown_factor × spiral_factor
lots = (equity × effective_risk%) / (SL_pips × pip_value)
lots = clamp(lots, 0.01, 0.10)  # Max 0.10 per account $1k
```

**Config changes**:
```python
brain_default_equity: Decimal = Decimal("1000")
brain_max_lots: Decimal = Decimal("0.10")
```

---

## Observability

### Prometheus Alert Rules

**Nuovo file**: `program/services/monitoring/prometheus/alert_rules.yml`

```yaml
groups:
  - name: moneymaker_critical
    rules:
      - alert: KillSwitchActivated
        expr: moneymaker_kill_switch_active == 1
        for: 0m
        labels: { severity: critical }
        annotations:
          summary: "Kill switch attivato"

      - alert: HighDrawdown
        expr: moneymaker_portfolio_drawdown_pct > 3
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "Drawdown sopra il 3%"

      - alert: CriticalDrawdown
        expr: moneymaker_portfolio_drawdown_pct > 5
        for: 0m
        labels: { severity: critical }
        annotations:
          summary: "Drawdown sopra il 5% - kill switch imminente"

      - alert: NoTicksReceived
        expr: rate(moneymaker_ticks_received_total[5m]) == 0
        for: 5m
        labels: { severity: critical }
        annotations:
          summary: "Nessun tick ricevuto negli ultimi 5 minuti"

      - alert: HighPipelineLatency
        expr: histogram_quantile(0.99, moneymaker_pipeline_latency_seconds_bucket) > 0.1
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "Latenza pipeline P99 > 100ms"

      - alert: DailyLossLimitApproaching
        expr: moneymaker_daily_loss_pct > 1.5
        for: 1m
        labels: { severity: warning }
        annotations:
          summary: "Daily loss al 75% del limite"

      - alert: SpiralProtectionActive
        expr: moneymaker_spiral_consecutive_losses > 3
        for: 0m
        labels: { severity: warning }
        annotations:
          summary: "Spiral protection attiva - sizing ridotto"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "Servizio {{ $labels.job }} non raggiungibile"

      - alert: HighErrorRate
        expr: rate(moneymaker_errors_total[5m]) > 0.1
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "Error rate > 0.1/s nel servizio {{ $labels.service }}"

      - alert: BridgeUnavailable
        expr: moneymaker_bridge_available == 0
        for: 2m
        labels: { severity: critical }
        annotations:
          summary: "MT5 Bridge non disponibile"
```

**Docker**: AlertManager aggiunto come servizio nel docker-compose.yml con webhook/log receiver (no email/Slack per ora — configurabile in futuro).

---

## Piano di Esecuzione (Bottom-Up Sequenziale)

| Giorno | Task | File Toccati | Test |
|--------|------|-------------|------|
| **1** | Bug daily loss reset | `portfolio.py` | 3 test |
| **1** | Bug auto_check signature | `main.py` | 2 test |
| **1** | Bug docker depends_on | `docker-compose.yml` | Validazione config |
| **2** | Spiral protection | `spiral_protection.py` (nuovo) | 8-10 test |
| **3** | Spiral integration + Margin check | `validator.py`, `portfolio.py`, `config.py` | 5 test |
| **4** | Kill switch manuale REST | `main.py` | 4 test |
| **4** | Kill switch manuale Console | `moneymaker_console.py` | 3 test |
| **5** | Dynamic position sizing | `position_sizer.py`, `config.py` | 5 test |
| **6** | Alert rules Prometheus | `alert_rules.yml` (nuovo), `prometheus.yml`, `docker-compose.yml` | `promtool check` |
| **7** | Integration test E2E | `test_safety_e2e.py` (nuovo) | 1 test completo |

**Totale**: ~690 righe di codice, 15 file, ~35 test nuovi

---

## Riepilogo File

### File Nuovi (3)
- `program/services/algo-engine/src/algo_engine/signals/spiral_protection.py`
- `program/services/monitoring/prometheus/alert_rules.yml`
- `program/services/algo-engine/tests/test_safety_e2e.py`

### File Modificati (12)
- `program/services/algo-engine/src/algo_engine/portfolio.py`
- `program/services/algo-engine/src/algo_engine/main.py`
- `program/services/algo-engine/src/algo_engine/config.py`
- `program/services/algo-engine/src/algo_engine/signals/validator.py`
- `program/services/algo-engine/src/algo_engine/signals/position_sizer.py`
- `program/services/algo-engine/src/algo_engine/kill_switch.py` (metriche Prometheus)
- `program/services/console/moneymaker_console.py`
- `program/infra/docker/docker-compose.yml`
- `program/services/monitoring/prometheus/prometheus.yml`
- `program/services/algo-engine/tests/test_portfolio.py`
- `program/services/algo-engine/tests/test_validator.py`
- `program/services/algo-engine/tests/test_position_sizer.py`

---

## Criteri di Successo

Il sistema è "100% pronto per paper trading" quando:

1. [ ] Tutti i 321 test esistenti continuano a passare
2. [ ] I ~35 nuovi test passano
3. [ ] La daily loss si resetta automaticamente a mezzanotte
4. [ ] Il kill switch auto_check funziona senza TypeError
5. [ ] Docker stack parte con dipendenze corrette
6. [ ] Spiral protection riduce sizing dopo 3 loss consecutive
7. [ ] Margin check blocca trade con margine insufficiente
8. [ ] Kill switch attivabile/disattivabile via REST e Console
9. [ ] Position sizing si adatta a equity $1,000 e drawdown
10. [ ] Alert Prometheus si attivano su condizioni critiche
11. [ ] Test E2E simula ciclo completo senza errori
