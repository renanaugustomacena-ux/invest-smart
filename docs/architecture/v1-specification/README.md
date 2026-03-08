# V1_Bot — System Design Documentation

Comprehensive engineering documentation covering every aspect of the MONEYMAKER V1 trading system. These 14 modules serve as the technical specification and implementation guide for the entire ecosystem.

## Document Index

| # | Module | Topics |
|---|---|---|
| 01 | [System Vision & Architecture](01_System_Vision_and_Architecture_Overview.md) | Mission, system goals, high-level architecture, service boundaries |
| 02 | [Infrastructure & Proxmox Setup](02_Infrastructure_and_Proxmox_Server_Setup.md) | Hardware, VM topology, network, storage, Proxmox configuration |
| 03 | [Microservices Architecture](03_Microservices_Architecture_and_Communication.md) | Service communication (gRPC, ZMQ), API contracts, resilience patterns |
| 04 | [Data Ingestion & Market Data](04_Data_Ingestion_and_Real_Time_Market_Data_Service.md) | Exchange connectors, normalization, OHLCV aggregation, tick storage |
| 05 | [Database & Time-Series Storage](05_Database_Architecture_and_Time_Series_Storage.md) | TimescaleDB schema, hypertables, retention, query patterns |
| 06 | [AI/ML Training Infrastructure](06_AI_ML_Training_Infrastructure_and_Pipeline.md) | GPU pipeline, JEPA/GNN/MLP architectures, model lifecycle |
| 07 | [AI Trading Brain](07_AI_Trading_Brain_Intelligence_Layer.md) | Strategy engine, feature extraction, signal aggregation |
| 08 | [MT5 Integration & Execution](08_MetaTrader5_Integration_and_Trade_Execution_Bridge.md) | MT5 API, order management, position tracking, safety checks |
| 09 | [Risk Management & Safety](09_Risk_Management_and_Safety_Systems.md) | Circuit breakers, drawdown limits, position sizing, kill switches |
| 10 | [Monitoring & Observability](10_Monitoring_Observability_and_Dashboard.md) | Prometheus metrics, Grafana dashboards, alerting, log aggregation |
| 11 | [Dev Workflow & Deployment](11_Development_Workflow_Testing_and_Deployment.md) | CI/CD, testing strategy, Docker, release process |
| 12 | [Security & Compliance](12_Security_Compliance_and_Audit.md) | Secrets management, audit trails, access control |
| 13 | [Roadmap & Phases](13_Roadmap_and_Implementation_Phases.md) | Implementation phases, milestones, prioritization |
| 14 | [Mathematical Foundations](14_Mathematical_Foundations_and_Quantitative_Finance.md) | Quantitative models, statistical methods, indicator math |

## Usage

These documents are the **single source of truth** for system design decisions. Reference them when:

- **Implementing** a new feature — check the relevant module for specifications
- **Onboarding** — read modules 01–03 for system understanding
- **Debugging** — consult the architecture module for data flow and service boundaries
- **Planning** — use module 13 for roadmap context
