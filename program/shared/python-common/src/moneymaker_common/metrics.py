"""Helper metriche Prometheus per i servizi MONEYMAKER.

Come i "contatori di produzione" della fabbrica: ogni servizio espone
un endpoint HTTP /metrics che Prometheus controlla ogni 15 secondi.
Permettono di vedere quanti pezzi produce, quanti ne scarta, e quanto
tempo impiega ogni operazione — essenziale per la supervisione.

Organizzate per dominio di servizio:
- Metriche comuni (condivise tra tutti i servizi)
- Metriche Algo Engine (indicatori, regime, segnali, pipeline)
- Metriche Data Ingestion (tick, candele)
- Metriche MT5 Bridge (esecuzioni, posizioni)
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server


def start_metrics_server(port: int = 9090) -> None:
    """Avvia il server HTTP delle metriche Prometheus."""
    start_http_server(port)


# ============================================================
# Metriche comuni condivise tra i servizi
# ============================================================

SERVICE_UP = Gauge(
    "moneymaker_service_up",
    "Se il servizio è in esecuzione",
    ["service"],
)

REQUEST_DURATION = Histogram(
    "moneymaker_request_duration_seconds",
    "Durata della richiesta in secondi",
    ["service", "method"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

ERROR_COUNTER = Counter(
    "moneymaker_errors_total",
    "Numero totale di errori",
    ["service", "error_type"],
)


# ============================================================
# Metriche Algo Engine — i "contatori" della linea di produzione segnali
# ============================================================

FEATURES_COMPUTED = Counter(
    "moneymaker_brain_features_computed_total",
    "Calcoli indicatori completati",
    ["symbol"],
)

REGIME_CLASSIFIED = Counter(
    "moneymaker_brain_regime_classified_total",
    "Classificazioni di regime per tipo",
    ["regime"],
)

SIGNALS_GENERATED = Counter(
    "moneymaker_brain_signals_generated_total",
    "Segnali di trading generati",
    ["symbol", "direction"],
)

SIGNALS_REJECTED = Counter(
    "moneymaker_brain_signals_rejected_total",
    "Segnali di trading rifiutati dal validatore",
    ["reason"],
)

SIGNAL_CONFIDENCE = Histogram(
    "moneymaker_brain_signal_confidence",
    "Distribuzione dei punteggi di confidenza dei segnali",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

PIPELINE_LATENCY = Histogram(
    "moneymaker_brain_pipeline_latency_seconds",
    "Latenza end-to-end della pipeline (indicatori → segnale)",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)


# ============================================================
# Metriche Data Ingestion — i "contatori" dell'approvvigionamento dati
# ============================================================

TICKS_RECEIVED = Counter(
    "moneymaker_ingestion_ticks_received_total",
    "Tick ricevuti dagli exchange",
    ["exchange", "symbol"],
)

BARS_COMPLETED = Counter(
    "moneymaker_ingestion_bars_completed_total",
    "Candele OHLCV completate dall'aggregatore",
    ["symbol", "timeframe"],
)

INGESTION_LATENCY = Histogram(
    "moneymaker_ingestion_latency_seconds",
    "Latenza dall'evento exchange al tick normalizzato",
    ["exchange"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1),
)


# ============================================================
# Metriche MT5 Bridge — i "contatori" della spedizione ordini
# ============================================================

TRADES_EXECUTED = Counter(
    "moneymaker_bridge_trades_executed_total",
    "Trade eseguiti tramite MT5",
    ["symbol", "direction", "status"],
)

OPEN_POSITIONS = Gauge(
    "moneymaker_bridge_open_positions",
    "Numero di posizioni attualmente aperte",
    ["symbol"],
)

EXECUTION_LATENCY = Histogram(
    "moneymaker_bridge_execution_latency_seconds",
    "Tempo dalla ricezione del segnale all'esecuzione del trade",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

SLIPPAGE_PIPS = Histogram(
    "moneymaker_bridge_slippage_pips",
    "Slippage tra prezzo richiesto e prezzo eseguito in pips",
    buckets=(0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0),
)


# ============================================================
# Metriche Risk Management & Monitoring avanzate
# ============================================================

KILL_SWITCH_ACTIVE = Gauge(
    "moneymaker_brain_kill_switch_active",
    "Se il kill switch globale è attivo (1=attivo, 0=disattivo)",
)

DAILY_LOSS_PCT = Gauge(
    "moneymaker_brain_daily_loss_pct",
    "Percentuale di perdita giornaliera corrente",
)

DRAWDOWN_PCT = Gauge(
    "moneymaker_brain_drawdown_pct",
    "Percentuale di drawdown corrente del portafoglio",
)

STRATEGY_SIGNALS = Counter(
    "moneymaker_brain_strategy_signals_total",
    "Segnali generati per strategia",
    ["strategy", "direction"],
)

STRATEGY_PROFIT = Gauge(
    "moneymaker_brain_strategy_profit",
    "Profitto netto per strategia",
    ["strategy"],
)

DATA_QUALITY_REJECTED = Counter(
    "moneymaker_brain_data_quality_rejected_total",
    "Barre scartate per problemi di qualità",
    ["symbol", "reason"],
)

RATE_LIMIT_HITS = Counter(
    "moneymaker_brain_rate_limit_hits_total",
    "Segnali bloccati dal rate limiter",
)

CORRELATION_BLOCKED = Counter(
    "moneymaker_brain_correlation_blocked_total",
    "Segnali bloccati per esposizione valutaria eccessiva",
    ["currency"],
)

PIPELINE_TIMEOUTS = Counter(
    "moneymaker_brain_pipeline_timeouts_total",
    "Timeout nella pipeline di elaborazione barre",
    ["symbol"],
)
