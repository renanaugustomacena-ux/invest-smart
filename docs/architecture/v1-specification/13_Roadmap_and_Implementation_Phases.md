# MONEYMAKER V1 -- Roadmap and Implementation Phases

> **Autore** | Renan Augusto Macena

---

## Table of Contents

1. [Roadmap Philosophy](#131-roadmap-philosophy)
2. [Prerequisites and Preparation (Phase 0)](#132-prerequisites-and-preparation-phase-0)
3. [Phase 1 -- Foundation: Database and Data Ingestion (Weeks 1-4)](#133-phase-1--foundation-database-and-data-ingestion-weeks-1-4)
4. [Phase 2 -- Intelligence: Feature Engineering and AI Models (Weeks 5-12)](#134-phase-2--intelligence-feature-engineering-and-ai-models-weeks-5-12)
5. [Phase 3 -- Execution: MT5 Bridge and Risk Management (Weeks 13-18)](#135-phase-3--execution-mt5-bridge-and-risk-management-weeks-13-18)
6. [Phase 4 -- Observability: Monitoring and Dashboard (Weeks 19-22)](#136-phase-4--observability-monitoring-and-dashboard-weeks-19-22)
7. [Phase 5 -- Hardening: Security and Testing (Weeks 23-26)](#137-phase-5--hardening-security-and-testing-weeks-23-26)
8. [Phase 6 -- Go-Live: Controlled Live Trading (Weeks 27-32+)](#138-phase-6--go-live-controlled-live-trading-weeks-27-32)
9. [Feature Backlog and Future Enhancements](#139-feature-backlog-and-future-enhancements)
10. [Risk Register](#1310-risk-register)
11. [Success Criteria and KPIs](#1311-success-criteria-and-kpis)
12. [Budget and Resource Planning](#1312-budget-and-resource-planning)
13. [Document Cross-Reference Guide](#1313-document-cross-reference-guide)
14. [Conclusion and Call to Action](#1314-conclusion-and-call-to-action)

---

## 13.1 Roadmap Philosophy

### The Crawl, Walk, Run Approach

This is the final document in the MONEYMAKER V1 Foundation Series. Twelve documents precede it, each describing a specific domain of the system in exhaustive technical detail: the architectural vision (Document 01), the Proxmox infrastructure (Document 02), the microservices communication patterns (Document 03), the data ingestion gateway (Document 04), the database architecture (Document 05), the MT5 execution bridge (Document 08), the risk management service (Document 09), the monitoring and dashboard stack (Document 10), the testing strategy (Document 11), and the security framework (Document 12). Together, those twelve documents describe what MONEYMAKER is. This thirteenth document describes how to build it.

The roadmap follows a strict crawl-walk-run approach. The word "strict" is not rhetorical decoration. It means that no phase begins until the prior phase is complete and validated. It means that every phase delivers a working, testable, demonstrable increment of the system, not a pile of half-finished components that cannot be verified in isolation. It means that at the end of every phase, you can point to something that functions, run it, observe its behavior, and confirm that it meets its acceptance criteria before moving to the next layer of complexity.

This discipline is essential because the alternative -- trying to build everything simultaneously, leaving validation until the end, and hoping that the pieces fit together when assembled -- is how complex software projects fail. It is how trading systems fail. You build half the data pipeline, skip ahead to the model because that is the exciting part, realize the data pipeline has a subtle normalization bug, spend a week debugging the model before discovering the data was corrupt, and lose confidence in every result you have produced. The crawl-walk-run approach eliminates this class of failure by ensuring that each layer is solid before the next layer is built on top of it.

### Each Phase Delivers a Working Increment

Phase 1 delivers a database filling with real-time market data. You can query it, chart it, and verify it against the broker's own data. Phase 2 delivers trained AI models that produce calibrated trading signals on historical data. You can backtest them, measure their performance, and evaluate their predictions. Phase 3 delivers a complete trading pipeline operating on a demo account. You can watch it make decisions, execute trades, and compute P&L. Phase 4 delivers full observability so that you can monitor everything from a single dashboard. Phase 5 hardens the system with security and comprehensive testing. Phase 6 transitions to live trading with extreme caution.

At no point in this sequence are you working on something that cannot be independently verified. At no point are you asked to trust that a component works based on anything other than observable evidence. This is the engineering equivalent of the scientific method applied to system construction: build a hypothesis (the component will behave as specified), run an experiment (test the component), observe the results (does it pass its validation criteria?), and only then proceed to build the next hypothesis on that foundation.

### Never Skip Safety Systems

Risk management is not a feature to be added in the final sprint before go-live. It is woven into every phase. Phase 1 includes data quality validation -- a form of risk management that protects the system from corrupt inputs. Phase 2 includes walk-forward validation and overfitting detection -- risk management for the model development process itself. Phase 3 explicitly builds the risk management service alongside the execution bridge, ensuring that no trade can execute without passing through the risk gate. Phase 4 adds monitoring and alerting -- real-time risk detection. Phase 5 adds security hardening -- protection against external threats. Phase 6 starts live trading with deliberately tight circuit breakers and minimum position sizes.

The temptation to defer safety systems is real. When you are excited about the AI models and impatient to see them trade, the circuit breaker implementation feels like bureaucratic overhead. It is not. The circuit breaker is the component that prevents a malfunctioning model from destroying your trading capital in a single afternoon. The kill switch is the component that lets you shut everything down in three seconds when the market does something no model anticipated. These are not optional features. They are structural requirements that are present in every phase of this roadmap, starting from Phase 1.

### Make It Work, Make It Right, Make It Fast

This principle, attributed to Kent Beck, perfectly captures the implementation philosophy for each component within each phase. First, make it work: get the basic functionality operational with correct behavior, even if the code is ugly and the performance is mediocre. Second, make it right: refactor the code, add error handling, write tests, clean up the interfaces, and ensure the design is maintainable. Third, make it fast: optimize performance where it matters, add caching, tune queries, and profile for bottlenecks.

In a trading system, "make it fast" is genuinely important -- stale data and slow execution cost money. But premature optimization is the root of a different kind of failure: it produces systems that are fast but wrong, or fast but unmaintainable. A data ingestion service that processes 100,000 ticks per second but occasionally drops messages due to a race condition in its buffer management is worse than one that processes 10,000 ticks per second reliably. Get it right first. Then get it fast.

### Solo Developer Considerations

MONEYMAKER V1 is being built by a single developer. This is both a constraint and an advantage. The constraint is obvious: there is one person doing all of the work, and that person has finite time, energy, and context-switching capacity. The advantage is less obvious but equally real: there is no coordination overhead, no merge conflicts, no design-by-committee, no meetings about meetings. A solo developer can make architectural decisions in minutes that would take a team weeks of debate.

The practical implications for this roadmap are as follows:

**Prioritize ruthlessly.** Not everything in this roadmap needs to happen on the first pass. The system described across the twelve preceding documents is comprehensive and sophisticated. A solo developer attempting to implement every feature described in every document before trading a single demo order will burn out before Phase 3. The roadmap identifies the critical path -- the minimum set of features needed for each phase milestone -- and distinguishes it from the nice-to-have enhancements that can be deferred.

**Work in focused sprints.** Context-switching is the productivity killer for solo developers. When you are building the feature engineering pipeline, you should be thinking about nothing but the feature engineering pipeline. When you are configuring the Proxmox firewall, you should be thinking about nothing but the Proxmox firewall. The phase structure of this roadmap supports focused work: each phase has a clear theme and a clear boundary.

**Automate early.** Every minute spent writing a deployment script, a database migration tool, or a test harness pays back tenfold over the life of the project. A solo developer does not have the luxury of manual processes that take 15 minutes each time -- those 15 minutes add up to hours per week, and hours per week add up to weeks per year. Automate the repetitive tasks in Phase 0 and Phase 1, and you will thank yourself in every subsequent phase.

**Document as you build.** This might seem ironic given that you are reading the thirteenth document in a thirteen-document series, all of which were written before a single line of production code. But the advice stands: as you implement each phase, update the relevant documents with any deviations from the original design, any lessons learned, and any configuration specifics that the design documents could not anticipate. Future-you -- the person who has to debug a production issue at 2 AM during the Tokyo session -- will be grateful for past-you's documentation discipline.

### Timeline Flexibility

The weekly estimates in this roadmap are guidelines, not deadlines. They are based on reasonable assumptions about a solo developer working part-time (20-25 hours per week) on this project. If you have more time, phases will complete faster. If you encounter unexpected complications -- a ROCm driver that refuses to cooperate with VFIO passthrough, a broker API that changed its authentication scheme, a subtle data normalization bug that takes three days to diagnose -- phases will take longer. The estimates include approximately 20% buffer, but complex systems have a way of consuming buffers.

The critical constraint is not time; it is quality. A phase that takes six weeks instead of four but delivers a solid, well-tested foundation is vastly preferable to a phase that hits its four-week deadline but leaves behind a brittle, partially-tested codebase that will cause problems in every subsequent phase. Every shortcut taken in an early phase compounds as technical debt in later phases. Build slowly, build correctly, and the compound returns of quality will accelerate the later phases.

---

## 13.2 Prerequisites and Preparation (Phase 0)

**Duration:** 1-2 weeks
**Theme:** Lay the groundwork before writing a single line of application code
**Documents Referenced:** Document 01 (Vision), Document 02 (Infrastructure)

### Master Timeline Overview

Before diving into Phase 0, here is the full project timeline in ASCII Gantt chart format. This provides a bird's-eye view of the entire journey from preparation through go-live. Each row represents a phase, and each character represents approximately one week.

```
Phase 0: Prerequisites     [####]..................................  Weeks 0-2
Phase 1: Database + Data   .....[########]..........................  Weeks 1-4
Phase 2: AI/ML Models      ..............[################]..........  Weeks 5-12
Phase 3: MT5 + Risk Mgmt   ..............................[############]  Weeks 13-18
Phase 4: Monitoring        ......................................[########]  Weeks 19-22
Phase 5: Security + Test   ..............................................[########]  Weeks 23-26
Phase 6: Go-Live           ......................................................[######...  Weeks 27-32+
                           |    |    |    |    |    |    |    |    |    |    |    |    |    |
                           W0   W4   W8   W12  W16  W20  W24  W28  W32  W36  W40  W44  W48
```

### Dependency Graph

The phases have strict dependencies. No phase can begin until its predecessors are complete.

```
Phase 0 (Prerequisites)
    |
    v
Phase 1 (Database + Data Ingestion)
    |
    +----------------+
    |                |
    v                v
Phase 2 (AI/ML)    Phase 4 (Monitoring) [can start partially in parallel]
    |                |
    v                |
Phase 3 (MT5 + Risk)|
    |                |
    +--------+-------+
             |
             v
        Phase 5 (Security + Testing)
             |
             v
        Phase 6 (Go-Live)
```

Note: Phase 4 (Monitoring) can begin partially during Phase 2 or Phase 3 because basic Prometheus and Grafana infrastructure does not depend on the trading pipeline. However, the trading-specific dashboards require Phase 3 to be operational. The dependency graph above shows the critical path.

### 13.2.1 Hardware Procurement and Assembly

The MONEYMAKER V1 infrastructure runs on a single bare-metal server. As described in Document 01 (System Vision and Architecture Overview) and Document 02 (Proxmox Infrastructure), the hardware specification is:

| Component | Specification | Purpose |
|-----------|--------------|---------|
| CPU | AMD Ryzen 9 7950X (16 cores / 32 threads) | All VM workloads, multi-service concurrency |
| RAM | 128 GB DDR5-5600 (4x32 GB) | VM memory allocation across all services |
| Boot Drive | 1 TB NVMe (Samsung 990 Pro or equivalent) | Proxmox OS, VM images, ZFS metadata |
| Data Drive | 2 TB NVMe (for ZFS data pool) | Database storage, model artifacts, logs |
| UPS | 1000VA minimum (APC Back-UPS or equivalent) | Power protection for graceful shutdown |
| Network | Managed switch supporting VLANs (TP-Link TL-SG108E or similar) | VLAN segmentation per Document 02 |
| Case + Cooling | Mid-tower with adequate airflow | Thermal management for 24/7 operation |

**Checklist -- Hardware:**

- [ ] All components ordered and received
- [ ] Server assembled and POST-verified
- [ ] BIOS configured: enable IOMMU (AMD-Vi), enable SVM, set XMP for DDR5
- [ ] UPS connected and tested (simulate power loss, verify clean shutdown)
- [ ] Managed switch configured with VLANs per Document 02 topology
- [ ] Network cabling complete (server to switch, switch to router/internet)
- [ ] GPU installed and verified in BIOS (for later VFIO passthrough)
- [ ] NVMe drives detected and healthy (check SMART data)
- [ ] Thermal monitoring: idle temperatures below 45C for CPU, 40C for GPU

If the hardware is already assembled and operational, this sub-phase is a verification step rather than a procurement step. Walk through the checklist regardless, because a misconfigured BIOS setting can cause problems in later phases.

### 13.2.2 Proxmox VE Installation

Document 02 covers Proxmox installation and configuration in exhaustive detail. The Phase 0 objective is to get Proxmox running with the foundational infrastructure in place.

**Installation Steps:**

1. Download Proxmox VE 8.x ISO from the official site
2. Create bootable USB drive and install on the primary NVMe
3. Configure network interfaces:
   - Management interface on VLAN 1 (or untagged management network)
   - Trunk interface to managed switch for VLAN traffic
4. Create ZFS pool on the data NVMe:

   ```
   zpool create -f -o ashift=12 datapool /dev/nvme1n1
   zfs set compression=lz4 datapool
   zfs set atime=off datapool
   ```

5. Configure VLANs as Linux bridges per Document 02:
   - VLAN 10: Data Processing (data ingestion service)
   - VLAN 20: Data Storage (PostgreSQL, Redis)
   - VLAN 30: Internal Services
   - VLAN 40: Trading Intelligence (Algo Engine, MT5 Bridge)
   - VLAN 50: Monitoring (Prometheus, Grafana)
6. Configure basic Proxmox firewall rules (detailed hardening in Phase 5)
7. Enable NTP synchronization (critical for financial timestamps)
8. Create storage volumes for VM images and backups

**Checklist -- Proxmox:**

- [ ] Proxmox VE installed and accessible via web UI (https://<ip>:8006)
- [ ] ZFS pool created and healthy (`zpool status` shows ONLINE)
- [ ] All VLANs configured as Linux bridges
- [ ] Can ping between VLANs (before firewall lockdown)
- [ ] NTP synchronized (`timedatectl` shows NTP active)
- [ ] Proxmox backups configured to ZFS dataset
- [ ] SSH access configured with key-based authentication
- [ ] Proxmox subscription notice suppressed (community edition)

### 13.2.3 Development Environment Setup

Before building any MONEYMAKER service, the development environment must be consistent and reproducible.

**Python Environment:**

MONEYMAKER's Python services (Algo Engine, Risk Management, Dashboard) require Python 3.11 or later. The dependency manager is `uv` (preferred for its speed) or `poetry` as an alternative.

```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project structure
mkdir -p moneymaker-v1/{services,configs,scripts,tests,models,data}

# Initialize Python project
cd moneymaker-v1
uv init
uv python install 3.11

# Core dependencies (to be refined per service)
uv add pandas numpy torch scikit-learn lightgbm xgboost
uv add sqlalchemy psycopg2-binary redis zmq grpcio
uv add prometheus-client structlog pyyaml
```

**Go Environment (for Data Ingestion Service):**

```bash
# Install Go 1.22+
wget https://go.dev/dl/go1.22.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.22.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin

# Initialize Go module
cd moneymaker-v1/services/data-ingestion
go mod init github.com/moneymaker/data-ingestion
```

**Git Repository:**

```bash
cd moneymaker-v1
git init
git add .
git commit -m "Initial project structure"
```

Create a `.gitignore` that excludes model checkpoints (large binary files), API keys, environment files, and compiled binaries. Set up a remote repository on GitHub or GitLab for backup and version history.

**IDE Configuration:**

Configure your IDE (VS Code, PyCharm, or Neovim) with:

- Python language server (Pylance or Pyright)
- Go extension (gopls)
- SQL extension for PostgreSQL syntax
- YAML linting for configuration files
- Docker extension for container management
- Remote SSH extension (for developing directly on the Proxmox server VMs)

**Checklist -- Development Environment:**

- [ ] Python 3.11+ installed and working
- [ ] uv or poetry configured for dependency management
- [ ] Go 1.22+ installed and working
- [ ] Git repository initialized with proper .gitignore
- [ ] IDE configured with all necessary extensions
- [ ] Can SSH from development machine to Proxmox host
- [ ] Project directory structure created

### 13.2.4 Account Setup

Several external accounts are required before building begins.

**MetaTrader 5 Demo Account:**

Open a demo account with a broker that provides XAU/USD (Gold) and major forex pairs. The broker must support MetaTrader 5 and provide the Python MetaTrader5 package connectivity. Recommended brokers with good MT5 demo support: IC Markets, Pepperstone, FP Markets, or Exness. Document the server name, login number, and password -- these will be needed in Phase 3 when building the MT5 Bridge (Document 08).

**Data Provider API Keys:**

- Binance API key (for BTC/USD data, as described in Document 04)
- Bybit API key (optional, for derivatives and funding rate data)
- Alpha Vantage API key (free tier, for supplementary macro data)
- FRED API key (Federal Reserve Economic Data, for macroeconomic indicators)

**Telegram Bot:**

Create a Telegram bot via BotFather for notification delivery. This will be the primary alerting channel as described in Document 10 (Monitoring and Dashboard). Record the bot token and your chat ID.

**Checklist -- Accounts:**

- [ ] MT5 demo account created and credentials recorded securely
- [ ] Binance API key generated (read-only permissions sufficient for data)
- [ ] Telegram bot created, token and chat ID recorded
- [ ] GitHub/GitLab repository created and remote configured
- [ ] All credentials stored in a password manager (NOT in code or plaintext files)

### Phase 0 Deliverables

At the end of Phase 0, you should be able to answer "yes" to every item on this master validation list:

- [ ] Can SSH into Proxmox host from development machine
- [ ] Can access Proxmox web UI at https://<ip>:8006
- [ ] ZFS pool is online and healthy
- [ ] VLANs are configured and routable
- [ ] Can run `python3 --version` and see 3.11+
- [ ] Can run `go version` and see 1.22+
- [ ] Git repository exists with initial commit
- [ ] MT5 demo credentials are accessible
- [ ] Data provider API keys are accessible
- [ ] Telegram bot sends a test message successfully
- [ ] UPS is connected and protecting the server

Phase 0 is complete. The foundation is poured. Nothing exciting has happened yet, and that is exactly right. The excitement comes from building on a solid foundation, not from building in a rush on sand.

---

## 13.3 Phase 1 -- Foundation: Database and Data Ingestion (Weeks 1-4)

**Goal:** Collect and store real-time market data reliably, continuously, and correctly.
**Theme:** Data is the lifeblood of the system. Without clean, reliable data, nothing downstream matters.
**Documents Referenced:** Document 04 (Data Ingestion), Document 05 (Database Architecture), Document 03 (Microservices Communication)

### Phase 1 Timeline

```
Week 1        Week 2        Week 3        Week 4
[DB Setup  ]  [Data Svc   ] [Data Svc   ] [Enrichment ]
[Schema    ]  [Connectors ] [Quality    ] [Indicators ]
[Redis     ]  [Normalize  ] [Gap Detect ] [Monitoring ]
[Backups   ]  [Store      ] [Validate   ] [Soak Test  ]
```

### Week 1-2: Database Setup

The database is the memory of the entire ecosystem. As Document 05 (Database Architecture and Time-Series Storage) establishes: "A trading system without persistent storage is a fish with the memory span of three seconds." The database must be operational before any data can flow.

**Deploy PostgreSQL VM on Proxmox:**

Create a new VM on VLAN 20 (Data Storage) per the topology defined in Document 02. Allocate resources conservatively for initial development -- they can be increased later:

| Resource | Allocation | Rationale |
|----------|-----------|-----------|
| vCPUs | 4 | Sufficient for initial data ingestion load |
| RAM | 16 GB | PostgreSQL shared_buffers + OS overhead |
| Disk | 200 GB (ZFS-backed) | Initial market data storage with compression |
| Network | VLAN 20 (10.0.2.x) | Isolated data storage network |

**Install PostgreSQL 16 and TimescaleDB:**

Follow the installation procedure from Document 05, Section 2.1. PostgreSQL 16 provides the ACID-compliant relational foundation, and TimescaleDB extends it with hypertable functionality for time-series data. The key configuration parameters from Document 05:

```
shared_buffers = 4GB            # 25% of RAM
effective_cache_size = 12GB     # 75% of RAM
work_mem = 256MB
maintenance_work_mem = 1GB
max_connections = 200
wal_level = replica
```

**Create Schema:**

Implement the core tables defined in Document 05, Section 3. The initial schema includes:

```sql
-- Market Data Tables (Document 05, Section 3.1)
CREATE TABLE market_ticks (
    timestamp    TIMESTAMPTZ NOT NULL,
    symbol       TEXT        NOT NULL,
    source       TEXT        NOT NULL,
    bid          NUMERIC(20,8),
    ask          NUMERIC(20,8),
    last_price   NUMERIC(20,8),
    volume       NUMERIC(20,8),
    spread       NUMERIC(20,8)
);
SELECT create_hypertable('market_ticks', 'timestamp',
    chunk_time_interval => INTERVAL '1 day');

-- OHLCV Bars at multiple timeframes
CREATE TABLE ohlcv_bars (
    timestamp    TIMESTAMPTZ NOT NULL,
    symbol       TEXT        NOT NULL,
    timeframe    TEXT        NOT NULL,  -- M1, M5, M15, H1, H4, D1
    source       TEXT        NOT NULL,
    open         NUMERIC(20,8) NOT NULL,
    high         NUMERIC(20,8) NOT NULL,
    low          NUMERIC(20,8) NOT NULL,
    close        NUMERIC(20,8) NOT NULL,
    volume       NUMERIC(20,8),
    tick_volume  INTEGER,
    spread       NUMERIC(20,8)
);
SELECT create_hypertable('ohlcv_bars', 'timestamp',
    chunk_time_interval => INTERVAL '7 days');

-- Symbol Metadata
CREATE TABLE symbol_metadata (
    symbol          TEXT PRIMARY KEY,
    display_name    TEXT,
    asset_class     TEXT,
    base_currency   TEXT,
    quote_currency  TEXT,
    pip_size        NUMERIC(20,10),
    lot_size        NUMERIC(20,8),
    min_lot         NUMERIC(20,8),
    max_lot         NUMERIC(20,8),
    trading_hours   JSONB,
    last_updated    TIMESTAMPTZ DEFAULT NOW()
);
```

**Configure TimescaleDB Features:**

- Create continuous aggregates for common timeframe rollups (M1 to M5, M5 to M15, etc.) as specified in Document 05, Section 4.2
- Enable compression on chunks older than 7 days (Document 05, Section 4.3)
- Set retention policies: tick data retained for 30 days, M1 bars for 6 months, H1+ bars indefinitely (Document 05, Section 4.4)

**Set Up Redis:**

Deploy Redis on the same VM (or a dedicated container within the VM) on VLAN 20. Redis serves two roles in MONEYMAKER, as described in Document 05, Section 5:

1. **Caching layer:** Latest prices, indicator values, and frequently-queried aggregations stored in Redis for sub-millisecond access
2. **Pub/Sub messaging:** Real-time event distribution using channels like `moneymaker:ticks:XAUUSD`, `moneymaker:bars:M1:XAUUSD`, and `moneymaker:events:system`

Configure Redis per Document 05, Section 5.3: bind to VLAN 20 interface only, set maxmemory to 2 GB with allkeys-lru eviction policy, enable AOF persistence for event durability.

**Implement Backup Procedures:**

- ZFS snapshot schedule: hourly snapshots retained for 24 hours, daily snapshots retained for 30 days
- pg_dump weekly backup to secondary storage
- Test backup restoration: drop and restore database from snapshot to verify integrity

**Validation Criteria -- Week 1-2:**

- [ ] PostgreSQL VM running on VLAN 20
- [ ] Can connect to database from other VLANs (data ingestion VM, development machine)
- [ ] All tables created, hypertables active
- [ ] Can INSERT a test row into market_ticks and query it back
- [ ] TimescaleDB continuous aggregates computing correctly
- [ ] Redis running and accepting connections
- [ ] Can PUBLISH/SUBSCRIBE on Redis channels
- [ ] ZFS snapshots automated and verified
- [ ] pg_dump backup tested and restoration verified

### Week 2-3: Data Ingestion Service

With the database operational, the Data Ingestion Service (Document 04) can begin populating it. This is the Go-based gateway described in Document 04 (Data Ingestion and Real-Time Market Data Service) and referenced in Document 03 (Microservices Architecture) as the first service in the data flow pipeline.

**Build the Data Fetching Service:**

Implement the Go gateway architecture from Document 04, Section 3. The core components are:

1. **Connection Manager:** Establishes and maintains WebSocket connections to data sources. Implements automatic reconnection with exponential backoff (Document 04, Section 4). Each connection runs in its own goroutine with a dedicated heartbeat goroutine.

2. **Exchange Adapters:** Implement the adapter interface for each data source:
   - MT5 adapter: Connect to MetaTrader 5 via the Python bridge (copy_rates_from_pos, copy_ticks_from) as described in Document 04, Section 2.2
   - Binance WebSocket adapter: Subscribe to `@kline` and `@trade` streams for BTC/USD (Document 04, Section 2.1)
   - Yahoo Finance adapter: REST-based polling for traditional market data (Document 04, Section 2.2)

3. **Normalization Pipeline:** Convert exchange-specific data formats into the canonical `MarketTick` and `OHLCVBar` structures defined in Document 04, Section 5. This includes symbol name normalization (Kraken's "XBT" to canonical "BTC"), timestamp alignment to UTC, and decimal precision standardization.

4. **Storage Writer:** Batch-insert normalized data into PostgreSQL using prepared statements and connection pooling. Target throughput: 10,000+ inserts per second for tick data.

5. **Distribution Layer:** Publish normalized data to:
   - ZeroMQ PUB socket (Document 03, Section 3 -- for real-time streaming to Algo Engine)
   - Redis channels (Document 05, Section 5.1 -- for caching and event notification)

**Implement Data Normalization:**

Per Document 04, Section 5, all incoming data must be normalized to a canonical format before storage or distribution. The normalization pipeline handles:

- Symbol mapping: Exchange-specific symbols to MONEYMAKER canonical names
- Timestamp normalization: All timestamps converted to UTC with nanosecond precision
- Price normalization: Consistent decimal precision per instrument
- Volume normalization: Unified volume representation across exchanges
- Spread computation: Calculate bid-ask spread where not provided natively

**Error Handling:**

Document 04, Section 4 specifies the reconnection and error handling strategy. Implement:

- Exponential backoff on connection failure (initial 1s, max 60s, with jitter)
- Data gap detection: track the timestamp of the last received message per source, alert if gap exceeds configurable threshold
- Rate limit handling: respect per-exchange rate limits as documented in Document 04, Section 2.1 (Binance: 1,200 requests/minute weight-based; Yahoo Finance: 2 requests/second)
- Graceful degradation: if one source fails, continue operating with remaining sources

**Validation Criteria -- Week 2-3:**

- [ ] Data Ingestion Service starts and connects to all configured data sources
- [ ] Real-time tick data flowing into market_ticks table
- [ ] OHLCV bars at M1, M5, M15, H1, H4, D1 timeframes populating ohlcv_bars table
- [ ] Data is normalized: consistent symbol names, UTC timestamps, correct precision
- [ ] ZeroMQ PUB socket is broadcasting data (verified with a test subscriber)
- [ ] Redis cache is being populated with latest prices
- [ ] Reconnection works: kill a WebSocket connection and verify automatic recovery
- [ ] No data gaps detected over 24-hour continuous operation test
- [ ] Memory usage stable (no leaks) over 24-hour operation

### Week 3-4: Data Quality and Enrichment

Raw data ingestion is necessary but not sufficient. Before the Algo Engine can consume this data, it must be validated, enriched, and augmented with computed indicators.

**Data Validation Rules:**

Implement the data quality checks described in Document 04, Section 5:

- **Price sanity checks:** Reject ticks where price deviates more than 5% from the previous tick (configurable per instrument). Gold does not move $100 in a single tick; if the data says it did, the data is wrong.
- **Timestamp ordering:** Every tick must have a timestamp greater than or equal to the previous tick for the same source and symbol. Out-of-order timestamps indicate a data feed issue.
- **Spread validation:** Bid must be less than ask. Spread must be within historically normal range for the instrument.
- **Volume validation:** Volume must be non-negative. Zero-volume bars should be flagged (may indicate market closure or data gap).
- **Duplicate detection:** Detect and discard duplicate ticks (same timestamp, same price, same source).

**Gap Detection and Filling:**

- Monitor for gaps in M1 bar data. If an expected M1 bar is missing (no data received during that minute), flag the gap in a `data_quality_events` table.
- For short gaps (< 5 minutes), attempt backfill from REST API.
- For longer gaps, log the event and notify via Telegram.
- Never fabricate data to fill gaps. Missing data is better than invented data.

**Basic Technical Indicator Computation:**

Implement the initial set of technical indicators that will be used by the Algo Engine (Document 07, Section 3). Start with the core indicators:

| Indicator | Parameters | Purpose |
|-----------|-----------|---------|
| SMA | 20, 50, 200 periods | Trend identification |
| EMA | 12, 26, 50 periods | Trend identification with recency bias |
| RSI | 14 periods | Momentum and overbought/oversold |
| MACD | 12, 26, 9 | Momentum and trend changes |
| Bollinger Bands | 20, 2.0 std | Volatility and mean reversion |
| ATR | 14 periods | Volatility measurement (used for position sizing in Document 09) |
| Stochastic | 14, 3, 3 | Momentum oscillator |
| ADX | 14 periods | Trend strength |

Store computed indicators alongside the raw data in a dedicated `computed_indicators` table or as additional columns on the OHLCV bars table, per the schema design in Document 05.

**Basic Monitoring:**

Set up initial Prometheus metrics for the data ingestion service:

- `moneymaker_data_ticks_total` -- counter of total ticks received per source
- `moneymaker_data_bars_total` -- counter of bars stored per timeframe
- `moneymaker_data_latency_seconds` -- histogram of data arrival latency
- `moneymaker_data_gaps_total` -- counter of detected data gaps
- `moneymaker_data_last_tick_timestamp` -- gauge of most recent tick time per source

These metrics will be consumed by the full monitoring stack in Phase 4, but having them emitted from the start enables early debugging and validation.

**Validation Criteria -- Week 3-4:**

- [ ] Data validation rules catching invalid data (verified with intentional bad data injection)
- [ ] Gap detection operational and logging detected gaps
- [ ] All 8 core technical indicators computing correctly (spot-check against TradingView or other reference)
- [ ] Indicators stored in database and queryable
- [ ] Prometheus metrics endpoint exposed and returning valid data
- [ ] System has been running continuously for 1+ week without manual intervention
- [ ] Total data volume and growth rate measured and within storage capacity

### Phase 1 Milestone

At the end of Phase 1, MONEYMAKER has its sensory system. The database is filling with real-time market data 24 hours a day, 5 days a week (for forex; 24/7 for crypto). OHLCV bars are computed at multiple timeframes. Core technical indicators are computed and stored. Basic data quality monitoring is operational. The system is not yet intelligent -- it cannot make trading decisions -- but it has the raw material from which intelligence will be forged.

**Phase 1 Completion Checklist:**

- [ ] PostgreSQL + TimescaleDB operational with full schema
- [ ] Redis operational for caching and pub/sub
- [ ] Data Ingestion Service running continuously without intervention
- [ ] Multiple data sources connected and feeding data
- [ ] OHLCV bars at M1, M5, M15, H1, H4, D1 timeframes
- [ ] Core technical indicators computed and stored
- [ ] Data quality validation active
- [ ] ZFS backups automated and tested
- [ ] Prometheus metrics emitted
- [ ] No data gaps in last 7 days of operation

**Phase 1 Risks and Mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Data source API changes | Medium | High | Implement adapter pattern; changes isolated to single adapter |
| API rate limit exceeded | Medium | Medium | Conservative rate limiting; exponential backoff; multiple sources |
| Data quality issues (wrong prices) | Medium | High | Multi-source cross-validation; sanity checks on every tick |
| PostgreSQL performance under load | Low | Medium | TimescaleDB optimizations; connection pooling; index tuning |
| ZFS pool failure | Very Low | Very High | ZFS scrub schedule; backup verification; UPS protection |

---

## 13.4 Phase 2 -- Intelligence: Feature Engineering and Statistical Models (Weeks 5-12)

**Goal:** Build statistical models that analyze market data and produce calibrated trading signals with confidence scores.
**Theme:** Transform raw data into actionable intelligence through quantitative analysis.
**Documents Referenced:** Document 05 (Database)

### Phase 2 Timeline

```
Week 5-6      Week 7-8      Week 9-10     Week 11-12
[Feature Eng] [Tree Models ] [Advanced   ] [Ensemble   ]
[Frac Diff  ] [LightGBM   ] [Strategies ] [Confidence ]
[Labeling   ] [XGBoost    ] [Regime Rout] [Fallback   ]
[Selection  ] [Walk-Fwd   ] [Validation ] [Calibration]
```

### Week 5-6: Feature Engineering Pipeline

The feature engineering pipeline transforms raw OHLCV data into a rich feature space that captures the multi-dimensional structure of market behavior. This is a critical component of the Algo Engine's signal generation pipeline.

**Implement Full Feature Engineering:**

Expand the basic indicators from Phase 1 into the complete 40+ feature set described in Document 07:

**Trend Features:**

- Simple Moving Averages (SMA) at 5, 10, 20, 50, 100, 200 periods
- Exponential Moving Averages (EMA) at 12, 26, 50, 100, 200 periods
- Moving average crossover signals (golden cross, death cross)
- Linear regression slope over rolling windows
- Ichimoku Cloud components (Tenkan-sen, Kijun-sen, Senkou Span A/B)

**Momentum Features:**

- RSI at 14, 21, 7 periods
- MACD line, signal line, histogram
- Stochastic %K and %D
- Rate of Change (ROC) at multiple periods
- Williams %R
- Commodity Channel Index (CCI)

**Volatility Features:**

- ATR at 14, 21 periods
- Bollinger Band width and %B
- Keltner Channel width
- Standard deviation of returns
- Parkinson volatility estimator
- Yang-Zhang volatility estimator

**Volume Features:**

- Volume Moving Average ratio
- On-Balance Volume (OBV)
- Volume Rate of Change
- Accumulation/Distribution Line
- Money Flow Index (MFI)

**Price Structure Features:**

- Higher High / Lower Low patterns
- Support/resistance levels (rolling pivot points)
- Candlestick pattern recognition (doji, engulfing, hammer)
- Price relative to key MAs (distance from SMA 200 as percentage)

**Fractional Differencing for Stationarity:**

As described in Document 06, Section 3 and referenced from Marcos Lopez de Prado's methodology, apply fractional differencing to price series to achieve stationarity while preserving memory. The differencing parameter d is in the range [0.35, 0.55], determined by the minimum value that passes the Augmented Dickey-Fuller test at the 95% confidence level. This is a critical preprocessing step: statistical models struggle with non-stationary data, but integer differencing (d=1) destroys the memory structure that contains predictive information.

```python
def fractional_diff(series, d, threshold=1e-5):
    """Apply fractional differencing with weight threshold."""
    weights = compute_weights(d, len(series), threshold)
    result = pd.Series(index=series.index, dtype=float)
    for i in range(len(weights), len(series)):
        result.iloc[i] = np.dot(
            weights.flatten(),
            series.iloc[i - len(weights):i].values
        )
    return result.dropna()
```

**Feature Normalization and Scaling:**

- Z-score normalization using rolling statistics (window = 252 trading days)
- Robust scaling for features with outliers (using median and IQR instead of mean and std)
- Clip extreme values at +/- 5 standard deviations
- Store scaler parameters alongside model artifacts for consistency

**Feature Selection:**

Not all 40+ features are equally informative. Apply feature selection techniques to identify the most predictive subset:

- Mutual Information: rank features by mutual information with the target variable
- Feature importance from preliminary LightGBM model
- Remove features with correlation > 0.95 to reduce multicollinearity
- Target: reduce to 20-30 most informative features for model input

**Triple Barrier Labeling:**

Implement the Triple Barrier labeling method for generating training targets. For each bar, define three barriers:

1. **Upper barrier (take profit):** Price reaches ATR * multiplier above entry
2. **Lower barrier (stop loss):** Price reaches ATR * multiplier below entry
3. **Time barrier (expiry):** Maximum holding period exceeded without touching either price barrier

The label is determined by which barrier is touched first:

- Upper barrier first: BUY (+1)
- Lower barrier first: SELL (-1)
- Time barrier first: HOLD (0) or assigned based on unrealized P&L at expiry

This labeling approach, borrowed from quantitative finance literature, is superior to simple future-return labeling because it accounts for the path-dependence of trading outcomes. A bar that eventually reaches the profit target but first triggers the stop loss is labeled differently than one that moves directly to profit.

**Validation Criteria -- Week 5-6:**

- [ ] Full 40+ feature pipeline implemented and tested
- [ ] Features are numerically stable (no NaN, no Inf, no extreme outliers)
- [ ] Fractional differencing applied; ADF test confirms stationarity
- [ ] Feature correlation matrix computed; redundant features identified
- [ ] Feature importance ranking produced
- [ ] Triple Barrier labels generated for 2+ years of historical data
- [ ] Label distribution is reasonable (not severely imbalanced)
- [ ] Feature pipeline produces identical output on same input (deterministic)

### Week 7-8: ML Model Development -- Tree-Based Models

Start with interpretable tree-based models. This follows the "make it work, make it right, make it fast" principle: tree-based models train quickly, are easy to debug, and provide strong baselines.

**LightGBM and XGBoost:**

Train gradient-boosted tree models:

```python
import lightgbm as lgb
import xgboost as xgb

# LightGBM configuration
lgb_params = {
    'objective': 'multiclass',
    'num_class': 3,  # BUY, HOLD, SELL
    'metric': 'multi_logloss',
    'num_leaves': 63,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'min_child_samples': 20,
    'reg_alpha': 0.1,
    'reg_lambda': 0.1,
    'n_estimators': 1000,
    'early_stopping_rounds': 50
}
```

**Training on Historical Data:**

- Minimum 2 years of historical data required for meaningful training
- Training set: older 70% of data
- Validation set: next 15% of data
- Test set: most recent 15% of data (never touched during development)

**Walk-Forward Validation:**

Implement walk-forward validation instead of simple train/test split or k-fold cross-validation. Walk-forward validation respects the temporal ordering of financial data:

```
Window 1: Train [Jan 2023 - Dec 2023]  Test [Jan 2024 - Mar 2024]
Window 2: Train [Apr 2023 - Mar 2024]  Test [Apr 2024 - Jun 2024]
Window 3: Train [Jul 2023 - Jun 2024]  Test [Jul 2024 - Sep 2024]
Window 4: Train [Oct 2023 - Sep 2024]  Test [Oct 2024 - Dec 2024]
Window 5: Train [Jan 2024 - Dec 2024]  Test [Jan 2025 - Mar 2025]
```

Aggregate performance across all test windows. If the model shows positive performance on some windows but negative on others, investigate whether the failing windows correspond to specific market regimes.

**Hyperparameter Optimization:**

Use Optuna for Bayesian hyperparameter optimization:

```python
import optuna

def objective(trial):
    params = {
        'num_leaves': trial.suggest_int('num_leaves', 15, 127),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'feature_fraction': trial.suggest_float('feature_fraction', 0.5, 1.0),
        'bagging_fraction': trial.suggest_float('bagging_fraction', 0.5, 1.0),
        'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
    }
    # Walk-forward validation with these params
    return avg_sharpe_ratio_across_windows(params)

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=200)
```

**Model Versioning:**

Store every trained model with its metadata in the strategy registry:

- Model architecture and hyperparameters
- Training data window (start date, end date)
- Feature list and scaler parameters
- Validation metrics: accuracy, Sharpe ratio, win rate, max drawdown
- Walk-forward performance per window
- Model file path and checksum

**Validation Criteria -- Week 7-8:**

- [ ] LightGBM and XGBoost models trained successfully
- [ ] Walk-forward validation implemented and producing per-window results
- [ ] Models show positive expectancy on out-of-sample data (Sharpe > 0.5)
- [ ] Hyperparameter optimization completed (100+ Optuna trials)
- [ ] Model artifacts stored in registry with full metadata
- [ ] Feature importance analysis completed
- [ ] Overfitting check: training performance vs validation performance gap < 20%

### Week 9-10: Advanced Strategy Development and Regime Routing

With tree-based baselines established, build advanced rule-based strategies that leverage regime classification and multi-timeframe analysis.

**Regime-Aware Strategy Routing:**

Implement strategy routing based on detected market regime. Different strategies perform better in different market conditions:

- **Trending regime:** Trend-following strategies (moving average crossovers, breakout detection)
- **Mean-reverting regime:** Mean-reversion strategies (Bollinger Band reversals, RSI extremes)
- **High-volatility regime:** Conservative strategies with wider stops and smaller positions
- **Low-volatility regime:** Range-trading strategies with tighter parameters

**Multi-Timeframe Confluence:**

Build strategies that confirm signals across multiple timeframes:

- M15 for entry timing
- H1 for trend direction
- H4 for major support/resistance levels
- Require agreement across at least 2 timeframes before emitting a signal

**COPER Experience Bank:**

Implement the COPER (Contextual Pattern Experience Repository) system:

- Store market state vectors alongside their outcomes
- Use cosine similarity to find historically similar market states
- Weight recent experiences more heavily than old ones
- Require minimum confidence threshold before using historical patterns

**Validation Criteria -- Week 9-10:**

- [ ] Regime-aware routing implemented and tested
- [ ] Multi-timeframe confluence producing filtered signals
- [ ] COPER experience bank storing and retrieving patterns
- [ ] Strategies produce meaningful signals (not random, not constant)
- [ ] Walk-forward validation shows positive expectancy across regimes

### Week 11-12: Ensemble and Confidence System

Individual models have strengths and weaknesses. The ensemble combines them to produce more robust predictions than any single model.

**Ensemble Architecture:**

The ensemble combines multiple rule-based and statistical model predictions:

```
LightGBM -----> [weight: 0.30]
XGBoost  -----> [weight: 0.25]  ---> Weighted Average ---> Final Signal
COPER --------> [weight: 0.25]
Technical ----> [weight: 0.20]
```

Weights are determined by each model's walk-forward validation Sharpe ratio, normalized to sum to 1.0. Models with negative out-of-sample Sharpe are excluded from the ensemble (weight set to 0).

**Confidence Scoring System (0-100):**

As specified in Document 07, Section 6, the confidence score reflects how certain the ensemble is about its prediction. It is computed from:

1. **Model agreement:** How many models agree on the direction? All 5 agree = high confidence base. 3/5 agree = moderate confidence. Split = low confidence.
2. **Probability margin:** How far is the winning class probability from the runner-up? 0.8 vs 0.1 = high margin. 0.4 vs 0.35 = low margin.
3. **Regime alignment:** Is the predicted action consistent with the current market regime? Buying in a downtrend regime reduces confidence.
4. **Historical accuracy:** How accurate has the model been recently (last 50 predictions)? Decaying accuracy reduces confidence.

```python
def compute_confidence(ensemble_probs, model_agreements, regime, recent_accuracy):
    base_confidence = model_agreement_score(model_agreements)  # 0-40
    margin_bonus = probability_margin_score(ensemble_probs)     # 0-30
    regime_bonus = regime_alignment_score(regime)                # 0-20
    accuracy_bonus = recent_accuracy_score(recent_accuracy)     # 0-10
    return min(100, base_confidence + margin_bonus + regime_bonus + accuracy_bonus)
```

**Confidence Gating:**

Document 07, Section 6 defines the confidence gating system -- a series of gates that a signal must pass through before it can trigger a trade:

1. **Maturity Gate:** The model must have been in production for at least N hours with stable predictions. A freshly deployed model starts with zero confidence regardless of its prediction.
2. **Drift Detection Gate:** If the model's recent prediction accuracy has drifted below a threshold (measured by comparing predictions to actual outcomes with a lag), confidence is capped.
3. **Silence Rule Gate:** After a significant loss, the system enters a "silence period" where confidence is reduced for a configurable duration (1-4 hours). This prevents revenge trading.

**Fallback Tier System:**

As described in Document 07, Section 7, the system implements a 4-tier fallback:

```
Tier 1: COPER (Contextual Prediction Experience Replay)
    |--- If similar historical context found with high match, use experience
    |
    v (if no match or low confidence)
Tier 2: ML Ensemble
    |--- Use ensemble prediction with confidence gating
    |
    v (if confidence below threshold)
Tier 3: Technical Signal Aggregation
    |--- Aggregate simple technical signals (MA crossovers, RSI extremes)
    |
    v (if technical signals ambiguous)
Tier 4: Conservative / Hold
    |--- Do nothing. Wait for clearer signal.
```

**Model Evaluation Metrics:**

Evaluate the complete ensemble using trading-specific metrics:

| Metric | Target | Description |
|--------|--------|-------------|
| Sharpe Ratio | > 1.0 | Risk-adjusted return |
| Win Rate | > 45% | Percentage of profitable trades |
| Profit Factor | > 1.3 | Gross profit / Gross loss |
| Maximum Drawdown | < 20% | Largest peak-to-trough decline |
| Calmar Ratio | > 0.5 | Annualized return / Max drawdown |
| Average Win / Average Loss | > 1.5 | Reward-to-risk ratio |

**Validation Criteria -- Week 11-12:**

- [ ] Ensemble produces predictions and confidence scores
- [ ] Ensemble outperforms best individual model on out-of-sample data
- [ ] Confidence scores are calibrated: high-confidence predictions are more accurate than low-confidence ones
- [ ] Confidence gating correctly filters low-quality signals
- [ ] Fallback tiers activate when expected (test by degrading model quality)
- [ ] Sharpe ratio > 1.0 on backtested results
- [ ] All model artifacts versioned and stored in registry

### Phase 2 Milestone

At the end of Phase 2, MONEYMAKER has its intelligence. The Algo Engine can consume market data, compute features, classify regimes, produce ensemble predictions with calibrated confidence scores, and fall back gracefully when confidence is low. The system cannot yet trade -- it has no connection to a broker and no risk management -- but it can demonstrate its analytical capability on historical data and in real-time on live market data (without execution).

**Phase 2 Completion Checklist:**

- [ ] Feature engineering pipeline operational (40+ features)
- [ ] Fractional differencing applied and stationarity verified
- [ ] Triple Barrier labeling implemented
- [ ] LightGBM and XGBoost models trained with walk-forward validation
- [ ] Transformer, BiLSTM, and Dilated CNN models trained on GPU
- [ ] Ensemble architecture combining all models
- [ ] Confidence scoring system producing calibrated scores (0-100)
- [ ] Confidence gating filtering low-quality signals
- [ ] 4-tier fallback system implemented
- [ ] Backtested Sharpe ratio > 1.0
- [ ] All models versioned in model registry with full metadata
- [ ] GPU passthrough stable for extended training runs

**Phase 2 Risks and Mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Model overfitting | High | Very High | Walk-forward validation; regularization; label smoothing; ensemble |
| GPU compatibility (ROCm on RDNA 4) | Medium | High | HSA_OVERRIDE_GFX_VERSION; fallback to CPU training if needed |
| Insufficient historical data quality | Medium | High | Multiple data sources; cross-validation of prices |
| Feature engineering bugs | Medium | High | Unit tests for every feature; comparison with reference implementations |
| Training instability (NaN gradients) | Medium | Medium | Gradient clipping; learning rate warmup; numerical stability checks |

---

## 13.5 Phase 3 -- Execution: MT5 Bridge and Risk Management (Weeks 13-18)

**Goal:** Connect AI decisions to trade execution with comprehensive safety systems that prevent catastrophic loss.
**Theme:** The bridge between intelligence and action, guarded by risk at every step.
**Documents Referenced:** Document 08 (MT5 Bridge), Document 09 (Risk Management), Document 03 (Communication)

### Phase 3 Timeline

```
Week 13-14    Week 15-16    Week 17-18
[MT5 VM     ] [Risk Svc   ] [Integration]
[Python Pkg ] [Ckt Break  ] [End-to-End ]
[Exec Bridge] [Position   ] [Paper Trade]
[Orders     ] [Kill Switch] [Soak Test  ]
```

### Week 13-14: MetaTrader 5 Integration

The MT5 Bridge is the only component in MONEYMAKER that directly interacts with the broker. As described in Document 08, it translates the Algo Engine's trading signals into MetaTrader 5 orders. This is the action layer described in Document 01 as "Pillar 3 -- Trade Execution."

**Windows VM Setup on Proxmox:**

MetaTrader 5 requires Windows. Create a Windows 10/11 VM on Proxmox VLAN 40 (Trading Intelligence):

| Resource | Allocation | Rationale |
|----------|-----------|-----------|
| vCPUs | 2 | MT5 is lightweight |
| RAM | 4 GB | Sufficient for MT5 + Python bridge |
| Disk | 50 GB | Windows + MT5 installation |
| Network | VLAN 40 | Trading intelligence network |

Install MetaTrader 5, log in with the demo account credentials from Phase 0, and enable "Algorithmic Trading" in MT5 settings.

**Python MetaTrader5 Package Integration:**

Install the Python MetaTrader5 package in the Windows VM:

```python
pip install MetaTrader5

import MetaTrader5 as mt5

# Initialize connection
if not mt5.initialize():
    print(f"MT5 initialization failed: {mt5.last_error()}")
    sys.exit(1)

# Log in to account
authorized = mt5.login(
    login=DEMO_LOGIN,
    password=DEMO_PASSWORD,
    server=BROKER_SERVER
)

# Verify connection
account_info = mt5.account_info()
print(f"Connected: {account_info.name}, Balance: {account_info.balance}")
```

**Execution Bridge Service:**

Build the service that receives AI decisions and translates them to MT5 orders. The bridge exposes a gRPC interface (Document 03, Section 3) that the Algo Engine calls with trading signals:

```protobuf
service ExecutionBridge {
    rpc SubmitOrder(OrderRequest) returns (OrderResponse);
    rpc ClosePosition(CloseRequest) returns (CloseResponse);
    rpc ModifyPosition(ModifyRequest) returns (ModifyResponse);
    rpc GetPositions(PositionsRequest) returns (PositionsResponse);
    rpc GetAccountInfo(AccountRequest) returns (AccountResponse);
}
```

**Order Types:**

Implement support for the order types specified in Document 08:

- **Market orders:** Immediate execution at current price. Used for the majority of entries and exits.
- **Limit orders:** Execute when price reaches a specified level. Used for entries at support/resistance.
- **Stop orders:** Execute when price breaks through a specified level. Used for breakout entries.
- **Stop-loss and take-profit:** Attached to every position without exception. The risk management service (Phase 3, Week 15-16) determines the levels.

**Position Management:**

- Open positions: send order to MT5 with all parameters (symbol, volume, type, SL, TP, magic number, comment)
- Close positions: close by ticket number, close all positions for a symbol, close partial position
- Modify positions: update stop-loss, take-profit, or trailing stop level
- Position tracking: maintain in-memory state of all open positions, synchronized with MT5 every second

**Slippage and Execution Quality Monitoring:**

Record for every executed order:

- Requested price vs actual fill price (slippage)
- Order submission time vs fill time (execution latency)
- Requote count
- Partial fill detection

Store execution quality metrics in the database (Document 05) for ongoing analysis.

**Validation Criteria -- Week 13-14:**

- [ ] Windows VM running on Proxmox with MT5 installed
- [ ] Python MetaTrader5 package connects to demo account
- [ ] Can submit market orders programmatically (buy and sell)
- [ ] Can submit limit and stop orders
- [ ] Can close positions by ticket number
- [ ] Can modify SL/TP on open positions
- [ ] Execution quality metrics being recorded
- [ ] gRPC interface operational (test with a simple client)
- [ ] Account info retrieval working (balance, equity, margin)

### Week 15-16: Risk Management Service

The risk management service is the guardian of the system. As described in Document 09, it sits between the Algo Engine and the Execution Bridge, inspecting every proposed trade before it is allowed to execute. No trade bypasses the risk gate. This is an architectural invariant, not a suggestion.

**Circuit Breakers:**

Implement the multi-level circuit breaker system from Document 09:

| Level | Threshold | Action | Reset Condition |
|-------|-----------|--------|-----------------|
| Daily | -2% of starting equity | Halt all new trades for remainder of day | New trading day (midnight UTC) |
| Weekly | -5% of starting equity | Halt all new trades for remainder of week | New trading week (Monday 00:00 UTC) |
| Monthly | -10% of starting equity | Halt all new trades for remainder of month | New month start |
| Maximum | -25% of peak equity | KILL SWITCH: close all positions, halt system | Manual reset only |

Each circuit breaker is independent. The daily breaker can trip without triggering the weekly breaker. The maximum drawdown breaker is a hard limit that requires human intervention to reset -- this prevents the system from resuming trading after a catastrophic loss without human review.

**Position Sizing -- Half-Kelly Criterion:**

Implement the position sizing algorithm from Document 09:

```python
def compute_position_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    account_equity: float,
    atr: float,
    risk_per_trade: float = 0.02  # 2% max risk per trade
) -> float:
    # Kelly criterion
    kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    # Half-Kelly for safety
    half_kelly = kelly_fraction / 2.0
    # Cap at max risk per trade
    position_risk = min(half_kelly, risk_per_trade)
    # Convert to lot size using ATR for stop distance
    risk_dollars = account_equity * position_risk
    stop_distance = atr * 2.0  # 2x ATR stop loss
    lot_size = risk_dollars / stop_distance
    # Round to broker lot step
    return round_to_lot_step(lot_size)
```

**Spiral Protection:**

Detect consecutive loss sequences and respond with increasingly conservative behavior:

```
3 consecutive losses: reduce position size by 25%
5 consecutive losses: reduce position size by 50%
7 consecutive losses: halt trading for 4 hours
10 consecutive losses: halt trading for 24 hours, alert operator
```

This prevents the "death spiral" where a model that has entered a losing regime continues to trade at full size, compounding losses with each trade.

**Kill Switch:**

Implement both automatic and manual kill switch functionality:

- **Automatic:** Triggered by maximum drawdown circuit breaker (25% from peak equity)
- **Manual:** Accessible via:
  - Telegram command: `/kill` sent to the MONEYMAKER bot
  - API endpoint: `POST /api/kill-switch` on the risk management service
  - Physical: SSH into the risk management VM and execute `moneymaker-kill.sh`
- **Kill switch action:** Close all open positions at market price, cancel all pending orders, halt all new order submission, send Telegram alert with full position summary

**Exposure Limits:**

| Limit Type | Threshold | Enforcement |
|------------|-----------|-------------|
| Per-symbol | Max 5% of equity in any single symbol | Reject orders that would exceed |
| Per-sector | Max 15% of equity in correlated symbols | Block correlated entries |
| Total | Max 30% of equity in total open risk | Reject new orders until exposure reduces |
| Margin | Never exceed 50% margin utilization | Block orders if margin would exceed |

**Validation Criteria -- Week 15-16:**

- [ ] Risk service operational and accepting trade proposals via gRPC
- [ ] Daily circuit breaker trips at -2% and blocks new trades (test with simulated losses)
- [ ] Weekly circuit breaker trips at -5%
- [ ] Monthly circuit breaker trips at -10%
- [ ] Maximum drawdown kill switch triggers at -25% (close all positions)
- [ ] Position sizing computes correct lot sizes for given parameters
- [ ] Half-Kelly never exceeds 2% risk per trade
- [ ] Spiral protection reduces position size after consecutive losses
- [ ] Kill switch (manual) closes all positions and halts trading
- [ ] Exposure limits enforced (test by attempting to exceed)
- [ ] Margin utilization monitoring operational
- [ ] All risk events logged in database with full detail

### Week 17-18: Integration and Paper Trading

With all core services built, integrate them into the complete trading pipeline and validate through extended paper trading.

**Connect All Services:**

Wire together the complete data-to-execution pipeline:

```
Data Ingestion (Go, VLAN 10)
    |
    | ZeroMQ PUB/SUB (real-time data stream)
    v
Algo Engine (Python, VLAN 40)
    |
    | gRPC (trade proposal with confidence)
    v
Risk Management Service (Python, VLAN 40)
    |
    | gRPC (approved/modified/rejected)
    v
MT5 Execution Bridge (Python, VLAN 40, Windows VM)
    |
    | MetaTrader5 Python API
    v
Broker (Demo Account)
```

**Communication Layer Verification:**

Verify all communication protocols defined in Document 03:

- ZeroMQ PUB/SUB: Data Ingestion publishes, Algo Engine subscribes. Topics: `tick.XAUUSD`, `bar.M15.XAUUSD`, etc.
- gRPC: Algo Engine sends `SubmitOrder` to Risk Service. Risk Service sends approved order to MT5 Bridge.
- Redis Pub/Sub: System events broadcast on `moneymaker:events:*` channels.

**End-to-End Testing on Demo Account:**

- Submit test trades through the full pipeline (data -> brain -> risk -> execution)
- Verify that risk service modifies position sizes when they exceed limits
- Verify that circuit breakers trip when drawdown thresholds are hit
- Test kill switch end-to-end: trigger and verify all positions close

**Paper Trading Soak Test:**

Run the complete system on the demo account for a minimum of 2 weeks continuous operation:

- Algo Engine receives real-time data and produces trading signals
- Risk Management approves or rejects each signal
- Approved signals are executed on the demo account
- Monitor P&L, win rate, and execution quality daily
- Fix bugs as they are discovered (there will be bugs)
- Tune parameters: confidence thresholds, position sizing, risk limits

During the paper trading period, maintain a daily log:

```
Date: YYYY-MM-DD
Trades: X opened, Y closed
P&L: +/- $XXX (X.X% of equity)
Win Rate: XX% (cumulative)
Max Drawdown: X.X% (cumulative)
Issues: [list any bugs, anomalies, or unexpected behavior]
Actions: [what was fixed, what needs attention]
```

**Validation Criteria -- Week 17-18:**

- [ ] Complete pipeline operational: data -> brain -> risk -> execution
- [ ] All gRPC connections stable and reconnecting on failure
- [ ] ZeroMQ data stream flowing without gaps
- [ ] Algo Engine producing signals on live market data
- [ ] Risk service approving/rejecting trades correctly
- [ ] Trades executing on demo account with correct parameters
- [ ] P&L tracking accurate (matches MT5 account history)
- [ ] 2+ weeks of continuous paper trading completed
- [ ] No unrecoverable errors during paper trading period
- [ ] Daily log maintained for entire paper trading period

### Phase 3 Milestone

At the end of Phase 3, MONEYMAKER is a complete, operational trading system running on a demo account. It receives market data in real-time, processes it through the Algo Engine, passes decisions through the risk management gate, and executes approved trades through MetaTrader 5. The system is not yet hardened, not yet fully monitored, and not yet trading with real money, but the core pipeline is proven.

**Phase 3 Completion Checklist:**

- [ ] MetaTrader 5 integration fully operational
- [ ] Risk management service enforcing all safety rules
- [ ] Circuit breakers tested and verified
- [ ] Kill switch tested (both automatic and manual)
- [ ] Complete pipeline operational end-to-end
- [ ] 2+ weeks of paper trading completed without critical failures
- [ ] Paper trading shows positive expectancy (or clear explanation if not)
- [ ] All bugs discovered during paper trading fixed
- [ ] Execution quality metrics within acceptable range

---

## 13.6 Phase 4 -- Observability: Monitoring and Dashboard (Weeks 19-22)

**Goal:** Full visibility into every aspect of the system -- infrastructure, services, trading performance, AI health, and risk status.
**Theme:** You cannot manage what you cannot measure. You cannot fix what you cannot see.
**Documents Referenced:** Document 10 (Monitoring and Dashboard), Document 03 (Microservices)

### Phase 4 Timeline

```
Week 19-20           Week 21-22
[Prometheus       ]  [Streamlit       ]
[Node Exporter    ]  [Trading Views   ]
[Custom Exporters ]  [Risk Dashboard  ]
[Grafana Dashb    ]  [Loki Logs       ]
[Alertmanager     ]  [Trade Journal   ]
```

### Week 19-20: Monitoring Infrastructure

**Deploy Monitoring VM:**

Create a monitoring VM on VLAN 50 (Monitoring) per Document 02 and Document 10:

| Resource | Allocation | Rationale |
|----------|-----------|-----------|
| vCPUs | 2 | Prometheus, Grafana, Alertmanager |
| RAM | 8 GB | Metric storage and query processing |
| Disk | 100 GB | Metric retention (90 days at 15s scrape interval) |
| Network | VLAN 50 | Isolated monitoring network with access to all VLANs |

**Prometheus Setup:**

- Install Prometheus and configure scrape targets for all VMs
- Node Exporter on every VM (CPU, memory, disk, network metrics)
- PostgreSQL Exporter on the database VM (query performance, connection count, replication lag)
- Redis Exporter on the database VM (memory usage, command stats, pub/sub metrics)
- Custom exporters for MONEYMAKER services (trade metrics, AI confidence, risk status)

**Custom Trading Metrics:**

Define and export the trading-specific metrics described in Document 10:

```
# Trading Performance
moneymaker_trades_total{symbol, direction, outcome}
moneymaker_pnl_dollars{symbol}
moneymaker_pnl_percent
moneymaker_equity_current
moneymaker_drawdown_current
moneymaker_drawdown_max

# Algo Engine Health
moneymaker_algo_confidence_histogram
moneymaker_algo_predictions_total{direction}
moneymaker_algo_regime_current{regime}
moneymaker_algo_signal_duration_seconds
moneymaker_algo_fallback_tier_used{tier}

# Risk Management
moneymaker_risk_circuit_breaker_status{level}
moneymaker_risk_exposure_percent{symbol}
moneymaker_risk_margin_utilization
moneymaker_risk_consecutive_losses
moneymaker_risk_kill_switch_status
```

**Grafana Dashboards:**

Create four primary dashboards, each aligned with a domain of concern from Document 10:

1. **System Overview Dashboard:** VM health across all VLANs, CPU/memory/disk per VM, network traffic between VLANs, service uptime indicators.

2. **Trading Performance Dashboard:** Equity curve, daily P&L, win rate, Sharpe ratio, open positions, recent trade history, cumulative return.

3. **Algo Engine Dashboard:** Confidence score distribution, predictions per hour, regime classification timeline, signal generation latency, fallback tier usage, drift indicators.

4. **Risk Status Dashboard:** Circuit breaker status (green/amber/red), current drawdown vs thresholds, margin utilization gauge, exposure heatmap by symbol, consecutive loss counter, kill switch status.

**Alertmanager + Telegram:**

Configure alert rules in Prometheus and route them to Telegram via Alertmanager:

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| Service Down | Target unreachable for 2 minutes | Critical | Telegram + log |
| Data Gap | No new ticks for 5 minutes | Warning | Telegram |
| High Drawdown | Drawdown > 1.5% today | Warning | Telegram |
| Circuit Breaker | Any circuit breaker tripped | Critical | Telegram + log |
| Kill Switch | Kill switch activated | Critical | Telegram (urgent) |
| Disk Full | Disk usage > 85% | Warning | Telegram |
| High Latency | Order execution > 2 seconds | Warning | Telegram |
| Model Drift | Accuracy below 40% (rolling 50 trades) | Warning | Telegram |

**Validation Criteria -- Week 19-20:**

- [ ] Prometheus scraping all targets successfully
- [ ] Node Exporter metrics visible for all VMs
- [ ] Custom trading metrics exported and scraped
- [ ] Grafana dashboards displaying real-time data
- [ ] All four dashboards functional and accurate
- [ ] Alertmanager sending test alerts to Telegram
- [ ] Alert rules firing correctly (test by simulating conditions)
- [ ] Dashboard accessible from development machine

### Week 21-22: Trading Dashboard and Log Aggregation

**Streamlit Operations Center:**

Build the interactive operations dashboard described in Document 10 using Streamlit:

1. **Live Trading View:** Real-time display of open positions, unrealized P&L, account balance, equity, free margin. Auto-refreshing every 5 seconds.

2. **AI Decision Log:** Table of recent AI decisions showing: timestamp, symbol, direction, confidence score, tier used, regime classification, reasoning summary. Filterable by symbol, direction, and confidence range.

3. **Risk Dashboard Panel:** Visual representation of all circuit breaker states, drawdown thermometer, exposure pie chart, margin utilization bar.

4. **Trade Journal:** Searchable history of all trades with full metadata: entry time, exit time, direction, size, entry price, exit price, P&L, holding period, AI confidence at entry, risk score at entry. Exportable to CSV for external analysis.

5. **System Health Panel:** Service status indicators (green/red) for all services, last heartbeat timestamps, error counts per service in the last hour.

**Log Aggregation with Loki:**

Deploy Grafana Loki for centralized log collection:

- Promtail agents on all VMs shipping logs to Loki
- Structured logging (JSON format) from all Python services using `structlog`
- Go service logs in structured JSON format
- Log retention: 30 days
- Log queries available in Grafana alongside metrics

**Validation Criteria -- Week 21-22:**

- [ ] Streamlit dashboard accessible and displaying real-time data
- [ ] All dashboard pages functional
- [ ] Trade journal showing full trade history with search/filter
- [ ] AI decision log displaying recent decisions with confidence scores
- [ ] Risk dashboard showing correct circuit breaker states
- [ ] Loki receiving logs from all services
- [ ] Can query logs in Grafana by service, severity, and time range
- [ ] Dashboard performance acceptable (page load < 3 seconds)

### Phase 4 Milestone

At the end of Phase 4, MONEYMAKER is fully observable. Every metric, every log, every trade, every AI decision is visible in a unified monitoring stack. Alerts fire automatically when something goes wrong. The operator can assess the health of the entire system from a single browser tab.

---

## 13.7 Phase 5 -- Hardening: Security and Testing (Weeks 23-26)

**Goal:** Secure the system against threats and validate it through comprehensive, rigorous testing.
**Theme:** Trust but verify. Then verify again.
**Documents Referenced:** Document 11 (Testing Strategy), Document 12 (Security Framework)

### Phase 5 Timeline

```
Week 23-24           Week 25-26
[Firewall Rules   ]  [Unit Tests     ]
[TLS/mTLS        ]  [Integration    ]
[Secrets Mgmt    ]  [End-to-End     ]
[Audit Trail     ]  [Stress Test    ]
[Access Control  ]  [Failover Test  ]
```

### Week 23-24: Security Hardening

**Firewall Rules:**

Implement the defense-in-depth firewall strategy from Document 12:

Default policy: DROP ALL on all VLANs. Then explicitly allow only the traffic that is required:

```
VLAN 10 (Data Ingestion) -> VLAN 20 (Database): TCP 5432, 6379    ALLOW
VLAN 10 (Data Ingestion) -> Internet: TCP 443 (WSS/HTTPS)         ALLOW
VLAN 30 (Internal)       -> VLAN 20 (Database): TCP 5432          ALLOW
VLAN 40 (Trading)        -> VLAN 20 (Database): TCP 5432, 6379    ALLOW
VLAN 40 (Trading)        -> VLAN 10 (Data): TCP 5555 (ZeroMQ)     ALLOW
VLAN 40 (Trading)        -> Internet: TCP 443 (broker connection)  ALLOW
VLAN 50 (Monitoring)     -> ALL VLANs: TCP 9090, 9100 (Prometheus) ALLOW
Management               -> ALL VLANs: TCP 22 (SSH)                ALLOW
ALL other traffic                                                   DROP
```

**TLS/mTLS for Inter-Service Communication:**

- Generate a Certificate Authority (CA) for the MONEYMAKER ecosystem
- Issue TLS certificates to every service
- Enable mTLS (mutual TLS) on all gRPC connections: both client and server authenticate
- Encrypt ZeroMQ connections with CurveZMQ
- Redis with TLS enabled (or network-level isolation only if TLS adds unacceptable latency)

**Secrets Management:**

Deploy HashiCorp Vault (or use Mozilla SOPS as a lighter alternative) for secrets management:

- MT5 credentials (login, password, server)
- Data provider API keys (Binance, Alpha Vantage, FRED)
- Database passwords (PostgreSQL, Redis)
- Telegram bot token
- TLS private keys and certificates
- No secret should exist in plaintext in configuration files, environment variables on disk, or source code

**Audit Trail:**

Implement the immutable audit trail from Document 12:

- Every trade decision: timestamp, signal, confidence, risk assessment, approval/rejection, execution result
- Every configuration change: what changed, who changed it (system or operator), when, previous value, new value
- Every model deployment: model version, validation metrics, deployment time, previous model version replaced
- Hash chain: each audit entry includes a cryptographic hash of the previous entry, creating a tamper-evident chain

**Validation Criteria -- Week 23-24:**

- [ ] Firewall rules applied on all VLANs with default DROP
- [ ] Services can still communicate through explicitly allowed ports
- [ ] Unauthorized traffic between VLANs is blocked (test with nmap)
- [ ] TLS enabled on all gRPC connections
- [ ] mTLS verified: connections without valid certificates are rejected
- [ ] All secrets stored in Vault/SOPS (no plaintext secrets anywhere)
- [ ] Services retrieve secrets from Vault/SOPS at startup
- [ ] Audit trail logging all trade decisions and configuration changes
- [ ] Audit trail hash chain integrity verifiable

### Week 25-26: Comprehensive Testing

**Unit Tests:**

Target 80%+ coverage on critical services per Document 11:

- Algo Engine: feature engineering functions, confidence scoring, regime classification
- Risk Management: circuit breaker logic, position sizing, exposure calculations, kill switch
- MT5 Bridge: order construction, position tracking, execution quality computation
- Data Ingestion: normalization logic, gap detection, indicator computation

**Integration Tests:**

Test service-to-service communication:

- Data Ingestion -> Database: data stored correctly
- Data Ingestion -> Algo Engine (ZeroMQ): data received and processed
- Algo Engine -> Risk Management (gRPC): trade proposals correctly evaluated
- Risk Management -> MT5 Bridge (gRPC): approved trades executed
- All services -> Monitoring (Prometheus): metrics scraped correctly

**End-to-End Tests:**

Test the complete signal-to-execution pipeline:

```
Test 1: Inject a known signal -> verify trade executes on demo account
Test 2: Inject a signal that should be rejected by risk -> verify rejection
Test 3: Simulate drawdown -> verify circuit breaker trips
Test 4: Trigger kill switch -> verify all positions close
Test 5: Simulate data gap -> verify system enters safe state
Test 6: Simulate model timeout -> verify fallback tier activates
```

**Stress Tests:**

- Simulate high-frequency data: send 10x normal tick volume and verify system handles it
- Simulate rapid trading: submit 50 orders in 10 seconds and verify risk management handles them correctly
- Simulate network partition: disconnect VLANs and verify graceful degradation

**Failover Tests:**

- Kill each service individually and verify the rest of the system responds correctly
- Kill the database VM and verify that services detect the failure and enter safe mode
- Simulate power failure (UPS disconnect test in controlled environment)
- Restore from backup and verify system resumes correctly

**Extended Paper Trading:**

Resume paper trading with the fully hardened and monitored system. Run for 4+ weeks of continuous operation:

- Monitor for stability issues
- Track P&L and compare with pre-hardening paper trading results
- Verify that security hardening has not introduced latency or functionality regressions

**Validation Criteria -- Week 25-26:**

- [ ] Unit test coverage > 80% on critical services
- [ ] All integration tests passing
- [ ] All 6 end-to-end test scenarios passing
- [ ] Stress tests completed without failures
- [ ] Failover tests completed: system recovers from every simulated failure
- [ ] 4+ weeks of extended paper trading completed
- [ ] No critical bugs in last 2 weeks of paper trading
- [ ] No security vulnerabilities found in audit

### Phase 5 Milestone

At the end of Phase 5, MONEYMAKER is secure, well-tested, and operationally proven through weeks of continuous paper trading. Every component has been tested individually, in integration, and end-to-end. The system has survived simulated failures, stress conditions, and security probes. It is ready for the most consequential phase: live trading.

---

## 13.8 Phase 6 -- Go-Live: Controlled Live Trading (Weeks 27-32+)

**Goal:** Transition from demo to live trading with extreme caution, starting with minimum risk and scaling gradually.
**Theme:** The system has been tested. Now it earns its right to trade real money -- one cautious step at a time.
**Documents Referenced:** All documents (this is where everything comes together)

### Week 27-28: Pre-Live Checklist

Before placing a single live trade, every item on this checklist must be verified. There is no shortcut, no "we will fix it later," no "it probably works." Every item is a gate that must be cleared.

**Pre-Live Gate Checklist:**

- [ ] **Phase 0 complete:** Infrastructure operational, accounts created
- [ ] **Phase 1 complete:** Database filling with clean data, no gaps in 4+ weeks
- [ ] **Phase 2 complete:** AI models trained and producing calibrated signals
- [ ] **Phase 3 complete:** Trading pipeline operational end-to-end on demo
- [ ] **Phase 4 complete:** Monitoring and alerting fully functional
- [ ] **Phase 5 complete:** Security hardened, all tests passing
- [ ] **Paper trading positive:** Positive expectancy confirmed over 4+ weeks
- [ ] **Risk parameters reviewed:** All circuit breaker thresholds, position sizing parameters, and exposure limits reviewed and documented
- [ ] **Backup procedures tested:** Can restore entire system from backup within 2 hours
- [ ] **Emergency procedures documented:** Written runbook for every failure scenario
- [ ] **Kill switch accessible:** Tested within the last 24 hours. Telegram command works. API endpoint works. SSH script works
- [ ] **Live broker account funded:** Minimum capital deposited (start small)
- [ ] **Operator availability:** Committed to monitoring the system closely for the first 2 weeks of live trading
- [ ] **Emotional readiness:** Accept that real money will be at risk. Accept that losses will occur. Accept that the system will make trades you disagree with. Trust the process

### Week 29-30: Micro-Live Trading

The transition to live trading begins with the smallest possible risk exposure. The purpose of micro-live trading is to verify that the system behaves the same with real money as it did with demo money. Spoiler: it will not behave identically, because real execution has slippage, requotes, and variable spreads that demo accounts partially or fully eliminate.

**Micro-Live Parameters:**

| Parameter | Demo Value | Micro-Live Value | Rationale |
|-----------|-----------|------------------|-----------|
| Lot size | Normal Kelly | 0.01 lots (minimum) | Absolute minimum risk |
| Max trades/day | No limit | 1-2 trades/day | Limit exposure while validating |
| Risk per trade | 2% | 1% | Half of normal risk |
| Daily circuit breaker | -2% | -1% | Extra tight |
| Weekly circuit breaker | -5% | -3% | Extra tight |
| Confidence threshold | 60 | 75 | Only highest-confidence signals |

**Monitoring During Micro-Live:**

- Check Grafana dashboard at least 3 times per day (morning, midday, evening)
- Review every trade within 1 hour of execution (is the reasoning sound? was the execution quality acceptable?)
- Compare live execution with what the demo account would have done (run demo in parallel)
- Track slippage: are live fills significantly worse than demo fills?
- Track spread: are live spreads significantly wider than demo spreads?

**Success Criteria for Micro-Live:**

After 2 weeks of micro-live trading:

- [ ] No unexpected behavior from the system
- [ ] Execution quality acceptable (slippage < 1 pip average on XAUUSD)
- [ ] P&L directionally consistent with demo results (does not need to be identical)
- [ ] No circuit breaker triggers (with the tight thresholds)
- [ ] No kill switch activations
- [ ] Operator confidence in the system has grown, not diminished

### Week 31-32: Gradual Scale-Up

If micro-live trading is successful, begin gradually increasing risk parameters:

**Scale-Up Schedule:**

```
Week 31:  Lot size -> 0.02    Risk/trade -> 1.25%   Circuit -> 1.5% daily
Week 32:  Lot size -> 0.03    Risk/trade -> 1.5%    Circuit -> 1.75% daily
Week 33:  Lot size -> Kelly   Risk/trade -> 2.0%    Circuit -> 2.0% daily (normal)
Week 34+: Normal parameters per Document 09
```

Each step-up requires a review of the previous week's performance. If any week shows concerning results (circuit breaker trip, unexpected behavior, degraded execution quality), pause the scale-up and investigate before proceeding.

### Ongoing: Continuous Improvement

MONEYMAKER V1 is not a product that is built once and left to run indefinitely. Financial markets evolve, and the system must evolve with them.

**Monthly Tasks:**

- Model retraining with fresh data (Document 06 training pipeline)
- Walk-forward validation of current models
- Champion-challenger evaluation: does the new model outperform the current one?
- Review trading performance KPIs against targets
- Review and adjust risk parameters based on live performance data

**Quarterly Tasks:**

- Strategy review: are the current strategies still appropriate for market conditions?
- Feature engineering review: are there new features that could improve model performance?
- Infrastructure review: are VMs appropriately sized? Is storage sufficient?
- Security audit: are there new vulnerabilities? Are certificates expiring?

**Annual Tasks:**

- Full system review and architecture assessment
- Technology stack evaluation: are there better tools available?
- Disaster recovery drill: full system restore from backup
- Documentation review and update

---

## 13.9 Feature Backlog and Future Enhancements

### Near-Term Enhancements (0-6 Months After Go-Live)

**Additional Asset Classes:**

- Expand from XAU/USD to major forex pairs (EUR/USD, GBP/USD, USD/JPY)
- Add equity indices (S&P 500 CFDs, NASDAQ CFDs)
- Each new instrument requires: data ingestion configuration, feature engineering validation, model retraining, risk parameter calibration

**Advanced Order Types:**

- OCO (One-Cancels-Other) orders for bracket entries
- Trailing stops managed at the broker level (reduced latency vs software-managed)
- Time-based order expiry for limit orders

**Multi-Broker Support:**

- Secondary broker for redundancy
- Execution quality comparison between brokers
- Automatic failover if primary broker connection fails

**Reinforcement Learning Agent:**

- DQN (Deep Q-Network) or PPO (Proximal Policy Optimization) for dynamic strategy selection
- The RL agent learns to select which strategy/model to trust based on current market conditions
- Trained in a simulated trading environment before live deployment

**COPER Experience Bank:**

- Full implementation of the Contextual Prediction Experience Replay system described in Document 07
- Store successful trading episodes with their full context (features, regime, confidence, outcome)
- Retrieve similar episodes when the current context matches, providing experience-based decision support

### Medium-Term Enhancements (6-12 Months)

**News Sentiment Analysis:**

- NLP pipeline for processing financial news headlines
- Sentiment scoring: positive/negative/neutral with confidence
- Event classification: rate decision, jobs report, CPI, geopolitical event
- Integration with Algo Engine as additional feature input

**Economic Calendar Integration:**

- Automatic detection of upcoming high-impact economic events
- Pre-event risk reduction: reduce position sizes 1 hour before major announcements
- Post-event volatility adaptation: adjust ATR multipliers during high-volatility periods

**Correlation-Based Portfolio Optimization:**

- Dynamic correlation matrix between all traded instruments
- Position-level correlation monitoring: avoid highly correlated positions
- Mean-variance optimization for multi-instrument portfolios

**Alternative Data Sources:**

- COT (Commitment of Traders) reports for positioning analysis
- Social media sentiment (Twitter/X, Reddit) for crowd behavior signals
- Options market data (put/call ratios, implied volatility surfaces)
- On-chain metrics for crypto instruments (whale movements, exchange flows)

**Mobile Monitoring App:**

- Lightweight mobile app (React Native or Flutter) for monitoring on the go
- Push notifications for critical alerts
- Quick kill switch access from mobile

### Long-Term Enhancements (12+ Months)

**Multi-Strategy Orchestration:**

- Multiple independent strategies running in parallel
- Capital allocation across strategies based on recent performance
- Strategy diversification to smooth equity curves

**Cross-Exchange Arbitrage Detection:**

- Price discrepancy detection between exchanges
- Statistical arbitrage on correlated pairs
- Latency-optimized execution for arbitrage opportunities

**Graph-Based Correlation Analysis:**

- Model market microstructure as a graph
- Assets as nodes, correlations as edges
- Detect structural relationships that change over time

**Self-Optimizing Hyperparameters:**

- Automated hyperparameter search running continuously in background
- New hyperparameter configurations evaluated on walk-forward validation
- Automatic promotion of better configurations (with human approval gate)

---

## 13.10 Risk Register

### Technical Risks

| ID | Risk | Likelihood | Impact | Mitigation | Owner | Review Frequency |
|----|------|-----------|--------|------------|-------|-----------------|
| T1 | Hardware failure (disk, CPU, RAM) | Low | Very High | ZFS redundancy, backups, UPS, SMART monitoring | Operator | Monthly |
| T2 | GPU incompatibility with ROCm updates | Medium | High | Pin ROCm version; test updates in staging; CPU fallback | Operator | Per ROCm release |
| T3 | Software bugs in trading logic | Medium | Very High | 80%+ test coverage; paper trading validation; code review | Developer | Continuous |
| T4 | Model overfitting (performs well on historical, fails on live) | High | High | Walk-forward validation; ensemble; confidence gating; monitoring | Developer | Monthly |
| T5 | Database corruption | Very Low | Very High | ZFS checksums; pg_dump backups; hourly ZFS snapshots | Operator | Weekly |
| T6 | Network failure (internet outage) | Low | High | Kill switch triggers on communication timeout; positions have SL | Operator | Monthly |
| T7 | Proxmox hypervisor failure | Very Low | Very High | Automated VM restart; ZFS-backed VM images; backup procedures | Operator | Quarterly |
| T8 | Memory leak in long-running services | Medium | Medium | Prometheus memory monitoring; automatic restart on threshold; profiling | Developer | Weekly |

### Market Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| M1 | Regime change (model trained on one regime, market shifts to another) | High | High | Regime detection; ensemble diversity; model retraining; confidence gating |
| M2 | Flash crash (extreme price movement in seconds) | Low | Very High | Stop-losses on every position; circuit breakers; maximum drawdown kill switch |
| M3 | Liquidity crisis (wide spreads, requotes, partial fills) | Medium | High | Spread monitoring; reject trades during abnormal spread conditions; exposure limits |
| M4 | Weekend gap (market opens with significant gap) | Medium | Medium | No positions held over weekend (configurable); reduced Friday position sizes |
| M5 | Correlation breakdown (historically correlated instruments diverge) | Medium | Medium | Dynamic correlation monitoring; correlation-based exposure limits |

### Operational Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| O1 | Operator burnout (solo developer, 24/7 markets) | High | High | Automation; alerts instead of manual monitoring; take breaks; accept imperfection |
| O2 | Knowledge concentration (single person knows everything) | High | Medium | Comprehensive documentation (these 13 documents); code comments; decision logs |
| O3 | Configuration error (wrong parameter causes excessive risk) | Medium | Very High | Configuration validation; audit trail; parameter change alerts; pre-live checklist |
| O4 | Broker account issues (account freeze, withdrawal problems) | Low | High | Multi-broker preparation; regular small withdrawals to verify; reputable broker selection |

### Financial Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| F1 | Sustained drawdown (model underperforms for weeks) | Medium | High | Circuit breakers; monthly review; model retraining trigger; capital preservation mode |
| F2 | Broker insolvency | Very Low | Very High | Regulated broker; segregated client funds; diversify across brokers (medium-term) |
| F3 | Regulatory change (new rules affecting retail trading) | Low | Medium | Monitor regulatory developments; geographic flexibility; compliance awareness |
| F4 | Tax liability from trading profits | Certain | Medium | Consult tax professional; set aside tax reserves; maintain detailed trade records |

### Risk Review Schedule

- **Weekly:** Review T3, T8, M1 during development phases
- **Monthly:** Review all technical and market risks; update mitigation status
- **Quarterly:** Full risk register review; add new risks, retire resolved risks
- **Annually:** Comprehensive risk assessment including long-term strategic risks

---

## 13.11 Success Criteria and KPIs

### Phase Completion Criteria

Each phase has explicit, binary completion criteria. A phase is complete when ALL criteria are met. There is no partial completion.

| Phase | Completion Criteria |
|-------|-------------------|
| Phase 0 | Proxmox running, VLANs configured, dev environment ready, all accounts created |
| Phase 1 | Database operational, data ingestion running 7+ days without gaps, indicators computed |
| Phase 2 | Ensemble model producing signals with Sharpe > 1.0 on walk-forward validation |
| Phase 3 | Complete pipeline operational on demo, 2+ weeks paper trading, risk management verified |
| Phase 4 | All Grafana dashboards live, Telegram alerts working, Streamlit dashboard functional |
| Phase 5 | 80%+ test coverage, all security hardening applied, 4+ weeks extended paper trading stable |
| Phase 6 | Micro-live trading for 2+ weeks, execution quality verified, scale-up criteria met |

### Trading KPIs

These are the performance metrics that determine whether MONEYMAKER is achieving its purpose. They are measured on a rolling basis once live trading begins.

| KPI | Target | Measurement Period | Red Flag |
|-----|--------|-------------------|----------|
| Positive Expectancy | After 100+ trades | Rolling 100 trades | Expectancy negative after 200+ trades |
| Sharpe Ratio | > 1.0 | Rolling 6 months | < 0.5 for 3 consecutive months |
| Maximum Drawdown | < 20% | From peak equity | > 15% triggers review; > 25% triggers kill switch |
| Win Rate | > 45% | Rolling 100 trades | < 35% for 50+ trades |
| Profit Factor | > 1.3 | Rolling 100 trades | < 1.0 (losing money) |
| Average Win / Average Loss | > 1.5 | Rolling 100 trades | < 1.0 |
| System Uptime | > 99% | Monthly | < 95% in any month |
| Recovery Factor | > 2.0 | Annualized | < 1.0 (drawdown exceeds annual return) |

### Technical KPIs

| KPI | Target | Measurement | Red Flag |
|-----|--------|-------------|----------|
| Order Execution Latency | < 500ms | Median, from signal to fill confirmation | > 2 seconds median |
| Data Freshness | < 2 seconds | Age of most recent tick in cache | > 10 seconds |
| Signal Generation Time | < 100ms | Time for Algo Engine to produce signal from features | > 500ms |
| Zero Data Loss | 0 ticks dropped | Comparison with exchange records | Any confirmed data loss |
| Backup Success Rate | 100% | Automated backup completion | Any failed backup |
| Backup Restore Test | Pass | Quarterly restore drill | Failed restore |
| Alert Delivery | < 30 seconds | Time from condition to Telegram message | > 5 minutes |

### Review Schedule

| Frequency | Scope | Actions |
|-----------|-------|---------|
| Daily (live trading) | P&L, open positions, recent trades, alerts | Log review; no action unless alert triggered |
| Weekly (development) | Phase progress, blockers, next steps | Update task list; adjust timeline if needed |
| Weekly (live trading) | Trading KPIs, execution quality, model health | Adjust parameters if needed; flag concerns |
| Monthly | Full KPI review, risk register update, model performance | Model retraining decision; risk parameter review |
| Quarterly | Strategy review, infrastructure review, security audit | Major decisions: new strategies, scale changes |
| Annually | Full system review, architecture assessment, technology evaluation | Strategic planning for next year |

---

## 13.12 Budget and Resource Planning

### One-Time Hardware Costs

| Item | Estimated Cost (EUR) | Notes |
|------|---------------------|-------|
| AMD Ryzen 9 7950X | ~550 | 16-core processor |
| 128 GB DDR5-5600 (4x32 GB) | ~350 | High-capacity memory |
| 1 TB NVMe (boot) | ~100 | Samsung 990 Pro or equivalent |
| 2 TB NVMe (data) | ~150 | For ZFS data pool |
| Motherboard (AM5, ATX) | ~250 | With good IOMMU support |
| Case + PSU (750W+) | ~200 | Quality PSU for 24/7 operation |
| UPS (1000VA) | ~150 | Power protection |
| Managed Switch | ~50 | VLAN-capable |
| Peripherals + cables | ~50 | Network cables, display adapter for setup |
| **Total Hardware** | **~2,450** | One-time investment |

### Recurring Monthly Costs

| Item | Estimated Cost (EUR/month) | Notes |
|------|---------------------------|-------|
| Electricity | ~30-50 | Server running 24/7 (~200-300W average) |
| Internet | ~30-50 | Reliable connection with low latency |
| Broker fees (spread) | Variable | Depends on trading frequency and volume |
| Data feeds | 0-50 | Most data sources free; premium feeds optional |
| Domain/DNS (optional) | ~2 | For remote access via domain name |
| Cloud backup (optional) | ~5-10 | Offsite backup to B2/S3 |
| **Total Monthly** | **~67-162** | Excluding trading costs |

### Software Costs

| Item | Cost | Notes |
|------|------|-------|
| Proxmox VE | Free (community) | No enterprise subscription needed |
| PostgreSQL + TimescaleDB | Free (open source) | Community edition |
| Redis | Free (open source) | Community edition |
| Prometheus + Grafana | Free (open source) | Grafana OSS |
| Python + libraries | Free (open source) | scikit-learn, LightGBM, etc. |
| Go | Free (open source) | Go compiler and tools |
| MetaTrader 5 | Free | Provided by broker |
| HashiCorp Vault | Free (open source) | Community edition |
| **Total Software** | **0** | Entirely open-source stack |

### Time Investment Estimate

| Phase | Estimated Hours | Notes |
|-------|----------------|-------|
| Phase 0 | 20-30 | Hardware setup, Proxmox installation |
| Phase 1 | 60-80 | Database + data ingestion |
| Phase 2 | 120-160 | Feature engineering + ML models (most intensive) |
| Phase 3 | 80-100 | MT5 bridge + risk management + integration |
| Phase 4 | 40-60 | Monitoring stack + dashboard |
| Phase 5 | 60-80 | Security hardening + comprehensive testing |
| Phase 6 | 40-60 | Go-live preparation + micro-live trading |
| **Total** | **420-570** | At 20 hrs/week = ~21-29 weeks |

### Contingency

Add 20% buffer to all time estimates. Complex systems consistently take longer than estimated. The total realistic timeline is 25-35 weeks from Phase 0 start to stable live trading. This is approximately 6-8 months of part-time work. Accept this timeline. Attempting to compress it by cutting corners on safety systems or testing will cost more time in debugging and recovery than it saves.

---

## 13.13 Document Cross-Reference Guide

### Document Map

This section maps each phase of the roadmap to the specific documents that provide detailed guidance for that phase's tasks.

| Phase | Primary Documents | Supporting Documents |
|-------|------------------|---------------------|
| Phase 0 | Doc 01 (Vision), Doc 02 (Infrastructure) | Doc 12 (Security - initial firewall) |
| Phase 1 | Doc 04 (Data Ingestion), Doc 05 (Database) | Doc 03 (Communication), Doc 10 (Monitoring basics) |
| Phase 2 | Doc 06 (ML Training), Doc 07 (Algo Engine) | Doc 05 (Database - model registry) |
| Phase 3 | Doc 08 (MT5 Bridge), Doc 09 (Risk Mgmt) | Doc 03 (Communication - gRPC), Doc 07 (Brain - signals) |
| Phase 4 | Doc 10 (Monitoring/Dashboard) | Doc 03 (Communication - metrics), Doc 05 (Database - metrics storage) |
| Phase 5 | Doc 11 (Testing), Doc 12 (Security) | All documents (test coverage spans entire system) |
| Phase 6 | All documents | Doc 09 (Risk - go-live parameters), Doc 10 (Monitoring - go-live dashboards) |

### Document Dependency Matrix

The documents form a dependency graph. Understanding these dependencies helps you know which documents to consult when working on a specific component.

```
Doc 01 (Vision) -----------> Foundation for everything
    |
    +-> Doc 02 (Infrastructure) -> Foundation for all VM deployment
    |       |
    |       +-> Doc 03 (Communication) -> Used by all services
    |       |
    |       +-> Doc 05 (Database) -> Used by all data-producing services
    |       |
    |       +-> Doc 10 (Monitoring) -> Monitors all services
    |
    +-> Doc 04 (Data Ingestion) -> Feeds Doc 05, Doc 06, Doc 07
    |
    +-> Doc 06 (ML Training) -> Produces models for Doc 07
    |       |
    |       +-> Doc 07 (Algo Engine) -> Consumes models, produces signals
    |               |
    |               +-> Doc 08 (MT5 Bridge) -> Executes signals
    |               |
    |               +-> Doc 09 (Risk Mgmt) -> Gates signals before execution
    |
    +-> Doc 11 (Testing) -> Tests all services
    |
    +-> Doc 12 (Security) -> Secures all services
    |
    +-> Doc 13 (Roadmap) -> Ties everything together [THIS DOCUMENT]
```

### Complete Document List

| # | Title | Focus Area | Key Contents |
|---|-------|-----------|-------------|
| 01 | System Vision and Architecture Overview | Architecture | Three Pillars, tech stack, design principles, system-of-systems concept |
| 02 | Proxmox Infrastructure and VM Topology | Infrastructure | Proxmox installation, VLAN layout, ZFS configuration, GPU passthrough, VM sizing |
| 03 | Microservices Architecture and Communication | Communication | Service decomposition, gRPC, ZeroMQ, Redis pub/sub, message formats, resilience |
| 04 | Data Ingestion and Real-Time Market Data Service | Data | Go gateway, WebSocket management, exchange adapters, normalization, distribution |
| 05 | Database Architecture and Time-Series Storage | Storage | PostgreSQL, TimescaleDB, Redis, schema design, hypertables, backup strategy |
| 08 | MetaTrader 5 Execution Bridge | Execution | Windows VM, MT5 Python API, order management, position tracking, execution quality |
| 09 | Risk Management Service | Safety | Circuit breakers, position sizing (half-Kelly), kill switch, exposure limits, spiral protection |
| 10 | Monitoring and Dashboard | Observability | Prometheus, Grafana, Alertmanager, Telegram, Streamlit dashboard, Loki logs |
| 11 | Testing Strategy | Quality | Unit tests, integration tests, end-to-end tests, stress tests, failover tests |
| 12 | Security Framework | Security | Firewall, TLS/mTLS, secrets management, audit trail, access control |
| 13 | Roadmap and Implementation Phases | Execution | This document: phased plan from zero to live trading |

### Recommended Reading Order

**For first-time readers (understanding the system):**

1. Document 01 (Vision) -- understand the big picture
2. Document 03 (Communication) -- understand how services interact
3. Document 07 (Algo Engine) -- understand the intelligence core
4. Document 09 (Risk Management) -- understand the safety systems
5. Document 13 (Roadmap) -- understand the implementation plan
6. All remaining documents in numerical order

**For implementers (building the system):**
Follow the phase order defined in this roadmap:

1. Document 02 (Infrastructure) -- Phase 0
2. Document 05 (Database), Document 04 (Data Ingestion) -- Phase 1
3. Document 06 (ML Training), Document 07 (Algo Engine) -- Phase 2
4. Document 08 (MT5 Bridge), Document 09 (Risk Management) -- Phase 3
5. Document 10 (Monitoring) -- Phase 4
6. Document 12 (Security), Document 11 (Testing) -- Phase 5

**For operators (running the system):**

1. Document 09 (Risk Management) -- know the safety systems
2. Document 10 (Monitoring) -- know what to watch
3. Document 12 (Security) -- know the security posture
4. Document 13 (Roadmap), Section 13.8 -- know the go-live procedures

---

## 13.14 Conclusion and Call to Action

### The Journey from Vision to Reality

You have now read thirteen documents that together describe, in exhaustive detail, every component, every decision, every protocol, and every safeguard of the MONEYMAKER V1 autonomous trading ecosystem. Document 01 established the vision: a system of cooperating, specialized services that together form an intelligence capable of observing financial markets, reasoning about their behavior, making probabilistic trading decisions, and executing those decisions with discipline that no human can sustain. Document 02 described the physical and virtual infrastructure on which this system lives. Documents 03 through 10 described each service in the ecosystem, from the Go-based data ingestion gateway to the Prometheus-powered monitoring stack. Documents 11 and 12 described how the system is tested and secured. And this document -- Document 13 -- has described how to build it all, phase by phase, from an empty server to a live trading operation.

The scope of this project is significant. Building MONEYMAKER V1 is not a weekend project. It is not a "download a bot and start trading" exercise. It is a genuine engineering endeavor that spans infrastructure, networking, database design, distributed systems, machine learning, financial engineering, risk management, security, monitoring, and testing. It requires proficiency across multiple programming languages (Python, Go, SQL), multiple paradigms (event-driven systems, request-response services, quantitative analysis), and multiple domains (software engineering, quantitative finance, system administration).

But the scope is also bounded. MONEYMAKER V1 is a finite, achievable system. Every component described in these documents has been implemented successfully by others -- there is no novel research required, no unsolved problems to crack. PostgreSQL is a mature database. TimescaleDB is a production-ready extension. MetaTrader 5 is the most widely used retail trading platform. Prometheus and Grafana are industry standards. The innovation in MONEYMAKER is not in any individual component; it is in the integration -- the way these components are connected, coordinated, and orchestrated to form a coherent autonomous trading system.

### The Importance of Patience and Discipline

The markets will be there tomorrow. They will be there next month. They will be there next year. There is no rush to go live. There is no trade that you will miss by spending an extra week on testing. There is no profit that you will forgo by running one more month of paper trading. The only thing you can lose by being patient is time. The things you can lose by being impatient include your trading capital, your confidence in the system, and your motivation to continue.

The same discipline that the Algo Engine applies to trading -- confidence gating, risk management, circuit breakers, kill switches -- should be applied to the development process itself. If a phase is not meeting its validation criteria, do not proceed to the next phase. If a model is overfitting, do not deploy it and hope for the best. If the paper trading results are negative, do not go live and assume that real money will fix the problem. The system is designed to be cautious, and the development process should mirror that caution.

### Building Block by Block

MONEYMAKER V1 is not built as a monolith. It is built as a system of blocks, each one solid before the next is placed on top. The database is the first block. The data ingestion service is the second. The Algo Engine is the third. The execution bridge is the fourth. The risk management service wraps around them all. The monitoring stack watches over everything. The security framework protects the perimeter. And this roadmap is the construction plan that ensures the blocks are placed in the right order.

Each block can be built independently, tested independently, and validated independently before being integrated with the others. This is the power of the microservices architecture described in Document 03. It means that if the Algo Engine is not ready, the data ingestion service can still run and collect data. If the MT5 Bridge has a Windows-specific issue, the Algo Engine can still generate and log signals. If the monitoring stack is being reconfigured, the trading pipeline continues to operate. Isolation is not just an architectural nicety; it is a development methodology that allows a solo developer to make progress on one front while another front is blocked.

### The System Will Grow and Improve Over Time

MONEYMAKER V1 is the foundation, not the final form. The "V1" in the name is intentional. It acknowledges that this is the first version of a system that will evolve over years. The feature backlog in Section 13.9 hints at the trajectory: news sentiment analysis, multi-strategy orchestration, cross-exchange arbitrage, graph-based correlation analysis. None of these enhancements are possible without a solid V1 foundation. All of them become straightforward additions once the foundation exists.

The architecture was designed for evolution. Adding a new data source means implementing one adapter interface. Adding a new strategy means calibrating it and registering it in the strategy registry. Adding a new strategy means implementing the strategy interface and registering it with the regime router. The microservices boundaries, the communication protocols, the database schema, the monitoring infrastructure -- all of these are designed to accommodate growth without requiring wholesale redesign.

### The First Step

The roadmap is defined. The phases are clear. The milestones are concrete. The risks are identified. The mitigations are planned. The budget is estimated. The cross-references are mapped. The success criteria are quantified.

The first step is Phase 0: ensure the hardware is assembled, Proxmox is installed, the development environment is configured, and all accounts are created. This is the least glamorous phase. There are no trading signals, no equity curves. There is only a server booting up, a hypervisor loading, a ZFS pool initializing, and a Python interpreter confirming its version. But this is the foundation. Everything that comes after -- the intelligence, the execution, the profits, the evolution -- rests on this foundation.

Begin Phase 0. Complete it with the same rigor and attention to detail that you will apply to the trading strategies and the risk management systems. Then begin Phase 1. Then Phase 2. Block by block. Phase by phase. Crawl, walk, run.

MONEYMAKER awakens one phase at a time.

---

**Document 13 of 13 -- MONEYMAKER V1 Foundation Series**
**Roadmap and Implementation Phases**
**Status:** Complete

*This is the final document in the V1_Bot Foundation Series. The thirteen documents together form the complete technical specification and implementation plan for the MONEYMAKER V1 autonomous trading ecosystem. The journey begins with Phase 0.*

---

### Appendix A: Master Checklist (All Phases)

This appendix consolidates every validation checklist from every phase into a single, sequential master checklist. Print this. Pin it to the wall. Check off each item as it is completed.

**PHASE 0 -- Prerequisites**

- [ ] Hardware assembled and POST-verified
- [ ] BIOS: IOMMU enabled, SVM enabled, XMP set
- [ ] UPS connected and tested
- [ ] Managed switch configured with VLANs
- [ ] Proxmox VE installed and web UI accessible
- [ ] ZFS pool created and healthy
- [ ] VLANs configured as Linux bridges
- [ ] NTP synchronized
- [ ] Python 3.11+ installed
- [ ] Go 1.22+ installed
- [ ] Git repository initialized
- [ ] MT5 demo account created
- [ ] Data provider API keys obtained
- [ ] Telegram bot created and tested

**PHASE 1 -- Database and Data Ingestion**

- [ ] PostgreSQL VM running on VLAN 20
- [ ] TimescaleDB extension installed
- [ ] All schema tables created with hypertables
- [ ] Redis running on VLAN 20
- [ ] ZFS backup schedule automated
- [ ] Data Ingestion Service connecting to sources
- [ ] Real-time data flowing to database
- [ ] Data normalized (symbols, timestamps, precision)
- [ ] ZeroMQ publishing data to subscribers
- [ ] Data validation rules active
- [ ] Gap detection operational
- [ ] 8 core technical indicators computing
- [ ] Prometheus metrics exported
- [ ] 7+ days continuous operation without gaps

**PHASE 2 -- AI/ML Models**

- [ ] 40+ features computed in pipeline
- [ ] Fractional differencing applied (ADF test passes)
- [ ] Triple Barrier labels generated
- [ ] Feature selection completed
- [ ] LightGBM trained with walk-forward validation
- [ ] XGBoost trained with walk-forward validation
- [ ] GPU passthrough operational (ROCm)
- [ ] Transformer model trained and converged
- [ ] BiLSTM model trained and converged
- [ ] Dilated CNN model trained and converged
- [ ] Ensemble architecture combining all models
- [ ] Confidence scoring calibrated (0-100)
- [ ] Confidence gating operational
- [ ] 4-tier fallback system functional
- [ ] Backtested Sharpe > 1.0

**PHASE 3 -- MT5 Bridge and Risk Management**

- [ ] Windows VM with MT5 installed
- [ ] Python MT5 package connecting to demo
- [ ] Market, limit, and stop orders working
- [ ] Position close and modify working
- [ ] gRPC interface operational
- [ ] Daily circuit breaker tested (-2%)
- [ ] Weekly circuit breaker tested (-5%)
- [ ] Monthly circuit breaker tested (-10%)
- [ ] Max drawdown kill switch tested (-25%)
- [ ] Half-Kelly position sizing correct
- [ ] Spiral protection active
- [ ] Manual kill switch tested
- [ ] Exposure limits enforced
- [ ] Complete pipeline operational end-to-end
- [ ] 2+ weeks paper trading completed

**PHASE 4 -- Monitoring and Dashboard**

- [ ] Prometheus scraping all targets
- [ ] Node Exporter on all VMs
- [ ] Custom trading metrics exported
- [ ] 4 Grafana dashboards functional
- [ ] Alertmanager sending to Telegram
- [ ] Alert rules firing correctly
- [ ] Streamlit dashboard displaying real-time data
- [ ] Trade journal with search/filter
- [ ] Loki receiving logs from all services

**PHASE 5 -- Security and Testing**

- [ ] Firewall: default DROP on all VLANs
- [ ] TLS/mTLS on all gRPC connections
- [ ] Secrets in Vault/SOPS (no plaintext)
- [ ] Audit trail with hash chain
- [ ] Unit tests > 80% coverage
- [ ] Integration tests passing
- [ ] End-to-end tests passing
- [ ] Stress tests completed
- [ ] Failover tests completed
- [ ] 4+ weeks extended paper trading stable

**PHASE 6 -- Go-Live**

- [ ] All pre-live gate checklist items verified
- [ ] Live account funded (minimum capital)
- [ ] Kill switch tested within 24 hours
- [ ] Micro-live trading: 2 weeks at minimum lot size
- [ ] Execution quality verified (slippage acceptable)
- [ ] No unexpected behavior during micro-live
- [ ] Scale-up commenced (if micro-live successful)
- [ ] Monthly model retraining schedule active
- [ ] Quarterly review schedule active

---

### Appendix B: Emergency Procedures Quick Reference

| Scenario | Action | Command/Procedure |
|----------|--------|------------------|
| System losing money rapidly | Activate kill switch | Telegram: `/kill` or API: `POST /api/kill-switch` |
| Service unresponsive | Restart service | `systemctl restart moneymaker-<service>` on the VM |
| Database unreachable | Check VM status | Proxmox UI: verify VM 103 is running; restart if needed |
| All services down | Check Proxmox | Verify Proxmox host is reachable; check UPS; check network |
| Data feed dead | Check ingestion service | SSH to data VM; check logs; restart service; verify exchange status |
| Model producing nonsensical signals | Disable ML tier | Set confidence threshold to 100 (no signal passes); investigate |
| Power outage | Wait for UPS | UPS provides time for graceful shutdown; system auto-recovers on power restore |
| Suspected security breach | Network isolation | Disable VLAN 40 (trading) uplink; investigate; change all credentials |

---

*fine del documento 13 -- Roadmap and Implementation Phases*
