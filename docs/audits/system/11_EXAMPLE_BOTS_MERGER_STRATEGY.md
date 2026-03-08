# REPORT 11: Analisi Bot di Esempio e Strategia di Merger

## Executive Summary

La directory `AI_Trading_Brain_Concepts/Exemples_Bot/` contiene **12 progetti open-source** che
coprono l'intero spettro del trading algoritmico: dal semplice bot Binance al framework enterprise
Nautilus Trader (core Rust). L'analisi identifica i **migliori pattern estraibili** per dominio
funzionale e propone due opzioni concrete: (A) un bot standalone Python che combina il meglio
di Freqtrade + Backtrader + CCXT per uso manuale immediato, o (B) l'integrazione graduale dei
pattern migliori nell'architettura MONEYMAKER esistente. La raccomandazione è **Opzione B** —
integrare in MONEYMAKER — perché il sistema ha già il 70% dell'infrastruttura necessaria e
duplicare sarebbe spreco di risorse.

---

## 1. Inventario Completo dei Progetti

### 1.1 Progetti Principali (root `Exemples_Bot/`)

| # | Progetto | Linguaggio | File | Focus | Stato |
|---|----------|-----------|------|-------|-------|
| 1 | **binance-trade-bot** | Python 3.8+ | ~25 .py (1.807 LoC) | Arbitraggio crypto ciclo-trading su Binance | Attivo |
| 2 | **freqtrade** | Python 3.11+ | 324 .py (~50k LoC) | Bot professionale, 100+ exchange, backtesting, FreqAI | Attivo, maturo |
| 3 | **gekko** | Node.js | 218 .js (~5k LoC) | Bot TA crypto con dashboard Vue.js | **Archiviato 2018** |
| 4 | **hummingbot** | Python/Cython | 743 .py | HFT/market-making, 140+ exchange, strategy v2 | Attivo |
| 5 | **ccxt** | Multi-lang | Migliaia | Libreria unificata API per 140+ exchange | Attivo, standard |
| 6 | **Stock-Prediction-Models** | Python | 70 .py/.ipynb | 30 modelli DL + 23 agenti RL | Research |

### 1.2 Progetti in `new/`

| # | Progetto | Linguaggio | File | Focus | Stato |
|---|----------|-----------|------|-------|-------|
| 7 | **backtrader** | Python 3.2+ | 171 .py | Framework backtesting event-driven, 122 indicatori | Stabile |
| 8 | **nautilus_trader** | Rust/Python | Migliaia | Platform enterprise, core Rust, nanosecond | Attivo |
| 9 | **vnpy** | Python 3.10+ | 59 .py (core) | Piattaforma quant, alpha module, 30+ broker | Attivo |
| 10 | **Lean** | C# | Migliaia | QuantConnect, backtesting istituzionale | Attivo |
| 11 | **TradingAgents** | Python | ~20 .py | Agenti RL per portfolio management | Research |
| 12 | **machine-learning-for-trading** | Python | 24 capitoli (notebook) | Libro completo ML per trading | Educational |

---

## 2. Analisi Best-of-Breed per Dominio

Per ogni dominio funzionale, identifico il progetto che eccelle e cosa estrarre.

### 2.1 Strategy Interface

| Progetto | Approccio | Voto |
|----------|-----------|------|
| **Freqtrade** | `IStrategy` con `populate_indicators()`, `populate_entry_trend()`, `populate_exit_trend()` | **MIGLIORE** |
| Hummingbot | Strategy v2 con controllers + executors + connectors | Eccellente ma complesso |
| Backtrader | `Strategy` con `init()`, `next()`, `notify_order()` | Semplice ed elegante |
| VnPy | CTA strategy con `on_bar()`, `on_tick()` | Buono per futures |
| Gekko | `init()`, `update()`, `check()` | Troppo semplice |

**Vincitore**: **Freqtrade IStrategy** — il miglior equilibrio tra potenza e semplicità.

Pattern chiave da `freqtrade/strategy/interface.py`:
```python
class IStrategy(ABC):
    # Parametri dichiarativi
    minimal_roi: dict = {"0": 0.10}       # ROI target per tempo
    stoploss: float = -0.10               # Stop loss %
    timeframe: str = "5m"                 # Timeframe candle
    can_short: bool = False               # Supporto short

    # Lifecycle hooks
    def populate_indicators(self, dataframe, metadata): ...
    def populate_entry_trend(self, dataframe, metadata): ...
    def populate_exit_trend(self, dataframe, metadata): ...

    # Hooks avanzati (opzionali)
    def custom_stoploss(self, pair, trade, ...): ...
    def custom_exit(self, pair, trade, ...): ...
    def adjust_trade_position(self, trade, ...): ...
```

**Applicazione MONEYMAKER**: Le 5 strategie esistenti (TrendFollowing, MeanReversion, Defensive,
MLProxy, RegimeRouter) già seguono un pattern simile con `BaseStrategy.generate_signal()`.
L'evoluzione è aggiungere i parametri dichiarativi (`minimal_roi`, `stoploss`, `timeframe`)
e gli hook avanzati (`custom_stoploss`, `adjust_trade_position`).

---

### 2.2 Backtesting Engine

| Progetto | Approccio | Voto |
|----------|-----------|------|
| **Freqtrade** | Event-driven con simulazione fee/slippage, caching | **MIGLIORE** |
| **Backtrader** | Event-driven puro, 122 indicatori, analyzers | **CO-MIGLIORE** |
| Lean | Istituzionale, market impact realistico | Eccellente ma C# |
| Nautilus | Parity backtest/live (identico codice) | Over-engineered |
| VnPy | CTA backtester con portfolio | Buono ma specifico |
| Binance-bot | Replay semplice | Insufficiente |

**Vincitore**: **Backtrader** per il framework, **Freqtrade** per le metriche.

Pattern chiave da `backtrader/cerebro.py`:
```python
class Cerebro:
    def addstrategy(self, strategy_cls, **kwargs): ...
    def adddata(self, data_feed): ...
    def addanalyzer(self, analyzer_cls): ...
    def run(self) -> list[Strategy]: ...

    # Analyzers integrati
    # - SharpeRatio, Returns, MaxDrawdown, SQN, TradeAnalyzer
    # - AnnualReturn, Calmar, VWR (Variability-Weighted Return)
```

Pattern chiave da `freqtrade/optimize/backtesting.py`:
```python
class Backtesting:
    def backtest(self, processed, start_date, end_date):
        # Per ogni candle:
        #   1. Check exit conditions
        #   2. Check entry conditions
        #   3. Simulate fills con slippage
        #   4. Track portfolio equity
        # Risultato: DataFrame con tutti i trade + metriche
```

**Applicazione MONEYMAKER**: MONEYMAKER non ha backtesting (Report 04, Finding C7). Adottare il
pattern Cerebro + Analyzers di Backtrader come framework, con le metriche di Freqtrade
(Sharpe, Calmar, profit factor, max drawdown, win rate).

---

### 2.3 Exchange Abstraction

| Progetto | Approccio | Voto |
|----------|-----------|------|
| **CCXT** | API unificata per 140+ exchange, multi-linguaggio | **STANDARD DE FACTO** |
| Hummingbot | Connettori nativi per 140+ exchange | Eccellente ma accoppiato |
| Freqtrade | Wrapper sopra CCXT | Buono |
| Nautilus | Adapter pattern modulare | Eccellente design |
| VnPy | Gateway per 30+ broker (CTP, IB, Binance) | Buono per futures |

**Vincitore**: **CCXT** — standard industria, usato da Freqtrade e altri.

Pattern chiave da `ccxt/base/exchange.py`:
```python
exchange = ccxt.binance({"apiKey": "...", "secret": "..."})

# API unificata — identica per TUTTI gli exchange
ohlcv = exchange.fetch_ohlcv("BTC/USDT", "1h")
balance = exchange.fetch_balance()
order = exchange.create_order("BTC/USDT", "limit", "buy", 0.01, 50000)

# Error handling strutturato
# RateLimitExceeded, InsufficientFunds, OrderNotFound, etc.
```

**Applicazione MONEYMAKER**: MONEYMAKER usa Polygon.io (forex) e Binance (crypto) con connettori
custom in Go. CCXT potrebbe:
1. Rimpiazzare il connettore Binance (Go → Python via ccxt)
2. Aggiungere supporto per altri exchange (Kraken, Bybit, OKX)
3. Non sostituisce MT5 per l'esecuzione forex (MT5 resta primario)

---

### 2.4 ML/AI Integration

| Progetto | Approccio | Voto |
|----------|-----------|------|
| **Freqtrade FreqAI** | Framework ML integrato con retraining automatico | **MIGLIORE** |
| **Stock-Prediction-Models** | 30 DL + 23 RL architetture | **MIGLIORE per architetture** |
| **VnPy Alpha** | Factor engineering Alpha 158 + LightGBM/MLP | Eccellente |
| ML-for-Trading | 24 capitoli libro (educational) | Reference |
| TradingAgents | DQN/PPO/A3C per portfolio | Research-grade |
| Hummingbot | scikit-learn base | Sufficiente |

**Vincitore**: **FreqAI** per il framework, **Stock-Prediction-Models** per le architetture.

Pattern chiave da `freqtrade/freqai/freqai_interface.py`:
```python
class IFreqaiModel(ABC):
    def train(self, dataframe, pair, dk): ...
    def predict(self, dataframe, pair, dk): ...

    # Features automatiche da:
    # - Indicatori tecnici (RSI, MACD, BB, etc.)
    # - Lag features (t-1, t-2, ..., t-n)
    # - Retraining su drift detection
```

Pattern chiave da `Stock-Prediction-Models/`:
```
deep-learning/
├── LSTM.py                    # LSTM per time series
├── Bidirectional-LSTM.py      # BiLSTM
├── Seq2Seq.py                 # Encoder-Decoder
├── Attention.py               # Seq2Seq + Attention
├── Encoder-Decoder-CNN.py     # CNN per pattern
└── ...                        # 30 modelli totali

agent/
├── double-q-learning.py       # Double DQN
├── dueling-q-learning.py      # Dueling DQN
├── actor-critic.py            # A2C
├── curiosity-q-learning.py    # Curiosity-driven
├── evolution-strategy.py      # Neuro-evolution
└── ...                        # 23 agenti totali
```

Pattern chiave da `vnpy/alpha/`:
```python
# Alpha 158 — 158 fattori predittivi (da Microsoft Qlib)
# Combinati con:
# - Lasso regression (feature selection)
# - LightGBM (gradient boosting)
# - MLP (deep learning)
```

**Applicazione MONEYMAKER**: MONEYMAKER ha già RAP Coach (MarketPerception→Memory→Strategy→Pedagogy)
e JEPA. I pattern da adottare:
1. FreqAI: retraining automatico su drift (MONEYMAKER ha `retraining_trigger.py` ma non è wired)
2. Stock-Prediction-Models: architetture RL per il Mode 1 (COPER) — Actor-Critic per decisioni
3. VnPy Alpha 158: fattori predittivi da aggiungere alla pipeline features (attualmente 60-dim)

---

### 2.5 Order Management & Risk

| Progetto | Approccio | Voto |
|----------|-----------|------|
| **Nautilus** | OCO, OTO, bracket orders, Rust core | **MIGLIORE design** |
| **Freqtrade** | Protections system (cooldown, max losses, pair locks) | **MIGLIORE per risk** |
| Backtrader | Order types (Market, Limit, Stop, StopTrail, Bracket, OCO) | Eccellente |
| Hummingbot | Multi-order management con circuit breaker | Buono |
| Binance-bot | Fee calc con BNB discount, dedup | Semplice |
| VnPy | TWAP, Sniper, Iceberg, BestLimit | Eccellente per execution |

**Vincitore**: **Freqtrade** per risk management, **VnPy** per algorithmic execution.

Pattern chiave da Freqtrade protections:
```python
# Protections — middleware tra segnale e ordine
protections = [
    {"method": "CooldownPeriod", "stop_duration_candles": 5},
    {"method": "MaxDrawdown", "max_allowed_drawdown": 0.2},
    {"method": "StoplossGuard", "trade_limit": 3, "stop_duration_candles": 10},
    {"method": "LowProfitPairs", "trade_limit": 2, "stop_duration": 60}
]
```

Pattern chiave da VnPy algorithmic execution:
```python
# Algoritmi di esecuzione (riduzione market impact)
class TwapAlgo:     # Time-Weighted Average Price — split in N intervalli
class SniperAlgo:   # Aspetta prezzo target, esegui tutto in un colpo
class IcebergAlgo:  # Mostra solo porzione dell'ordine totale
class BestLimitAlgo: # Limit order al best bid/ask, aggiorna continuamente
```

**Applicazione MONEYMAKER**: MONEYMAKER ha kill switch, spiral protection, position sizer, validator
(~90% safety). Mancano:
1. Freqtrade protections: CooldownPeriod e LowProfitPairs da aggiungere al validator
2. VnPy algos: TWAP e Iceberg per ordini large su MT5 (attualmente solo market orders)
3. Bracket orders: OCO (One-Cancels-Other) per SL+TP simultanei

---

### 2.6 Notifications & Control

| Progetto | Approccio | Voto |
|----------|-----------|------|
| **Freqtrade** | Telegram bot con 15+ comandi + FastAPI REST | **MIGLIORE** |
| Hummingbot | Telegram, Discord, Email via notifier | Buono |
| Binance-bot | Apprise (multi-service: Telegram, Discord, Slack) | Semplice ma flessibile |
| VnPy | WeChat + custom GUI | Specifico Cina |

**Vincitore**: **Freqtrade Telegram** per comandi, **Binance-bot Apprise** per multi-service.

Pattern chiave da Freqtrade Telegram:
```
/status     — Posizioni aperte con PnL
/profit     — Profit giornaliero/settimanale/totale
/balance    — Balance broker
/forceexit  — Chiudi posizione manualmente
/performance — Win rate per coppia
/daily      — PnL giornaliero
/stats      — Statistiche complete
/stopbuy    — Blocca nuovi acquisti (≈ kill switch)
```

**Applicazione MONEYMAKER**: MONEYMAKER ha `telegram.py` e `dispatcher.py` per alerting ma solo
notifiche passive. Adottare il pattern Freqtrade per comandi attivi (status, profit, forceexit,
kill switch via Telegram).

---

### 2.7 Real-time Data

| Progetto | Approccio | Voto |
|----------|-----------|------|
| **Hummingbot** | WebSocket asincrono con fallback REST, multi-exchange | **MIGLIORE** |
| Binance-bot | `unicorn-binance-websocket-api` con cache | Buono |
| CCXT | CCXT Pro per WebSocket, REST standard | Standard |
| Nautilus | Tokio async, nanosecond timestamps | Enterprise |

**Vincitore**: **Hummingbot** per design, **CCXT** per standardizzazione.

**Applicazione MONEYMAKER**: Data Ingestion (Go) è già solido con WebSocket Polygon.io + Binance
+ aggregazione OHLCV + ZMQ publish. Nessun cambiamento necessario — il pattern MONEYMAKER è
già al livello di Hummingbot.

---

### 2.8 Factor Engineering / Feature Pipeline

| Progetto | Approccio | Voto |
|----------|-----------|------|
| **VnPy Alpha** | Alpha 158 (Microsoft Qlib) — 158 fattori predittivi | **MIGLIORE** |
| **ML-for-Trading** | 24 capitoli di feature engineering per ML | **MIGLIORE educational** |
| Freqtrade | TA-Lib + pandas-ta indicators | Standard |
| Backtrader | 122 indicatori built-in | Completo |

**Vincitore**: **VnPy Alpha 158** per i fattori, **ML-for-Trading** come reference.

Alpha 158 include:
- Price features: open/close/high/low ratios, returns multi-periodo
- Volume features: VWAP, volume ratios, accumulation/distribution
- Volatility features: rolling std, ATR, Bollinger width
- Momentum features: ROC, RSI, MACD, Williams %R
- Mean reversion: z-scores, percentile ranks
- Cross-sectional: rank features (non applicabile a MONEYMAKER single-asset)

**Applicazione MONEYMAKER**: La pipeline attuale è 60-dim. Si possono aggiungere fattori Alpha 158
selezionati (esclusi cross-sectional) portando a ~80-100 features, con feature selection
automatica via Lasso o mutual information.

---

## 3. Tabella Comparativa Globale

| Dominio | Gekko | Binance-Bot | Freqtrade | Hummingbot | CCXT | Stock-Pred | Backtrader | Nautilus | VnPy | Lean | MONEYMAKER |
|---------|-------|-------------|-----------|------------|------|------------|------------|----------|------|------|---------|
| Strategy Interface | ★ | ★★ | ★★★★★ | ★★★★ | — | — | ★★★★ | ★★★★ | ★★★ | ★★★★ | ★★★ |
| Backtesting | ★★ | ★ | ★★★★★ | ★ | — | ★★★ | ★★★★★ | ★★★★ | ★★★ | ★★★★★ | ☆ |
| Exchange API | ★★ | ★★ | ★★★★ | ★★★★★ | ★★★★★ | — | ★★ | ★★★★ | ★★★ | ★★★ | ★★★ |
| ML/AI | ☆ | ☆ | ★★★★ | ★★ | — | ★★★★★ | ☆ | ☆ | ★★★★ | ★★ | ★★★ |
| Risk Management | ☆ | ★ | ★★★★ | ★★★ | — | ☆ | ★★★★ | ★★★★★ | ★★★ | ★★★★ | ★★★★ |
| Notifications | ☆ | ★★★ | ★★★★★ | ★★★ | — | ☆ | ☆ | ☆ | ★★ | ★★ | ★★ |
| Real-time Data | ★★ | ★★★ | ★★★ | ★★★★★ | ★★★★ | ☆ | ★★ | ★★★★★ | ★★★ | ★★★ | ★★★★ |
| Documentation | ★★ | ★★★ | ★★★★★ | ★★★★ | ★★★★★ | ★★★ | ★★★★ | ★★★ | ★★ | ★★★★ | ★★★ |

Legenda: ☆ = assente, ★ = minimale, ★★★ = buono, ★★★★★ = eccellente

---

## 4. Piano di Merger — Due Opzioni

### Opzione A: Bot Standalone Combinato

Creare un singolo script Python che combina il meglio di ciascun progetto in un bot
controllato manualmente dall'utente.

**Architettura proposta**:
```
moneymaker_standalone_bot/
├── main.py                 # Entry point con CLI (argparse)
├── config.yaml             # Configurazione asset, strategie, risk
├── strategies/
│   ├── base.py             # IStrategy interface (da Freqtrade)
│   ├── trend_following.py  # EMA cross + ADX (da MONEYMAKER)
│   ├── mean_reversion.py   # BB + RSI (da MONEYMAKER)
│   └── ml_strategy.py      # LSTM/GRU prediction (da Stock-Pred)
├── exchange/
│   ├── ccxt_adapter.py     # CCXT wrapper per crypto
│   └── mt5_adapter.py      # MT5 wrapper per forex
├── backtest/
│   ├── engine.py           # Cerebro-style engine (da Backtrader)
│   └── analyzers.py        # Sharpe, Calmar, DrawDown (da Backtrader)
├── risk/
│   ├── kill_switch.py      # Kill switch (da MONEYMAKER)
│   ├── position_sizer.py   # Sizing (da MONEYMAKER)
│   └── protections.py      # CooldownPeriod, MaxDrawdown (da Freqtrade)
├── notifications/
│   ├── telegram_bot.py     # Comandi attivi (da Freqtrade)
│   └── apprise_notifier.py # Multi-service (da Binance-bot)
└── data/
    ├── feeds.py            # OHLCV data loader
    └── indicators.py       # Indicatori tecnici
```

**Pro**: Indipendente, facile da testare, utilizzabile subito
**Contro**: Duplica codice di MONEYMAKER, non beneficia dell'infrastruttura esistente

---

### Opzione B: Integrazione in MONEYMAKER (RACCOMANDATO)

Integrare i pattern migliori nei servizi MONEYMAKER esistenti, mantenendo l'architettura
a microservizi.

**Cosa integrare e dove**:

| Pattern | Sorgente | Destinazione MONEYMAKER | Effort |
|---------|----------|---------------------|--------|
| Strategy parametri dichiarativi | Freqtrade IStrategy | `strategies/base.py` | 2h |
| Custom stoploss hook | Freqtrade | `strategies/base.py` | 2h |
| Backtesting engine | Backtrader Cerebro | Nuovo modulo `algo-engine/backtest/` | 3-5 giorni |
| Analyzers (Sharpe, Calmar) | Backtrader | `algo-engine/backtest/analyzers.py` | 1 giorno |
| Protections middleware | Freqtrade | `signals/protections.py` | 1 giorno |
| TWAP/Iceberg execution | VnPy | `mt5-bridge/algo_executor.py` | 2 giorni |
| Telegram comandi attivi | Freqtrade | `console/telegram_commands.py` | 2 giorni |
| Alpha 158 features | VnPy | `features/alpha_factors.py` | 2-3 giorni |
| RL Agent (Actor-Critic) | Stock-Pred | `nn/rl_agent.py` | 1 settimana |
| Retraining on drift | FreqAI | Wire `retraining_trigger.py` | 1 giorno |
| Bracket orders (OCO) | Nautilus | `mt5-bridge/order_manager.py` | 1 giorno |
| Hyperopt framework | Freqtrade/Optuna | `ml-training/hyperopt/` | 3-5 giorni |

**Pro**: Sfrutta infrastruttura esistente, nessuna duplicazione, approccio incrementale
**Contro**: Più lento da implementare, richiede conoscenza dell'architettura MONEYMAKER

---

### Raccomandazione: **Opzione B** (Integrazione in MONEYMAKER)

Motivazione:
1. MONEYMAKER ha già pipeline features (60-dim), cascade orchestrator, safety systems, gRPC
2. Duplicare in un bot standalone significherebbe ricostruire il 70% di MONEYMAKER
3. I pattern da integrare sono modulari — si possono aggiungere uno alla volta
4. Il valore incrementale è massimo: ogni feature aggiunta migliora l'intero sistema

---

## 5. Mapping Dettagliato su MONEYMAKER

### 5.1 Backtesting → `algo-engine/src/algo_engine/backtest/`

**Nuovo modulo** da creare ispirato a Backtrader + Freqtrade:

```
algo-engine/src/algo_engine/backtest/
├── __init__.py
├── engine.py           # BacktestEngine: loop su OHLCV storici
├── data_feed.py        # Feed da TimescaleDB (query hypertable)
├── simulator.py        # Simulazione ordini con fee/slippage
├── analyzers.py        # SharpeRatio, MaxDrawdown, CalmarRatio, WinRate
└── report.py           # Generatore report HTML/JSON
```

Compatibilità: usa le stesse strategie (`strategies/`) e features (`features/pipeline.py`)
della pipeline live. Il backtest deve produrre gli stessi segnali del live.

### 5.2 Strategy Enhancement → `strategies/base.py`

Aggiungere a `BaseStrategy`:
```python
class BaseStrategy(ABC):
    # NUOVI parametri dichiarativi (da Freqtrade)
    minimal_roi: dict = {"0": 0.05, "60": 0.03, "120": 0.01}
    stoploss: float = -0.05
    trailing_stop: bool = True
    trailing_stop_positive: float = 0.01

    # Hook avanzati (opzionali, da Freqtrade)
    def custom_stoploss(self, current_price, trade) -> float: ...
    def custom_exit(self, current_price, trade) -> Optional[str]: ...
```

### 5.3 Protections → `signals/protections.py`

**Nuovo modulo** middleware tra signal generation e signal routing:

| Protection | Da | Descrizione |
|-----------|-----|-------------|
| CooldownPeriod | Freqtrade | Dopo un trade, attendi N candle prima di rientrare |
| MaxDrawdown | Freqtrade | Blocca trading se drawdown > X% in finestra temporale |
| StoplossGuard | Freqtrade | Dopo N stoploss consecutivi, pausa per M candle |
| LowProfitPairs | Freqtrade | Escludi coppie con profit < threshold |

Compatibilità: si inserisce tra `generator.py` e `signal_router.py` nella pipeline.

### 5.4 Algorithmic Execution → `mt5-bridge/algo_executor.py`

**Nuovo modulo** per esecuzione intelligente (da VnPy):

| Algo | Uso | Descrizione |
|------|-----|-------------|
| TWAP | Ordini large | Split ordine in N parti a intervalli regolari |
| Iceberg | Nascondere size | Mostra solo porzione dell'ordine |
| BestLimit | Ridurre slippage | Limit al best bid/ask, aggiorna ogni tick |

Compatibilità: si inserisce tra `order_manager.py` e `connector.py` nel MT5 Bridge.

### 5.5 Telegram Commands → `console/telegram_commands.py`

Espandere il Telegram bot da notifiche passive a comandi attivi (da Freqtrade):

| Comando | Azione |
|---------|--------|
| `/status` | Posizioni aperte con PnL real-time |
| `/profit` | Profit giornaliero/settimanale/totale |
| `/balance` | Balance MT5 |
| `/forceexit <id>` | Chiudi posizione specifica |
| `/performance` | Win rate per coppia |
| `/daily` | PnL ultimi 7 giorni |
| `/kill` | Attiva kill switch |
| `/resume` | Disattiva kill switch |
| `/mode <1-4>` | Cambia modo cascade |

### 5.6 Alpha Factors → `features/alpha_factors.py`

**Nuovo modulo** con fattori predittivi selezionati da VnPy Alpha 158:

| Categoria | Fattori | Count |
|-----------|---------|-------|
| Price ratios | open/close, high/low, close/vwap | 8 |
| Returns | ret_1d, ret_5d, ret_20d, ret_60d | 4 |
| Volatility | std_5d, std_20d, atr_14, bb_width | 4 |
| Momentum | roc_5, roc_20, rsi_14, macd_signal | 4 |
| Volume | vol_ratio_5_20, vwap_deviation, ad_line | 3 |
| Mean reversion | zscore_20, percentile_60 | 2 |

Totale: ~25 nuovi fattori → pipeline da 60-dim a ~85-dim.

Compatibilità: `METADATA_DIM` deve essere aggiornato da 60 a 85 in tutti i moduli che
lo referenziano (RAP Coach, JEPA, MarketVectorizer, etc.).

### 5.7 RL Agent → `nn/rl_agent.py`

**Nuovo modulo** ispirato a Stock-Prediction-Models Actor-Critic:

```python
class TradingRLAgent:
    """Actor-Critic agent per decisioni di trading.

    State:  feature vector (85-dim) + portfolio state
    Action: BUY / SELL / HOLD + size (continuous)
    Reward: risk-adjusted PnL (Sharpe-weighted)
    """
    def __init__(self, state_dim, action_dim, hidden_dim=256): ...
    def select_action(self, state) -> Action: ...
    def update(self, batch) -> dict: ...
```

Compatibilità: si inserisce come nuova strategia nel cascade (Mode 1 COPER) accanto a MLProxy.

---

## 6. Findings — Cosa NON Adottare

| # | Progetto/Pattern | Motivo Scarto |
|---|-----------------|---------------|
| 1 | **Gekko** intero | Archiviato 2018, Node.js, non mantenuto. Zero valore estraibile. |
| 2 | **Lean** intero | C#, richiede transpiling. Over-engineered per MONEYMAKER. |
| 3 | **Nautilus Rust core** | Troppo complesso da integrare. Solo i pattern di design sono utili. |
| 4 | Binance-bot cycle trading | Strategia troppo specifica (arbitraggio cross-coin). |
| 5 | Hummingbot Cython | Ottimizzazione prematura. MONEYMAKER non ha problemi di performance. |
| 6 | CCXT come exchange primario | MONEYMAKER usa MT5 per forex — CCXT è per crypto only. |
| 7 | VnPy cross-sectional features | MONEYMAKER fa single-asset trading, non portfolio. |
| 8 | TradingAgents OpenAI Gym | Research-grade, non production-ready. I pattern RL di Stock-Pred sono migliori. |
| 9 | ML-for-Trading notebooks | Educational — utile come reference ma non codice estraibile. |
| 10 | Hummingbot market-making | MONEYMAKER è directional trading, non market-making. |

---

## 7. Priorità di Implementazione

### Tier 1: Impatto Immediato (Settimana 1-2)

Queste integrazioni portano valore immediato al sistema MONEYMAKER attuale senza rompere nulla.

| # | Feature | Effort | Impatto |
|---|---------|--------|---------|
| 1 | Protections middleware (`signals/protections.py`) | 1 giorno | Riduce overtrade, migliora risk |
| 2 | Telegram comandi attivi | 2 giorni | Controllo manuale real-time |
| 3 | Strategy parametri dichiarativi | 2 ore | Configurabilità strategie |
| 4 | Bracket orders OCO su MT5 | 1 giorno | SL+TP atomici |

### Tier 2: Valore Strategico (Settimana 3-6)

Queste richiedono più effort ma trasformano il sistema.

| # | Feature | Effort | Impatto |
|---|---------|--------|---------|
| 5 | Backtesting engine | 3-5 giorni | Validazione strategie prima del live |
| 6 | Alpha 158 features (selezionate) | 2-3 giorni | Feature vector più ricco |
| 7 | TWAP/Iceberg execution | 2 giorni | Riduzione slippage ordini large |
| 8 | Hyperopt con Optuna | 3-5 giorni | Ottimizzazione automatica parametri |

### Tier 3: Evoluzione ML (Settimana 7+)

Queste richiedono il training ML funzionante (dipende da Report 04 findings).

| # | Feature | Effort | Impatto |
|---|---------|--------|---------|
| 9 | RL Agent (Actor-Critic) | 1 settimana | Decisioni autonome |
| 10 | FreqAI retraining on drift | 1 giorno (wiring) | Modello sempre aggiornato |
| 11 | Attention mechanisms | 3-5 giorni | Migliore feature importance |
| 12 | Ensemble voting | 2-3 giorni | Confidence boosting |

---

## 8. Istruzioni con Checkbox

### Segmento A: Protections Middleware

- [ ] Creare `program/services/algo-engine/src/algo_engine/signals/protections.py`
- [ ] Implementare `CooldownProtection`: blocca rientro su coppia per N candle dopo trade
- [ ] Implementare `MaxDrawdownProtection`: blocca trading se drawdown > X% in finestra
- [ ] Implementare `StoplossGuard`: pausa dopo N stoploss consecutivi
- [ ] Implementare `LowProfitFilter`: escludi coppie con profit storico negativo
- [ ] Integrare protections tra `generator.py` e `signal_router.py`
- [ ] Aggiungere config protections in `BrainSettings`
- [ ] Scrivere test per ogni protection (min 4 test ciascuna)

### Segmento B: Telegram Comandi Attivi

- [ ] Estendere `program/services/algo-engine/src/algo_engine/observability/telegram.py`
- [ ] Aggiungere handler per `/status` — posizioni aperte con PnL
- [ ] Aggiungere handler per `/profit` — profit giornaliero/settimanale
- [ ] Aggiungere handler per `/balance` — equity da portfolio.py
- [ ] Aggiungere handler per `/forceexit <pair>` — chiudi posizione via gRPC
- [ ] Aggiungere handler per `/kill` e `/resume` — kill switch toggle
- [ ] Aggiungere handler per `/mode <1-4>` — switch cascade mode
- [ ] Aggiungere handler per `/daily` — PnL ultimi 7 giorni
- [ ] Testare ogni comando con bot Telegram di test

### Segmento C: Strategy Enhancement

- [ ] Aggiungere `minimal_roi: dict` a `BaseStrategy` con default `{"0": 0.05}`
- [ ] Aggiungere `trailing_stop: bool` e `trailing_stop_positive: float`
- [ ] Aggiungere hook `custom_stoploss()` opzionale (default: return self.stoploss)
- [ ] Aggiungere hook `custom_exit()` opzionale (default: return None)
- [ ] Aggiungere hook `adjust_trade_position()` per DCA (default: no-op)
- [ ] Aggiornare TrendFollowing, MeanReversion, Defensive con parametri specifici
- [ ] Scrivere test per nuovi hook

### Segmento D: Backtesting Engine

- [ ] Creare directory `program/services/algo-engine/src/algo_engine/backtest/`
- [ ] Implementare `BacktestEngine` (pattern Cerebro da Backtrader)
- [ ] Implementare `DataFeed` che legge OHLCV da TimescaleDB
- [ ] Implementare `OrderSimulator` con fee (0.1%) e slippage (1 pip)
- [ ] Implementare `SharpeAnalyzer`, `CalmarAnalyzer`, `MaxDrawdownAnalyzer`
- [ ] Implementare `TradeAnalyzer` (win rate, avg PnL, profit factor)
- [ ] Implementare `ReportGenerator` (output JSON + console summary)
- [ ] Integrare con pipeline features esistente (pipeline.py → 60-dim vector)
- [ ] Integrare con strategie esistenti (TrendFollowing, MeanReversion)
- [ ] Aggiungere walk-forward validation (train/test split con rolling window)
- [ ] Scrivere test E2E: backtest su dati sintetici, verificare metriche
- [ ] Aggiungere comando console: `moneymaker backtest --strategy trend --period 6m`

### Segmento E: Algorithmic Execution

- [ ] Creare `program/services/mt5-bridge/src/mt5_bridge/algo_executor.py`
- [ ] Implementare `TwapExecutor`: split ordine in N parti a intervalli configurabili
- [ ] Implementare `IcebergExecutor`: mostra solo X% dell'ordine totale
- [ ] Implementare `BracketOrder`: SL + TP simultanei come OCO su MT5
- [ ] Integrare con `order_manager.py` — seleziona executor in base a size ordine
- [ ] Soglia: ordini > 0.05 lotti → TWAP automatico
- [ ] Scrivere test per ogni executor

### Segmento F: Alpha Factors

- [ ] Creare `program/services/algo-engine/src/algo_engine/features/alpha_factors.py`
- [ ] Implementare 25 fattori selezionati da Alpha 158 (vedi sezione 5.6)
- [ ] Aggiornare `pipeline.py` per includere alpha factors
- [ ] Aggiornare `METADATA_DIM` da 60 a 85 in tutto il codebase
- [ ] Aggiornare RAP Coach input dims (MarketPerception, etc.)
- [ ] Aggiornare JEPA input dims
- [ ] Aggiornare test di architettura (`test_architecture.py`)
- [ ] Verificare che pipeline completa funziona con 85-dim vector
- [ ] Documentare ogni nuovo fattore e la sua formula

### Segmento G: RL Agent

- [ ] Creare `program/services/algo-engine/src/algo_engine/nn/rl_agent.py`
- [ ] Implementare `ActorCriticAgent` con state=85-dim, action=3 (BUY/SELL/HOLD)
- [ ] Implementare reward function basata su Sharpe risk-adjusted
- [ ] Implementare replay buffer per experience replay
- [ ] Integrare come opzione in Mode 1 (COPER) del cascade
- [ ] Aggiungere config `rl_enabled: bool = False` in BrainSettings
- [ ] Scrivere test per forward pass e update

### Segmento H: Hyperopt

- [ ] Aggiungere `optuna` a requirements di ml-training
- [ ] Creare `program/services/ml-training/src/ml_training/hyperopt/`
- [ ] Implementare `HyperoptRunner` che ottimizza parametri strategia via backtesting
- [ ] Definire spazio di ricerca: stoploss, ROI, indicatori, soglie regime
- [ ] Implementare early stopping su Sharpe < threshold
- [ ] Salvare risultati migliori come JSON per deployment
- [ ] Scrivere test per hyperopt con parametri sintetici

---

## 9. Riepilogo

### Cosa Prendere da Ogni Progetto

| Progetto | Cosa Estrarre | Priorità |
|----------|--------------|----------|
| **Freqtrade** | IStrategy interface, Protections, Telegram comandi, Hyperopt | ALTA |
| **Backtrader** | Cerebro engine, Analyzers (Sharpe/Calmar/DrawDown) | ALTA |
| **VnPy** | Alpha 158 fattori, TWAP/Iceberg execution | MEDIA |
| **Stock-Prediction-Models** | Actor-Critic RL, Attention mechanisms, Ensemble voting | MEDIA |
| **CCXT** | Error handling patterns, rate limiting patterns | BASSA |
| **Hummingbot** | Event-driven patterns, multi-order management | BASSA |
| **FreqAI** | Retraining on drift (wiring del codice MONEYMAKER esistente) | MEDIA |
| **Nautilus** | OCO/bracket order patterns | BASSA |

### Cosa Scartare

| Progetto | Motivo |
|----------|--------|
| Gekko | Morto, Node.js |
| Lean | C#, over-engineered |
| Binance-bot strategy | Troppo specifico |
| TradingAgents | Research-grade |
| ML-for-Trading | Solo educational |

### Effort Totale Stimato

| Tier | Settimane | Giorni Lavoro |
|------|-----------|---------------|
| Tier 1 (immediato) | 1-2 | 4-5 giorni |
| Tier 2 (strategico) | 3-6 | 10-15 giorni |
| Tier 3 (ML evolution) | 7+ | 10-15 giorni |
| **TOTALE** | ~10 settimane | ~25-35 giorni |

Questo effort si somma al piano di produzione del Report 10 (~40-50 giorni).
L'integrazione dei pattern può avvenire in parallelo alle fasi 3-6 del piano di produzione.
