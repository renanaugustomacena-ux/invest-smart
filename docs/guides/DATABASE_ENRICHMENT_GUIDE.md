# Guida al Popolamento Database con Dati Reali di Mercato

Questa guida spiega come arricchire il database MONEYMAKER con dati finanziari reali (non mock o sintetici) e come normalizzarli per l'architettura AI/ML.

---

## Indice

1. [Prerequisiti](#1-prerequisiti)
2. [Verifica Stato Database](#2-verifica-stato-database)
3. [Avvio Infrastruttura](#3-avvio-infrastruttura)
4. [Configurazione API Keys](#4-configurazione-api-keys)
5. [Avvio Servizi Data Ingestion](#5-avvio-servizi-data-ingestion)
6. [Verifica Flusso Dati](#6-verifica-flusso-dati)
7. [Normalizzazione per AI/ML](#7-normalizzazione-per-aiml)
8. [Backfill Dati Storici](#8-backfill-dati-storici)
9. [Monitoring e Troubleshooting](#9-monitoring-e-troubleshooting)

---

## 1. Prerequisiti

### Software Richiesto

| Software | Versione Minima | Scopo |
|----------|-----------------|-------|
| Docker Desktop | 24+ | Container per database e servizi |
| Docker Compose | V2 | Orchestrazione servizi |
| Go | 1.22+ | Compilazione data-ingestion (opzionale) |
| Python | 3.10+ | Servizi external-data e Algo Engine |
| Git | 2.x | Gestione repository |

### API Keys Richieste

| Provider | Obbligatoria | Scopo | Costo |
|----------|--------------|-------|-------|
| **Polygon.io** | SI | Dati Forex real-time (WebSocket) | Free tier disponibile |
| **FRED** | NO (consigliata) | Yield curve, tassi reali | Gratuito |
| **CBOE** | NO | VIX (dati pubblici) | Gratuito |
| **CFTC** | NO | COT reports (dati pubblici) | Gratuito |

### Risorse Hardware Minime

- **RAM**: 8GB minimo (16GB consigliato per ML)
- **Storage**: 50GB+ per dati storici
- **CPU**: 4 core minimo
- **Rete**: Connessione stabile per WebSocket

---

## 2. Verifica Stato Database

### Verifica Container Docker

```bash
# Controlla se i container MONEYMAKER sono in esecuzione
docker ps | grep moneymaker
```

### Query di Verifica Dati

Se il container PostgreSQL e' attivo, esegui queste query:

```bash
docker exec -it moneymaker-postgres psql -U moneymaker -d moneymaker -c "
SELECT 'ohlcv_bars' as tabella, COUNT(*) as records,
       MIN(time) as primo, MAX(time) as ultimo
FROM ohlcv_bars
UNION ALL
SELECT 'market_ticks', COUNT(*), MIN(time), MAX(time) FROM market_ticks
UNION ALL
SELECT 'vix_data', COUNT(*), MIN(time), MAX(time) FROM vix_data
UNION ALL
SELECT 'yield_curve_data', COUNT(*), MIN(time), MAX(time) FROM yield_curve_data
UNION ALL
SELECT 'cot_data', COUNT(*), MIN(report_date), MAX(report_date) FROM cot_data;
"
```

### Interpretazione Risultati

| Risultato | Significato | Azione |
|-----------|-------------|--------|
| `records = 0` per tutte | Database vuoto | Seguire questa guida dall'inizio |
| `records > 0` ma `ultimo` vecchio | Dati stale | Riavviare servizi ingestion |
| `records > 0` e `ultimo` recente | Sistema operativo | Verificare qualita' dati |

---

## 3. Avvio Infrastruttura

### 3.1 Configurazione Environment

```bash
# Naviga nella directory program
cd D:\BOT\trading-ecosystem-main\program

# Copia il template di configurazione
cp .env.example .env

# Modifica .env con un editor
notepad .env   # Windows
# oppure: nano .env   # Linux/Mac
```

### 3.2 Variabili Critiche da Configurare

Modifica il file `.env` con questi valori:

```env
# === DATABASE ===
MONEYMAKER_DB_HOST=localhost
MONEYMAKER_DB_PORT=5432
MONEYMAKER_DB_NAME=moneymaker
MONEYMAKER_DB_USER=moneymaker
MONEYMAKER_DB_PASSWORD=UnaPasswordMoltoSicura123!   # CAMBIARE!

# === REDIS ===
MONEYMAKER_REDIS_HOST=localhost
MONEYMAKER_REDIS_PORT=6379
MONEYMAKER_REDIS_PASSWORD=RedisPasswordSicura456!   # CAMBIARE!

# === API KEYS (Dati Reali) ===
POLYGON_API_KEY=la_tua_chiave_polygon_qui
FRED_API_KEY=la_tua_chiave_fred_qui   # Opzionale

# === AMBIENTE ===
MONEYMAKER_ENV=production   # Usare 'production' per dati reali
```

### 3.3 Avvio Servizi Base

```bash
# Naviga nella directory Docker
cd D:\BOT\trading-ecosystem-main\program\infra\docker

# Avvia database e cache
docker-compose up -d postgres redis

# Verifica che i container siano attivi
docker-compose ps

# Output atteso:
# NAME              STATUS          PORTS
# moneymaker-postgres  Up (healthy)    0.0.0.0:5432->5432/tcp
# moneymaker-redis     Up (healthy)    0.0.0.0:6379->6379/tcp
```

### 3.4 Verifica Schema Database

```bash
# Verifica che le tabelle siano state create
docker exec -it moneymaker-postgres psql -U moneymaker -d moneymaker -c "\dt"

# Output atteso: lista di tabelle incluse ohlcv_bars, market_ticks, etc.
```

### 3.5 Avvio Monitoring (Opzionale ma Consigliato)

```bash
# Avvia Prometheus e Grafana
docker-compose up -d prometheus grafana

# Accesso:
# - Prometheus: http://localhost:9091
# - Grafana: http://localhost:3000 (admin/admin)
```

---

## 4. Configurazione API Keys

### 4.1 Polygon.io (Obbligatoria per Dati Forex)

1. **Registrazione**: Vai su https://polygon.io e crea un account
2. **Piano**: Il piano gratuito include dati Forex delayed (15 min)
3. **API Key**: Dashboard → API Keys → Copia la chiave
4. **Configurazione**:
   ```env
   POLYGON_API_KEY=pk_xxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

**Simboli Forex Configurati di Default**:
- `C:XAUUSD` - Oro/USD (asset primario MONEYMAKER)
- `C:EURUSD` - Euro/USD
- `C:GBPUSD` - Sterlina/USD
- `C:USDJPY` - USD/Yen
- `C:AUDUSD` - Dollaro Australiano/USD
- `C:USDCAD` - USD/Dollaro Canadese
- `C:NZDUSD` - Dollaro Neozelandese/USD
- `C:USDCHF` - USD/Franco Svizzero

### 4.2 FRED (Opzionale - Dati Macro)

1. **Registrazione**: Vai su https://fred.stlouisfed.org/docs/api/api_key.html
2. **API Key**: Gratuita, aumenta rate limits da 30 a 120 req/min
3. **Configurazione**:
   ```env
   FRED_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

**Serie FRED Utilizzate**:
- `DGS2`, `DGS5`, `DGS10`, `DGS30` - Treasury yields
- `T10YIE`, `T5YIE` - Breakeven inflation
- `RECPROUSM156N` - Probabilita' recessione

### 4.3 Dati Pubblici (Nessuna API Key)

- **CBOE VIX**: Endpoint pubblico `cdn.cboe.com`
- **CFTC COT**: File pubblici `cftc.gov/dea/newcot/`

---

## 5. Avvio Servizi Data Ingestion

### 5.1 Data Ingestion Service (Go) - Dati Forex Real-time

```bash
# Opzione A: Via Docker (Consigliata)
cd D:\BOT\trading-ecosystem-main\program\infra\docker
docker-compose up -d data-ingestion

# Opzione B: Esecuzione Locale (Sviluppo)
cd D:\BOT\trading-ecosystem-main\program\services\data-ingestion
go run cmd/server/main.go
```

**Cosa fa il servizio**:
1. Connessione WebSocket a Polygon.io
2. Ricezione tick bid/ask in tempo reale
3. Normalizzazione simboli (es. `C:XAUUSD` → `XAU/USD`)
4. Aggregazione in candele OHLCV (M1, M5, M15, H1, H4, D1)
5. Scrittura batch su TimescaleDB
6. Cache su Redis (TTL 300s)
7. Pubblicazione via ZeroMQ (porta 5555)

### 5.2 External Data Service (Python) - Dati Macro

```bash
# Via Docker (quando disponibile)
docker-compose up -d external-data

# Oppure esecuzione locale
cd D:\BOT\trading-ecosystem-main\program\services\external-data
pip install -r requirements.txt
python -m external_data.main
```

**Frequenze di Aggiornamento**:

| Dato | Frequenza | Provider |
|------|-----------|----------|
| VIX spot | 1 minuto | CBOE |
| VIX term structure | 5 minuti | CBOE |
| Yield curve | 1 ora | FRED |
| Real rates | 1 ora | FRED |
| COT reports | 24 ore | CFTC (settimanale) |

### 5.3 Configurazione Simboli Personalizzati

Modifica `program/services/data-ingestion/config.yaml`:

```yaml
exchanges:
  polygon:
    enabled: true
    symbols:
      - "C:XAUUSD"    # Oro
      - "C:EURUSD"    # Euro
      - "C:GBPUSD"    # Sterlina
      # Aggiungi altri simboli qui
    channels:
      - "trade"       # Tick data
      - "aggregate"   # Candele 1m pre-aggregate
```

---

## 6. Verifica Flusso Dati

### 6.1 Verifica Logs

```bash
# Logs data ingestion
docker-compose logs -f data-ingestion

# Output atteso:
# [INFO] Connected to Polygon WebSocket
# [INFO] Subscribed to C:XAUUSD
# [INFO] Received tick: XAU/USD bid=2045.67 ask=2045.89
# [INFO] Flushed batch: 1000 ticks to TimescaleDB
```

### 6.2 Query Database - Dati Recenti

```sql
-- Ultimi tick ricevuti (ultimi 5 minuti)
SELECT symbol, time, bid, ask, spread, source
FROM market_ticks
WHERE time > NOW() - INTERVAL '5 minutes'
ORDER BY time DESC
LIMIT 10;

-- Ultime candele aggregate
SELECT symbol, timeframe, time, open, high, low, close, volume
FROM ohlcv_bars
WHERE time > NOW() - INTERVAL '1 hour'
ORDER BY time DESC
LIMIT 20;

-- Dati VIX recenti
SELECT time, vix_spot, regime, term_slope, is_contango
FROM vix_data
ORDER BY time DESC
LIMIT 5;

-- Yield curve recente
SELECT time, rate_2y, rate_10y, spread_2s10s, is_inverted
FROM yield_curve_data
ORDER BY time DESC
LIMIT 5;
```

### 6.3 Verifica Redis Cache

```bash
# Connessione a Redis
docker exec -it moneymaker-redis redis-cli

# Lista chiavi tick
KEYS moneymaker:tick:*

# Ultimo tick per XAU/USD
GET moneymaker:tick:XAU/USD

# Dati macro cached
GET macro:vix
GET macro:yield_curve
```

### 6.4 Health Check Endpoints

| Servizio | URL | Risposta Attesa |
|----------|-----|-----------------|
| Data Ingestion | http://localhost:8081/health | `{"status":"healthy"}` |
| Data Ingestion Metrics | http://localhost:9090/metrics | Prometheus metrics |
| External Data Metrics | http://localhost:9095/metrics | Prometheus metrics |

---

## 7. Normalizzazione per AI/ML

### 7.1 Formato Canonico MONEYMAKER

Tutti i dati vengono normalizzati secondo questo standard:

| Campo | Formato | Esempio |
|-------|---------|---------|
| **Simbolo** | `BASE/QUOTE` | `XAU/USD`, `EUR/USD` |
| **Timestamp** | UTC, Unix ms | `1709136000000` |
| **Prezzi** | NUMERIC(20,8) | `2045.67000000` |
| **Source** | String | `polygon`, `cboe`, `fred` |

### 7.2 Pipeline di Normalizzazione

```
Raw Exchange Data
    ↓
[1] Connector (WebSocket parsing)
    ↓
[2] Normalizer (symbol mapping, decimal precision)
    ↓
[3] Data Quality Checker (OHLC validation, spike detection)
    ↓
[4] Data Sanity Checker (statistical plausibility)
    ↓
[5] Aggregator (tick → OHLCV bars)
    ↓
[6] Feature Pipeline (25+ technical indicators)
    ↓
[7] Market Vectorizer (60-dim normalized vector)
    ↓
ML Models (JEPA, GNN, MLP, Ensemble)
```

### 7.3 Tabelle ML

```sql
-- Registry modelli addestrati
SELECT model_name, version, model_type, is_active,
       training_samples, validation_accuracy
FROM model_registry
WHERE is_active = true;

-- Predizioni ML per feedback loop
SELECT symbol, model_name, direction, confidence, regime,
       inference_time_us
FROM ml_predictions
WHERE predicted_at > NOW() - INTERVAL '1 hour'
ORDER BY predicted_at DESC;

-- Metriche performance modelli
SELECT model_name, metric_name, metric_value, recorded_at
FROM model_metrics
WHERE recorded_at > NOW() - INTERVAL '24 hours'
ORDER BY recorded_at DESC;
```

### 7.4 Feature Engineering

Il servizio Algo Engine calcola automaticamente:

**Indicatori Tecnici (25+)**:
- RSI (14 periodi)
- EMA (fast 12, slow 26)
- MACD (line, signal, histogram)
- Bollinger Bands (20, 2 std)
- ATR (14 periodi)
- ADX + DI+/DI-
- Stochastic %K/%D
- OBV, Donchian, Williams %R, ROC, CCI

**Vettore 60-Dimensionale**:
```
[0-5]   Price features (OHLCV + spread)
[6-15]  Trend indicators (EMA, SMA, MACD)
[16-25] Momentum oscillators (RSI, Stoch, ROC)
[26-33] Volatility measures (ATR, BB width)
[34-40] Volume indicators (OBV, volume ratio)
[41-50] Context features (time, session, macro)
[51-59] Market microstructure (spread, tick freq)
```

### 7.5 Integrazione Dati Macro

I dati macro vengono integrati come feature aggiuntive:

| Dato | Feature | Range |
|------|---------|-------|
| VIX spot | `vix_level` | 0-100 |
| VIX regime | `vix_regime` | 0=calm, 1=elevated, 2=panic |
| Yield slope | `yield_2s10s` | -3% to +3% |
| COT sentiment | `cot_sentiment` | -1 to +1 |

---

## 8. Backfill Dati Storici

### 8.1 Perche' il Backfill e' Importante

- **ML Training**: Richiede 2+ anni di dati per pattern robusti
- **Regime Detection**: Necessita di dati su diversi cicli di mercato
- **Backtesting**: Validazione strategie su dati storici

### 8.2 Polygon REST API per Storico

```python
import httpx
import asyncio
from datetime import datetime, timedelta

POLYGON_API_KEY = "la_tua_chiave"
BASE_URL = "https://api.polygon.io"

async def fetch_historical_bars(
    symbol: str,
    timeframe: str,  # "hour", "day"
    start_date: str,  # "2023-01-01"
    end_date: str
) -> list:
    """Scarica candele storiche da Polygon."""

    url = f"{BASE_URL}/v2/aggs/ticker/{symbol}/range/1/{timeframe}/{start_date}/{end_date}"
    params = {
        "apiKey": POLYGON_API_KEY,
        "limit": 50000,
        "sort": "asc"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()

    if data.get("status") == "OK":
        return data.get("results", [])
    return []

# Esempio: scarica 1 anno di dati orari per Gold
bars = await fetch_historical_bars(
    symbol="C:XAUUSD",
    timeframe="hour",
    start_date="2023-01-01",
    end_date="2024-01-01"
)
```

### 8.3 Script Backfill Completo

Crea file `program/scripts/backfill_historical.py`:

```python
#!/usr/bin/env python3
"""
Script per backfill dati storici da Polygon.io a TimescaleDB.
Uso: python backfill_historical.py --symbol C:XAUUSD --start 2023-01-01 --end 2024-01-01
"""

import asyncio
import httpx
import asyncpg
from datetime import datetime
from decimal import Decimal
import argparse
import os

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
DB_URL = os.getenv("MONEYMAKER_DB_URL", "postgresql://moneymaker:password@localhost:5432/moneymaker")

# Rate limiting: Free tier = 5 calls/min
RATE_LIMIT_DELAY = 12  # secondi tra chiamate

async def backfill_symbol(
    pool: asyncpg.Pool,
    symbol: str,
    start_date: str,
    end_date: str,
    timeframe: str = "hour"
):
    """Backfill dati storici per un simbolo."""

    # Converti simbolo in formato canonico
    canonical = symbol.replace("C:", "").replace("X:", "")
    canonical = f"{canonical[:3]}/{canonical[3:]}"

    print(f"[INFO] Backfill {canonical} da {start_date} a {end_date}")

    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/{timeframe}/{start_date}/{end_date}"
    params = {"apiKey": POLYGON_API_KEY, "limit": 50000, "sort": "asc"}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)
        data = response.json()

    if data.get("status") != "OK":
        print(f"[ERROR] API error: {data}")
        return 0

    results = data.get("results", [])
    if not results:
        print(f"[WARN] Nessun dato per {symbol}")
        return 0

    # Prepara records per insert
    records = []
    for bar in results:
        records.append((
            datetime.fromtimestamp(bar["t"] / 1000),  # time
            canonical,                                  # symbol
            "H1" if timeframe == "hour" else "D1",     # timeframe
            Decimal(str(bar["o"])),                    # open
            Decimal(str(bar["h"])),                    # high
            Decimal(str(bar["l"])),                    # low
            Decimal(str(bar["c"])),                    # close
            Decimal(str(bar.get("v", 0))),             # volume
            bar.get("n", 0),                           # tick_count
            Decimal("0"),                              # spread_avg
            "polygon-backfill"                         # source
        ))

    # Insert batch
    async with pool.acquire() as conn:
        await conn.executemany("""
            INSERT INTO ohlcv_bars
            (time, symbol, timeframe, open, high, low, close, volume, tick_count, spread_avg, source)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (time, symbol, timeframe) DO NOTHING
        """, records)

    print(f"[OK] Inseriti {len(records)} bars per {canonical}")
    return len(records)

async def main():
    parser = argparse.ArgumentParser(description="Backfill dati storici")
    parser.add_argument("--symbol", required=True, help="Simbolo Polygon (es. C:XAUUSD)")
    parser.add_argument("--start", required=True, help="Data inizio (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="Data fine (YYYY-MM-DD)")
    parser.add_argument("--timeframe", default="hour", choices=["hour", "day"])
    args = parser.parse_args()

    pool = await asyncpg.create_pool(DB_URL)

    try:
        count = await backfill_symbol(
            pool, args.symbol, args.start, args.end, args.timeframe
        )
        print(f"\n[DONE] Totale records inseriti: {count}")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### 8.4 Strategia di Backfill Consigliata

**Priorita' Simboli**:
1. `C:XAUUSD` - Asset primario MONEYMAKER
2. `C:EURUSD`, `C:GBPUSD` - Major pairs alta liquidita'
3. Altri simboli configurati

**Priorita' Timeframe**:
1. `D1` (daily) - Richiede meno storage, pattern macro
2. `H1` (hourly) - Bilanciamento granularita'/storage
3. `M15`, `M5` - Solo se storage sufficiente (> 100GB)

**Finestre Temporali**:
| Scopo | Periodo Minimo | Ideale |
|-------|----------------|--------|
| ML Training | 2 anni | 5 anni |
| Regime Detection | 3 anni | 7 anni |
| Backtesting | 1 anno | 3 anni |

### 8.5 Backfill Dati Macro

```bash
# VIX storico (CBOE fornisce CSV)
# Download da: https://www.cboe.com/tradable_products/vix/vix_historical_data/

# FRED storico (via API)
curl "https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key=YOUR_KEY&file_type=json"

# COT storico (CFTC archivi)
# Download da: https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm
```

---

## 9. Monitoring e Troubleshooting

### 9.1 Stack Monitoring

| Componente | Porta | URL | Credenziali |
|------------|-------|-----|-------------|
| Prometheus | 9091 | http://localhost:9091 | - |
| Grafana | 3000 | http://localhost:3000 | admin/admin |
| Data Ingestion Health | 8081 | http://localhost:8081/health | - |
| Data Ingestion Metrics | 9090 | http://localhost:9090/metrics | - |

### 9.2 Dashboard Grafana Pre-configurate

1. **Market Data Overview**: Tick rate, latency, simboli attivi
2. **Database Health**: Query latency, disk usage, connections
3. **Service Health**: Uptime, error rates, memory usage

### 9.3 Alert Comuni e Soluzioni

#### Problema: Connessione Polygon Fallita
```
[ERROR] WebSocket connection failed: 401 Unauthorized
```
**Soluzione**:
1. Verifica `POLYGON_API_KEY` in `.env`
2. Verifica che la chiave non sia scaduta su polygon.io
3. Controlla firewall/proxy

#### Problema: Database Non Raggiungibile
```
[ERROR] connection refused: localhost:5432
```
**Soluzione**:
1. `docker-compose ps` - verifica stato container
2. `docker-compose logs postgres` - controlla errori
3. Verifica variabili `MONEYMAKER_DB_*` in `.env`

#### Problema: Gap nei Dati
```sql
-- Identifica gap > 2 ore nei dati H1
SELECT
    symbol,
    time as gap_start,
    LEAD(time) OVER (PARTITION BY symbol ORDER BY time) as gap_end,
    LEAD(time) OVER (PARTITION BY symbol ORDER BY time) - time as gap_duration
FROM ohlcv_bars
WHERE symbol = 'XAU/USD'
  AND timeframe = 'H1'
  AND time > NOW() - INTERVAL '7 days'
HAVING LEAD(time) OVER (PARTITION BY symbol ORDER BY time) - time > INTERVAL '2 hours';
```
**Soluzione**: Esegui backfill per i periodi mancanti

#### Problema: Rate Limiting Polygon
```
[WARN] Rate limit exceeded, backing off
```
**Soluzione**:
1. Riduci frequenza sottoscrizioni
2. Considera upgrade piano Polygon
3. Implementa caching piu' aggressivo

### 9.4 Query Diagnostiche Utili

```sql
-- Salute generale database
SELECT
    schemaname,
    relname as table_name,
    pg_size_pretty(pg_total_relation_size(relid)) as total_size,
    n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Chunks TimescaleDB
SELECT
    hypertable_name,
    chunk_name,
    range_start,
    range_end,
    pg_size_pretty(total_bytes) as size
FROM timescaledb_information.chunks
ORDER BY range_start DESC
LIMIT 20;

-- Latenza media inserimenti
SELECT
    date_trunc('hour', time) as hour,
    COUNT(*) as ticks,
    AVG(EXTRACT(EPOCH FROM (ingest_time - time))) as avg_latency_sec
FROM market_ticks
WHERE time > NOW() - INTERVAL '24 hours'
GROUP BY 1
ORDER BY 1 DESC;
```

### 9.5 Comandi Console MONEYMAKER

```bash
# Status sistema
python program/services/console/moneymaker_console.py sys status

# Health database
python program/services/console/moneymaker_console.py sys db

# Gap detection
python program/services/console/moneymaker_console.py data gaps --symbol XAU/USD

# Performance modelli ML
python program/services/console/moneymaker_console.py ml status
```

---

## Checklist Finale

Dopo aver completato la configurazione, verifica:

- [ ] Docker containers attivi (`docker-compose ps` mostra tutti "healthy")
- [ ] Database contiene tick recenti (< 5 minuti)
- [ ] Candele OHLCV aggregate per tutti i timeframe
- [ ] Dati VIX aggiornati (< 5 minuti)
- [ ] Yield curve aggiornata (< 2 ore)
- [ ] Metriche Prometheus attive
- [ ] Grafana dashboard funzionanti
- [ ] Nessun gap significativo nei dati (query di verifica)
- [ ] ZeroMQ pubblica messaggi (Algo Engine riceve dati)

---

## Supporto

Per problemi o domande:
1. Controlla i log: `docker-compose logs -f [service]`
2. Verifica lo stato: `docker-compose ps`
3. Consulta la documentazione dei provider API
4. Apri un issue sul repository del progetto
