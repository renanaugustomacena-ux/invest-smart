# Database e Storage

| Campo         | Valore                                     |
|---------------|--------------------------------------------|
| **Titolo**    | Database e Storage                         |
| **Autore**    | Renan Augusto Macena                       |
| **Data**      | 2026-02-28                                 |
| **Versione**  | 1.0.0                                      |
| **Progetto**  | MONEYMAKER Trading Ecosystem                  |

---

## Indice

1. [Capitolo 1: Overview — L'Archivio di una Banca](#capitolo-1-overview--larchivio-di-una-banca)
2. [Capitolo 2: Diagramma ER — Entita' e Relazioni](#capitolo-2-diagramma-er--entita-e-relazioni)
3. [Capitolo 3: TimescaleDB — Architettura Hypertable](#capitolo-3-timescaledb--architettura-hypertable)
4. [Capitolo 4: Pipeline di Ingestione Dati](#capitolo-4-pipeline-di-ingestione-dati)
5. [Capitolo 5: Audit Log — Registro Immutabile](#capitolo-5-audit-log--registro-immutabile)
6. [Capitolo 6: Policy di Ritenzione Dati](#capitolo-6-policy-di-ritenzione-dati)
7. [Capitolo 7: Backup e Ripristino](#capitolo-7-backup-e-ripristino)
8. [Capitolo 8: Pattern di Query](#capitolo-8-pattern-di-query)

---

## Capitolo 1: Overview — L'Archivio di una Banca

### L'Analogia Fondamentale

Immaginate il sistema di archiviazione di una grande banca internazionale. Ogni documento che la banca gestisce ha uno scopo preciso, un formato rigoroso e una durata di conservazione definita per legge. Se un singolo documento viene perso, alterato o corrotto, le conseguenze possono essere catastrofiche: un bonifico smarrito, un saldo che non quadra, un'ispezione della banca centrale che trova irregolarita'. Allo stesso modo, il layer di storage del MONEYMAKER Trading Ecosystem rappresenta la memoria persistente e inviolabile dell'intero sistema di trading algoritmico.

Ogni tabella del database corrisponde a un tipo specifico di documento che la banca deve conservare:

- **`market_ticks`** sono le **ricevute delle transazioni**: ogni singola variazione di prezzo registrata dai mercati finanziari. Come una ricevuta bancaria che riporta data, ora, importo e causale, ogni tick contiene il simbolo, il timestamp con precisione al microsecondo, bid, ask, ultimo prezzo, volume e spread. Questi sono i dati grezzi, la materia prima da cui tutto il resto viene derivato.

- **`ohlcv_bars`** sono i **riepiloghi giornalieri**: candele aggregate che condensano migliaia di tick in un singolo record con prezzo di apertura, massimo, minimo, chiusura e volume. Come il rendiconto mensile che la banca invia al correntista, le barre OHLCV offrono una visione sintetica e navigabile di cio' che e' accaduto in un determinato intervallo temporale.

- **`trading_signals`** sono i **moduli d'ordine**: documenti che registrano la decisione presa dal motore algoritmico. Ogni segnale contiene la direzione (BUY, SELL, HOLD), il livello di confidenza, i lotti suggeriti, lo stop-loss e il take-profit. Come un modulo d'ordine compilato dal gestore patrimoniale prima di eseguire un'operazione, il segnale deve essere completo, tracciabile e immutabile.

- **`trade_executions`** sono le **transazioni eseguite**: il record che conferma l'effettiva esecuzione dell'ordine sul mercato. Contengono il prezzo richiesto, il prezzo effettivo di esecuzione, lo slippage in pips, il profitto o la perdita. Come la contabile bancaria che certifica un bonifico andato a buon fine, ogni execution registra esattamente cosa e' successo quando l'ordine ha colpito il mercato.

- **`audit_log`** e' il **registro del caveau a prova di manomissione**: un libro mastro in cui ogni voce e' concatenata crittograficamente alla precedente. Non puo' essere modificato ne' cancellato. Come il registro delle operazioni nel caveau di una banca, protetto da sigilli e catene hash, l'audit log garantisce l'integrita' totale della storia operativa del sistema.

### Perche' PostgreSQL con TimescaleDB

La scelta di PostgreSQL come motore di database primario non e' casuale. PostgreSQL offre conformita' ACID completa (Atomicita', Consistenza, Isolamento, Durabilita'), supporto nativo per JSON/JSONB, un ecosistema di estensioni maturo e una comunita' che ne garantisce la longevita'. TimescaleDB, costruito come estensione nativa di PostgreSQL, aggiunge capacita' specifiche per serie temporali senza sacrificare la compatibilita' SQL standard. Questa combinazione consente al MONEYMAKER di gestire sia dati relazionali tradizionali (modelli statistici, configurazioni, audit) sia flussi di dati temporali ad alta frequenza (tick, barre, predizioni) in un unico motore, eliminando la complessita' operativa di gestire database multipli.

### Principio Architetturale: Decimal Precision Everywhere

Un principio inviolabile del layer di storage e' la **precisione decimale assoluta**. Nel trading finanziario, un errore di arrotondamento di 0.00001 su un milione di transazioni puo' tradursi in migliaia di dollari di discrepanza. Per questo motivo, tutti i campi che rappresentano prezzi, volumi, profitti e lotti utilizzano il tipo `NUMERIC` di PostgreSQL (non `FLOAT` o `DOUBLE PRECISION`). Nel codice Go di ingestione, i valori vengono trattati come `json.Number` per evitare la conversione a floating-point IEEE 754. Nel codice Python, si utilizza il tipo `Decimal` del modulo standard library. Questa disciplina attraversa ogni layer dello stack, dal WebSocket al database.

```mermaid
graph TD
    subgraph "Analogia: Archivio Bancario"
        A["Ricevute Transazioni<br/><b>market_ticks</b>"]
        B["Riepiloghi Giornalieri<br/><b>ohlcv_bars</b>"]
        C["Moduli d'Ordine<br/><b>trading_signals</b>"]
        D["Transazioni Eseguite<br/><b>trade_executions</b>"]
        E["Registro del Caveau<br/><b>audit_log</b>"]
        F["Archivio Modelli<br/><b>model_registry</b>"]
        G["Cartelle Cliniche<br/><b>trade_records + experiences</b>"]
    end

    H["Mercato<br/>Exchange"] -->|"tick per tick"| A
    A -->|"aggregazione"| B
    B -->|"analisi algoritmica"| C
    C -->|"esecuzione MT5"| D
    D -->|"hash chain"| E
    C -->|"calibrazione"| F
    D -->|"apprendimento"| G

    style A fill:#4CAF50,color:white
    style B fill:#2196F3,color:white
    style C fill:#FF9800,color:white
    style D fill:#9C27B0,color:white
    style E fill:#F44336,color:white
    style F fill:#607D8B,color:white
    style G fill:#795548,color:white
```

---

## Capitolo 2: Diagramma ER — Entita' e Relazioni

### Visione d'Insieme dello Schema

Lo schema del database MONEYMAKER e' organizzato in tre macro-aree logiche: **dati di mercato** (market_ticks, ohlcv_bars), **pipeline di trading** (trading_signals, trade_executions, trade_records, strategy_performance) e **infrastruttura statistica** (model_registry, model_metrics, ml_predictions, model_checkpoints, feature_drift_logs, performance_snapshots). A queste si aggiungono le tabelle di **conoscenza e grafo** (strategy_knowledge, trade_experiences, market_graph_entities, market_graph_relations) e il **registro di audit** (audit_log).

Le relazioni tra le tabelle seguono un modello prevalentemente gerarchico: i segnali di trading generano esecuzioni, le esecuzioni generano record di trade, i record di trade alimentano le esperienze di apprendimento. I modelli statistici producono predizioni e metriche. Il grafo di mercato collega entita' (simboli, regimi, strategie) attraverso relazioni pesate che il sistema utilizza per il ragionamento contestuale.

### Diagramma Entita'-Relazione Completo

```mermaid
erDiagram
    ohlcv_bars {
        TEXT symbol
        TEXT timeframe
        TIMESTAMPTZ time
        NUMERIC open
        NUMERIC high
        NUMERIC low
        NUMERIC close
        NUMERIC volume
        INTEGER tick_count
    }

    market_ticks {
        TEXT symbol
        TIMESTAMPTZ time
        NUMERIC bid
        NUMERIC ask
        NUMERIC last_price
        NUMERIC volume
        NUMERIC spread
        TEXT source
    }

    trading_signals {
        UUID signal_id PK
        TEXT symbol
        TEXT direction
        NUMERIC confidence
        NUMERIC suggested_lots
        NUMERIC stop_loss
        NUMERIC take_profit
        TEXT model_version
        TEXT regime
        TEXT source_tier
    }

    trade_executions {
        UUID order_id PK
        UUID signal_id FK
        TEXT symbol
        TEXT direction
        NUMERIC requested_price
        NUMERIC executed_price
        NUMERIC quantity
        TEXT status
        NUMERIC slippage_pips
        NUMERIC profit
    }

    audit_log {
        BIGSERIAL id PK
        TEXT service
        TEXT action
        TEXT entity_type
        TEXT entity_id
        JSONB details
        TEXT prev_hash
        TEXT hash
    }

    model_registry {
        TEXT model_name PK
        TEXT version PK
        TEXT model_type
        TEXT checkpoint_path
        BOOLEAN is_active
        INTEGER training_samples
        NUMERIC validation_accuracy
    }

    model_metrics {
        INTEGER model_id FK
        TEXT metric_name
        NUMERIC metric_value
    }

    ml_predictions {
        UUID prediction_id PK
        TEXT symbol
        TEXT model_name
        TEXT model_version
        TEXT direction
        NUMERIC confidence
    }

    strategy_performance {
        UUID signal_id PK
        TEXT strategy_name
        TEXT symbol
        TEXT direction
        NUMERIC entry_price
        NUMERIC exit_price
        NUMERIC profit
    }

    trade_records {
        UUID signal_id PK
        TEXT symbol
        TEXT timeframe
        TEXT direction
        NUMERIC lots
        NUMERIC entry_price
        NUMERIC exit_price
        NUMERIC stop_loss
        NUMERIC take_profit
        TEXT outcome
        NUMERIC pnl
        TEXT regime
        NUMERIC confidence
    }

    trade_experiences {
        INTEGER trade_id FK
        TEXT context_hash
        TEXT symbol
        TEXT regime
        TEXT embedding_json
        TEXT outcome
        NUMERIC effectiveness_score
    }

    strategy_knowledge {
        TEXT content_hash PK
        TEXT category
        TEXT title
        TEXT content
        TEXT embedding_json
        NUMERIC effectiveness_score
    }

    market_graph_entities {
        SERIAL id PK
        TEXT entity_type
        TEXT entity_name
        JSONB properties_json
    }

    market_graph_relations {
        SERIAL id PK
        INTEGER source_entity_id FK
        TEXT relation_type
        INTEGER target_entity_id FK
        NUMERIC weight
    }

    model_checkpoints {
        TEXT checkpoint_hash PK
        TEXT file_path
        BIGINT file_size_bytes
        NUMERIC val_loss
        BOOLEAN is_active
        TEXT tier
    }

    feature_drift_logs {
        SERIAL id PK
        TEXT feature_name
        NUMERIC z_score
        NUMERIC baseline_mean
        NUMERIC current_value
        BOOLEAN is_drifted
    }

    performance_snapshots {
        SERIAL id PK
        TEXT period_type
        TEXT symbol
        INTEGER total_trades
        NUMERIC win_rate
        NUMERIC avg_pnl
        NUMERIC sharpe_ratio
        NUMERIC max_drawdown
    }

    trading_signals ||--o{ trade_executions : "signal_id"
    trade_records ||--o{ trade_experiences : "trade_id"
    model_registry ||--o{ model_metrics : "model_id"
    market_graph_entities ||--o{ market_graph_relations : "source_entity_id"
    market_graph_entities ||--o{ market_graph_relations : "target_entity_id"
```

### Descrizione Dettagliata delle Tabelle

**Tabelle Dati di Mercato:**

La tabella `ohlcv_bars` memorizza le candele aggregate per ogni combinazione di simbolo e timeframe. La chiave composita `(symbol, timeframe, time)` garantisce unicita'. Il campo `tick_count` registra quanti tick grezzi sono stati aggregati nella candela, fornendo una misura indiretta della liquidita' in quel periodo. Questa tabella e' una hypertable TimescaleDB partizionata per tempo con chunk da 1 giorno.

La tabella `market_ticks` e' la piu' voluminosa dell'intero sistema. Ogni tick rappresenta una singola quotazione ricevuta dal mercato. Il campo `source` identifica l'exchange o il provider di dati che ha originato il tick, consentendo di tracciare e confrontare la qualita' dei dati tra fonti diverse. Anche questa e' una hypertable, partizionata con chunk da 1 ora per gestire l'altissimo volume di inserimenti.

**Tabelle Pipeline di Trading:**

La tabella `trading_signals` registra ogni decisione presa dal motore algoritmico. Il campo `source_tier` indica quale livello del sistema di fallback a 4 tier ha generato il segnale (STATISTICAL_PRIMARY, STATISTICAL_FALLBACK, TECHNICAL, SAFE_DEFAULT). Il campo `regime` registra il regime di mercato identificato al momento della generazione del segnale. Questa informazione e' fondamentale per l'analisi post-hoc delle performance per regime.

La tabella `trade_executions` e' collegata a `trading_signals` tramite `signal_id`. Registra l'esito effettivo dell'esecuzione: prezzo richiesto vs prezzo effettivo, slippage, status dell'ordine (FILLED, PARTIALLY_FILLED, REJECTED, EXPIRED) e profitto risultante. La differenza tra `requested_price` e `executed_price` alimenta direttamente le metriche di qualita' dell'esecuzione.

**Tabelle Infrastruttura Statistica:**

La tabella `model_registry` funge da catalogo centrale di tutti i modelli calibrati. Ogni modello e' identificato dalla coppia `(model_name, version)`. Il campo `is_active` indica quale versione e' attualmente in produzione. I campi `training_samples` e `validation_accuracy` forniscono metriche di qualita' del modello al momento del training.

La tabella `model_metrics` estende il registry con metriche arbitrarie per ogni modello. Questo schema flessibile consente di registrare metriche diverse per modelli diversi senza alterare lo schema della tabella.

La tabella `ml_predictions` memorizza ogni predizione generata dai modelli statistici in produzione. Questa tabella e' una hypertable TimescaleDB con chunk da 1 giorno e compressione attivata dopo 7 giorni.

**Tabelle SQLModel (Algo Engine):**

La tabella `trade_records` e' il cuore della memoria operativa del brain. Ogni record contiene tutti i dettagli di un'operazione: simbolo, timeframe, direzione, lotti (tipo `Decimal` per precisione assoluta), prezzi di entrata e uscita, stop-loss, take-profit, esito (WIN, LOSS, BREAKEVEN), P&L, regime di mercato e livello di confidenza. Questa tabella alimenta il ciclo di apprendimento continuo del sistema.

La tabella `trade_experiences` estende ogni trade record con un contesto vettoriale. Il campo `embedding_json` contiene la rappresentazione vettoriale del contesto di mercato al momento del trade, consentendo al sistema di ricercare esperienze simili per analogia. Il campo `effectiveness_score` misura quanto l'esperienza e' stata utile per migliorare le decisioni future.

La tabella `strategy_knowledge` memorizza la conoscenza esplicita acquisita dal sistema sotto forma di testi categorizzati con embedding vettoriali. Ogni voce e' identificata da un `content_hash` che previene duplicati. Le categorie includono regole di trading, osservazioni di mercato, lezioni apprese e pattern ricorrenti.

Le tabelle `market_graph_entities` e `market_graph_relations` implementano un grafo di conoscenza relazionale. Le entita' possono essere simboli, regimi, strategie o concetti di mercato. Le relazioni pesate tra entita' (CORRELATES_WITH, BELONGS_TO_REGIME, PERFORMS_WELL_IN) consentono al brain di ragionare sulle interdipendenze tra asset e condizioni di mercato.

La tabella `model_checkpoints` tiene traccia di tutti i checkpoint salvati durante il training, con hash crittografico per verificare l'integrita', dimensione del file, loss di validazione e flag di attivazione. Il campo `tier` indica il livello di qualita' del checkpoint.

La tabella `feature_drift_logs` registra le deviazioni delle feature rispetto alla baseline. Quando il z-score di una feature supera la soglia configurata, il flag `is_drifted` viene impostato a `true`, attivando alert di monitoraggio.

La tabella `performance_snapshots` memorizza fotografie periodiche delle performance del sistema, suddivise per tipo di periodo (DAILY, WEEKLY, MONTHLY), simbolo, con metriche aggregate: numero di trades, win rate, P&L medio, Sharpe ratio e maximum drawdown.

---

## Capitolo 3: TimescaleDB — Architettura Hypertable

### Cos'e' una Hypertable

Una hypertable di TimescaleDB e' un'astrazione che trasforma una tabella PostgreSQL ordinaria in una struttura partizionata automaticamente per tempo. Dall'esterno, l'utente interagisce con una singola tabella; internamente, TimescaleDB suddivide automaticamente i dati in "chunk" temporali, ciascuno dei quali e' una partizione fisica indipendente. Questo approccio offre tre vantaggi fondamentali: (1) le query con filtri temporali accedono solo ai chunk rilevanti, riducendo drasticamente i tempi di scansione; (2) le operazioni di manutenzione (VACUUM, compressione, eliminazione) possono essere eseguite su singoli chunk senza bloccare l'intera tabella; (3) l'inserimento ad alta frequenza non soffre di contention perche' i nuovi dati vanno sempre nell'ultimo chunk attivo.

### Configurazione delle Hypertable nel MONEYMAKER

Il MONEYMAKER utilizza quattro hypertable con parametri di partizionamento specificamente calibrati per il profilo di carico di ciascuna tabella:

**`ohlcv_bars`** — Chunk da 1 giorno. Le barre OHLCV vengono generate dall'aggregatore in tempo reale e inserite in batch. Il volume e' moderato (circa 1 barra per simbolo per timeframe per periodo), ma le query di range temporale sono frequentissime durante il backtesting e l'analisi. Chunk giornalieri offrono il miglior compromesso tra granularita' e numero totale di chunk da gestire.

```sql
SELECT create_hypertable('ohlcv_bars', 'time',
    chunk_time_interval => INTERVAL '1 day');
```

**`market_ticks`** — Chunk da 1 ora. I tick di mercato arrivano ad altissima frequenza (potenzialmente migliaia al secondo durante sessioni volatili). Chunk orari mantengono ogni singola partizione a dimensioni gestibili per VACUUM e compressione, permettendo al contempo query efficienti su finestre temporali brevi.

```sql
SELECT create_hypertable('market_ticks', 'time',
    chunk_time_interval => INTERVAL '1 hour');
```

**`ml_predictions`** — Chunk da 1 giorno, con compressione automatica dopo 7 giorni. Le predizioni statistiche vengono generate a frequenza inferiore rispetto ai tick, ma devono essere conservate per l'analisi della calibrazione del modello. La compressione dopo 7 giorni riduce lo spazio su disco dell'80-90% senza impatto sulle query analitiche.

```sql
SELECT create_hypertable('ml_predictions', 'time',
    chunk_time_interval => INTERVAL '1 day');

ALTER TABLE ml_predictions SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,model_name',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('ml_predictions', INTERVAL '7 days');
```

**`strategy_performance`** — Chunk da 1 giorno, con compressione automatica dopo 30 giorni. Le performance delle strategie vengono scritte con frequenza relativamente bassa ma lette frequentemente nelle dashboard e nei report. La compressione dopo 30 giorni consente accesso veloce ai dati recenti e archiviazione efficiente dei dati storici.

```sql
SELECT create_hypertable('strategy_performance', 'time',
    chunk_time_interval => INTERVAL '1 day');

ALTER TABLE strategy_performance SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'strategy_name,symbol',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('strategy_performance', INTERVAL '30 days');
```

### Aggregati Continui

TimescaleDB supporta gli aggregati continui (continuous aggregates), viste materializzate che vengono aggiornate automaticamente quando nuovi dati vengono inseriti. Il MONEYMAKER utilizza un aggregato continuo per il riepilogo giornaliero delle strategie:

```sql
CREATE MATERIALIZED VIEW strategy_daily_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    strategy_name,
    symbol,
    COUNT(*) AS total_trades,
    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) AS winning_trades,
    SUM(profit) AS total_profit,
    AVG(profit) AS avg_profit,
    MAX(profit) AS max_profit,
    MIN(profit) AS min_profit
FROM strategy_performance
GROUP BY bucket, strategy_name, symbol;

SELECT add_continuous_aggregate_policy('strategy_daily_summary',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

Questo aggregato viene aggiornato ogni ora, coprendo i dati fino a 1 ora prima del momento corrente e ricalcolando i bucket degli ultimi 3 giorni per catturare eventuali dati arrivati in ritardo.

```mermaid
graph TB
    subgraph "Architettura Hypertable"
        direction TB
        T["Tabella Regolare PostgreSQL"]
        H["CREATE hypertable(...)"]
        T -->|"trasformazione"| H

        subgraph "ohlcv_bars — chunk 1 giorno"
            OC1["Chunk 2026-02-26"]
            OC2["Chunk 2026-02-27"]
            OC3["Chunk 2026-02-28<br/>(attivo)"]
        end

        subgraph "market_ticks — chunk 1 ora"
            MC1["Chunk 08:00-09:00"]
            MC2["Chunk 09:00-10:00"]
            MC3["Chunk 10:00-11:00<br/>(attivo)"]
        end

        subgraph "ml_predictions — chunk 1 giorno"
            PC1["Chunk 2026-02-21<br/>(compresso)"]
            PC2["Chunk 2026-02-27"]
            PC3["Chunk 2026-02-28<br/>(attivo)"]
        end

        subgraph "strategy_performance — chunk 1 giorno"
            SC1["Chunk 2026-01-28<br/>(compresso)"]
            SC2["Chunk 2026-02-27"]
            SC3["Chunk 2026-02-28<br/>(attivo)"]
        end

        H --> OC1
        H --> MC1
        H --> PC1
        H --> SC1
    end

    subgraph "Aggregato Continuo"
        CA["strategy_daily_summary<br/>aggiornamento: ogni 1 ora"]
        SC3 -->|"materializzazione"| CA
    end

    style OC3 fill:#4CAF50,color:white
    style MC3 fill:#4CAF50,color:white
    style PC3 fill:#4CAF50,color:white
    style SC3 fill:#4CAF50,color:white
    style PC1 fill:#9E9E9E,color:white
    style SC1 fill:#9E9E9E,color:white
    style CA fill:#FF9800,color:white
```

---

## Capitolo 4: Pipeline di Ingestione Dati

### Architettura End-to-End

La pipeline di ingestione dati del MONEYMAKER e' progettata per trasportare quotazioni di mercato dal WebSocket dell'exchange fino al database TimescaleDB con latenza minima e precisione decimale preservata a ogni passaggio. La pipeline segue un'architettura a due rami paralleli: un ramo pubblica i dati aggregati via ZMQ per il consumo in tempo reale, l'altro persiste i dati grezzi nel database per analisi storica.

Il componente di ingestione e' scritto in Go 1.22 per massimizzare il throughput e minimizzare le allocazioni di memoria. Go e' stato scelto rispetto a Python per questa componente critica perche' offre: (1) goroutine per concorrenza leggera senza l'overhead dei thread OS; (2) il garbage collector ottimizzato per latenza di Go e' ideale per workload di streaming; (3) il type system statico previene intere classi di errori a runtime.

### Flusso dei Dati

Il flusso inizia con la connessione WebSocket all'exchange. Il **Connector** gestisce la connessione, il reconnect automatico e il parsing dei messaggi grezzi. Ogni messaggio viene deserializzato in un `RawMessage` che preserva i valori numerici come `json.Number` — una stringa che rappresenta il numero esatto senza conversione a float64. Questa scelta e' critica: un prezzo come `1.23456` verrebbe troncato silenziosamente a `1.2345600000000001` in float64, una discrepanza invisibile ma cumulativa.

Il **Normalizer** trasforma il `RawMessage` in un `NormalizedTick`, applicando validazioni (spread non negativo, volume non negativo, timestamp monotonicamente crescente) e mappando i nomi dei campi dal formato specifico dell'exchange al formato canonico del MONEYMAKER. Il normalizer opera come un adapter pattern che consente di supportare exchange multipli con formati diversi dietro un'interfaccia uniforme.

Da qui i dati si biforcano in due percorsi paralleli:

**Percorso 1 — Aggregazione e Pubblicazione ZMQ:** L'**Aggregator** accumula tick in candele OHLCV per ogni combinazione di simbolo e timeframe. Quando una candela e' completa (il timestamp del nuovo tick supera la fine della finestra temporale corrente), la barra viene finalizzata e inviata al **ZMQ Publisher** che la trasmette su `tcp://*:5555`. I consumer (Algo Engine, dashboard) ricevono le barre in tempo reale via sottoscrizione ZMQ. Il protocollo ZMQ e' stato scelto per la sua bassissima latenza e il pattern pub/sub che consente consumer multipli senza overhead sul publisher.

**Percorso 2 — Persistenza nel Database:** Il **DBWriter** riceve i tick normalizzati e li accumula in un **Ring Buffer** in memoria. Il buffer ha una capacita' configurabile (default: 10.000 tick o 5 secondi, qualunque condizione si verifichi prima). Quando il buffer si riempie o il timer scade, il **Batch Worker** scarica il buffer e utilizza il comando `COPY FROM STDIN` di PostgreSQL per inserire tutti i tick in un'unica operazione. `COPY` e' ordini di grandezza piu' veloce di `INSERT` multipli perche' bypassa il parser SQL, il planner e la transazione per riga. Per 10.000 tick, un `COPY` completa in 10-50ms contro i 2-5 secondi di 10.000 `INSERT` individuali.

La precisione decimale e' preservata a ogni passaggio della catena: `json.Number` nel parsing Go, tipo `NUMERIC` nella definizione della tabella PostgreSQL, formato testo nel protocollo `COPY`. Nessun valore viene mai convertito a floating-point IEEE 754.

```mermaid
sequenceDiagram
    participant EX as Exchange
    participant WS as WebSocket
    participant CO as Connector
    participant RM as RawMessage
    participant NO as Normalizer
    participant NT as NormalizedTick
    participant AG as Aggregator
    participant ZQ as ZMQ Publisher<br/>tcp://*:5555
    participant DW as DBWriter
    participant RB as Ring Buffer
    participant BW as Batch Worker
    participant PG as TimescaleDB

    EX->>WS: Quotazione JSON
    WS->>CO: Frame binario
    CO->>RM: json.Number<br/>(no float64)
    RM->>NO: RawMessage
    NO->>NT: NormalizedTick<br/>validato

    par Percorso 1: Real-Time
        NT->>AG: tick
        AG->>AG: Accumula OHLCV
        AG->>ZQ: Bar completa
        Note over ZQ: Consumer Algo Engine,<br/>Dashboard
    and Percorso 2: Persistenza
        NT->>DW: tick
        DW->>RB: Append
        RB->>BW: Buffer pieno<br/>o timer scaduto
        BW->>PG: COPY FROM STDIN<br/>(batch 10K righe)
        Note over PG: NUMERIC type<br/>precisione preservata
    end
```

### Garanzia di Precisione Decimale

La catena di custodia della precisione decimale attraversa cinque strati:

1. **WebSocket** — Il messaggio JSON contiene il prezzo come stringa letterale: `"price": "1.23456"`
2. **Go Parsing** — `json.Decoder` con `UseNumber()` produce `json.Number("1.23456")`, nessuna conversione
3. **Normalizer** — Il valore rimane stringa fino alla costruzione del buffer COPY
4. **COPY Protocol** — Il valore viene scritto come testo nel formato TSV del protocollo COPY
5. **PostgreSQL** — La colonna `NUMERIC` memorizza il valore con precisione arbitraria

---

## Capitolo 5: Audit Log — Registro Immutabile

### Principio di Immutabilita'

L'audit log del MONEYMAKER implementa un registro append-only con hash chain crittografica. Ogni voce del registro contiene l'hash SHA-256 della voce precedente, creando una catena in cui la modifica di qualsiasi voce passata invalida tutte le voci successive. Questo meccanismo e' ispirato alla struttura dei blockchain ma implementato in modo piu' semplice ed efficiente all'interno di PostgreSQL.

L'immutabilita' e' garantita da due meccanismi complementari:

1. **Hash chain crittografica** — Ogni voce calcola il proprio hash come `SHA256(prev_hash + action + details)`. Per verificare l'integrita' dell'intera catena, basta ricalcolare gli hash in sequenza e confrontarli con quelli memorizzati.

2. **Trigger PostgreSQL** — Un trigger `BEFORE UPDATE OR DELETE` sulla tabella `audit_log` blocca qualsiasi tentativo di modifica o cancellazione, restituendo un errore esplicito. Questo previene manomissioni anche da parte di utenti con privilegi di superutente (a meno che non disabilitino esplicitamente i trigger, operazione che viene essa stessa loggata nei log di PostgreSQL).

### Struttura della Voce di Audit

Ogni voce dell'audit log contiene:

- **`service`** — Il microservizio che ha generato l'evento (algo-engine, data-ingestion, mt5-bridge, console)
- **`action`** — L'azione eseguita (SIGNAL_GENERATED, ORDER_SUBMITTED, ORDER_FILLED, MODEL_ACTIVATED, CONFIG_CHANGED, KILL_SWITCH_ACTIVATED)
- **`entity_type`** — Il tipo di entita' coinvolta (signal, order, model, config, system)
- **`entity_id`** — L'identificativo dell'entita' specifica (UUID del segnale, ID dell'ordine, nome del modello)
- **`details`** — Un campo JSONB contenente tutti i dettagli dell'evento in formato strutturato
- **`prev_hash`** — L'hash SHA-256 della voce precedente nella catena
- **`hash`** — L'hash SHA-256 calcolato come `SHA256(prev_hash || action || details::text)`

### Trigger di Protezione

```sql
CREATE OR REPLACE FUNCTION audit_log_protect()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log e'' immutabile: UPDATE e DELETE non sono consentiti';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW
    EXECUTE FUNCTION audit_log_protect();
```

### Funzione di Inserimento con Hash Chain

```sql
CREATE OR REPLACE FUNCTION audit_log_insert(
    p_service TEXT,
    p_action TEXT,
    p_entity_type TEXT,
    p_entity_id TEXT,
    p_details JSONB
) RETURNS VOID AS $$
DECLARE
    v_prev_hash TEXT;
    v_new_hash TEXT;
BEGIN
    SELECT hash INTO v_prev_hash
    FROM audit_log
    ORDER BY id DESC
    LIMIT 1;

    IF v_prev_hash IS NULL THEN
        v_prev_hash := 'GENESIS';
    END IF;

    v_new_hash := encode(
        sha256((v_prev_hash || p_action || p_details::text)::bytea),
        'hex'
    );

    INSERT INTO audit_log (service, action, entity_type, entity_id, details, prev_hash, hash)
    VALUES (p_service, p_action, p_entity_type, p_entity_id, p_details, v_prev_hash, v_new_hash);
END;
$$ LANGUAGE plpgsql;
```

```mermaid
graph LR
    subgraph "Hash Chain — Audit Log"
        G["GENESIS<br/>prev_hash: null<br/>hash: abc123..."]
        E1["Entry #1<br/>SIGNAL_GENERATED<br/>prev_hash: GENESIS<br/>hash: SHA256(GENESIS + action + details)<br/>= def456..."]
        E2["Entry #2<br/>ORDER_SUBMITTED<br/>prev_hash: def456...<br/>hash: SHA256(def456 + action + details)<br/>= ghi789..."]
        E3["Entry #3<br/>ORDER_FILLED<br/>prev_hash: ghi789...<br/>hash: SHA256(ghi789 + action + details)<br/>= jkl012..."]
        E4["Entry #4<br/>MODEL_ACTIVATED<br/>prev_hash: jkl012...<br/>hash: SHA256(jkl012 + action + details)<br/>= mno345..."]
    end

    G -->|"hash chain"| E1
    E1 -->|"hash chain"| E2
    E2 -->|"hash chain"| E3
    E3 -->|"hash chain"| E4

    T["TRIGGER<br/>BEFORE UPDATE/DELETE<br/>RAISE EXCEPTION"]
    T -.->|"protegge"| G
    T -.->|"protegge"| E1
    T -.->|"protegge"| E2
    T -.->|"protegge"| E3
    T -.->|"protegge"| E4

    style G fill:#4CAF50,color:white
    style E1 fill:#2196F3,color:white
    style E2 fill:#2196F3,color:white
    style E3 fill:#2196F3,color:white
    style E4 fill:#2196F3,color:white
    style T fill:#F44336,color:white
```

### Verifica dell'Integrita'

La verifica della catena puo' essere eseguita con una singola query ricorsiva:

```sql
WITH RECURSIVE chain AS (
    SELECT id, prev_hash, hash, action, details,
           encode(sha256((prev_hash || action || details::text)::bytea), 'hex') AS computed_hash
    FROM audit_log
    WHERE id = 1
    UNION ALL
    SELECT a.id, a.prev_hash, a.hash, a.action, a.details,
           encode(sha256((a.prev_hash || a.action || a.details::text)::bytea), 'hex')
    FROM audit_log a
    JOIN chain c ON a.id = c.id + 1
)
SELECT id, hash = computed_hash AS valid
FROM chain
WHERE hash != computed_hash;
```

Se la query restituisce righe, la catena e' compromessa e le voci con `valid = false` indicano il punto di manomissione.

---

## Capitolo 6: Policy di Ritenzione Dati

### Filosofia di Ritenzione

Il MONEYMAKER adotta una strategia di ritenzione differenziata basata sulla criticita' e sul valore analitico dei dati nel tempo. I dati di trading operativo (trade_records) vengono conservati per 2 anni completi per supportare analisi di backtesting a lungo termine e audit normativi. I dati di diagnostica statistica (feature_drift_logs) hanno una vita utile piu' breve di 90 giorni perche' i pattern di drift sono rilevanti solo nel contesto del modello corrente. Le policy sono implementate sia come configurazione di compressione TimescaleDB sia come job di pruning eseguibili dalla console.

### Tabella delle Policy

```mermaid
graph TD
    subgraph "Policy di Ritenzione"
        TR["trade_records<br/>730 giorni (2 anni)<br/>Alta criticita'"]
        TE["trade_experiences<br/>365 giorni (1 anno)<br/>Media criticita'"]
        FD["feature_drift_logs<br/>90 giorni<br/>Bassa criticita'"]
        PS["performance_snapshots<br/>365 giorni (1 anno)<br/>Media criticita'"]
        MT["market_ticks<br/>Compresso dopo 1 giorno<br/>Purge da policy"]
        OB["ohlcv_bars<br/>Compresso dopo 7 giorni<br/>Conservazione a lungo termine"]
        ML["ml_predictions<br/>Compresso dopo 7 giorni<br/>Policy di purge"]
        SP["strategy_performance<br/>Compresso dopo 30 giorni<br/>Policy di purge"]
    end

    CMD1["Console: maint retention<br/>(visualizza policy)"]
    CMD2["Console: maint prune-old DAYS<br/>(esegue pruning)"]

    CMD1 -->|"legge"| TR
    CMD1 -->|"legge"| TE
    CMD1 -->|"legge"| FD
    CMD1 -->|"legge"| PS
    CMD2 -->|"elimina dati vecchi"| FD
    CMD2 -->|"elimina dati vecchi"| PS

    style TR fill:#F44336,color:white
    style TE fill:#FF9800,color:white
    style FD fill:#4CAF50,color:white
    style PS fill:#FF9800,color:white
    style MT fill:#9E9E9E,color:white
    style OB fill:#2196F3,color:white
    style ML fill:#9E9E9E,color:white
    style SP fill:#9E9E9E,color:white
```

| Tabella | Ritenzione | Compressione | Note |
|---------|-----------|-------------|------|
| `trade_records` | 730 giorni (2 anni) | N/A | Dati operativi critici, necessari per backtesting e audit |
| `trade_experiences` | 365 giorni (1 anno) | N/A | Contesto vettoriale per apprendimento, meno critico dopo ricalibrazione |
| `feature_drift_logs` | 90 giorni | N/A | Rilevante solo per il modello corrente |
| `performance_snapshots` | 365 giorni (1 anno) | N/A | Report periodici, utili per trend annuali |
| `market_ticks` | Variabile (per policy) | Dopo 1 giorno | Volume altissimo, compressione aggressiva |
| `ohlcv_bars` | Lungo termine | Dopo 7 giorni | Volume moderato, valore analitico permanente |
| `ml_predictions` | Variabile (per policy) | Dopo 7 giorni | Utili per calibrazione modello |
| `strategy_performance` | Variabile (per policy) | Dopo 30 giorni | Feed per aggregato continuo |

### Comandi Console

Il comando `maint retention` mostra le policy di ritenzione attive:

```
MONEYMAKER> maint retention
Policy di ritenzione:
  trade_records:          730 giorni (2 anni)
  trade_experiences:      365 giorni (1 anno)
  feature_drift_logs:      90 giorni
  performance_snapshots:  365 giorni (1 anno)
```

Il comando `maint prune-old DAYS` esegue il pruning effettivo dei dati piu' vecchi del numero di giorni specificato. Questo comando richiede conferma interattiva per prevenire eliminazioni accidentali:

```
MONEYMAKER> maint prune-old 90
ATTENZIONE: Eliminare dati piu' vecchi di 90 giorni? [y/N] y
[success] Pruning completato: 1,247 drift log, 89 snapshot rimossi
```

### Compressione TimescaleDB

Le policy di compressione TimescaleDB vengono configurate al momento della creazione delle hypertable e operano automaticamente in background. La compressione di TimescaleDB utilizza algoritmi column-oriented che raggiungono tipicamente rapporti di compressione 10:1 - 20:1 per dati di serie temporali. I chunk compressi rimangono interrogabili con query SQL standard, sebbene con tempi di accesso leggermente superiori per query punto rispetto ai chunk non compressi.

---

## Capitolo 7: Backup e Ripristino

### Strategia di Backup

Il MONEYMAKER implementa una strategia di backup basata su `pg_dump` con compressione gzip. Il backup viene eseguito tramite il comando console `maint backup`, che produce un file SQL compresso contenente l'intero schema e tutti i dati del database. Il file viene salvato nella directory dei log della console con un nome che include il timestamp esatto del backup.

### Procedura di Backup

Il comando `maint backup` esegue internamente:

```bash
pg_dump --clean --if-exists \
  -d postgresql://moneymaker:moneymaker@localhost:5432/moneymaker_brain \
  | gzip > program/services/console/logs/moneymaker_backup_YYYYMMDD_HHMMSS.sql.gz
```

L'opzione `--clean` include istruzioni `DROP` prima di ogni `CREATE`, consentendo di sovrascrivere un database esistente durante il ripristino. L'opzione `--if-exists` aggiunge `IF EXISTS` alle istruzioni `DROP` per evitare errori se le tabelle non esistono nel database di destinazione.

Il file di backup risultante si trova in:
```
program/services/console/logs/moneymaker_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Procedura di Ripristino

Il ripristino richiede due passaggi manuali:

1. **Decompressione**: `gunzip moneymaker_backup_20260228_143000.sql.gz`
2. **Esecuzione**: `psql -d moneymaker_brain < moneymaker_backup_20260228_143000.sql`

### Backup Specifici per TimescaleDB

Per backup che preservano correttamente le hypertable, i chunk e le policy di compressione, e' necessario utilizzare il tool `timescaledb-backup` che comprende la struttura interna delle hypertable:

```bash
# Backup con timescaledb-backup
pg_dump --format=directory --jobs=4 \
  -d postgresql://moneymaker:moneymaker@localhost:5432/moneymaker_brain \
  -f /backup/moneymaker_full

# Restore con timescaledb-restore
pg_restore --format=directory --jobs=4 \
  --clean --if-exists \
  -d postgresql://moneymaker:moneymaker@localhost:5432/moneymaker_brain \
  /backup/moneymaker_full
```

Il formato directory con job paralleli e' significativamente piu' veloce per database di grandi dimensioni perche' dumpa e ripristina tabelle multiple contemporaneamente.

```mermaid
graph TD
    subgraph "Backup"
        DB["PostgreSQL/TimescaleDB<br/>moneymaker_brain"]
        PGD["pg_dump --clean --if-exists"]
        GZ["gzip"]
        FILE["moneymaker_backup_YYYYMMDD_HHMMSS.sql.gz<br/>program/services/console/logs/"]

        DB -->|"dump SQL"| PGD
        PGD -->|"stream"| GZ
        GZ -->|"file compresso"| FILE
    end

    subgraph "Ripristino"
        FILE2["moneymaker_backup_YYYYMMDD_HHMMSS.sql.gz"]
        GUNZ["gunzip"]
        SQL["moneymaker_backup_YYYYMMDD_HHMMSS.sql"]
        PSQL["psql -d moneymaker_brain"]
        DB2["PostgreSQL/TimescaleDB<br/>moneymaker_brain (ripristinato)"]

        FILE2 -->|"decompressione"| GUNZ
        GUNZ -->|"file SQL"| SQL
        SQL -->|"esecuzione"| PSQL
        PSQL -->|"ripristino"| DB2
    end

    subgraph "Backup TimescaleDB-Aware"
        DB3["PostgreSQL/TimescaleDB"]
        PGDD["pg_dump --format=directory --jobs=4"]
        DIR["/backup/moneymaker_full/<br/>(directory)"]
        PGR["pg_restore --format=directory --jobs=4"]
        DB4["Database Ripristinato"]

        DB3 -->|"dump parallelo"| PGDD
        PGDD -->|"directory"| DIR
        DIR -->|"restore parallelo"| PGR
        PGR -->|"ripristino"| DB4
    end

    CMD["Console: maint backup"]
    CMD -->|"esegue"| PGD

    style DB fill:#2196F3,color:white
    style FILE fill:#4CAF50,color:white
    style DB2 fill:#4CAF50,color:white
    style DB4 fill:#4CAF50,color:white
    style CMD fill:#FF9800,color:white
```

### Raccomandazioni Operative

1. **Frequenza di backup**: Eseguire un backup completo giornaliero durante le ore di bassa attivita' (weekend o dopo la chiusura del mercato Forex venerdi' sera)
2. **Retention dei backup**: Conservare gli ultimi 7 backup giornalieri, 4 backup settimanali e 3 backup mensili
3. **Verifica**: Testare periodicamente il ripristino su un database temporaneo per confermare l'integrita' dei backup
4. **Storage esterno**: Copiare i backup su storage esterno (NAS, S3) per protezione da guasti del disco locale
5. **Monitoraggio**: Verificare che il file di backup abbia una dimensione ragionevole (non vuoto, non drammaticamente diverso dal precedente)

---

## Capitolo 8: Pattern di Query

### Query Piu' Comuni

Il MONEYMAKER utilizza un insieme ricorrente di query per il monitoraggio operativo, la diagnostica e l'analisi delle performance. Questa sezione documenta i pattern piu' importanti con esempi SQL pronti all'uso.

### Ultimi N Segnali di Trading

Questa query recupera gli ultimi N segnali generati dal sistema, utile per il monitoraggio in tempo reale della pipeline decisionale:

```sql
SELECT signal_id, symbol, direction, confidence, regime,
       lots, entry_price, stop_loss, take_profit,
       outcome, pnl, created_at
FROM trade_records
ORDER BY created_at DESC
LIMIT 20;
```

### Rilevamento Gap nei Dati di Mercato

Questa query identifica periodi con volume di tick anomalmente basso, indicativo di problemi di connessione o interruzioni dell'exchange:

```sql
SELECT
    time_bucket('1 hour', time) AS bucket,
    symbol,
    COUNT(*) AS tick_count,
    MIN(time) AS first_tick,
    MAX(time) AS last_tick
FROM market_ticks
WHERE time > NOW() - INTERVAL '7 days'
GROUP BY bucket, symbol
HAVING COUNT(*) < 100
ORDER BY bucket DESC;
```

Un bucket con meno di 100 tick per ora e' sospetto per la maggior parte delle coppie Forex principali durante le ore di mercato attive. La soglia puo' essere adattata per simboli meno liquidi.

### Performance per Strategia

Questa query fornisce un riepilogo aggregato delle performance di ogni strategia, incluse metriche fondamentali come profitto totale, numero di trade e percentuale di vittorie:

```sql
SELECT
    strategy_name,
    COUNT(*) AS total_trades,
    SUM(profit) AS total_profit,
    AVG(profit) AS avg_profit,
    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) AS win_rate,
    MAX(profit) AS best_trade,
    MIN(profit) AS worst_trade
FROM strategy_performance
WHERE time > NOW() - INTERVAL '30 days'
GROUP BY strategy_name
ORDER BY total_profit DESC;
```

### Feature Drift Attivo

Questa query identifica le feature il cui valore corrente devia significativamente dalla baseline, segnalando potenziali problemi di distribuzione dei dati:

```sql
SELECT
    feature_name,
    z_score,
    baseline_mean,
    current_value,
    ABS(z_score) AS abs_z,
    checked_at
FROM feature_drift_logs
WHERE is_drifted = true
ORDER BY ABS(z_score) DESC;
```

Un z-score assoluto superiore a 3 indica una deviazione di 3 deviazioni standard dalla media storica, un segnale forte che il modello potrebbe operare su dati fuori dalla distribuzione di riferimento.

### Analisi dello Slippage di Esecuzione

Questa query analizza lo slippage tra il prezzo richiesto e il prezzo effettivo di esecuzione, una metrica critica per valutare la qualita' dell'esecuzione:

```sql
SELECT
    symbol,
    direction,
    COUNT(*) AS executions,
    AVG(slippage_pips) AS avg_slippage,
    MAX(slippage_pips) AS max_slippage,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY slippage_pips) AS p95_slippage
FROM trade_executions
WHERE status = 'FILLED'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY symbol, direction
ORDER BY avg_slippage DESC;
```

### Controllo Integrita' Audit Log

Come documentato nel Capitolo 5, la verifica della hash chain puo' essere eseguita con una query ricorsiva. Per un controllo rapido, questa query identifica eventuali buchi nella sequenza degli ID:

```sql
SELECT
    a.id AS missing_after,
    a.id + 1 AS missing_id
FROM audit_log a
LEFT JOIN audit_log b ON b.id = a.id + 1
WHERE b.id IS NULL
  AND a.id < (SELECT MAX(id) FROM audit_log);
```

### Stato dei Modelli Statistici

Questa query mostra tutti i modelli attivi con le loro metriche principali:

```sql
SELECT
    mr.model_name,
    mr.version,
    mr.model_type,
    mr.is_active,
    mr.training_samples,
    mr.validation_accuracy,
    mm.metric_name,
    mm.metric_value
FROM model_registry mr
LEFT JOIN model_metrics mm ON mr.model_name = mm.model_id::TEXT
WHERE mr.is_active = true
ORDER BY mr.model_name, mm.metric_name;
```

```mermaid
graph TD
    subgraph "Pattern di Query Operativi"
        Q1["Ultimi N Segnali<br/>trade_records<br/>ORDER BY created_at DESC"]
        Q2["Gap nei Dati<br/>market_ticks<br/>time_bucket + HAVING"]
        Q3["Performance Strategia<br/>strategy_performance<br/>GROUP BY strategy_name"]
        Q4["Feature Drift<br/>feature_drift_logs<br/>WHERE is_drifted = true"]
        Q5["Slippage Esecuzione<br/>trade_executions<br/>AVG + PERCENTILE"]
        Q6["Integrita' Audit<br/>audit_log<br/>CTE ricorsiva"]
        Q7["Stato Modelli<br/>model_registry + model_metrics<br/>JOIN + WHERE is_active"]
    end

    subgraph "Consumer"
        DASH["Dashboard Grafana"]
        CON["Console MONEYMAKER"]
        AE["Algo Engine"]
        MON["Alerting Prometheus"]
    end

    Q1 --> CON
    Q1 --> DASH
    Q2 --> MON
    Q2 --> CON
    Q3 --> DASH
    Q3 --> AE
    Q4 --> MON
    Q4 --> AE
    Q5 --> DASH
    Q6 --> MON
    Q7 --> CON
    Q7 --> DASH

    style Q1 fill:#2196F3,color:white
    style Q2 fill:#F44336,color:white
    style Q3 fill:#4CAF50,color:white
    style Q4 fill:#FF9800,color:white
    style Q5 fill:#9C27B0,color:white
    style Q6 fill:#F44336,color:white
    style Q7 fill:#607D8B,color:white
```

### Indici Raccomandati

Per garantire performance ottimali sulle query documentate sopra, i seguenti indici sono raccomandati:

```sql
-- trade_records: ricerca per simbolo e data
CREATE INDEX idx_trade_records_symbol_created
ON trade_records (symbol, created_at DESC);

-- trade_records: filtro per regime
CREATE INDEX idx_trade_records_regime
ON trade_records (regime, created_at DESC);

-- trade_executions: ricerca per status e data
CREATE INDEX idx_trade_executions_status_created
ON trade_executions (status, created_at DESC);

-- feature_drift_logs: feature in drift
CREATE INDEX idx_feature_drift_active
ON feature_drift_logs (is_drifted) WHERE is_drifted = true;

-- model_registry: modelli attivi
CREATE INDEX idx_model_registry_active
ON model_registry (is_active) WHERE is_active = true;

-- market_graph_relations: navigazione grafo
CREATE INDEX idx_graph_relations_source
ON market_graph_relations (source_entity_id, relation_type);

CREATE INDEX idx_graph_relations_target
ON market_graph_relations (target_entity_id, relation_type);
```

Questi indici parziali (con clausola `WHERE`) sono particolarmente efficienti perche' indicizzano solo le righe rilevanti, riducendo lo spazio su disco e il tempo di aggiornamento durante gli inserimenti.
