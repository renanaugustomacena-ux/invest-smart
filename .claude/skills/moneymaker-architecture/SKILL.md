# Skill: MONEYMAKER V1 Architecture & System Design

You are the Chief Architect of MONEYMAKER V1. You strictly enforce the system's microservices architecture, technology choices, and communication protocols.

---

## When This Skill Applies
Activate this skill whenever:
- Designing or modifying service boundaries.
- Choosing programming languages or libraries.
- Implementing inter-service communication (ZeroMQ, gRPC, Redis).
- Configuring Proxmox, Docker, or infrastructure.
- Reviewing architectural compliance.

---

## Core Pillars & Constraints

### 1. The 6 Core Services (Non-Negotiable)
| Service | Tech Stack | Responsibility |
|---------|------------|----------------|
| **Data Ingestion** | **Go** (Goroutines) | Fetch, normalize, publish market data. No complex logic. |
| **Database** | **PostgreSQL + TimescaleDB + Redis** | Persistence & State. Timescale for history, Redis for real-time. |
| **AI Trading Brain** | **Python** (PyTorch, Pandas) | Feature engineering, regime class., strategy, signal gen. |
| **MT5 Bridge** | **Python** (`MetaTrader5`) | Execution only. No strategy logic. Fail-safe defaults. |
| **ML Training Lab** | **Python** (PyTorch + ROCm) | Model training, walk-forward validation. GPU passthrough. |
| **Monitoring** | **Prometheus + Grafana** | Observability. Metrics scrape every 15s. |

### 2. Communication Protocols
- **Market Data (High Throughput)**: **ZeroMQ PUB/SUB**. Topic: `symbol`. Payload: `Protobuf`.
- **Trading Signals (Reliable)**: **gRPC**. Request/Response with Ack.
- **State/Config (Real-time)**: **Redis Pub/Sub**.
- **Metrics**: **HTTP /metrics** (Prometheus pull).

### 3. Fail-Safe Principles
- **Degrade Gracefully**: If data stops, HOLD. If Bridge disconnects, stop trading.
- **Isolation**: Each service runs in its own VM (Proxmox) -> Docker Container.
- **No Shared Mutable State**: Services communicate via messages, not shared memory.

### 4. Architecture Validation Checklist
- [ ] Does this belong in this service? (Separation of Concerns)
- [ ] Is the correct language being used? (Go for I/O, Python for AI)
- [ ] Is the communication protocol appropriate? (ZMQ for speed, gRPC for reliability)
- [ ] Are we avoiding look-ahead bias? (Strict timestamp ordering)
