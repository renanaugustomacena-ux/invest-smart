# Console Operativa MONEYMAKER

**Autore:** Renan Augusto Macena
**Data:** 2026-02-28
**Versione:** 1.0.0

---

## Indice

1. [Overview](#1-overview)
2. [Architettura della Console](#2-architettura-della-console)
3. [Modalita TUI](#3-modalita-tui)
4. [Categoria: brain](#4-categoria-brain)
5. [Categoria: data](#5-categoria-data)
6. [Categoria: mt5](#6-categoria-mt5)
7. [Categoria: risk](#7-categoria-risk)
8. [Categoria: signal](#8-categoria-signal)
9. [Categoria: market](#9-categoria-market)
10. [Categoria: test](#10-categoria-test)
11. [Categoria: build](#11-categoria-build)
12. [Categoria: sys](#12-categoria-sys)
13. [Categoria: config](#13-categoria-config)
14. [Categoria: svc](#14-categoria-svc)
15. [Categoria: maint](#15-categoria-maint)
16. [Categoria: tool](#16-categoria-tool)
17. [Categoria: help](#17-categoria-help)
18. [Categoria: exit](#18-categoria-exit)
19. [Modalita CLI](#19-modalita-cli)
20. [Riferimento Comandi Pericolosi](#20-riferimento-comandi-pericolosi)

---

## 1. Overview

Immaginate la torre di controllo di un grande aeroporto internazionale. Da quella posizione sopraelevata, i controllori del traffico aereo hanno una visione completa di ogni pista, ogni aereo in avvicinamento, ogni veicolo a terra. Possono comunicare con qualsiasi pilota, possono autorizzare decolli e atterraggi, possono dichiarare emergenze e deviare il traffico. Soprattutto, possono premere il pulsante rosso che ferma tutto in caso di pericolo imminente.

La Console Operativa MONEYMAKER e la torre di controllo del nostro ecosistema di trading. Da un'unica interfaccia, l'operatore ha visibilita su ogni componente del sistema: lo stato dell'Algo Engine, i dati di mercato in arrivo, le posizioni aperte su MetaTrader 5, i livelli di rischio, la salute dei servizi Docker, lo stato del database e della cache Redis. L'operatore puo impartire comandi a qualsiasi servizio, avviare o fermare componenti, eseguire test, effettuare manutenzione, e attivare i meccanismi di emergenza quando necessario.

```mermaid
graph TD
    A["Operatore MONEYMAKER"] --> B["Console Operativa"]
    B --> C["Torre di Controllo"]

    C --> D["Pista 1:<br/>Algo Engine<br/>(decisioni di trading)"]
    C --> E["Pista 2:<br/>Data Ingestion<br/>(flusso dati di mercato)"]
    C --> F["Pista 3:<br/>MT5 Bridge<br/>(esecuzione ordini)"]
    C --> G["Pista 4:<br/>Risk Manager<br/>(sicurezza)"]
    C --> H["Hangar:<br/>Infrastruttura<br/>(Docker, DB, Redis)"]

    I["Pulsante Emergenza:<br/>Kill Switch"] -.-> C
```

La console opera in due modalita distinte: la modalita TUI (Text User Interface), che fornisce un'interfaccia interattiva a pannelli multipli con aggiornamento in tempo reale, e la modalita CLI (Command Line Interface), che permette l'esecuzione di singoli comandi da terminale per automazione e scripting. Entrambe le modalita hanno accesso allo stesso set completo di comandi e producono gli stessi risultati, ma differiscono nell'esperienza utente e nel caso d'uso ottimale.

La console non e un semplice wrapper attorno a comandi esistenti. E un sistema integrato che comprende la topologia dell'ecosistema MONEYMAKER e puo orchestrare operazioni complesse che coinvolgono piu servizi simultaneamente. Ad esempio, il comando `test suite` esegue prima i test Python dell'Algo Engine, poi i test Go del Data Ingestion, raccoglie i risultati di entrambi e presenta un riepilogo unificato. Il comando `sys health` interroga simultaneamente PostgreSQL, Redis e Docker per fornire un quadro completo della salute del sistema in un singolo output.

Ogni comando della console e classificato in una delle 15 categorie tematiche, organizzate per dominio di responsabilita. Questa organizzazione riflette l'architettura a microservizi dell'ecosistema e permette all'operatore di navigare intuitivamente verso il comando necessario. La sintassi segue sempre lo schema `CATEGORIA SOTTOCOMANDO [ARGOMENTI]`, rendendo i comandi prevedibili e auto-documentanti.

---

## 2. Architettura della Console

L'architettura della console segue il pattern Command con un Dispatcher centrale che riceve l'input dell'utente, identifica la categoria e il sottocomando, e delega l'esecuzione al handler appropriato registrato nel Command Registry. Questo design permette di aggiungere nuovi comandi senza modificare il core della console.

```mermaid
graph LR
    subgraph "Input"
        A["Utente"] -->|"TUI: tastiera"| B["Console"]
        A -->|"CLI: argv"| B
    end

    subgraph "Console Core"
        B --> C["Dispatcher"]
        C --> D["Command Registry"]
        D --> E["BrainCommands"]
        D --> F["DataCommands"]
        D --> G["MT5Commands"]
        D --> H["RiskCommands"]
        D --> I["SignalCommands"]
        D --> J["MarketCommands"]
        D --> K["TestCommands"]
        D --> L["BuildCommands"]
        D --> M["SysCommands"]
        D --> N["ConfigCommands"]
        D --> O["SvcCommands"]
        D --> P["MaintCommands"]
        D --> Q["ToolCommands"]
    end

    subgraph "Backend"
        E -->|"gRPC stub"| R["Algo Engine Service"]
        F -->|"gRPC stub"| S["Data Ingestion"]
        G -->|"gRPC stub"| T["MT5 Bridge"]
        H -->|"Redis"| U["Redis Server"]
        I -->|"SQL"| V["PostgreSQL"]
        M -->|"SQL + Redis + subprocess"| W["Infrastruttura"]
        O -->|"subprocess"| X["Docker Compose"]
        P -->|"SQL"| V
    end
```

### Command Registry

Il Command Registry e un dizionario che mappa la coppia (categoria, sottocomando) al relativo handler. All'avvio della console, ogni modulo di comandi registra i propri handler nel registry. Il Dispatcher utilizza questo registro per risolvere il comando immesso dall'utente e invocare la funzione corretta con gli argomenti forniti.

Ogni handler e una funzione asincrona che riceve gli argomenti del comando come lista di stringhe e restituisce una stringa di output da visualizzare all'utente. Gli handler possono interagire con qualsiasi backend: database PostgreSQL per query SQL dirette, Redis per operazioni sulla cache e pub/sub, Docker tramite subprocess per la gestione dei container, servizi gRPC per la comunicazione con i microservizi, e il filesystem per l'accesso a log e file di configurazione.

```mermaid
flowchart TD
    A["Input utente:<br/>'mt5 positions'"] --> B["Dispatcher.dispatch()"]
    B --> C["Parsing: categoria='mt5',<br/>sottocomando='positions',<br/>args=[]"]
    C --> D["Registry lookup:<br/>handlers['mt5']['positions']"]
    D --> E{"Handler trovato?"}
    E -->|"Si"| F["Esecuzione handler<br/>mt5_positions()"]
    E -->|"No"| G["Errore: comando sconosciuto<br/>Suggerimenti simili"]
    F --> H["Output formattato<br/>restituito all'utente"]
```

### Interazione con i Backend

La console interagisce con cinque tipi di backend, ciascuno con il proprio meccanismo di connessione e gestione degli errori:

**PostgreSQL (diretto):** Connessione tramite `asyncpg` con pool di connessioni. Utilizzato per query sui segnali, audit log, drift metrics, e operazioni di manutenzione. Le query sono parametrizzate per prevenire SQL injection.

**Redis (diretto):** Connessione tramite `aioredis`. Utilizzato per leggere lo stato del kill switch, le metriche in tempo reale, e la cache. Le operazioni sono tutte non-bloccanti.

**Docker (subprocess):** Invocazione di `docker compose` come processo esterno. Utilizzato per gestire i container dei servizi (up, down, restart, logs, status). L'output viene catturato e formattato.

**Servizi gRPC (stub):** Client gRPC per comunicare con Algo Engine, Data Ingestion e MT5 Bridge. Attualmente molti comandi sono implementati come stub che restituiscono un messaggio informativo fino a quando i servizi non saranno completamente operativi.

**Filesystem:** Lettura diretta di file di log, configurazione e cache. Utilizzato per comandi come `config view`, `tool logs`, e operazioni di pulizia cache.

---

## 3. Modalita TUI

La modalita TUI (Text User Interface) e l'interfaccia interattiva principale della console MONEYMAKER. Fornisce un'esperienza simile a un'applicazione desktop, con pannelli multipli che mostrano informazioni in tempo reale, una barra di stato, e un prompt per l'immissione dei comandi.

### Layout

```
+============================================================================+
|  MONEYMAKER Trading Console v1.0.0  |  2026-02-28 14:32:15  |  DB:OK Redis:OK |
+============================================================================+
|                          |                                                  |
|   MARKET DATA            |   AI BRAIN                                       |
|   -----------------      |   -----------------                              |
|   EURUSD: 1.0923/25      |   Status: RUNNING                               |
|   GBPUSD: 1.2654/56      |   Regime: TRENDING                              |
|   USDJPY: 149.82/84      |   Model: v3.2.1                                 |
|   XAUUSD: 2042.50/80     |   Confidence: 0.78                              |
|   Spread: 2.0 pts        |   Last Signal: BUY EURUSD (14:31:02)            |
|   Session: London         |   Signals Today: 12                             |
|                          |                                                  |
+--------------------------+--------------------------------------------------+
|                          |                                                  |
|   RISK & POSITIONS       |   SYSTEM                                         |
|   -----------------      |   -----------------                              |
|   Kill Switch: ARMED     |   Docker: 3/3 running                           |
|   Daily P/L: +0.42%      |   PostgreSQL: OK (142 MB)                       |
|   Drawdown: 1.8%         |   Redis: OK (12 MB, 847 keys)                   |
|   Open Positions: 2/5    |   CPU: 23%  RAM: 4.2/16 GB                      |
|   #1 EURUSD BUY +18p     |   Disk: 45/500 GB                               |
|   #2 GBPUSD SELL -5p     |   Uptime: 3d 14h 22m                            |
|                          |                                                  |
+--------------------------+--------------------------------------------------+
|  moneymaker> mt5 positions                                                     |
|  [help] brain data mt5 risk signal market test build sys config svc maint   |
+=============================================================================+
```

```mermaid
graph TD
    subgraph "Layout TUI - 4 Pannelli"
        subgraph "Header"
            A["Versione | Ora | Stato Connessioni"]
        end

        subgraph "Pannello Superiore Sinistro"
            B["MARKET DATA<br/>Prezzi real-time<br/>Spread corrente<br/>Sessione attiva"]
        end

        subgraph "Pannello Superiore Destro"
            C["AI BRAIN<br/>Stato servizio<br/>Regime mercato<br/>Confidenza modello<br/>Ultimo segnale"]
        end

        subgraph "Pannello Inferiore Sinistro"
            D["RISK & POSITIONS<br/>Kill Switch stato<br/>P/L giornaliero<br/>Drawdown<br/>Lista posizioni"]
        end

        subgraph "Pannello Inferiore Destro"
            E["SYSTEM<br/>Docker containers<br/>Database stato<br/>Redis stato<br/>Risorse HW"]
        end

        subgraph "Footer"
            F["Prompt comandi | Riferimento categorie"]
        end
    end

    A --> B
    A --> C
    B --> D
    C --> E
    D --> F
    E --> F
```

### Gestione Input da Tastiera

L'interfaccia TUI gestisce l'input carattere per carattere tramite la libreria `curses` (o `windows-curses` su Windows):

- **Caratteri stampabili** (lettere, numeri, spazi, trattini): vengono aggiunti al buffer del comando corrente e visualizzati nel prompt.
- **Enter**: il buffer viene inviato al Dispatcher per l'esecuzione, l'output viene visualizzato nell'area principale, e il buffer viene svuotato.
- **Backspace**: cancella l'ultimo carattere dal buffer.
- **Ctrl+C**: termina la console in modo pulito, chiudendo tutte le connessioni e i thread di background.
- **Freccia Su/Giu**: naviga la cronologia dei comandi precedenti.
- **Tab**: autocompletamento del comando corrente basato sul registry.

### Refresh e Polling

La TUI opera con due cicli di aggiornamento indipendenti:

**Rendering a 8 Hz (125ms):** Il ciclo di rendering ridisegna i pannelli 8 volte al secondo. Questo garantisce un'esperienza fluida e reattiva senza consumare troppe risorse CPU. Il rendering e incrementale: solo i pannelli con dati aggiornati vengono ridisegnati.

**Status Polling a 1 Hz (1000ms):** Un thread di background (`StatusPoller`) interroga i backend ogni secondo per aggiornare i dati visualizzati nei pannelli. Il polling avviene in parallelo per tutti i backend (DB, Redis, Docker) utilizzando `asyncio.gather()` per minimizzare la latenza totale.

```mermaid
flowchart LR
    subgraph "Thread Principale"
        A["Rendering Loop<br/>8 Hz"] --> B["Ridisegna pannelli<br/>con dati piu recenti"]
        B --> A
    end

    subgraph "Thread Background"
        C["StatusPoller<br/>1 Hz"] --> D["Query PostgreSQL"]
        C --> E["Query Redis"]
        C --> F["docker ps"]
        D --> G["Aggiorna stato DB"]
        E --> H["Aggiorna stato Redis"]
        F --> I["Aggiorna stato Docker"]
        G --> C
        H --> C
        I --> C
    end

    G -.->|"dati condivisi<br/>(thread-safe)"| A
    H -.-> A
    I -.-> A
```

---

## 4. Categoria: brain

La categoria `brain` gestisce il ciclo di vita e lo stato dell'Algo Engine, il componente di intelligenza artificiale che genera i segnali di trading. Tutti i comandi di questa categoria comunicano con il servizio Algo Engine tramite gRPC. Attualmente, i comandi sono implementati come stub gRPC in attesa che il servizio sia completamente operativo in modalita server.

```mermaid
flowchart TD
    subgraph "brain commands"
        A["brain start"] --> B["Avvia servizio Algo Engine"]
        C["brain stop"] --> D["Ferma servizio Algo Engine"]
        E["brain pause"] --> F["Sospendi generazione segnali"]
        G["brain resume"] --> H["Riprendi generazione segnali"]
        I["brain status"] --> J["Stato corrente del servizio"]
        K["brain eval"] --> L["Esegui valutazione modello"]
        M["brain checkpoint"] --> N["Salva checkpoint modello"]
        O["brain model-info"] --> P["Info modello caricato"]
    end
```

### brain start

**Sintassi:** `brain start`
**Argomenti:** nessuno
**Funzionamento:** Invia una richiesta gRPC al servizio Algo Engine per avviare il ciclo di generazione segnali. Il servizio carica il modello piu recente dal checkpoint, inizializza le connessioni ai dati di mercato, e inizia ad analizzare i dati in arrivo per generare segnali di trading.
**Stato:** gRPC stub -- restituisce il messaggio informativo fino alla completa implementazione del servizio server.
**Output esempio:**
```
[STUB] brain start: gRPC call to Algo Engine service (not yet implemented)
Service would start signal generation pipeline
```

### brain stop

**Sintassi:** `brain stop`
**Argomenti:** nessuno
**Funzionamento:** Invia una richiesta gRPC per fermare il ciclo di generazione segnali. Il servizio completa l'elaborazione del segnale corrente (se in corso), salva lo stato interno, e si pone in modalita idle. Le posizioni aperte NON vengono chiuse automaticamente.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] brain stop: gRPC call to Algo Engine service (not yet implemented)
Service would stop signal generation gracefully
```

### brain pause

**Sintassi:** `brain pause`
**Argomenti:** nessuno
**Funzionamento:** Sospende temporaneamente la generazione di segnali senza fermare il servizio. L'Algo Engine continua a ricevere e processare i dati di mercato (mantenendo lo stato interno aggiornato), ma non emette segnali di trading. Utile durante periodi di alta volatilita o eventi di news.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] brain pause: gRPC call to Algo Engine service (not yet implemented)
Service would pause signal emission while maintaining state
```

### brain resume

**Sintassi:** `brain resume`
**Argomenti:** nessuno
**Funzionamento:** Riprende la generazione di segnali dopo una pausa. Il servizio riprende immediatamente l'analisi e l'emissione di segnali basandosi sullo stato interno mantenuto durante la pausa.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] brain resume: gRPC call to Algo Engine service (not yet implemented)
Service would resume signal emission
```

### brain status

**Sintassi:** `brain status`
**Argomenti:** nessuno
**Funzionamento:** Interroga il servizio Algo Engine per ottenere lo stato corrente: running/stopped/paused, versione del modello caricato, numero di segnali generati nella sessione corrente, ultima confidenza, regime di mercato corrente, e metriche di performance.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] brain status: gRPC call to Algo Engine service (not yet implemented)
Would return: state, model version, signals count, last confidence, regime
```

### brain eval

**Sintassi:** `brain eval`
**Argomenti:** nessuno
**Funzionamento:** Esegue una valutazione completa del modello corrente sui dati storici recenti. Calcola metriche di performance come accuracy, precision, recall, Sharpe ratio dei segnali generati, e confronta con le performance attese.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] brain eval: gRPC call to Algo Engine service (not yet implemented)
Would trigger model evaluation and return performance metrics
```

### brain checkpoint

**Sintassi:** `brain checkpoint`
**Argomenti:** nessuno
**Funzionamento:** Forza il salvataggio di un checkpoint del modello corrente. Il checkpoint include i pesi del modello, lo stato dell'ottimizzatore, e le metriche di performance al momento del salvataggio. Utile prima di operazioni di manutenzione o aggiornamenti.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] brain checkpoint: gRPC call to Algo Engine service (not yet implemented)
Would save model checkpoint to persistent storage
```

### brain model-info

**Sintassi:** `brain model-info`
**Argomenti:** nessuno
**Funzionamento:** Restituisce informazioni dettagliate sul modello attualmente caricato: architettura (MarketRAPCoach), numero di parametri, dimensioni (hidden_dim, metadata_dim, output_dim), data di addestramento, dataset utilizzato, e metriche del checkpoint.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] brain model-info: gRPC call to Algo Engine service (not yet implemented)
Would return: architecture, parameters count, dimensions, training date
```

---

## 5. Categoria: data

La categoria `data` gestisce il servizio di raccolta dati di mercato (Data Ingestion), scritto in Go. Permette di controllare il flusso dei dati, aggiungere o rimuovere simboli dalla lista di monitoraggio, eseguire backfill di dati storici, e verificare la presenza di lacune nei dati.

```mermaid
flowchart TD
    subgraph "data commands"
        A["data start"] -->|"gRPC stub"| B["Avvia ingestion"]
        C["data stop"] -->|"gRPC stub"| D["Ferma ingestion"]
        E["data status"] -->|"gRPC stub"| F["Stato servizio"]
        G["data symbols"] -->|"gRPC stub"| H["Lista simboli attivi"]
        I["data add SYMBOL"] -->|"gRPC stub"| J["Aggiungi simbolo"]
        K["data remove SYMBOL"] -->|"gRPC stub"| L["Rimuovi simbolo"]
        M["data backfill SYMBOL DAYS"] -->|"gRPC stub"| N["Backfill storico"]
        O["data gaps"] -->|"SQL diretto"| P["Trova lacune dati"]
    end
```

### data start

**Sintassi:** `data start`
**Argomenti:** nessuno
**Funzionamento:** Avvia il servizio di raccolta dati tramite gRPC. Il servizio si connette ai feed di mercato del broker e inizia a ricevere tick e candele per tutti i simboli configurati.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] data start: gRPC call to Data Ingestion service (not yet implemented)
```

### data stop

**Sintassi:** `data stop`
**Argomenti:** nessuno
**Funzionamento:** Ferma la raccolta dati. I dati gia ricevuti rimangono nel database.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] data stop: gRPC call to Data Ingestion service (not yet implemented)
```

### data status

**Sintassi:** `data status`
**Argomenti:** nessuno
**Funzionamento:** Interroga il servizio per ottenere lo stato: running/stopped, simboli monitorati, tick/secondo, ultima candela ricevuta.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] data status: gRPC call to Data Ingestion service (not yet implemented)
```

### data symbols

**Sintassi:** `data symbols`
**Argomenti:** nessuno
**Funzionamento:** Lista tutti i simboli attualmente configurati per la raccolta dati.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] data symbols: gRPC call to Data Ingestion service (not yet implemented)
```

### data add

**Sintassi:** `data add SYMBOL`
**Argomenti:** `SYMBOL` -- il simbolo da aggiungere (es. EURUSD, GBPJPY)
**Funzionamento:** Aggiunge un nuovo simbolo alla lista di monitoraggio del servizio di raccolta dati. Il servizio inizia immediatamente a raccogliere tick e candele per il nuovo simbolo.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] data add EURUSD: gRPC call to Data Ingestion service (not yet implemented)
```

### data remove

**Sintassi:** `data remove SYMBOL`
**Argomenti:** `SYMBOL` -- il simbolo da rimuovere
**Funzionamento:** Rimuove un simbolo dalla lista di monitoraggio. I dati storici del simbolo rimangono nel database.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] data remove NZDUSD: gRPC call to Data Ingestion service (not yet implemented)
```

### data backfill

**Sintassi:** `data backfill SYMBOL DAYS`
**Argomenti:** `SYMBOL` -- il simbolo, `DAYS` -- numero di giorni di storico da scaricare
**Funzionamento:** Richiede al servizio di scaricare i dati storici per il simbolo specificato, coprendo il numero di giorni indicato. Utile per popolare il database con lo storico necessario per l'analisi e il backtesting.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] data backfill EURUSD 90: gRPC call to Data Ingestion service (not yet implemented)
```

### data gaps

**Sintassi:** `data gaps`
**Argomenti:** nessuno
**Funzionamento:** Esegue una query SQL diretta su PostgreSQL per identificare lacune nei dati di mercato. Analizza le candele per ogni simbolo e timeframe, cercando intervalli mancanti dove ci si aspetterebbe dati (escludendo weekend e festivi). Questo comando funziona immediatamente perche opera direttamente sul database senza dipendere dal servizio gRPC.
**Stato:** Funzionante immediatamente (SQL diretto).
**Output esempio:**
```
Data Gap Analysis
=================
EURUSD M5: OK (no gaps detected)
EURUSD H1: 2 gaps found
  - 2026-02-25 14:00 to 2026-02-25 14:30 (30 min)
  - 2026-02-26 09:00 to 2026-02-26 09:15 (15 min)
GBPUSD M5: OK (no gaps detected)
```

---

## 6. Categoria: mt5

La categoria `mt5` gestisce la connessione e le operazioni con il terminale MetaTrader 5 tramite il servizio MT5 Bridge.

```mermaid
flowchart TD
    subgraph "mt5 commands"
        A["mt5 connect"] --> B["Connetti al terminale"]
        C["mt5 disconnect"] --> D["Disconnetti"]
        E["mt5 status"] --> F["Stato connessione e conto"]
        G["mt5 positions"] --> H["Lista posizioni aperte"]
        I["mt5 history DAYS"] --> J["Storico operazioni"]
        K["mt5 close-all"] --> L["CHIUDI TUTTE LE POSIZIONI<br/>(PERICOLOSO)"]
    end
```

### mt5 connect

**Sintassi:** `mt5 connect`
**Argomenti:** nessuno
**Funzionamento:** Invia una richiesta gRPC al MT5 Bridge per stabilire la connessione con il terminale MetaTrader 5 utilizzando le credenziali configurate nel file `.env`. Verifica che il terminale sia in esecuzione, che le credenziali siano corrette, e che il trading algoritmico sia abilitato.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] mt5 connect: gRPC call to MT5 Bridge service (not yet implemented)
Would connect to MT5 terminal with configured credentials
```

### mt5 disconnect

**Sintassi:** `mt5 disconnect`
**Argomenti:** nessuno
**Funzionamento:** Disconnette dal terminale MT5. Le posizioni aperte rimangono attive sul server del broker con i loro SL/TP.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] mt5 disconnect: gRPC call to MT5 Bridge service (not yet implemented)
```

### mt5 status

**Sintassi:** `mt5 status`
**Argomenti:** nessuno
**Funzionamento:** Interroga il MT5 Bridge per ottenere lo stato completo: connessione (connected/disconnected), numero conto, server broker, bilancio, equity, margine libero, numero posizioni aperte, e stato del trailing stop.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] mt5 status: gRPC call to MT5 Bridge service (not yet implemented)
Would return: connection state, account, balance, equity, margin, positions
```

### mt5 positions

**Sintassi:** `mt5 positions`
**Argomenti:** nessuno
**Funzionamento:** Richiede al MT5 Bridge la lista dettagliata di tutte le posizioni attualmente aperte. Per ogni posizione mostra: ticket, simbolo, direzione, volume, prezzo di apertura, SL, TP, profitto corrente in pips e in valuta, e durata.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] mt5 positions: gRPC call to MT5 Bridge service (not yet implemented)
Would return list of open positions with P/L details
```

### mt5 history

**Sintassi:** `mt5 history [DAYS]`
**Argomenti:** `DAYS` (opzionale, default: 7) -- numero di giorni di storico da visualizzare
**Funzionamento:** Richiede lo storico delle operazioni chiuse negli ultimi N giorni. Per ogni operazione mostra: ticket, simbolo, direzione, volume, prezzo apertura/chiusura, profitto, e durata.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] mt5 history 7: gRPC call to MT5 Bridge service (not yet implemented)
Would return trade history for the last 7 days
```

### mt5 close-all

**Sintassi:** `mt5 close-all`
**Argomenti:** nessuno
**Funzionamento:** **COMANDO PERICOLOSO** -- Chiude immediatamente tutte le posizioni aperte al prezzo di mercato corrente. Questo comando richiede conferma esplicita (y/N) prima dell'esecuzione. Utilizzare solo in caso di emergenza o quando si desidera azzerare l'esposizione.
**Stato:** gRPC stub.
**Output esempio:**
```
WARNING: This will close ALL open positions at market price!
Are you sure? [y/N]: y
[STUB] mt5 close-all: gRPC call to MT5 Bridge service (not yet implemented)
Would close all open positions immediately
```

---

## 7. Categoria: risk

La categoria `risk` gestisce i parametri di rischio, i meccanismi di sicurezza e i limiti operativi del sistema di trading.

```mermaid
flowchart TD
    subgraph "risk commands"
        A["risk status"] --> B["Stato rischio corrente"]
        C["risk limits"] --> D["Mostra limiti configurati"]
        E["risk set-max-dd PERCENT"] --> F["Imposta max drawdown"]
        G["risk set-max-pos N"] --> H["Imposta max posizioni"]
        I["risk kill-switch"] --> J["ATTIVA KILL SWITCH<br/>(PERICOLOSO)"]
        K["risk circuit-breaker STATE"] --> L["Gestisci circuit breaker"]
    end
```

### risk status

**Sintassi:** `risk status`
**Argomenti:** nessuno
**Funzionamento:** Mostra un riepilogo completo dello stato del rischio: kill switch (ARMED/TRIGGERED), profitto/perdita giornaliero, drawdown corrente, numero posizioni aperte vs limite, esposizione totale per simbolo, e stato dei circuit breaker.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] risk status: gRPC call to risk management (not yet implemented)
Would return: kill switch state, daily P/L, drawdown, positions, exposure
```

### risk limits

**Sintassi:** `risk limits`
**Argomenti:** nessuno
**Funzionamento:** Mostra tutti i limiti di rischio attualmente configurati: max daily loss, max drawdown, max position count, max lot size, max spread, e soglie del circuit breaker.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] risk limits: gRPC call to risk management (not yet implemented)
Would return all configured risk limits and thresholds
```

### risk set-max-dd

**Sintassi:** `risk set-max-dd PERCENT`
**Argomenti:** `PERCENT` -- nuova percentuale massima di drawdown (es. 15.0)
**Funzionamento:** Aggiorna il limite massimo di drawdown a runtime. Il nuovo valore viene immediatamente applicato alla logica del kill switch. Utilizzare con cautela: aumentare il limite di drawdown espone il conto a rischi maggiori.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] risk set-max-dd 15.0: gRPC call to risk management (not yet implemented)
Would update max drawdown threshold to 15.0%
```

### risk set-max-pos

**Sintassi:** `risk set-max-pos N`
**Argomenti:** `N` -- nuovo numero massimo di posizioni simultanee (es. 8)
**Funzionamento:** Aggiorna il limite massimo di posizioni contemporanee aperte. Il nuovo valore viene immediatamente applicato alla validazione pre-ordine numero 5.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] risk set-max-pos 8: gRPC call to risk management (not yet implemented)
Would update max position count to 8
```

### risk kill-switch

**Sintassi:** `risk kill-switch`
**Argomenti:** nessuno
**Funzionamento:** **COMANDO PERICOLOSO** -- Attiva manualmente il Kill Switch, bloccando immediatamente tutti i nuovi segnali di trading. Lo stato viene propagato a tutti i servizi tramite Redis broadcast. Richiede conferma esplicita (y/N). Una volta attivato, richiede reset manuale per essere disattivato.
**Stato:** gRPC stub.
**Output esempio:**
```
WARNING: Activating Kill Switch will BLOCK ALL new trading signals!
Existing positions will NOT be closed automatically.
Are you sure? [y/N]: y
[STUB] risk kill-switch: gRPC call to risk management (not yet implemented)
Would broadcast KILL_SWITCH_ACTIVE to all services via Redis
```

### risk circuit-breaker

**Sintassi:** `risk circuit-breaker [STATE]`
**Argomenti:** `STATE` (opzionale) -- senza argomenti mostra lo stato, con `reset SYMBOL` resetta un circuit breaker specifico
**Funzionamento:** Senza argomenti, mostra lo stato (CLOSED/OPEN/HALF-OPEN) di tutti i circuit breaker per ogni simbolo/strategia. Con l'argomento `reset SYMBOL`, forza il reset del circuit breaker per il simbolo specificato, riportandolo allo stato CLOSED.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] risk circuit-breaker: gRPC call to risk management (not yet implemented)
Would return state of all circuit breakers by symbol/strategy
```

---

## 8. Categoria: signal

La categoria `signal` permette di interrogare e analizzare i segnali di trading generati dall'Algo Engine.

```mermaid
flowchart TD
    subgraph "signal commands"
        A["signal status"] --> B["Stato pipeline segnali"]
        C["signal last N"] --> D["Ultimi N segnali dal DB"]
        E["signal pending"] --> F["Segnali in attesa"]
        G["signal confidence"] --> H["Distribuzione confidenza"]
    end
```

### signal status

**Sintassi:** `signal status`
**Argomenti:** nessuno
**Funzionamento:** Mostra lo stato della pipeline di generazione e esecuzione segnali: segnali generati oggi, segnali eseguiti, segnali rifiutati (con breakdown per motivo di rifiuto), tasso di esecuzione, e latenza media.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] signal status: gRPC call to signal pipeline (not yet implemented)
Would return: signals generated, executed, rejected, execution rate, latency
```

### signal last

**Sintassi:** `signal last [N]`
**Argomenti:** `N` (opzionale, default: 10) -- numero di segnali recenti da visualizzare
**Funzionamento:** Esegue una query SQL diretta su PostgreSQL per recuperare gli ultimi N segnali registrati nell'audit log. Per ogni segnale mostra: timestamp, simbolo, direzione, confidenza, prezzo, SL, TP, esito (eseguito/rifiutato), e motivo del rifiuto se applicabile.
**Stato:** Funzionante immediatamente (SQL diretto).
**Output esempio:**
```
Last 5 Trading Signals
=======================
2026-02-28 14:31:02  EURUSD  BUY   conf=0.82  EXECUTED  ticket=12345
2026-02-28 14:28:15  GBPUSD  SELL  conf=0.71  EXECUTED  ticket=12344
2026-02-28 14:25:33  USDJPY  BUY   conf=0.65  REJECTED  reason=spread_too_high
2026-02-28 14:22:01  EURUSD  BUY   conf=0.78  REJECTED  reason=duplicate_signal
2026-02-28 14:18:44  XAUUSD  SELL  conf=0.88  EXECUTED  ticket=12343
```

### signal pending

**Sintassi:** `signal pending`
**Argomenti:** nessuno
**Funzionamento:** Mostra i segnali attualmente in coda di esecuzione (se la pipeline implementa un buffer). In condizioni normali, questa coda dovrebbe essere vuota o contenere al massimo 1-2 segnali.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] signal pending: gRPC call to signal pipeline (not yet implemented)
Would return list of signals awaiting execution
```

### signal confidence

**Sintassi:** `signal confidence`
**Argomenti:** nessuno
**Funzionamento:** Mostra la distribuzione della confidenza dei segnali generati nelle ultime 24 ore: media, mediana, deviazione standard, minimo, massimo, e istogramma testuale.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] signal confidence: gRPC call to signal pipeline (not yet implemented)
Would return confidence distribution statistics
```

---

## 9. Categoria: market

La categoria `market` fornisce informazioni sul mercato e le condizioni di trading correnti.

```mermaid
flowchart TD
    subgraph "market commands"
        A["market regime"] --> B["Regime di mercato corrente"]
        C["market symbols"] --> D["Simboli disponibili"]
        E["market spread SYMBOL"] --> F["Spread corrente"]
        G["market calendar"] --> H["Calendario economico<br/>(pianificato)"]
    end
```

### market regime

**Sintassi:** `market regime`
**Argomenti:** nessuno
**Funzionamento:** Interroga l'Algo Engine per ottenere la classificazione corrente del regime di mercato: TRENDING, MEAN_REVERTING, HIGH_VOLATILITY, o LOW_VOLATILITY. Include anche la confidenza della classificazione e la durata del regime corrente.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] market regime: gRPC call to Algo Engine service (not yet implemented)
Would return: current regime, confidence, duration
```

### market symbols

**Sintassi:** `market symbols`
**Argomenti:** nessuno
**Funzionamento:** Mostra tutti i simboli disponibili per il trading, con informazioni di base come spread tipico, sessioni di trading, e se il simbolo e attualmente monitorato dal Data Ingestion.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] market symbols: gRPC call to market data service (not yet implemented)
Would return list of available trading symbols with details
```

### market spread

**Sintassi:** `market spread SYMBOL`
**Argomenti:** `SYMBOL` -- il simbolo di cui visualizzare lo spread (es. EURUSD)
**Funzionamento:** Interroga il terminale MT5 tramite il bridge per ottenere lo spread corrente del simbolo in punti e in pips, insieme allo spread medio dell'ultima ora e al massimo della giornata.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] market spread EURUSD: gRPC call to MT5 Bridge (not yet implemented)
Would return: current spread, 1h average, daily max
```

### market calendar

**Sintassi:** `market calendar`
**Argomenti:** nessuno
**Funzionamento:** Mostra gli eventi economici pianificati per le prossime 24 ore con il relativo impatto previsto (alto/medio/basso). Utile per decidere se sospendere il trading durante eventi ad alto impatto.
**Stato:** Pianificato -- non ancora implementato.
**Output esempio:**
```
[PLANNED] market calendar: Feature not yet implemented
Would show upcoming economic events with impact level
```

---

## 10. Categoria: test

La categoria `test` esegue le suite di test dell'ecosistema MONEYMAKER, coprendo sia i test Python dell'Algo Engine che i test Go del Data Ingestion.

```mermaid
flowchart TD
    subgraph "test commands"
        A["test all"] --> B["pytest algo-engine completo"]
        C["test brain-verify"] --> D["pytest brain_verification"]
        E["test cascade"] --> F["pytest test_cascade"]
        G["test go"] --> H["go test ./..."]
        I["test suite"] --> J["all + go in sequenza"]
    end
```

### test all

**Sintassi:** `test all`
**Argomenti:** nessuno
**Funzionamento:** Esegue l'intera suite di test Python dell'Algo Engine utilizzando pytest. I test vengono eseguiti nella directory `program/services/algo-engine/` con il virtualenv `.venv/`. Il comando cattura stdout e stderr e presenta un riepilogo dei risultati (pass/fail/skip).
**Stato:** Funzionante immediatamente (esecuzione locale pytest).
**Output esempio:**
```
Running: pytest program/services/algo-engine/ -v
...
316 passed, 0 failed, 2 skipped in 45.3s
```

### test brain-verify

**Sintassi:** `test brain-verify`
**Argomenti:** nessuno
**Funzionamento:** Esegue solo i test di verifica del cervello artificiale (`brain_verification`), che controllano la correttezza delle dimensioni dei tensori, le firme dei moduli, e la coerenza del flusso forward.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Running: pytest program/services/algo-engine/tests/brain_verification/ -v
...
18 passed, 0 failed in 12.1s
```

### test cascade

**Sintassi:** `test cascade`
**Argomenti:** nessuno
**Funzionamento:** Esegue i test della cascata end-to-end (`test_cascade`), che verificano il flusso completo dal segnale alla decisione, includendo orchestratore, maturity gate, e signal router.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Running: pytest program/services/algo-engine/tests/test_cascade/ -v
...
18 passed, 0 failed in 8.7s
```

### test go

**Sintassi:** `test go`
**Argomenti:** nessuno
**Funzionamento:** Esegue i test Go del servizio Data Ingestion utilizzando `go test ./...` nella directory `program/services/data-ingestion/`. Copre test unitari per i parser dei dati, i connettori WebSocket, e le pipeline di canali.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Running: go test ./... in program/services/data-ingestion/
ok   data-ingestion/internal/parser     0.234s
ok   data-ingestion/internal/connector  0.567s
ok   data-ingestion/internal/pipeline   0.891s
```

### test suite

**Sintassi:** `test suite`
**Argomenti:** nessuno
**Funzionamento:** Esegue prima `test all` (pytest Python), poi `test go` (go test), in sequenza. Questo garantisce che tutti i test dell'ecosistema vengano eseguiti e che il risultato sia presentato in un riepilogo unificato. Se i test Python falliscono, i test Go vengono comunque eseguiti.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
=== Running Python tests ===
316 passed, 0 failed, 2 skipped in 45.3s

=== Running Go tests ===
3 packages tested, all passed in 1.692s

=== SUITE SUMMARY ===
Python: 316/318 passed
Go:     3/3 packages passed
Overall: PASS
```

---

## 11. Categoria: build

La categoria `build` gestisce la compilazione e la costruzione delle immagini Docker dei servizi MONEYMAKER.

```mermaid
flowchart TD
    subgraph "build commands"
        A["build all"] --> B["docker compose build<br/>(tutti i servizi)"]
        C["build brain"] --> D["docker compose build algo-engine"]
        E["build ingestion"] --> F["docker compose build data-ingestion"]
        G["build bridge"] --> H["docker compose build mt5-bridge"]
        I["build test-only"] --> J["Build senza push,<br/>solo verifica"]
    end
```

### build all

**Sintassi:** `build all`
**Argomenti:** nessuno
**Funzionamento:** Esegue `docker compose build` per costruire tutte le immagini Docker dei servizi MONEYMAKER. Il contesto di build e la directory `program/` e utilizza i Dockerfile specifici di ogni servizio.
**Stato:** Funzionante immediatamente (subprocess docker).
**Output esempio:**
```
Building all services...
[+] Building algo-engine...         done (34.2s)
[+] Building data-ingestion...   done (21.5s)
[+] Building mt5-bridge...       done (28.1s)
All images built successfully.
```

### build brain

**Sintassi:** `build brain`
**Argomenti:** nessuno
**Funzionamento:** Costruisce solo l'immagine Docker del servizio Algo Engine.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Building algo-engine...
[+] Building algo-engine...         done (34.2s)
```

### build ingestion

**Sintassi:** `build ingestion`
**Argomenti:** nessuno
**Funzionamento:** Costruisce solo l'immagine Docker del servizio Data Ingestion (Go).
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Building data-ingestion...
[+] Building data-ingestion...   done (21.5s)
```

### build bridge

**Sintassi:** `build bridge`
**Argomenti:** nessuno
**Funzionamento:** Costruisce solo l'immagine Docker del servizio MT5 Bridge.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Building mt5-bridge...
[+] Building mt5-bridge...       done (28.1s)
```

### build test-only

**Sintassi:** `build test-only`
**Argomenti:** nessuno
**Funzionamento:** Esegue la build di tutti i servizi in modalita verifica senza push al registry. Utile per verificare che i Dockerfile siano corretti e che le immagini si costruiscano senza errori, senza consumare spazio nel registry.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Building all services (test-only, no push)...
[+] Building algo-engine...         done (34.2s)
[+] Building data-ingestion...   done (21.5s)
[+] Building mt5-bridge...       done (28.1s)
Build verification: PASS
```

---

## 12. Categoria: sys

La categoria `sys` fornisce informazioni sullo stato dell'infrastruttura e delle risorse del sistema.

```mermaid
flowchart TD
    subgraph "sys commands"
        A["sys status"] --> B["docker ps"]
        C["sys resources"] --> D["CPU/RAM/Disk/GPU"]
        E["sys health"] --> F["DB + Redis + Docker check"]
        G["sys db"] --> H["PG version/size/connections"]
        I["sys redis"] --> J["Redis version/memory/keys"]
        K["sys audit"] --> L["Audit log (pianificato)"]
    end
```

### sys status

**Sintassi:** `sys status`
**Argomenti:** nessuno
**Funzionamento:** Esegue `docker ps --format` per mostrare lo stato di tutti i container Docker dell'ecosistema MONEYMAKER: nome, immagine, stato (running/stopped/restarting), porte esposte, e uptime.
**Stato:** Funzionante immediatamente (subprocess docker).
**Output esempio:**
```
MONEYMAKER Docker Status
=====================
NAME              IMAGE                    STATUS          PORTS
moneymaker-brain     moneymaker/algo-engine:latest  Up 3 days       50051->50051
moneymaker-ingest    moneymaker/data-ingest:1.0  Up 3 days       50052->50052
moneymaker-mt5       moneymaker/mt5-bridge:1.0   Up 3 days       50055->50055
moneymaker-postgres  timescaledb/latest       Up 5 days       5432->5432
moneymaker-redis     redis:7-alpine           Up 5 days       6379->6379
```

### sys resources

**Sintassi:** `sys resources`
**Argomenti:** nessuno
**Funzionamento:** Raccoglie e visualizza le metriche delle risorse hardware del sistema: utilizzo CPU (per core e totale), RAM (usata/totale), spazio disco (per mount point), e stato GPU (se disponibile, tramite `rocm-smi` per AMD o `nvidia-smi` per NVIDIA).
**Stato:** Funzionante immediatamente (psutil + subprocess).
**Output esempio:**
```
System Resources
================
CPU:  23% (8 cores, avg load 1.84)
RAM:  4.2 / 16.0 GB (26%)
Disk: 45.3 / 500.0 GB (9%) [D:\]
GPU:  AMD RX 9070 XT - 38C, 12% util, 8.2/16.0 GB VRAM
```

### sys health

**Sintassi:** `sys health`
**Argomenti:** nessuno
**Funzionamento:** Esegue un controllo di salute completo su tutti i componenti dell'infrastruttura: connessione PostgreSQL (SELECT 1), connessione Redis (PING), stato container Docker. Restituisce un riepilogo con stato OK/WARN/FAIL per ogni componente.
**Stato:** Funzionante immediatamente (SQL + Redis + subprocess).
**Output esempio:**
```
MONEYMAKER Health Check
====================
PostgreSQL:  OK  (latency: 2ms, version: 16.1)
Redis:       OK  (latency: 1ms, version: 7.2.4)
Docker:      OK  (5/5 containers running)
Overall:     HEALTHY
```

### sys db

**Sintassi:** `sys db`
**Argomenti:** nessuno
**Funzionamento:** Interroga PostgreSQL per informazioni dettagliate: versione, dimensione totale del database, numero di connessioni attive, tabelle piu grandi, e stato delle estensioni (TimescaleDB, pg_stat_statements).
**Stato:** Funzionante immediatamente (SQL diretto).
**Output esempio:**
```
PostgreSQL Info
===============
Version:      PostgreSQL 16.1 + TimescaleDB 2.13.0
Database:     moneymaker_trading
Size:         142 MB
Connections:  8 active / 100 max
Top tables:   candles_m5 (89 MB), signals (12 MB), audit_log (8 MB)
Extensions:   timescaledb (2.13.0), pg_stat_statements (1.10)
```

### sys redis

**Sintassi:** `sys redis`
**Argomenti:** nessuno
**Funzionamento:** Interroga Redis per informazioni dettagliate: versione, memoria utilizzata, numero totale di chiavi, chiavi per namespace, e uptime.
**Stato:** Funzionante immediatamente (Redis diretto).
**Output esempio:**
```
Redis Info
==========
Version:  7.2.4
Memory:   12.4 MB / 256 MB max
Keys:     847 total
  moneymaker:market:*    412 keys
  moneymaker:signal:*    235 keys
  moneymaker:state:*      48 keys
  moneymaker:cache:*     152 keys
Uptime:   5 days 14 hours
```

### sys audit

**Sintassi:** `sys audit`
**Argomenti:** nessuno
**Funzionamento:** Mostra gli ultimi eventi dell'audit log di sicurezza: login, modifiche configurazione, attivazioni kill switch, e operazioni amministrative.
**Stato:** Pianificato -- non ancora implementato.
**Output esempio:**
```
[PLANNED] sys audit: Feature not yet implemented
Would show security audit log entries
```

---

## 13. Categoria: config

La categoria `config` gestisce la visualizzazione e la validazione della configurazione dell'ecosistema MONEYMAKER.

```mermaid
flowchart TD
    subgraph "config commands"
        A["config broker KEY"] --> B["Leggi config broker<br/>(stub)"]
        C["config risk K V"] --> D["Imposta param rischio<br/>(stub)"]
        E["config view"] --> F["Mostra .env<br/>(segreti mascherati)"]
        G["config validate"] --> H["Verifica variabili<br/>critiche"]
    end
```

### config broker

**Sintassi:** `config broker KEY`
**Argomenti:** `KEY` -- la chiave di configurazione del broker da leggere
**Funzionamento:** Legge un valore di configurazione specifico del broker. I valori sensibili (password, chiavi API) vengono mascherati nell'output.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] config broker mt5_server: would read broker configuration
```

### config risk

**Sintassi:** `config risk K V`
**Argomenti:** `K` -- chiave del parametro di rischio, `V` -- nuovo valore
**Funzionamento:** Aggiorna un parametro di rischio a runtime. Le modifiche sono temporanee e non persistono al riavvio del servizio. Per modifiche permanenti, aggiornare il file `.env`.
**Stato:** gRPC stub.
**Output esempio:**
```
[STUB] config risk max_lot_size 0.5: would update risk parameter
```

### config view

**Sintassi:** `config view`
**Argomenti:** nessuno
**Funzionamento:** Legge il file `.env` e visualizza tutte le variabili di configurazione. I valori sensibili (contenenti "PASSWORD", "SECRET", "KEY", "TOKEN") vengono automaticamente mascherati con asterischi, mostrando solo i primi 2 e gli ultimi 2 caratteri.
**Stato:** Funzionante immediatamente (lettura file).
**Output esempio:**
```
MONEYMAKER Configuration (.env)
============================
MT5_ACCOUNT=12345678
MT5_PASSWORD=my****rd
MT5_SERVER=ICMarkets-Demo
MT5_TIMEOUT_MS=10000
BRAIN_DATABASE_URL=postgresql://moneymaker:****th@localhost:5432/moneymaker_trading
REDIS_HOST=localhost
REDIS_PORT=6379
MAX_POSITION_COUNT=5
MAX_LOT_SIZE=1.0
```

### config validate

**Sintassi:** `config validate`
**Argomenti:** nessuno
**Funzionamento:** Verifica che tutte le variabili di configurazione critiche siano definite e abbiano valori validi. Controlla in particolare: `BRAIN_DATABASE_URL` (formato URL PostgreSQL valido), `REDIS_HOST` (non vuoto), `MT5_ACCOUNT` (intero positivo), e la raggiungibilita di PostgreSQL e Redis con le credenziali fornite.
**Stato:** Funzionante immediatamente (validazione locale + connessione test).
**Output esempio:**
```
Configuration Validation
========================
BRAIN_DATABASE_URL:  OK  (valid PostgreSQL URL, connection successful)
REDIS_HOST:          OK  (localhost, PING successful)
MT5_ACCOUNT:         OK  (12345678)
MT5_PASSWORD:        OK  (set, not empty)
MT5_SERVER:          OK  (ICMarkets-Demo)
MAX_POSITION_COUNT:  OK  (5, within range 1-20)
MAX_LOT_SIZE:        OK  (1.0, within range 0.01-100)

Validation: ALL CHECKS PASSED
```

---

## 14. Categoria: svc

La categoria `svc` gestisce il ciclo di vita dei servizi Docker dell'ecosistema MONEYMAKER.

```mermaid
flowchart TD
    subgraph "svc commands"
        A["svc up"] --> B["docker compose up -d"]
        C["svc down"] --> D["docker compose down"]
        E["svc restart SERVICE"] --> F["docker compose restart"]
        G["svc logs SERVICE"] --> H["Ultimi 50 log lines"]
        I["svc status"] --> J["docker ps"]
        K["svc scale SERVICE N"] --> L["docker compose scale"]
    end
```

### svc up

**Sintassi:** `svc up`
**Argomenti:** nessuno
**Funzionamento:** Avvia tutti i servizi dell'ecosistema MONEYMAKER in modalita detached tramite `docker compose up -d`. I servizi vengono avviati nell'ordine definito dalle dipendenze nel file `docker-compose.yml` (database prima, poi servizi applicativi).
**Stato:** Funzionante immediatamente (subprocess docker).
**Output esempio:**
```
Starting MONEYMAKER services...
[+] Running 5/5
 - Container moneymaker-postgres  Started
 - Container moneymaker-redis     Started
 - Container moneymaker-brain     Started
 - Container moneymaker-ingest    Started
 - Container moneymaker-mt5       Started
All services started successfully.
```

### svc down

**Sintassi:** `svc down`
**Argomenti:** nessuno
**Funzionamento:** Ferma tutti i servizi tramite `docker compose down`. I volumi dei dati (PostgreSQL, Redis) vengono preservati.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Stopping MONEYMAKER services...
[+] Running 5/5
 - Container moneymaker-mt5       Stopped
 - Container moneymaker-ingest    Stopped
 - Container moneymaker-brain     Stopped
 - Container moneymaker-redis     Stopped
 - Container moneymaker-postgres  Stopped
All services stopped.
```

### svc restart

**Sintassi:** `svc restart SERVICE`
**Argomenti:** `SERVICE` -- nome del servizio da riavviare (es. algo-engine, data-ingestion, mt5-bridge)
**Funzionamento:** Riavvia un singolo servizio tramite `docker compose restart SERVICE`. Il servizio viene fermato e riavviato con la stessa configurazione.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Restarting algo-engine...
[+] Restarting moneymaker-brain... done
Service algo-engine restarted successfully.
```

### svc logs

**Sintassi:** `svc logs SERVICE [-f]`
**Argomenti:** `SERVICE` -- nome del servizio, `-f` (opzionale) -- follow mode (streaming continuo)
**Funzionamento:** Mostra le ultime 50 righe di log del servizio specificato tramite `docker compose logs --tail 50 SERVICE`. Con il flag `-f`, entra in modalita follow dove i nuovi log vengono stampati in tempo reale (Ctrl+C per uscire).
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Logs for algo-engine (last 50 lines):
2026-02-28 14:30:01 [INFO] Signal generated: BUY EURUSD conf=0.82
2026-02-28 14:30:01 [INFO] Signal sent to MT5 Bridge
2026-02-28 14:30:02 [INFO] Execution confirmed: ticket=12345
...
```

### svc status

**Sintassi:** `svc status`
**Argomenti:** nessuno
**Funzionamento:** Equivalente a `sys status`, mostra lo stato di tutti i container Docker tramite `docker ps`.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
(Same output as sys status - docker ps formatted)
```

### svc scale

**Sintassi:** `svc scale SERVICE N`
**Argomenti:** `SERVICE` -- nome del servizio, `N` -- numero di istanze desiderate
**Funzionamento:** Scala il numero di istanze di un servizio tramite `docker compose up -d --scale SERVICE=N`. Utile per servizi stateless che possono beneficiare di piu istanze parallele.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Scaling data-ingestion to 3 instances...
[+] Running 3/3
 - Container moneymaker-ingest-1  Started
 - Container moneymaker-ingest-2  Started
 - Container moneymaker-ingest-3  Started
```

---

## 15. Categoria: maint

La categoria `maint` fornisce strumenti di manutenzione per il database, la cache e i dati storici.

```mermaid
flowchart TD
    subgraph "maint commands"
        A["maint vacuum"] --> B["VACUUM ANALYZE<br/>su PostgreSQL"]
        C["maint reindex"] --> D["REINDEX DATABASE"]
        E["maint clear-cache"] --> F["Pulisci pycache + Redis"]
        G["maint retention"] --> H["Mostra policy ritenzione"]
        I["maint backup"] --> J["pg_dump compresso"]
        K["maint prune-old DAYS"] --> L["Elimina dati vecchi<br/>(PERICOLOSO)"]
    end
```

### maint vacuum

**Sintassi:** `maint vacuum`
**Argomenti:** nessuno
**Funzionamento:** Esegue `VACUUM ANALYZE` su tutte le tabelle del database PostgreSQL. Questa operazione recupera lo spazio occupato da righe cancellate e aggiorna le statistiche delle tabelle per migliorare le performance delle query. Sicura da eseguire durante le operazioni normali (non blocca le letture).
**Stato:** Funzionante immediatamente (SQL diretto).
**Output esempio:**
```
Running VACUUM ANALYZE on moneymaker_trading...
VACUUM ANALYZE completed successfully.
Reclaimed: 12 MB
Tables analyzed: 15
Duration: 3.2s
```

### maint reindex

**Sintassi:** `maint reindex`
**Argomenti:** nessuno
**Funzionamento:** Esegue `REINDEX DATABASE moneymaker_trading` per ricostruire tutti gli indici. Utile dopo grandi operazioni di inserimento o cancellazione che possono frammentare gli indici. Attenzione: questa operazione puo bloccare temporaneamente le scritture sulle tabelle indicizzate.
**Stato:** Funzionante immediatamente (SQL diretto).
**Output esempio:**
```
Running REINDEX DATABASE moneymaker_trading...
REINDEX completed successfully.
Indexes rebuilt: 28
Duration: 8.7s
```

### maint clear-cache

**Sintassi:** `maint clear-cache`
**Argomenti:** nessuno
**Funzionamento:** Esegue due operazioni di pulizia: (1) rimuove tutte le directory `__pycache__` nel progetto tramite ricerca ricorsiva e cancellazione, (2) esegue `FLUSHDB` su Redis per svuotare la cache. I dati persistenti (PostgreSQL) non vengono toccati.
**Stato:** Funzionante immediatamente (filesystem + Redis).
**Output esempio:**
```
Clearing caches...
Python: Removed 23 __pycache__ directories
Redis:  FLUSHDB executed, 847 keys removed
Cache cleared successfully.
```

### maint retention

**Sintassi:** `maint retention`
**Argomenti:** nessuno
**Funzionamento:** Mostra la policy di ritenzione dei dati configurata: per quanto tempo vengono mantenuti i dati tick-by-tick, le candele per ogni timeframe, i segnali, l'audit log, e le metriche di drift.
**Stato:** Funzionante immediatamente (legge configurazione).
**Output esempio:**
```
Data Retention Policy
=====================
Tick data (M1):     30 days
Candles (M5):       90 days
Candles (H1):       365 days
Candles (D1):       unlimited
Signals:            365 days
Audit log:          unlimited
Drift metrics:      180 days
Model snapshots:    90 days
```

### maint backup

**Sintassi:** `maint backup`
**Argomenti:** nessuno
**Funzionamento:** Esegue un backup completo del database utilizzando `pg_dump` con compressione gzip. Il file di backup viene salvato nella directory `backups/` con un nome che include data e ora (es. `moneymaker_trading_20260228_143200.sql.gz`).
**Stato:** Funzionante immediatamente (subprocess pg_dump).
**Output esempio:**
```
Creating database backup...
Output: backups/moneymaker_trading_20260228_143200.sql.gz
Size:   38 MB (compressed from 142 MB)
Duration: 12.4s
Backup completed successfully.
```

### maint prune-old

**Sintassi:** `maint prune-old DAYS`
**Argomenti:** `DAYS` -- cancella i dati piu vecchi di N giorni
**Funzionamento:** **COMANDO PERICOLOSO** -- Cancella definitivamente i dati piu vecchi del numero di giorni specificato dalle tabelle di drift metrics e model snapshots. NON tocca le candele, i segnali o l'audit log. Richiede conferma esplicita (y/N) prima dell'esecuzione. Mostra un conteggio delle righe che verranno cancellate prima di chiedere conferma.
**Stato:** Funzionante immediatamente (SQL diretto, con conferma).
**Output esempio:**
```
WARNING: This will permanently delete old data!

Rows to be deleted:
  drift_metrics:    2,847 rows (older than 90 days)
  model_snapshots:  12 rows (older than 90 days)

This action cannot be undone. Are you sure? [y/N]: y
Deleting old drift_metrics... 2,847 rows deleted
Deleting old model_snapshots... 12 rows deleted
Pruning completed. Freed approximately 4.2 MB.
```

---

## 16. Categoria: tool

La categoria `tool` fornisce utility diagnostiche e informative per l'operatore.

```mermaid
flowchart TD
    subgraph "tool commands"
        A["tool logs"] --> B["Ultime 20 righe di log<br/>(formato JSON)"]
        C["tool list"] --> D["Dump di tutti i comandi<br/>disponibili"]
    end
```

### tool logs

**Sintassi:** `tool logs`
**Argomenti:** nessuno
**Funzionamento:** Legge le ultime 20 righe del file di log principale della console MONEYMAKER in formato JSON strutturato. Ogni riga include: timestamp, livello (INFO/WARN/ERROR), modulo di origine, e messaggio. Utile per diagnosticare problemi della console stessa.
**Stato:** Funzionante immediatamente (lettura file).
**Output esempio:**
```
Console Logs (last 20 entries)
==============================
2026-02-28 14:32:15 [INFO]  dispatcher  Command executed: sys status (23ms)
2026-02-28 14:32:10 [INFO]  poller      Status poll completed (DB:OK Redis:OK Docker:OK)
2026-02-28 14:31:55 [WARN]  poller      Redis latency elevated: 45ms (threshold: 20ms)
2026-02-28 14:31:45 [INFO]  dispatcher  Command executed: mt5 positions (156ms)
...
```

### tool list

**Sintassi:** `tool list`
**Argomenti:** nessuno
**Funzionamento:** Genera un dump completo di tutti i comandi registrati nel Command Registry, organizzati per categoria. Per ogni comando mostra: sintassi, breve descrizione, e stato (funzionante/stub/pianificato).
**Stato:** Funzionante immediatamente (lettura registry).
**Output esempio:**
```
MONEYMAKER Console - All Commands
==============================
brain (8 commands):
  brain start          - Start Algo Engine service [STUB]
  brain stop           - Stop Algo Engine service [STUB]
  brain pause          - Pause signal generation [STUB]
  ...

data (8 commands):
  data start           - Start data ingestion [STUB]
  data gaps            - Find data gaps [WORKS]
  ...

(continues for all 15 categories)
Total: 75 commands (12 working, 58 stubs, 5 planned)
```

---

## 17. Categoria: help

```mermaid
flowchart TD
    A["help"] --> B["Mostra tutte le categorie<br/>con descrizione"]
    B --> C["brain - Algo Engine management"]
    B --> D["data - Data ingestion"]
    B --> E["mt5 - MetaTrader 5 bridge"]
    B --> F["risk - Risk management"]
    B --> G["signal - Signal analysis"]
    B --> H["market - Market info"]
    B --> I["test - Test suites"]
    B --> J["build - Docker builds"]
    B --> K["sys - System status"]
    B --> L["config - Configuration"]
    B --> M["svc - Service lifecycle"]
    B --> N["maint - Maintenance"]
    B --> O["tool - Utilities"]
    B --> P["help - This help"]
    B --> Q["exit - Exit console"]
```

### help

**Sintassi:** `help` oppure `help CATEGORY`
**Argomenti:** `CATEGORY` (opzionale) -- se specificata, mostra l'help dettagliato per quella categoria
**Funzionamento:** Senza argomenti, mostra l'elenco di tutte le 15 categorie con una breve descrizione di ciascuna. Con un argomento categoria, mostra tutti i comandi di quella categoria con sintassi, argomenti, descrizione e stato.
**Stato:** Funzionante immediatamente.
**Output esempio (senza argomenti):**
```
MONEYMAKER Trading Console - Help
==============================
brain    Algo Engine management (start, stop, pause, resume, status, eval, checkpoint, model-info)
data     Data ingestion control (start, stop, status, symbols, add, remove, backfill, gaps)
mt5      MetaTrader 5 bridge (connect, disconnect, status, positions, history, close-all)
risk     Risk management (status, limits, set-max-dd, set-max-pos, kill-switch, circuit-breaker)
signal   Signal analysis (status, last, pending, confidence)
market   Market information (regime, symbols, spread, calendar)
test     Test suites (all, brain-verify, cascade, go, suite)
build    Docker builds (all, brain, ingestion, bridge, test-only)
sys      System status (status, resources, health, db, redis, audit)
config   Configuration (broker, risk, view, validate)
svc      Service lifecycle (up, down, restart, logs, status, scale)
maint    Maintenance (vacuum, reindex, clear-cache, retention, backup, prune-old)
tool     Utilities (logs, list)
help     Show this help
exit     Exit console

Type 'help CATEGORY' for detailed help on a category.
```

---

## 18. Categoria: exit

```mermaid
flowchart TD
    A["exit"] --> B["Ferma StatusPoller thread"]
    B --> C["Chiudi connessione PostgreSQL"]
    C --> D["Chiudi connessione Redis"]
    D --> E["Salva cronologia comandi"]
    E --> F["Ripristina terminale<br/>(curses endwin)"]
    F --> G["Processo terminato<br/>(exit code 0)"]
```

### exit

**Sintassi:** `exit` oppure `Ctrl+C`
**Argomenti:** nessuno
**Funzionamento:** Termina la console MONEYMAKER in modo pulito. Il processo di chiusura segue un ordine preciso: (1) ferma il thread di background StatusPoller, (2) chiude le connessioni al database PostgreSQL e a Redis, (3) salva la cronologia dei comandi per la sessione successiva, (4) ripristina il terminale allo stato originale (necessario dopo l'uso di curses). L'exit code e 0 per una chiusura normale.
**Stato:** Funzionante immediatamente.
**Output esempio:**
```
Shutting down MONEYMAKER Console...
StatusPoller stopped.
Database connection closed.
Redis connection closed.
Command history saved (47 entries).
Goodbye.
```

---

## 19. Modalita CLI

La modalita CLI (Command Line Interface) permette di eseguire singoli comandi della console direttamente dal terminale, senza entrare nell'interfaccia interattiva TUI. Questa modalita e ideale per l'automazione, gli script, i cron job, e l'integrazione con altri strumenti.

### Sintassi

```
python moneymaker_console.py CATEGORIA SOTTOCOMANDO [ARGOMENTI]
```

```mermaid
flowchart TD
    A["python moneymaker_console.py<br/>CATEGORIA SOTTOCOMANDO ARGS"] --> B["Parsing argv"]
    B --> C["Dispatcher.dispatch()"]
    C --> D["Esecuzione handler"]
    D --> E{"Successo?"}
    E -->|"Si"| F["stdout: output<br/>exit code: 0"]
    E -->|"No"| G["stderr: errore<br/>exit code: 1"]
```

### Exit Codes

- **0**: comando eseguito con successo
- **1**: errore nell'esecuzione del comando (argomenti invalidi, servizio non raggiungibile, operazione fallita)

### Output

L'output in modalita CLI e testo puro senza formattazione ANSI, adatto al piping e al parsing da script. L'output standard (stdout) contiene il risultato del comando, mentre l'output di errore (stderr) contiene messaggi di errore e warning.

### Esempi Pratici

**Esempio 1: Controllo stato sistema**
```bash
python moneymaker_console.py sys health
```
Output:
```
PostgreSQL:  OK  (latency: 2ms)
Redis:       OK  (latency: 1ms)
Docker:      OK  (5/5 running)
Overall:     HEALTHY
```

**Esempio 2: Visualizzare le ultime operazioni di trading**
```bash
python moneymaker_console.py signal last 5
```
Output:
```
2026-02-28 14:31:02  EURUSD  BUY   conf=0.82  EXECUTED
2026-02-28 14:28:15  GBPUSD  SELL  conf=0.71  EXECUTED
2026-02-28 14:25:33  USDJPY  BUY   conf=0.65  REJECTED
2026-02-28 14:22:01  EURUSD  BUY   conf=0.78  REJECTED
2026-02-28 14:18:44  XAUUSD  SELL  conf=0.88  EXECUTED
```

**Esempio 3: Backup del database automatizzato (cron job)**
```bash
python moneymaker_console.py maint backup && echo "Backup OK" || echo "Backup FAILED"
```

**Esempio 4: Verifica configurazione in uno script CI/CD**
```bash
python moneymaker_console.py config validate
if [ $? -ne 0 ]; then
    echo "Configuration validation failed!"
    exit 1
fi
```

**Esempio 5: Monitoraggio risorse con output parsabile**
```bash
python moneymaker_console.py sys resources | grep "CPU"
```
Output:
```
CPU:  23% (8 cores, avg load 1.84)
```

**Esempio 6: Esecuzione della suite di test completa**
```bash
python moneymaker_console.py test suite
```

**Esempio 7: Pulizia dati vecchi da script di manutenzione programmata**
```bash
echo "y" | python moneymaker_console.py maint prune-old 90
```
Nota: il pipe di "y" soddisfa la richiesta di conferma automaticamente.

---

## 20. Riferimento Comandi Pericolosi

Alcuni comandi della console MONEYMAKER hanno conseguenze potenzialmente irreversibili o significative sul sistema di trading. Questi comandi richiedono tutti una conferma esplicita (y/N) prima dell'esecuzione, dove il default e "N" (no) per prevenire esecuzioni accidentali.

```mermaid
flowchart TD
    subgraph "Comandi Pericolosi"
        A["mt5 close-all"] --> D["Chiude TUTTE le posizioni<br/>al prezzo di mercato"]
        B["risk kill-switch"] --> E["Blocca TUTTI i nuovi<br/>segnali di trading"]
        C["maint prune-old DAYS"] --> F["Elimina DEFINITIVAMENTE<br/>dati storici"]
    end

    D --> G{"Conferma y/N?"}
    E --> G
    F --> G
    G -->|"y"| H["Esecuzione"]
    G -->|"N (default)"| I["Annullato"]
```

### mt5 close-all

**Livello di pericolo:** ALTO
**Conseguenze:** Chiude immediatamente tutte le posizioni aperte al prezzo di mercato corrente. Questo significa che:
- Le posizioni in profitto vengono chiuse, cristallizzando il guadagno ma rinunciando a ulteriori movimenti favorevoli.
- Le posizioni in perdita vengono chiuse, realizzando la perdita.
- In condizioni di mercato volatile, lo slippage potrebbe peggiorare significativamente il prezzo di chiusura.
- L'operazione non puo essere annullata una volta eseguita.

**Quando usarlo:** Solo in caso di emergenza quando si ritiene che mantenere le posizioni aperte rappresenti un rischio maggiore rispetto alla chiusura immediata. Ad esempio: comportamento anomalo del sistema, sospetto di hacking, o evento di mercato catastrofico imminente (black swan).

**Conferma richiesta:**
```
WARNING: This will close ALL open positions at market price!
Currently open: 3 positions (EURUSD BUY +18p, GBPUSD SELL -5p, USDJPY BUY +3p)
Estimated P/L impact: +16 pips net
Are you sure? [y/N]:
```

### risk kill-switch

**Livello di pericolo:** MEDIO-ALTO
**Conseguenze:** Attiva il Kill Switch globale che blocca immediatamente tutti i nuovi segnali di trading. Le posizioni esistenti NON vengono chiuse (rimangono con i loro SL/TP). Il Kill Switch rimane attivo fino al reset manuale, anche attraverso riavvii del sistema. Una volta attivato:
- L'Algo Engine continua a generare segnali, ma tutti vengono rifiutati dall'OrderManager.
- Il PositionTracker continua a operare (trailing stop ancora attivi).
- Nessun nuovo trade puo essere aperto fino al reset.

**Quando usarlo:** Quando si osserva un pattern di perdite anomale, quando il mercato entra in condizioni estreme, durante la manutenzione del sistema, o quando si sospetta un malfunzionamento dell'Algo Engine.

**Conferma richiesta:**
```
WARNING: Activating Kill Switch will BLOCK ALL new trading signals!
Existing positions will NOT be closed automatically.
Kill Switch requires manual reset to deactivate.
Are you sure? [y/N]:
```

### maint prune-old

**Livello di pericolo:** MEDIO
**Conseguenze:** Elimina definitivamente le righe dal database PostgreSQL nelle tabelle `drift_metrics` e `model_snapshots` che sono piu vecchie del numero di giorni specificato. I dati cancellati non possono essere recuperati a meno che non esista un backup recente. Le tabelle principali (candles, signals, audit_log) NON vengono toccate.

**Quando usarlo:** Come parte della manutenzione periodica per mantenere il database snello e performante. Si raccomanda di eseguire `maint backup` prima di `maint prune-old`.

**Conferma richiesta:**
```
WARNING: This will permanently delete old data!

Rows to be deleted:
  drift_metrics:    2,847 rows (older than 90 days)
  model_snapshots:  12 rows (older than 90 days)

This action cannot be undone. Are you sure? [y/N]:
```

### Raccomandazioni di Sicurezza

Per minimizzare il rischio di esecuzioni accidentali di comandi pericolosi:

1. **Non utilizzare pipe automatici** per i comandi pericolosi in produzione (es. `echo "y" | ... close-all`). Utilizzare pipe automatici solo in ambienti di test o in script di emergenza pre-approvati.

2. **Verificare sempre lo stato** prima di eseguire un comando pericoloso. Ad esempio, eseguire `mt5 positions` prima di `mt5 close-all` per sapere esattamente quali posizioni verranno chiuse.

3. **Mantenere backup aggiornati** prima di operazioni di manutenzione distruttive. Eseguire `maint backup` prima di `maint prune-old`.

4. **Documentare ogni attivazione** del Kill Switch nell'audit log manuale del team, includendo il motivo dell'attivazione, l'orario, e il piano di riattivazione.

5. **Testare su ambiente demo** prima di utilizzare comandi pericolosi su un conto reale. Il sistema MONEYMAKER supporta la configurazione di ambienti demo e live separati tramite file `.env` diversi.
