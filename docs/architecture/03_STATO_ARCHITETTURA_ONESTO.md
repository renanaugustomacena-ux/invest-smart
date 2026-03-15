# Stato dell'Architettura — Valutazione Onesta

**Per**: Renan
**Data**: 2026-02-28
**Tono**: Brutalmente onesto, zero marketing

---

## Verdetto Rapido

**MONEYMAKER e' al 70% per il trading rule-based.**

Il sistema puo' GIA' oggi:
- Ricevere dati di mercato in tempo reale
- Generare segnali di trading basati su regole (trend following, mean reversion)
- Eseguire ordini su MetaTrader 5
- Registrare tutto in un database

Il sistema NON puo' ancora:
- Fare backtesting automatizzato

---

## Cosa FUNZIONA Davvero (verificato nel codice)

### 1. Data Ingestion (Go) — PRONTO

| Aspetto | Stato | Dettagli |
|---------|-------|----------|
| Connessione Polygon.io | FUNZIONA | WebSocket con auto-reconnect |
| Connessione Binance | FUNZIONA | WebSocket alternativo |
| Normalizzazione simboli | FUNZIONA | `c:xauusd` → `XAU/USD` |
| Aggregazione OHLCV | FUNZIONA | M1, M5, M15, H1 |
| Broadcast ZeroMQ | FUNZIONA | Porta 5555 |
| Scrittura database | FUNZIONA | Batch writer con pool |
| Codice Go | 3,521 righe | Tutto reale, niente stub |

### 2. Algo Engine (Python) — PRONTO (rule-based)

| Aspetto | Stato | Dettagli |
|---------|-------|----------|
| Feature engineering (60-dim) | FUNZIONA | 25+ indicatori calcolati |
| Classificazione regime | FUNZIONA | 5 regimi (trend up/down, ranging, volatile, reversal) |
| Cascade 4 modalita' | FUNZIONA | COPER → Hybrid → Knowledge → Conservative |
| Strategie rule-based | FUNZIONANO | TrendFollowing, MeanReversion, Defensive |
| Validazione segnali | FUNZIONA | 7 controlli di rischio |
| Rate limiting | FUNZIONA | Max segnali per minuto |
| Database audit trail | FUNZIONA | Ogni segnale registrato |
| Test suite | 321 test PASSANO | 100% pass rate |

### 3. MT5 Bridge (Python) — PRONTO

| Aspetto | Stato | Dettagli |
|---------|-------|----------|
| Server gRPC | FUNZIONA | Riceve segnali dal Brain |
| Connettore MT5 | FUNZIONA | Usa MetaTrader5 Python package |
| Order Manager | FUNZIONA | Validazione lotti, spread, dedup |
| Position Tracker | FUNZIONA | Trailing stop, monitoraggio |
| Rate limiting | FUNZIONA | Max 10 ordini/minuto |

### 4. Infrastruttura — PRONTA

| Aspetto | Stato | Dettagli |
|---------|-------|----------|
| Docker Compose | DEFINITO | 8 servizi con health checks |
| Schema database | COMPLETO | 7 script SQL, hypertables, RBAC |
| Proto gRPC | COMPLETO | 5 file proto, contratti definiti |
| TLS/mTLS | CONFIGURABILE | Certificati generabili |
| CI/CD | DEFINITO | GitHub Actions (ci.yml + security.yml) |

---

## Cosa NON Funziona (la verita')

### 1. Backtesting — NON ESISTE

Non c'e' nessun framework per:
- Caricare dati storici e simulare trading
- Calcolare Sharpe, drawdown, win rate su dati passati
- Walk-forward analysis
- Validazione out-of-sample

(Il DOC 8 descrive come farlo, ma il codice non e' scritto)

### 2. Monitoring — PARZIALE

- Prometheus: configurazione base c'e', metriche definite nel codice
- Grafana: **nessuna dashboard pre-costruita** (solo il container vuoto)
- Alert rules: **non configurate** (solo documentate)
- Devono essere create manualmente dopo il deploy

### 3. Safety Systems — PARZIALI

- Il drawdown viene **tracciato** ma il kill switch **non e' implementato nel codice**
- Il daily loss limit viene **calcolato** ma non c'e' un hard stop automatico
- La spiral protection (ridurre size dopo N loss consecutive) e' **documentata ma non codificata**

---

## La Cascata di Trading Attuale

Ecco esattamente cosa succede OGGI quando il Brain riceve un tick:

```
1. Tick arriva via ZMQ                             ← FUNZIONA
2. Feature engineering: 60 indicatori calcolati     ← FUNZIONA
3. Regime detection: trend/ranging/volatile?        ← FUNZIONA
4. TradingAdvisor.recommend() tenta 4 modalita':

   Mode 1: COPER (analisi statistica avanzata + knowledge)
     → Richiede maturity alta + confidence > 0.7
     → RegimeRouter + analisi multi-fattore

   Mode 2: Hybrid (multi-factor combinato)
     → Combinazione indicatori tecnici + regime + knowledge
     → Soglia confidence intermedia

   Mode 3: Knowledge-Only (pattern storici)
     → Disponibile se la knowledge base e' popolata
     → Strategie basate su pattern conosciuti

   Mode 4: Conservative (rule-based base)
     → RegimeRouter sceglie la strategia:
       - TRENDING → TrendFollowingStrategy (EMA cross + ADX)
       - RANGING → MeanReversionStrategy (BB + RSI + Stochastic)
       - VOLATILE → DefensiveStrategy (HOLD)

5. Se il segnale passa la validazione (7 checks)   ← FUNZIONA
6. SignalRouter invia al MT5 Bridge via gRPC        ← FUNZIONA
7. MT5 Bridge esegue l'ordine su MetaTrader 5       ← FUNZIONA
```

**Tradotto**: il sistema opera come un bot rule-based sofisticato con cascade a 4 livelli.

---

## Quanto Manca per Ogni Milestone

### Milestone 1: Paper Trading Rule-Based su Demo MT5

**Stato: 85% — mancano 2-3 giorni di lavoro**

| Task | Stato | Sforzo |
|------|-------|--------|
| Deploy Docker stack | Da fare | 2-4 ore |
| Configurare .env con API keys | Da fare | 30 min |
| Connettere a Polygon.io (API key) | Da fare | 30 min |
| Aprire account demo MT5 | Da fare | 15 min |
| Verificare che i segnali arrivano al MT5 | Da fare | 1-2 ore |
| Monitorare per 48h in paper mode | Da fare | 48 ore di attesa |
| **Totale lavoro attivo** | | **~5 ore** |

**Cosa serve**: un account demo MT5, una API key di Polygon.io, e far partire Docker.

### Milestone 2: Grafana Dashboard Funzionanti

**Stato: 30% — mancano 1-2 giorni**

| Task | Stato | Sforzo |
|------|-------|--------|
| Prometheus config completa | Parziale | 1 ora |
| Creare dashboard Trading Overview | Da fare | 2-3 ore |
| Creare dashboard Infrastructure | Da fare | 2 ore |
| Configurare alert rules | Da fare | 1-2 ore |
| **Totale** | | **6-8 ore** |

### Milestone 3: Kill Switch e Safety Systems

**Stato: 20% — mancano 2-3 giorni**

| Task | Stato | Sforzo |
|------|-------|--------|
| Implementare hard kill switch (max drawdown) | Da fare | 4 ore |
| Implementare daily loss limiter | Da fare | 3 ore |
| Implementare spiral protection | Da fare | 3 ore |
| Test dei safety systems | Da fare | 4 ore |
| **Totale** | | **14 ore** |

### Milestone 4: Backtesting Framework

**Stato: 0% — mancano 1-2 settimane**

| Task | Stato | Sforzo |
|------|-------|--------|
| DataLoader da TimescaleDB (dati storici) | Da fare | 1 giorno |
| Engine di backtesting (walk-forward) | Da fare | 3-4 giorni |
| Transaction cost model | Da fare | 1 giorno |
| Report generator (Sharpe, Calmar, etc.) | Da fare | 1-2 giorni |
| Validazione con CPCV | Da fare | 2 giorni |
| **Totale** | | **8-10 giorni** |

### Milestone 5: Deploy su Proxmox

**Stato: 0% — manca 1 settimana**

| Task | Stato | Sforzo |
|------|-------|--------|
| Installare Proxmox su bare metal | Da fare | 2-3 ore |
| Creare VM 100 (Ubuntu + Docker) | Da fare | 1-2 ore |
| Creare VM 101 (Windows + MT5) | Da fare | 2-3 ore |
| Configurare rete (IP statici, bridge) | Da fare | 1-2 ore |
| Clonare repo e deploy Docker | Da fare | 1-2 ore |
| Test end-to-end su Proxmox | Da fare | 4-8 ore |
| GPU passthrough (se VM 102) | Da fare | 4-8 ore |
| **Totale** | | **2-4 giorni** |

---

## Ordine Consigliato di Lavoro

```
FASE 1 (questa settimana):
  → Deploy Docker su Windows (come adesso)
  → Account demo MT5 + API key Polygon
  → Primo paper trade rule-based
  → Verifica che il flusso tick→signal→order funziona

FASE 2 (prossima settimana):
  → Safety systems (kill switch, daily limit)
  → Dashboard Grafana base
  → 1 settimana di paper trading per raccogliere dati

FASE 3 (settimana 3-4):
  → Installare Proxmox sul bare metal
  → Migrare tutto su VM 100 + VM 101
  → Paper trading su Proxmox per validare

FASE 4 (settimana 5-8):
  → Backtesting framework
  → Walk-forward validation
  → Ottimizzazione parametri strategie
  → Se profittevole: passare a live con size minimo
```

---

## Riepilogo Brutale

| Componente | Pronto? | Percentuale |
|------------|---------|------------|
| Ricevere dati di mercato | SI | 100% |
| Calcolare indicatori tecnici | SI | 100% |
| Classificare il regime di mercato | SI | 100% |
| Generare segnali rule-based | SI | 100% |
| Eseguire ordini su MT5 | SI | 100% |
| Registrare tutto nel database | SI | 100% |
| Test suite che passa | SI | 100% (321/321) |
| Dashboard di monitoraggio | PARZIALE | 30% |
| Kill switch / safety | PARZIALE | 20% |
| Backtesting | NO | 0% |
| Deploy Proxmox | NO | 0% (ma il codice e' ready) |

**Bottom line**: Puoi iniziare a fare paper trading con regole OGGI. Per il backtesting serve ancora lavoro.
