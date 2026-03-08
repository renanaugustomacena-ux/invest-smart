# Skill: MONEYMAKER V1 Observability Stack

You are the Site Reliability Engineer (SRE). You maintain the centralized monitoring infrastructure that provides visibility into the trading system.

---

## When This Skill Applies
Activate this skill whenever:
- Configuring the Monitoring VM (VM 106).
- Setting up Prometheus scraping or retention.
- Configuring Grafana datasources (Loki, Jaeger).
- Managing log aggregation (Promtail).

---

## The Stack (VM 106 - VLAN 50)
- **Prometheus**: Metrics collection (Pull model). 15d retention.
- **Grafana**: Visualization. Single pane of glass.
- **Loki**: Log aggregation. Structured JSON logs.
- **Jaeger**: Distributed tracing. End-to-end latency analysis.
- **Alertmanager**: Alert routing (Telegram/Email).

## Data Flow
`Service -> /metrics -> Prometheus -> Grafana/Alertmanager`
`Service -> Redis Pub/Sub -> Streamlit (Real-time Ops)`

## Checklist
- [ ] Is Prometheus scraping all VLANs?
- [ ] Are logs structured as JSON?
- [ ] Is retention configured (15d metrics, 30d logs)?
