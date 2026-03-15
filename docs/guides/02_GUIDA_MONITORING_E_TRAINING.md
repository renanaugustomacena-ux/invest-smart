# Guida Monitoring — Cosa Guardare e Come Capire i Numeri

**Per**: Renan (operatore del sistema)
**Data**: 2026-02-28

---

## 1. Grafana — La Tua Dashboard Principale

**URL**: `http://10.0.0.100:3000` (oppure `http://localhost:3000` in dev)
**Login**: admin / la password che hai messo in `.env` (`GRAFANA_PASSWORD`)

### Cosa Vedrai (Dashboard Trading Overview)

```
┌─────────────────────────────────────────────────────┐
│  EQUITY CURVE          │  DAILY P&L                  │
│  ▄▄█████▀▀▀████▄      │  ██ ▄█ ██ ▄▄ █▄ ██ ▄█     │
│  (linea che sale = ok) │  (barre verdi = profitto)   │
├─────────────────────────────────────────────────────│
│  OPEN POSITIONS: 2     │  DRAWDOWN: 1.2%             │
│  SIGNALS/HOUR: 4       │  WIN RATE (30d): 58%        │
├─────────────────────────────────────────────────────│
│  SIGNAL CONFIDENCE     │  REGIME DISTRIBUTION        │
│  Mediana: 0.72         │  TRENDING: 45%              │
│  Min: 0.35  Max: 0.91  │  RANGING: 35%               │
│                        │  VOLATILE: 20%              │
└─────────────────────────────────────────────────────┘
```

### Numeri Chiave — Cosa e' Buono e Cosa e' Preoccupante

| Metrica | Buono | Attenzione | Pericolo |
|---------|-------|------------|----------|
| **Drawdown** | < 3% | 3-5% | > 5% (kill switch si attiva) |
| **Win Rate** | > 55% | 45-55% | < 45% (strategia non funziona) |
| **Signal Confidence (mediana)** | > 0.65 | 0.50-0.65 | < 0.50 (Algo Engine insicuro) |
| **Signals/Hour** | 2-10 | 0-2 (troppo cauto) | > 20 (overtrading) |
| **Tick Latency P99** | < 5ms | 5-50ms | > 50ms (dati in ritardo) |
| **Calcolo Latency** | < 10ms | 10-50ms | > 100ms (elaborazione troppo lenta) |
| **Order Execution Latency** | < 200ms | 200-500ms | > 1s (broker lento) |

### Come Leggere l'Equity Curve

- **Linea che sale costante**: il sistema sta guadagnando — tutto ok
- **Linea piatta**: il sistema e' in HOLD — sta aspettando segnali migliori
- **Piccolo calo e poi recupero**: drawdown normale — il sistema sta gestendo il rischio
- **Calo costante senza recupero**: qualcosa non va — controlla i log dell'Algo Engine

---

## 2. Prometheus — I Dati Raw

**URL**: `http://10.0.0.100:9091`

Non devi usare Prometheus direttamente (Grafana lo fa per te), ma se vuoi controllare una metrica specifica:

**Query utili da scrivere nella barra di Prometheus**:

```
# Quanti tick sta ricevendo al secondo
rate(moneymaker_ticks_received_total[1m])

# Confidence media dei segnali
avg(moneymaker_signal_confidence)

# Quanti ordini sono stati eseguiti oggi
increase(moneymaker_mt5_orders_filled_total[24h])

# Drawdown corrente
moneymaker_portfolio_drawdown_pct
```

---

## 3. Health Checks — Controllare Che Tutto Sia Vivo

### Dalla Linea di Comando (SSH in VM 100)

```bash
# Stato di tutti i container
docker compose ps

# Output atteso:
# NAME                    STATUS
# macena-postgres         Up (healthy)
# macena-redis            Up (healthy)
# macena-data-ingestion   Up (healthy)
# macena-brain            Up (healthy)
# macena-mt5-bridge       Up (healthy)
# macena-prometheus       Up
# macena-grafana          Up
```

### Endpoint HTTP

```bash
# Algo Engine
curl http://localhost:8080/health
# Risposta attesa: {"status": "healthy", "signals_generated": 42, ...}

# Data Ingestion
curl http://localhost:8081/healthz
# Risposta attesa: {"postgres": "healthy", "redis": "healthy", "ready": "true"}
```

### Se Qualcosa Non Va

| Problema | Sintomo | Soluzione |
|----------|---------|-----------|
| Container "Restarting" | Loop di crash | `docker compose logs macena-brain` per capire l'errore |
| "unhealthy" | Health check fallisce | Controlla se PostgreSQL/Redis sono up |
| Nessun tick | `rate(moneymaker_ticks_received_total[1m]) = 0` | Polygon.io API key scaduta o problemi di rete |
| Nessun segnale | Algo Engine non genera signal | Controlla regime — potrebbe essere HIGH_VOLATILITY (HOLD) |
| Ordini rifiutati | MT5 rejecta gli ordini | Controlla spread, margin, dimensione lotto |

---

## 4. Console MONEYMAKER — Il Tuo Telecomando

La console TUI e' lo strumento piu' diretto per controllare il sistema:

```bash
# Dalla VM 100
cd /opt/moneymaker
python program/services/console/moneymaker_console.py

# Oppure in modalita' comando singolo
python program/services/console/moneymaker_console.py brain status
python program/services/console/moneymaker_console.py positions
python program/services/console/moneymaker_console.py signals
python program/services/console/moneymaker_console.py risk
```

### Comandi Piu' Importanti

| Comando | Cosa Fa |
|---------|---------|
| `brain status` | Stato del Brain: regime corrente, segnali/ora, confidence |
| `positions` | Posizioni aperte con P&L non realizzato |
| `signals` | Ultimi segnali generati (BUY/SELL/HOLD) |
| `risk` | Drawdown corrente, perdita giornaliera, margine utilizzato |
| `trades` | Storico esecuzioni con slippage e profitto |
| `test all` | Esegue tutti i 321 test per verificare integrita' |

---

## 5. Cosa Monitorare Quotidianamente

### Check Mattutino (2 minuti)

1. Apri Grafana (`http://10.0.0.100:3000`)
2. Controlla l'equity curve — e' salita, piatta, o scesa?
3. Controlla il drawdown — e' sotto il 3%?
4. Controlla i segnali delle ultime 24h — quanti? Che confidence?
5. Controlla la latenza — e' tutto sotto i target?

### Check Settimanale (10 minuti)

1. Win rate degli ultimi 7 giorni — e' sopra il 50%?
2. Profit factor — e' sopra 1.3?
3. Numero di trade — ne ha fatti troppi pochi (< 5) o troppi (> 50)?
4. Regime distribution — e' stato troppo in HOLD?
5. Slippage medio — e' accettabile (< 1 pip)?

### Check Mensile (30 minuti)

1. Performance cumulativa — confronta con il benchmark (buy & hold)
2. Sharpe ratio del mese — e' sopra 1.0?
3. Max drawdown del mese — e' sotto il 10%?
4. Aggiorna TLS certificati se necessario (validita' 365 giorni)
5. Controlla lo storage del database (`df -h`)
