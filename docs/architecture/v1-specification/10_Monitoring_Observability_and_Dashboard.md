# 10. Monitoring, Observability, and Dashboard

> **Autore** | Renan Augusto Macena

## Document Metadata

| Field              | Value                                              |
|--------------------|-----------------------------------------------------|
| **Document ID**    | V1BOT-DOC-010                                       |
| **Version**        | 1.0                                                 |
| **Last Updated**   | 2026-02-21                                          |
| **Author**         | V1_Bot Architecture Team                            |
| **Status**         | Active                                              |
| **Classification** | Internal / Technical                                |
| **Dependencies**   | DOC-001 (Architecture), DOC-002 (Infrastructure), DOC-003 (Microservices), DOC-009 (Risk Management) |

---

## Table of Contents

1. [10.1 Observability Philosophy](#101-observability-philosophy)
2. [10.2 Monitoring Architecture Overview](#102-monitoring-architecture-overview)
3. [10.3 Infrastructure Monitoring](#103-infrastructure-monitoring)
4. [10.4 Service-Level Monitoring](#104-service-level-monitoring)
5. [10.5 Trading Performance Metrics](#105-trading-performance-metrics)
6. [10.6 Prometheus Configuration](#106-prometheus-configuration)
7. [10.7 Grafana Dashboards](#107-grafana-dashboards)
8. [10.8 Streamlit Trading Operations Center](#108-streamlit-trading-operations-center)
9. [10.9 Alerting System](#109-alerting-system)
10. [10.10 Log Aggregation](#1010-log-aggregation)
11. [10.11 Distributed Tracing](#1011-distributed-tracing)
12. [10.12 Health Checks and Self-Healing](#1012-health-checks-and-self-healing)
13. [10.13 Capacity Planning and Performance Baselines](#1013-capacity-planning-and-performance-baselines)
14. [10.14 Deployment and Configuration](#1014-deployment-and-configuration)

---

## 10.1 Observability Philosophy

### 10.1.1 Why Observability Is Non-Negotiable in Automated Trading

Automated trading systems operate in an environment where the cost of ignorance is measured in direct financial loss. Unlike traditional web applications where a few seconds of degraded performance might cause user frustration, a few seconds of undetected anomaly in a trading system can result in unauthorized position accumulation, unchecked drawdowns, or missed hedging signals that cascade into catastrophic losses. The V1_Bot ecosystem therefore treats observability not as a supplementary operational concern but as a foundational architectural pillar with the same importance as the trading logic itself.

The distinction between monitoring and observability is crucial to understand before proceeding. Monitoring is the practice of collecting predefined metrics and checking them against known thresholds -- it answers the question "is this known thing broken?" Observability, by contrast, is the property of a system that allows operators to ask arbitrary questions about its internal state based on the external outputs it produces. A truly observable system allows engineers to diagnose novel failure modes that were never anticipated at design time. In trading systems, novel failure modes are the norm: market microstructure changes, broker API behavior shifts, data provider outages with partial data, GPU thermal throttling affecting processing latency -- these are not scenarios you can enumerate exhaustively in advance.

The V1_Bot monitoring infrastructure is therefore designed to support both reactive monitoring (alerting on known failure conditions) and proactive observability (enabling deep investigation of unknown-unknowns through rich telemetry data).

### 10.1.2 The Three Pillars of Observability

The industry-standard framework for observability rests on three complementary data types, each of which the V1_Bot system implements comprehensively.

**Pillar 1: Metrics**

Metrics are numerical measurements collected at regular intervals that describe the state and behavior of system components. They are cheap to store, fast to query, and ideal for dashboards and alerting. In V1_Bot, metrics are collected via Prometheus and exposed by every microservice through `/metrics` HTTP endpoints. Metrics fall into four semantic types:

- **Counters**: Monotonically increasing values (e.g., `v1bot_trades_executed_total`, `v1bot_orders_rejected_total`). Counters can only go up; rate functions are applied to derive throughput.
- **Gauges**: Point-in-time values that can go up or down (e.g., `v1bot_account_equity`, `v1bot_open_positions_count`, `v1bot_gpu_temperature_celsius`).
- **Histograms**: Distributions of observed values, bucketed (e.g., `v1bot_order_latency_seconds`, `v1bot_prediction_latency_seconds`). These allow computation of quantiles (p50, p95, p99) without storing every individual observation.
- **Summaries**: Similar to histograms but with pre-computed quantiles calculated on the client side. Used sparingly due to aggregation limitations.

Every V1_Bot metric follows a strict naming convention: `v1bot_<subsystem>_<metric_name>_<unit>`, where unit suffixes follow Prometheus conventions (`_seconds`, `_bytes`, `_total`, `_ratio`). Labels are used judiciously to add dimensions without causing cardinality explosions.

**Pillar 2: Logs**

Logs are discrete, timestamped textual records of events that occurred within the system. They provide the narrative context that metrics cannot -- the "what exactly happened" behind a metric anomaly. V1_Bot uses structured JSON logging across all services, aggregated through Grafana Loki with Promtail agents. Every log entry includes mandatory fields: `timestamp`, `service`, `level`, `trace_id`, `span_id`, `message`, and service-specific context fields. This structure enables powerful correlation between logs and traces, allowing operators to jump from a Grafana metric anomaly to the exact log entries produced during that anomaly window.

**Pillar 3: Traces**

Distributed traces follow a single request or operation as it flows through multiple services. In V1_Bot, a critical traced operation is the full trade decision lifecycle: market data arrives at Data Ingestion, flows through the Algo Engine for prediction, passes through Risk Manager for vetting, and arrives at the Execution Bridge for order placement. Jaeger collects and visualizes these traces via OpenTelemetry instrumentation, providing end-to-end latency breakdowns and dependency mapping. Traces answer the question "where exactly did this operation spend its time, and why?"

### 10.1.3 Trading-Specific Observability Requirements

Beyond the standard three pillars, trading systems impose additional observability requirements that do not exist in general-purpose software:

- **Tick-Level Timing Accuracy**: Timestamps must be synchronized across all VMs to microsecond precision using NTP/PTP. A 100ms clock skew between Data Ingestion and Execution Bridge could make latency measurements meaningless.
- **Financial Auditability**: Every trade decision, risk check, and order execution must be logged with sufficient detail for post-trade audit and regulatory review. These logs are immutable once written.
- **Real-Time P&L Visibility**: Unlike most software systems, trading systems produce a single, unambiguous metric of success -- profit and loss. This must be visible in real time, broken down by strategy, symbol, and time period.
- **Anomaly Detection on Model Behavior**: AI model drift, confidence distribution shifts, and feature importance changes must be detected before they manifest as trading losses.
- **Broker Connectivity Monitoring**: The connection to MetaTrader 5 is the single point of execution. Its health, latency, and reliability must be monitored with higher priority than any internal service.

### 10.1.4 Operational Principles

The V1_Bot monitoring system is governed by several operational principles:

1. **Alert on symptoms, not causes**: Alert on "order latency exceeds 500ms" (symptom the user experiences) rather than "CPU usage exceeds 80%" (a cause that may or may not produce symptoms).
2. **Every alert must be actionable**: If an alert fires and the operator's response is "I don't know what to do about this," the alert is poorly designed. Every alert has a linked runbook.
3. **Dashboards tell a story**: Dashboards are not collections of random metrics. Each dashboard answers a specific operational question and arranges panels to guide the operator's eye from overview to detail.
4. **Instrument before you need it**: Every new feature or service added to V1_Bot must include metrics, structured logging, and trace propagation from day one. Retrofitting observability is expensive and produces gaps.
5. **Cost-aware retention**: High-resolution data (5-second scrapes) is retained for 48 hours, then downsampled. Raw logs are retained for 30 days; aggregated metrics for 365 days. Trading performance data is retained indefinitely for backtesting comparison.

---

## 10.2 Monitoring Architecture Overview

### 10.2.1 Centralized Monitoring VM

The monitoring infrastructure runs on a dedicated Proxmox VM (`vm-monitor`, VM ID 106) with resources allocated specifically for observability workloads:

| Resource         | Allocation     | Purpose                                       |
|------------------|----------------|------------------------------------------------|
| **vCPUs**        | 4 cores        | Prometheus TSDB compaction, Grafana rendering   |
| **RAM**          | 8 GB           | Prometheus in-memory chunks, Loki indexes       |
| **OS Disk**      | 32 GB (SSD)    | Ubuntu 22.04 LTS, monitoring stack binaries     |
| **Data Disk**    | 256 GB (SSD)   | Prometheus TSDB, Loki chunks, Grafana SQLite    |
| **Network**      | VLAN 50 (mgmt) | Monitoring traffic isolated from trading data   |

The monitoring VM resides on VLAN 50 (Management) but has firewall rules permitting it to scrape metrics endpoints on all other VLANs (VLAN 10 for Data Ingestion, VLAN 20 for Algo Engine, VLAN 30 for Execution, VLAN 40 for Database). This is the only VM with cross-VLAN read access to all service metrics.

### 10.2.2 High-Level Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                           Proxmox Host (pve-trade-01)                             |
|                                                                                   |
|  +----------------+  +----------------+  +----------------+  +----------------+   |
|  | vm-data-ingest |  |  vm-algo-engine   |  | vm-exec-bridge |  | vm-risk-mgr    |   |
|  |   (VLAN 10)    |  |   (VLAN 20)    |  |   (VLAN 30)    |  |   (VLAN 30)    |   |
|  |                |  |                |  |                |  |                |   |
|  | Go service     |  | Python service |  | Python service |  | Python service |   |
|  | :9100 node_exp |  | :9100 node_exp |  | :9100 node_exp |  | :9100 node_exp |   |
|  | :8081 /metrics |  | :8082 /metrics |  | :8083 /metrics |  | :8084 /metrics |   |
|  | :3100 promtail |  | :3100 promtail |  | :3100 promtail |  | :3100 promtail |   |
|  +-------+--------+  +-------+--------+  +-------+--------+  +-------+--------+   |
|          |                    |                    |                   |            |
|          |        VLAN 50 (Management Network)     |                  |            |
|          +----------+---------+----------+---------+------------------+            |
|                     |                    |                                         |
|          +----------+--------------------+----------+                              |
|          |           vm-monitor (VM 106)            |                              |
|          |              (VLAN 50)                   |                              |
|          |                                          |                              |
|          |  +-------------+  +------------------+   |                              |
|          |  | Prometheus   |  | Grafana          |   |                              |
|          |  | :9090        |  | :3000            |   |                              |
|          |  | pull metrics |  | dashboards       |   |                              |
|          |  +-------------+  +------------------+   |                              |
|          |                                          |                              |
|          |  +-------------+  +------------------+   |                              |
|          |  | Loki         |  | Alertmanager     |   |                              |
|          |  | :3100        |  | :9093            |   |                              |
|          |  | log storage  |  | alert routing    |   |                              |
|          |  +-------------+  +------------------+   |                              |
|          |                                          |                              |
|          |  +-------------+  +------------------+   |                              |
|          |  | Jaeger       |  | Streamlit        |   |                              |
|          |  | :16686       |  | :8501            |   |                              |
|          |  | trace UI     |  | trading ops      |   |                              |
|          |  +-------------+  +------------------+   |                              |
|          +------------------------------------------+                              |
|                                                                                   |
|  +----------------+                                                               |
|  |  vm-database   |                                                               |
|  |   (VLAN 40)    |                                                               |
|  | PostgreSQL     |                                                               |
|  | TimescaleDB    |                                                               |
|  | Redis          |                                                               |
|  | :9100 node_exp |                                                               |
|  | :9187 pg_exp   |                                                               |
|  | :9121 redis_ex |                                                               |
|  +----------------+                                                               |
+-----------------------------------------------------------------------------------+
```

### 10.2.3 Prometheus Pull Model

Prometheus operates on a pull-based model: it actively scrapes HTTP endpoints exposed by each service at configured intervals. This design was chosen over push-based alternatives (like StatsD or InfluxDB line protocol) for several reasons specific to the trading context:

- **Liveness Detection**: If Prometheus cannot scrape a target, the target is confirmed down. Push-based systems cannot distinguish between "service is down" and "service is healthy but not producing events."
- **Centralized Configuration**: All scrape targets are defined in `prometheus.yml` on the monitoring VM. Adding a new service requires only a configuration change and reload, not a change to the service itself.
- **Backpressure Safety**: Services expose metrics passively; they are never blocked by a slow monitoring backend. This is critical for trading services where any added latency is unacceptable.

Scrape intervals are differentiated by service criticality:

| Target Category       | Scrape Interval | Scrape Timeout | Rationale                               |
|-----------------------|-----------------|----------------|-----------------------------------------|
| Trading services      | 5s              | 3s             | High-resolution for latency monitoring  |
| Infrastructure (Node) | 15s             | 10s            | Standard infrastructure cadence         |
| Database exporters    | 10s             | 8s             | Balance between resolution and load     |
| Proxmox host          | 30s             | 15s            | Host-level metrics change slowly        |

### 10.2.4 Data Flow Architecture

The monitoring data flow follows a well-defined pipeline:

```
  Services                    Collection           Storage            Presentation
  --------                    ----------           -------            ------------

  Go/Python apps              Prometheus           Prometheus TSDB    Grafana Dashboards
  (custom metrics) ---------> (scrape) ----------> (15d retention) -> (visualization)
                                   |                                       |
  Node Exporter     ------------->-+                                       |
  (host metrics)                   |                                       |
                                   +---> Recording Rules ---> Alerts ----> Alertmanager
  PostgreSQL Exporter ------>-+    |                                       |    |
  Redis Exporter      ------>-+----+                                       |    +--> Telegram
                                                                           |
  Promtail agents              Loki                Loki Chunks         Grafana Explore
  (structured logs) ---------> (push) -----------> (30d retention) -> (log queries)
                                                                           |
  OTel SDKs                    Jaeger Collector     Jaeger Storage     Jaeger UI / Grafana
  (trace spans)   -----------> (push) -----------> (7d retention)  -> (trace view)
                                                                           |
  Redis Pub/Sub                                                        Streamlit
  (live state)   -------------------------------------------------->  (trading ops)
```

### 10.2.5 Redis as the Real-Time Data Bus

While Prometheus provides the canonical time-series storage for metrics, many trading dashboard features require sub-second update latency that Prometheus's 5-second scrape interval cannot provide. For these real-time needs, services publish state updates to Redis Pub/Sub channels and Redis key-value stores, which the Streamlit Trading Operations Center consumes directly.

The Redis data bus carries:

- **Live prices and spreads** (updated every tick, key: `v1bot:live:prices:<symbol>`)
- **Current open positions** (updated on every position change, key: `v1bot:live:positions`)
- **Real-time P&L** (updated every second, key: `v1bot:live:pnl`)
- **AI prediction results** (published on every prediction cycle, channel: `v1bot:predictions`)
- **Risk manager state** (circuit breaker status, drawdown levels, channel: `v1bot:risk:state`)
- **System health heartbeats** (every 5 seconds per service, key: `v1bot:health:<service>`)

This dual-path architecture (Prometheus for historical metrics, Redis for live state) ensures that operators see sub-second updates on the Streamlit dashboard while maintaining full historical queryability in Grafana.

### 10.2.6 Retention Policies

Data retention is configured based on the trade-off between storage cost and operational need:

| Data Type              | Hot Retention | Warm Retention | Cold/Archive      |
|------------------------|---------------|----------------|--------------------|
| Prometheus raw metrics | 48 hours      | 15 days        | Downsampled 365d   |
| Prometheus recordings  | 15 days       | 90 days        | N/A                |
| Loki logs              | 7 days        | 30 days        | Compressed archive |
| Jaeger traces          | 3 days        | 7 days         | Sampled archive    |
| Trading P&L data       | Always hot    | Always hot     | Indefinite (DB)    |
| Alert history          | 30 days       | 90 days        | N/A                |

Prometheus is configured with `--storage.tsdb.retention.time=15d` and `--storage.tsdb.retention.size=200GB` (whichever limit is hit first). A separate CronJob runs Prometheus remote-write to a long-term storage backend for metrics older than 15 days that have been downsampled to 5-minute resolution.

---

## 10.3 Infrastructure Monitoring

### 10.3.1 Proxmox Host Monitoring

The Proxmox hypervisor itself is the foundation upon which all VMs run. Its health directly affects every trading service. The following metrics are collected from the Proxmox host via Node Exporter (running directly on the host at `:9100`) and the Proxmox API exporter:

**CPU Monitoring (Per-Core)**

```yaml
# Prometheus recording rules for CPU monitoring
groups:
  - name: v1bot_proxmox_cpu
    interval: 15s
    rules:
      - record: v1bot:proxmox:cpu_usage_per_core:ratio
        expr: |
          1 - avg by (cpu) (
            rate(node_cpu_seconds_total{mode="idle", instance="pve-trade-01:9100"}[2m])
          )

      - record: v1bot:proxmox:cpu_usage_total:ratio
        expr: |
          1 - avg(
            rate(node_cpu_seconds_total{mode="idle", instance="pve-trade-01:9100"}[2m])
          )

      - record: v1bot:proxmox:cpu_iowait:ratio
        expr: |
          avg by (cpu) (
            rate(node_cpu_seconds_total{mode="iowait", instance="pve-trade-01:9100"}[2m])
          )

      - record: v1bot:proxmox:cpu_steal:ratio
        expr: |
          avg(
            rate(node_cpu_seconds_total{mode="steal", instance="pve-trade-01:9100"}[2m])
          )

      - record: v1bot:proxmox:load_average_normalized:ratio
        expr: |
          node_load5{instance="pve-trade-01:9100"}
          /
          count(node_cpu_seconds_total{mode="idle", instance="pve-trade-01:9100"})
```

Per-core CPU monitoring is essential because Proxmox can pin VM vCPUs to specific physical cores. If the Algo Engine VM is pinned to cores 8-15 and those cores are saturated while cores 0-7 are idle, aggregate CPU usage would appear normal while the AI service suffers critical latency degradation.

**Memory Monitoring**

```yaml
      - record: v1bot:proxmox:memory_usage:ratio
        expr: |
          1 - (
            node_memory_MemAvailable_bytes{instance="pve-trade-01:9100"}
            /
            node_memory_MemTotal_bytes{instance="pve-trade-01:9100"}
          )

      - record: v1bot:proxmox:memory_pressure:bool
        expr: |
          rate(node_vmstat_pgmajfault{instance="pve-trade-01:9100"}[5m]) > 100

      - record: v1bot:proxmox:swap_usage:ratio
        expr: |
          1 - (
            node_memory_SwapFree_bytes{instance="pve-trade-01:9100"}
            /
            node_memory_SwapTotal_bytes{instance="pve-trade-01:9100"}
          )
```

Any swap usage above 0% on the Proxmox host triggers a WARNING alert, because swap introduces unpredictable latency that could affect trading operations. Memory pressure (high page fault rates) triggers CRITICAL alerting even before memory is fully consumed.

**ZFS Pool Health**

The Proxmox host uses ZFS for VM storage. ZFS health monitoring includes:

```yaml
      # ZFS pool health (scraped via custom text collector)
      - record: v1bot:proxmox:zfs_pool_healthy:bool
        expr: |
          node_zfs_pool_state{instance="pve-trade-01:9100", state="online"} == 1

      - record: v1bot:proxmox:zfs_arc_hit:ratio
        expr: |
          node_zfs_arc_hits{instance="pve-trade-01:9100"}
          /
          (node_zfs_arc_hits{instance="pve-trade-01:9100"} + node_zfs_arc_misses{instance="pve-trade-01:9100"})

      - record: v1bot:proxmox:zfs_pool_free:ratio
        expr: |
          node_zfs_pool_free_bytes{instance="pve-trade-01:9100"}
          /
          node_zfs_pool_size_bytes{instance="pve-trade-01:9100"}
```

A ZFS pool dropping below 80% free space triggers a WARNING (ZFS performance degrades significantly above 80% utilization due to copy-on-write fragmentation). Any pool state other than "online" triggers an immediate CRITICAL alert.

**Network Monitoring (Per-VLAN)**

```yaml
  - name: v1bot_proxmox_network
    interval: 15s
    rules:
      # Per-VLAN traffic rates
      - record: v1bot:proxmox:network_rx_bytes:rate5m
        expr: |
          rate(node_network_receive_bytes_total{
            instance="pve-trade-01:9100",
            device=~"vmbr0\\..*"
          }[5m])

      - record: v1bot:proxmox:network_tx_bytes:rate5m
        expr: |
          rate(node_network_transmit_bytes_total{
            instance="pve-trade-01:9100",
            device=~"vmbr0\\..*"
          }[5m])

      # Network error rates
      - record: v1bot:proxmox:network_errors:rate5m
        expr: |
          rate(node_network_receive_errs_total{instance="pve-trade-01:9100"}[5m])
          +
          rate(node_network_transmit_errs_total{instance="pve-trade-01:9100"}[5m])

      # Dropped packets (critical for trading data)
      - record: v1bot:proxmox:network_drops:rate5m
        expr: |
          rate(node_network_receive_drop_total{instance="pve-trade-01:9100"}[5m])
          +
          rate(node_network_transmit_drop_total{instance="pve-trade-01:9100"}[5m])
```

Any non-zero network drop rate on VLAN 10 (Data Ingestion) or VLAN 30 (Execution) triggers immediate investigation, as dropped packets could mean lost market data or failed order transmissions.

**Disk I/O and Temperature**

```yaml
  - name: v1bot_proxmox_disk
    interval: 15s
    rules:
      - record: v1bot:proxmox:disk_io_utilization:ratio
        expr: |
          rate(node_disk_io_time_seconds_total{instance="pve-trade-01:9100"}[5m])

      - record: v1bot:proxmox:disk_read_latency:seconds
        expr: |
          rate(node_disk_read_time_seconds_total{instance="pve-trade-01:9100"}[5m])
          /
          rate(node_disk_reads_completed_total{instance="pve-trade-01:9100"}[5m])

      - record: v1bot:proxmox:disk_write_latency:seconds
        expr: |
          rate(node_disk_write_time_seconds_total{instance="pve-trade-01:9100"}[5m])
          /
          rate(node_disk_writes_completed_total{instance="pve-trade-01:9100"}[5m])

      # Temperature monitoring (SMART data via node_exporter textfile collector)
      - record: v1bot:proxmox:disk_temperature:celsius
        expr: |
          node_hwmon_temp_celsius{instance="pve-trade-01:9100"}

      - record: v1bot:proxmox:cpu_temperature:celsius
        expr: |
          node_hwmon_temp_celsius{instance="pve-trade-01:9100", sensor="coretemp"}
```

SSD write latency above 5ms triggers a WARNING; above 20ms triggers CRITICAL. CPU temperatures above 80C trigger a WARNING; above 90C trigger CRITICAL with automatic reduction of workload.

**GPU Monitoring**

The GPU (if present) is monitored via the `nvidia-gpu-exporter` running on the Algo Engine VM:

```yaml
  - name: v1bot_gpu
    interval: 5s
    rules:
      - record: v1bot:gpu:utilization:ratio
        expr: nvidia_gpu_duty_cycle / 100

      - record: v1bot:gpu:memory_used:ratio
        expr: |
          nvidia_gpu_memory_used_bytes
          /
          nvidia_gpu_memory_total_bytes

      - record: v1bot:gpu:temperature:celsius
        expr: nvidia_gpu_temperature_celsius

      - record: v1bot:gpu:power_draw:watts
        expr: nvidia_gpu_power_draw_watts

      - record: v1bot:gpu:clock_throttle:bool
        expr: |
          nvidia_gpu_clock_speed_mhz < (nvidia_gpu_max_clock_speed_mhz * 0.9)
```

GPU thermal throttling is a critical issue for trading because it introduces unpredictable latency spikes in computation. If the GPU clock drops below 90% of maximum due to thermal limits, a WARNING alert fires and the Algo Engine begins routing predictions to CPU-based fallback strategies.

### 10.3.2 Per-VM Monitoring

Each VM runs Node Exporter v1.7.x on port 9100, providing standard Linux host metrics. Additionally, each VM reports V1_Bot-specific health information through a custom textfile collector that writes to `/var/lib/node_exporter/textfile_collector/v1bot.prom`.

Key per-VM metrics monitored:

| Metric                       | Warning Threshold | Critical Threshold | Applies To         |
|------------------------------|-------------------|--------------------|---------------------|
| CPU utilization              | > 70% for 5m      | > 90% for 2m       | All VMs             |
| Memory utilization           | > 80%             | > 95%              | All VMs             |
| Disk space free              | < 20%             | < 10%              | All VMs             |
| System load (1m / num_cpus)  | > 1.5             | > 3.0              | All VMs             |
| Open file descriptors        | > 80% of limit    | > 95% of limit     | Data Ingestion, DB  |
| Network connections (ESTAB)  | > 5000            | > 10000            | Data Ingestion      |
| Process count                | > 300             | > 500              | All VMs             |
| NTP clock offset             | > 10ms            | > 50ms             | All VMs             |

### 10.3.3 Node Exporter Configuration

Node Exporter is deployed as a systemd service on each VM with carefully selected collectors enabled. Not all default collectors are relevant; enabling unnecessary collectors wastes scrape time and storage:

```yaml
# /etc/systemd/system/node_exporter.service
[Unit]
Description=Node Exporter for V1_Bot Monitoring
Documentation=https://github.com/prometheus/node_exporter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter \
  --web.listen-address=":9100" \
  --web.telemetry-path="/metrics" \
  --collector.cpu \
  --collector.diskstats \
  --collector.filesystem \
  --collector.hwmon \
  --collector.loadavg \
  --collector.meminfo \
  --collector.netdev \
  --collector.netstat \
  --collector.os \
  --collector.processes \
  --collector.sockstat \
  --collector.stat \
  --collector.systemd \
  --collector.textfile \
  --collector.time \
  --collector.vmstat \
  --collector.zfs \
  --no-collector.arp \
  --no-collector.bcache \
  --no-collector.bonding \
  --no-collector.btrfs \
  --no-collector.conntrack \
  --no-collector.entropy \
  --no-collector.fibrechannel \
  --no-collector.infiniband \
  --no-collector.ipvs \
  --no-collector.mdadm \
  --no-collector.nfs \
  --no-collector.nfsd \
  --no-collector.nvme \
  --no-collector.powersupplyclass \
  --no-collector.pressure \
  --no-collector.rapl \
  --no-collector.schedstat \
  --no-collector.thermal_zone \
  --no-collector.timex \
  --no-collector.udp_queues \
  --no-collector.xfs \
  --collector.textfile.directory="/var/lib/node_exporter/textfile_collector" \
  --collector.filesystem.mount-points-exclude="^/(sys|proc|dev|host|etc)($$|/)" \
  --collector.diskstats.device-exclude="^(ram|loop|fd|sr)\\d+$$"
Restart=always
RestartSec=5
SyslogIdentifier=node_exporter
CPUAccounting=true
MemoryAccounting=true
MemoryMax=128M

[Install]
WantedBy=multi-user.target
```

The textfile collector directory allows services to write custom `.prom` files containing additional metrics that are scraped alongside Node Exporter's built-in metrics. This is used for V1_Bot service health indicators and for metrics that cannot be easily exposed via HTTP (e.g., cron job results, backup status).

---

## 10.4 Service-Level Monitoring

### 10.4.1 Data Ingestion Service (Go)

The Data Ingestion service is the entry point for all market data. Its monitoring focuses on data freshness, throughput, and connection health.

**Custom Metrics Exposed on `:8081/metrics`**

```go
package metrics

import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
)

var (
    // Throughput metrics
    MessagesReceivedTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "v1bot_data_ingestion_messages_received_total",
            Help: "Total number of market data messages received",
        },
        []string{"source", "symbol", "message_type"},
    )

    MessagesProcessedTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "v1bot_data_ingestion_messages_processed_total",
            Help: "Total number of messages successfully processed and forwarded",
        },
        []string{"source", "symbol"},
    )

    MessagesDroppedTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "v1bot_data_ingestion_messages_dropped_total",
            Help: "Total number of messages dropped (buffer overflow, parse error)",
        },
        []string{"source", "reason"},
    )

    // Latency metrics
    MessageProcessingLatency = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "v1bot_data_ingestion_processing_latency_seconds",
            Help:    "Time from message receipt to forwarding completion",
            Buckets: []float64{0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5},
        },
        []string{"source", "symbol"},
    )

    EndToEndDataLatency = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "v1bot_data_ingestion_e2e_latency_seconds",
            Help:    "End-to-end latency from exchange timestamp to local receipt",
            Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0},
        },
        []string{"source", "symbol"},
    )

    // Connection status
    WebSocketConnectionStatus = promauto.NewGaugeVec(
        prometheus.GaugeOpts{
            Name: "v1bot_data_ingestion_websocket_connected",
            Help: "WebSocket connection status (1=connected, 0=disconnected)",
        },
        []string{"source", "endpoint"},
    )

    WebSocketReconnectsTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "v1bot_data_ingestion_websocket_reconnects_total",
            Help: "Total number of WebSocket reconnection attempts",
        },
        []string{"source"},
    )

    // Data freshness
    LastMessageTimestamp = promauto.NewGaugeVec(
        prometheus.GaugeOpts{
            Name: "v1bot_data_ingestion_last_message_timestamp_seconds",
            Help: "Unix timestamp of the last received message per symbol",
        },
        []string{"source", "symbol"},
    )

    // Buffer utilization
    InternalBufferUtilization = promauto.NewGaugeVec(
        prometheus.GaugeOpts{
            Name: "v1bot_data_ingestion_buffer_utilization_ratio",
            Help: "Current utilization of internal message buffers",
        },
        []string{"buffer_name"},
    )

    // Goroutine and connection pool
    ActiveGoroutines = promauto.NewGauge(
        prometheus.GaugeOpts{
            Name: "v1bot_data_ingestion_active_goroutines",
            Help: "Number of active goroutines in the data ingestion service",
        },
    )
)
```

**Key Data Ingestion Alerts**

| Alert Name                         | Condition                                                  | Severity | Action                              |
|------------------------------------|------------------------------------------------------------|----------|--------------------------------------|
| `DataIngestionWebSocketDown`       | `v1bot_data_ingestion_websocket_connected == 0` for 30s    | CRITICAL | Check connectivity, auto-reconnect   |
| `DataIngestionStaleData`           | `time() - v1bot_data_ingestion_last_message_timestamp_seconds > 60` | CRITICAL | Verify market hours, check source |
| `DataIngestionHighLatency`         | `histogram_quantile(0.99, ...) > 0.1` (100ms)             | WARNING  | Investigate network, check load      |
| `DataIngestionDroppedMessages`     | `rate(v1bot_data_ingestion_messages_dropped_total[5m]) > 0` | WARNING | Check buffer sizes, processing speed |
| `DataIngestionBufferNearFull`      | `v1bot_data_ingestion_buffer_utilization_ratio > 0.8`      | WARNING  | Scale buffers, check consumers       |
| `DataIngestionHighReconnectRate`   | `rate(v1bot_data_ingestion_websocket_reconnects_total[15m]) > 3` | WARNING | Network instability, check firewall |

### 10.4.2 Algo Engine Service (Python)

The Algo Engine is the most computationally intensive service and requires careful monitoring of both its trading strategy performance and its computational resource usage.

**Custom Metrics Exposed on `:8082/metrics`**

```python
# algo_engine/metrics.py
from prometheus_client import Counter, Gauge, Histogram, Info, Summary

# Prediction metrics
prediction_requests_total = Counter(
    'v1bot_algo_engine_prediction_requests_total',
    'Total number of prediction requests received',
    ['model_name', 'symbol', 'timeframe']
)

prediction_latency_seconds = Histogram(
    'v1bot_algo_engine_prediction_latency_seconds',
    'Time to generate a prediction',
    ['model_name', 'execution_device'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

prediction_confidence = Histogram(
    'v1bot_algo_engine_prediction_confidence',
    'Distribution of prediction confidence scores',
    ['model_name', 'signal_type'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
)

# Model health
active_model_version = Info(
    'v1bot_algo_engine_active_model',
    'Information about the currently active model'
)

model_last_recalibration_timestamp = Gauge(
    'v1bot_algo_engine_model_last_recalibration_timestamp_seconds',
    'Unix timestamp of the last model recalibration',
    ['model_name']
)

feature_drift_score = Gauge(
    'v1bot_algo_engine_feature_drift_score',
    'Population Stability Index (PSI) for feature drift detection',
    ['model_name', 'feature_name']
)

prediction_distribution_drift = Gauge(
    'v1bot_algo_engine_prediction_drift_score',
    'KL divergence between current and baseline prediction distributions',
    ['model_name']
)

# GPU/compute metrics
prediction_batch_size = Histogram(
    'v1bot_algo_engine_prediction_batch_size',
    'Number of samples in each prediction batch',
    ['model_name'],
    buckets=[1, 2, 4, 8, 16, 32, 64, 128]
)

# Fallback tier usage
fallback_tier_usage_total = Counter(
    'v1bot_algo_engine_fallback_tier_usage_total',
    'Number of times each fallback tier was invoked',
    ['tier', 'reason']
    # tier: "primary_gpu", "secondary_gpu", "cpu_fallback", "rule_based"
)

# Ensemble metrics
ensemble_model_agreement = Gauge(
    'v1bot_algo_engine_ensemble_agreement_ratio',
    'Agreement ratio among ensemble models (1.0 = unanimous)',
    ['symbol']
)

ensemble_models_active = Gauge(
    'v1bot_algo_engine_ensemble_models_active',
    'Number of models currently active in the ensemble',
    ['symbol']
)

# Cache metrics
feature_cache_hit_total = Counter(
    'v1bot_algo_engine_feature_cache_hit_total',
    'Feature computation cache hits'
)

feature_cache_miss_total = Counter(
    'v1bot_algo_engine_feature_cache_miss_total',
    'Feature computation cache misses'
)
```

The Algo Engine monitoring pays special attention to **confidence distribution monitoring**. If the model suddenly starts producing predictions with uniformly low confidence (below 0.3), it may indicate feature pipeline corruption or model drift. Conversely, if confidence is uniformly high (above 0.95), the model may be overfitting to recent patterns. A healthy confidence distribution shows a spread with a slight right skew.

**Fallback tier monitoring** tracks how often the system falls back from primary strategy to secondary strategy to rule-based fallback. If the `cpu_fallback` or `rule_based` tier is invoked more than 5% of the time during trading hours, this indicates reliability issues that need investigation.

### 10.4.3 Execution Bridge Service (Python)

The Execution Bridge is the most latency-sensitive service, as it interfaces directly with the MetaTrader 5 terminal for order placement and management.

**Custom Metrics Exposed on `:8083/metrics`**

```python
# execution_bridge/metrics.py
from prometheus_client import Counter, Gauge, Histogram, Enum

# Order execution metrics
orders_submitted_total = Counter(
    'v1bot_execution_orders_submitted_total',
    'Total orders submitted to MT5',
    ['symbol', 'order_type', 'direction']
)

orders_filled_total = Counter(
    'v1bot_execution_orders_filled_total',
    'Total orders successfully filled',
    ['symbol', 'order_type', 'direction']
)

orders_rejected_total = Counter(
    'v1bot_execution_orders_rejected_total',
    'Total orders rejected by MT5 or broker',
    ['symbol', 'reason']
)

orders_timed_out_total = Counter(
    'v1bot_execution_orders_timed_out_total',
    'Total orders that timed out waiting for fill',
    ['symbol']
)

# Latency metrics
order_submission_latency_seconds = Histogram(
    'v1bot_execution_order_submission_latency_seconds',
    'Time from order decision to MT5 submission',
    ['symbol', 'order_type'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

order_fill_latency_seconds = Histogram(
    'v1bot_execution_order_fill_latency_seconds',
    'Time from MT5 submission to fill confirmation',
    ['symbol', 'order_type'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

e2e_trade_latency_seconds = Histogram(
    'v1bot_execution_e2e_trade_latency_seconds',
    'End-to-end latency from signal generation to fill confirmation',
    ['symbol'],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Slippage tracking
order_slippage_pips = Histogram(
    'v1bot_execution_slippage_pips',
    'Slippage in pips (positive = unfavorable)',
    ['symbol', 'direction'],
    buckets=[-5, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 5, 10, 20]
)

# Fill rate
fill_rate_ratio = Gauge(
    'v1bot_execution_fill_rate_ratio',
    'Rolling fill rate (filled / submitted) over last 100 orders',
    ['symbol']
)

# MT5 connection status
mt5_connection_status = Enum(
    'v1bot_execution_mt5_connection_status',
    'Current MT5 connection state',
    states=['connected', 'disconnected', 'reconnecting', 'error']
)

mt5_terminal_connected = Gauge(
    'v1bot_execution_mt5_terminal_connected',
    'MT5 terminal connection status (1=connected, 0=disconnected)'
)

mt5_last_heartbeat_timestamp = Gauge(
    'v1bot_execution_mt5_last_heartbeat_timestamp_seconds',
    'Unix timestamp of the last MT5 heartbeat response'
)

# Position tracking
open_positions_count = Gauge(
    'v1bot_execution_open_positions_count',
    'Number of currently open positions',
    ['symbol']
)

open_positions_volume = Gauge(
    'v1bot_execution_open_positions_volume_lots',
    'Total volume of open positions in lots',
    ['symbol', 'direction']
)

# Account state
account_equity = Gauge(
    'v1bot_execution_account_equity',
    'Current account equity'
)

account_balance = Gauge(
    'v1bot_execution_account_balance',
    'Current account balance'
)

account_margin_level = Gauge(
    'v1bot_execution_account_margin_level_ratio',
    'Current margin level ratio'
)

account_free_margin = Gauge(
    'v1bot_execution_account_free_margin',
    'Current free margin available'
)
```

**Key Execution Alerts**

| Alert                        | Condition                                              | Severity | Response                                |
|------------------------------|--------------------------------------------------------|----------|-----------------------------------------|
| `MT5Disconnected`            | `mt5_terminal_connected == 0` for 15s                  | CRITICAL | Kill switch, auto-reconnect             |
| `HighSlippage`               | `p95 slippage > 3 pips` over 10 trades                 | WARNING  | Review execution timing, check spread   |
| `LowFillRate`                | `fill_rate_ratio < 0.9` over 20 trades                 | WARNING  | Check broker, review order types        |
| `OrderLatencyHigh`           | `p99 submission latency > 500ms`                       | CRITICAL | Network check, MT5 terminal check       |
| `HighMarginUsage`            | `margin_level_ratio < 2.0`                             | WARNING  | Reduce position sizes                   |
| `CriticalMarginLevel`       | `margin_level_ratio < 1.2`                             | CRITICAL | Close positions, kill switch            |

### 10.4.4 Risk Manager Service (Python)

The Risk Manager's monitoring focuses on the health of the safety systems themselves -- monitoring the monitors.

**Custom Metrics Exposed on `:8084/metrics`**

```python
# risk_manager/metrics.py
from prometheus_client import Counter, Gauge, Histogram, Enum

# Circuit breaker status
circuit_breaker_state = Enum(
    'v1bot_risk_circuit_breaker_state',
    'Current circuit breaker state',
    ['breaker_name'],
    states=['closed', 'open', 'half_open']
)

circuit_breaker_trips_total = Counter(
    'v1bot_risk_circuit_breaker_trips_total',
    'Total number of circuit breaker trips',
    ['breaker_name', 'reason']
)

# Drawdown monitoring
current_drawdown_ratio = Gauge(
    'v1bot_risk_current_drawdown_ratio',
    'Current drawdown from peak equity',
    ['period']  # 'daily', 'weekly', 'monthly', 'absolute'
)

max_drawdown_limit_ratio = Gauge(
    'v1bot_risk_max_drawdown_limit_ratio',
    'Configured maximum drawdown limit',
    ['period']
)

drawdown_headroom_ratio = Gauge(
    'v1bot_risk_drawdown_headroom_ratio',
    'Remaining drawdown capacity before limit (1.0 = full headroom)',
    ['period']
)

# Veto and approval tracking
trade_signals_evaluated_total = Counter(
    'v1bot_risk_signals_evaluated_total',
    'Total trade signals evaluated by risk manager',
    ['symbol']
)

trade_signals_approved_total = Counter(
    'v1bot_risk_signals_approved_total',
    'Trade signals approved and forwarded to execution',
    ['symbol']
)

trade_signals_vetoed_total = Counter(
    'v1bot_risk_signals_vetoed_total',
    'Trade signals vetoed by risk manager',
    ['symbol', 'veto_reason']
)

# Kill switch
kill_switch_active = Gauge(
    'v1bot_risk_kill_switch_active',
    'Kill switch status (1=active/trading halted, 0=normal)'
)

kill_switch_activations_total = Counter(
    'v1bot_risk_kill_switch_activations_total',
    'Total number of kill switch activations',
    ['trigger_reason']
)

# Risk check latency
risk_check_latency_seconds = Histogram(
    'v1bot_risk_check_latency_seconds',
    'Time to perform full risk evaluation on a trade signal',
    ['check_type'],
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05]
)

# Position risk metrics
portfolio_var_ratio = Gauge(
    'v1bot_risk_portfolio_var_ratio',
    'Portfolio Value at Risk (VaR) as ratio of equity',
    ['confidence_level']  # '95', '99'
)

correlation_exposure = Gauge(
    'v1bot_risk_correlation_exposure',
    'Maximum correlation exposure across open positions'
)

max_single_position_risk_ratio = Gauge(
    'v1bot_risk_max_single_position_risk_ratio',
    'Largest single position risk as ratio of equity'
)
```

The Risk Manager itself must be monitored for liveness with special urgency. If the Risk Manager goes down, all trade signals should be halted until it recovers. The Risk Manager exposes a `/health` endpoint that the Execution Bridge checks before processing any trade signal; if the health check fails, the Execution Bridge automatically activates its local kill switch.

### 10.4.5 Database Monitoring

The database layer comprises PostgreSQL with TimescaleDB and Redis, each with its own exporter.

**PostgreSQL / TimescaleDB (via `postgres_exporter` on `:9187`)**

Key metrics monitored:

| Metric                                    | Warning      | Critical     | Notes                                  |
|-------------------------------------------|--------------|--------------|----------------------------------------|
| Active connections / max_connections       | > 70%        | > 90%        | Connection pool saturation             |
| Transaction rate (TPS)                     | Context-dep  | Context-dep  | Baseline comparison                    |
| Query latency (p99)                       | > 100ms      | > 500ms      | Excludes long-running analytics        |
| Replication lag (if replica exists)        | > 1s         | > 10s        | Only in HA deployments                 |
| Dead tuples ratio                         | > 10%        | > 25%        | Autovacuum may be failing              |
| Table bloat                               | > 30%        | > 50%        | Needs VACUUM FULL                      |
| WAL generation rate                       | Context-dep  | > 1GB/min    | Disk space concern                     |
| TimescaleDB chunk count                   | > 1000       | > 5000       | Retention policy review                |
| TimescaleDB compression ratio             | < 5:1        | < 2:1        | Data pattern change                    |
| TimescaleDB continuous aggregate lag      | > 5min       | > 30min      | Aggregate refresh failing              |

```yaml
# Custom recording rules for database monitoring
groups:
  - name: v1bot_database
    interval: 10s
    rules:
      - record: v1bot:db:connection_usage:ratio
        expr: |
          pg_stat_activity_count{datname="v1bot_trading"}
          /
          pg_settings_max_connections

      - record: v1bot:db:transaction_rate:rate5m
        expr: |
          rate(pg_stat_database_xact_commit{datname="v1bot_trading"}[5m])
          +
          rate(pg_stat_database_xact_rollback{datname="v1bot_trading"}[5m])

      - record: v1bot:db:cache_hit:ratio
        expr: |
          pg_stat_database_blks_hit{datname="v1bot_trading"}
          /
          (pg_stat_database_blks_hit{datname="v1bot_trading"} + pg_stat_database_blks_read{datname="v1bot_trading"})

      - record: v1bot:db:timescaledb_chunks:count
        expr: |
          pg_timescaledb_chunks_total{datname="v1bot_trading"}
```

**Redis (via `redis_exporter` on `:9121`)**

```yaml
      - record: v1bot:redis:memory_usage:ratio
        expr: |
          redis_memory_used_bytes / redis_memory_max_bytes

      - record: v1bot:redis:hit_rate:ratio
        expr: |
          rate(redis_keyspace_hits_total[5m])
          /
          (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))

      - record: v1bot:redis:connected_clients:count
        expr: redis_connected_clients

      - record: v1bot:redis:evicted_keys:rate5m
        expr: rate(redis_evicted_keys_total[5m])

      - record: v1bot:redis:pubsub_channels:count
        expr: redis_pubsub_channels
```

Redis cache hit ratio below 90% triggers investigation, as it may indicate that feature caching in the Algo Engine is not functioning correctly. Any key eviction events trigger a WARNING, as Redis should be sized to hold all active trading state without eviction.

---

## 10.5 Trading Performance Metrics

### 10.5.1 Real-Time P&L Tracking

The most critical business metric for a trading system is profit and loss. V1_Bot tracks P&L at multiple granularities with the following Prometheus metrics:

```python
# trading_metrics/pnl.py
from prometheus_client import Gauge, Counter, Histogram

# Real-time P&L
realized_pnl = Gauge(
    'v1bot_trading_realized_pnl',
    'Cumulative realized P&L',
    ['period']  # 'session', 'daily', 'weekly', 'monthly', 'all_time'
)

unrealized_pnl = Gauge(
    'v1bot_trading_unrealized_pnl',
    'Current unrealized P&L from open positions'
)

total_pnl = Gauge(
    'v1bot_trading_total_pnl',
    'Total P&L (realized + unrealized)',
    ['period']
)

# Per-trade P&L distribution
trade_pnl_distribution = Histogram(
    'v1bot_trading_trade_pnl',
    'P&L distribution of individual closed trades',
    ['symbol', 'direction', 'strategy'],
    buckets=[-500, -200, -100, -50, -20, -10, -5, 0, 5, 10, 20, 50, 100, 200, 500, 1000]
)

# Equity curve tracking (sampled every minute)
account_equity_snapshot = Gauge(
    'v1bot_trading_equity_snapshot',
    'Account equity sampled periodically for equity curve construction'
)

equity_high_water_mark = Gauge(
    'v1bot_trading_equity_high_water_mark',
    'Highest equity value achieved (for drawdown calculation)'
)
```

### 10.5.2 Equity Curve Construction

The equity curve is stored both in Prometheus (for Grafana visualization) and in PostgreSQL (for backtesting comparison). A background task samples equity every 60 seconds during trading hours:

```python
# trading_metrics/equity_curve.py
import time
import asyncio
from datetime import datetime, timezone
from prometheus_client import Gauge

equity_gauge = Gauge('v1bot_trading_equity_snapshot', 'Equity snapshot')
hwm_gauge = Gauge('v1bot_trading_equity_high_water_mark', 'High water mark')

class EquityCurveTracker:
    def __init__(self, execution_bridge, db_connection, redis_client):
        self.bridge = execution_bridge
        self.db = db_connection
        self.redis = redis_client
        self.high_water_mark = 0.0
        self._running = False

    async def start(self):
        """Start periodic equity sampling."""
        self._running = True
        # Initialize HWM from database
        self.high_water_mark = await self.db.fetchval(
            "SELECT COALESCE(MAX(equity), 0) FROM v1bot.equity_snapshots"
        )
        hwm_gauge.set(self.high_water_mark)

        while self._running:
            try:
                await self._sample_equity()
            except Exception as e:
                logger.error(f"Equity sampling failed: {e}", exc_info=True)
            await asyncio.sleep(60)

    async def _sample_equity(self):
        account_info = await self.bridge.get_account_info()
        equity = account_info['equity']
        balance = account_info['balance']
        timestamp = datetime.now(timezone.utc)

        # Update Prometheus
        equity_gauge.set(equity)

        # Update high water mark
        if equity > self.high_water_mark:
            self.high_water_mark = equity
            hwm_gauge.set(self.high_water_mark)

        # Calculate current drawdown
        drawdown = 0.0
        if self.high_water_mark > 0:
            drawdown = (self.high_water_mark - equity) / self.high_water_mark

        # Persist to database
        await self.db.execute(
            """
            INSERT INTO v1bot.equity_snapshots
                (timestamp, equity, balance, high_water_mark, drawdown_ratio)
            VALUES ($1, $2, $3, $4, $5)
            """,
            timestamp, equity, balance, self.high_water_mark, drawdown
        )

        # Publish to Redis for Streamlit real-time display
        await self.redis.publish('v1bot:equity:update', json.dumps({
            'timestamp': timestamp.isoformat(),
            'equity': equity,
            'balance': balance,
            'hwm': self.high_water_mark,
            'drawdown': drawdown,
            'unrealized_pnl': equity - balance,
        }))
```

### 10.5.3 Win Rate and Trade Statistics

```python
# Prometheus metrics for trade statistics
trades_closed_total = Counter(
    'v1bot_trading_trades_closed_total',
    'Total number of closed trades',
    ['symbol', 'direction', 'strategy', 'outcome']  # outcome: 'win', 'loss', 'breakeven'
)

win_rate_rolling = Gauge(
    'v1bot_trading_win_rate_rolling',
    'Rolling win rate over last N trades',
    ['window_size']  # '20', '50', '100'
)

average_win_amount = Gauge(
    'v1bot_trading_average_win_amount',
    'Average profit on winning trades (rolling)',
    ['window_size']
)

average_loss_amount = Gauge(
    'v1bot_trading_average_loss_amount',
    'Average loss on losing trades (rolling)',
    ['window_size']
)

profit_factor = Gauge(
    'v1bot_trading_profit_factor',
    'Ratio of gross profits to gross losses (rolling)',
    ['window_size']
)

expectancy_per_trade = Gauge(
    'v1bot_trading_expectancy_per_trade',
    'Expected value per trade in account currency (rolling)',
    ['window_size']
)
```

### 10.5.4 Risk-Adjusted Performance Metrics

These metrics are computed by a periodic background task (every 5 minutes during trading, every hour outside trading) and exposed as Prometheus gauges:

```python
# trading_metrics/risk_adjusted.py
import numpy as np
from prometheus_client import Gauge

sharpe_ratio = Gauge(
    'v1bot_trading_sharpe_ratio',
    'Annualized Sharpe ratio',
    ['period']  # 'daily', 'weekly', 'monthly'
)

sortino_ratio = Gauge(
    'v1bot_trading_sortino_ratio',
    'Annualized Sortino ratio (downside deviation only)',
    ['period']
)

calmar_ratio = Gauge(
    'v1bot_trading_calmar_ratio',
    'Calmar ratio (annualized return / max drawdown)',
    ['period']
)

max_drawdown_ratio = Gauge(
    'v1bot_trading_max_drawdown_ratio',
    'Maximum drawdown experienced',
    ['period']  # 'daily', 'weekly', 'monthly', 'all_time'
)

max_drawdown_duration_seconds = Gauge(
    'v1bot_trading_max_drawdown_duration_seconds',
    'Duration of the longest drawdown period',
    ['period']
)


def compute_risk_metrics(equity_series: np.ndarray, risk_free_rate: float = 0.05):
    """Compute risk-adjusted performance metrics from equity time series."""
    if len(equity_series) < 2:
        return {}

    returns = np.diff(equity_series) / equity_series[:-1]
    daily_returns = returns  # Assuming daily sampling

    # Sharpe Ratio (annualized)
    excess_returns = daily_returns - (risk_free_rate / 252)
    sharpe = np.sqrt(252) * np.mean(excess_returns) / (np.std(excess_returns) + 1e-10)

    # Sortino Ratio (annualized)
    downside_returns = daily_returns[daily_returns < 0]
    downside_deviation = np.sqrt(np.mean(downside_returns**2)) if len(downside_returns) > 0 else 1e-10
    sortino = np.sqrt(252) * np.mean(excess_returns) / downside_deviation

    # Maximum Drawdown
    cumulative = np.cumprod(1 + daily_returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (running_max - cumulative) / running_max
    max_dd = np.max(drawdowns)

    # Calmar Ratio
    annualized_return = (equity_series[-1] / equity_series[0]) ** (252 / len(returns)) - 1
    calmar = annualized_return / (max_dd + 1e-10)

    return {
        'sharpe': sharpe,
        'sortino': sortino,
        'max_drawdown': max_dd,
        'calmar': calmar,
        'annualized_return': annualized_return,
    }
```

### 10.5.5 Trade Duration and R-Multiple Analysis

```python
# Trade duration tracking
trade_duration_seconds = Histogram(
    'v1bot_trading_trade_duration_seconds',
    'Duration of closed trades in seconds',
    ['symbol', 'direction', 'outcome'],
    buckets=[60, 300, 900, 1800, 3600, 7200, 14400, 28800, 86400, 172800, 604800]
)

# R-Multiple tracking (profit/loss expressed as multiples of initial risk)
trade_r_multiple = Histogram(
    'v1bot_trading_r_multiple',
    'R-multiple of closed trades (profit / initial risk amount)',
    ['symbol', 'strategy'],
    buckets=[-5, -3, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 3, 5, 10, 20]
)

average_r_multiple = Gauge(
    'v1bot_trading_average_r_multiple',
    'Average R-multiple (expectancy in R)',
    ['window_size']
)
```

R-multiple analysis normalizes trade outcomes by initial risk, providing a risk-adjusted view of trading performance. A system with an average R-multiple of 0.5 means that, on average, each trade returns half of the initial risk amount. This is more meaningful than absolute P&L because it accounts for varying position sizes.

### 10.5.6 Performance Breakdown Dimensions

Trading performance is broken down across multiple dimensions to identify strengths and weaknesses:

**By Symbol**

```promql
# Win rate by symbol (PromQL)
sum(v1bot_trading_trades_closed_total{outcome="win"}) by (symbol)
/
sum(v1bot_trading_trades_closed_total) by (symbol)
```

**By Trading Session**

```python
session_pnl = Gauge(
    'v1bot_trading_session_pnl',
    'P&L by trading session',
    ['session']  # 'asian', 'london', 'new_york', 'overlap_london_ny'
)

session_trade_count = Counter(
    'v1bot_trading_session_trades_total',
    'Number of trades per session',
    ['session', 'outcome']
)
```

**By Day of Week**

```python
day_of_week_pnl = Gauge(
    'v1bot_trading_day_of_week_pnl',
    'Cumulative P&L by day of week',
    ['day']  # 'monday', 'tuesday', ..., 'friday'
)
```

**By Strategy**

```python
strategy_pnl = Gauge(
    'v1bot_trading_strategy_pnl',
    'P&L by strategy identifier',
    ['strategy', 'period']
)

strategy_sharpe = Gauge(
    'v1bot_trading_strategy_sharpe',
    'Sharpe ratio by strategy',
    ['strategy']
)
```

These dimensional breakdowns are stored in PostgreSQL for historical analysis and exposed as Prometheus gauges for real-time Grafana dashboards. The dimensional analysis often reveals critical insights: a system might be profitable overall but consistently losing money during the Asian session, or profitable on EUR/USD but losing on GBP/USD. These insights feed back into the Algo Engine's training pipeline as feature engineering inputs.

### 10.5.7 Trading Performance Summary Table

The following table defines the complete set of trading performance metrics tracked by V1_Bot, their computation frequency, and their storage locations:

| Metric                    | Computation Frequency | Prometheus | PostgreSQL | Redis (Live) |
|---------------------------|-----------------------|------------|------------|--------------|
| Real-time P&L             | Every tick            | Yes        | No         | Yes          |
| Equity curve              | Every 60s             | Yes        | Yes        | Yes          |
| Win rate (rolling)        | On trade close        | Yes        | Yes        | Yes          |
| Sharpe ratio              | Every 5min            | Yes        | Yes        | No           |
| Sortino ratio             | Every 5min            | Yes        | Yes        | No           |
| Maximum drawdown          | Continuous            | Yes        | Yes        | Yes          |
| Profit factor             | On trade close        | Yes        | Yes        | Yes          |
| R-multiple distribution   | On trade close        | Yes        | Yes        | No           |
| Trade duration stats      | On trade close        | Yes        | Yes        | No           |
| Session performance       | End of session        | Yes        | Yes        | No           |
| Symbol performance        | On trade close        | Yes        | Yes        | Yes          |
| Strategy performance      | On trade close        | Yes        | Yes        | Yes          |
| Calmar ratio              | Every hour            | Yes        | Yes        | No           |
| Daily/weekly/monthly P&L  | End of period         | Yes        | Yes        | No           |

---

## 10.6 Prometheus Configuration

### 10.6.1 Main Configuration File

The Prometheus server configuration defines all scrape targets, global settings, and external label metadata for the V1_Bot ecosystem. This configuration is the single source of truth for all metric collection.

```yaml
# /opt/monitoring/prometheus/prometheus.yml

global:
  scrape_interval: 15s          # Default scrape interval (overridden per-job)
  scrape_timeout: 10s           # Default scrape timeout
  evaluation_interval: 10s      # How often to evaluate recording/alerting rules
  external_labels:
    environment: "production"
    cluster: "v1bot"
    datacenter: "proxmox-01"

# Rule files for recording rules and alerting rules
rule_files:
  - "/opt/monitoring/prometheus/rules/recording_rules.yml"
  - "/opt/monitoring/prometheus/rules/alert_rules_infrastructure.yml"
  - "/opt/monitoring/prometheus/rules/alert_rules_trading.yml"
  - "/opt/monitoring/prometheus/rules/alert_rules_ai.yml"
  - "/opt/monitoring/prometheus/rules/alert_rules_risk.yml"
  - "/opt/monitoring/prometheus/rules/alert_rules_database.yml"

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - "localhost:9093"
      timeout: 10s
      api_version: v2

# Scrape configurations for each service
scrape_configs:

  # -------------------------------------------------------------------
  # Prometheus self-monitoring
  # -------------------------------------------------------------------
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
        labels:
          service: "prometheus"
          vm: "vm-monitor"

  # -------------------------------------------------------------------
  # Node Exporters (infrastructure metrics for each VM)
  # -------------------------------------------------------------------
  - job_name: "node_exporters"
    scrape_interval: 15s
    scrape_timeout: 10s
    static_configs:
      - targets: ["10.10.50.10:9100"]
        labels:
          vm: "pve-trade-01"
          role: "proxmox_host"

      - targets: ["10.10.10.10:9100"]
        labels:
          vm: "vm-data-ingest"
          role: "data_ingestion"
          vlan: "10"

      - targets: ["10.10.20.10:9100"]
        labels:
          vm: "vm-algo-engine"
          role: "algo_engine"
          vlan: "20"

      - targets: ["10.10.30.10:9100"]
        labels:
          vm: "vm-exec-bridge"
          role: "execution_bridge"
          vlan: "30"

      - targets: ["10.10.30.20:9100"]
        labels:
          vm: "vm-risk-mgr"
          role: "risk_manager"
          vlan: "30"

      - targets: ["10.10.40.10:9100"]
        labels:
          vm: "vm-database"
          role: "database"
          vlan: "40"

      - targets: ["10.10.50.20:9100"]
        labels:
          vm: "vm-monitor"
          role: "monitoring"
          vlan: "50"

    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        regex: "(.+):.*"
        replacement: "${1}"

  # -------------------------------------------------------------------
  # Data Ingestion Service (Go) -- high-frequency scrape
  # -------------------------------------------------------------------
  - job_name: "v1bot_data_ingestion"
    scrape_interval: 5s
    scrape_timeout: 3s
    metrics_path: "/metrics"
    static_configs:
      - targets: ["10.10.10.10:8081"]
        labels:
          service: "data_ingestion"
          language: "go"

  # -------------------------------------------------------------------
  # Algo Engine Service (Python) -- high-frequency scrape
  # -------------------------------------------------------------------
  - job_name: "v1bot_algo_engine"
    scrape_interval: 5s
    scrape_timeout: 3s
    metrics_path: "/metrics"
    static_configs:
      - targets: ["10.10.20.10:8082"]
        labels:
          service: "algo_engine"
          language: "python"

  # -------------------------------------------------------------------
  # Execution Bridge Service (Python) -- highest priority scrape
  # -------------------------------------------------------------------
  - job_name: "v1bot_execution_bridge"
    scrape_interval: 5s
    scrape_timeout: 3s
    metrics_path: "/metrics"
    static_configs:
      - targets: ["10.10.30.10:8083"]
        labels:
          service: "execution_bridge"
          language: "python"

  # -------------------------------------------------------------------
  # Risk Manager Service (Python)
  # -------------------------------------------------------------------
  - job_name: "v1bot_risk_manager"
    scrape_interval: 5s
    scrape_timeout: 3s
    metrics_path: "/metrics"
    static_configs:
      - targets: ["10.10.30.20:8084"]
        labels:
          service: "risk_manager"
          language: "python"

  # -------------------------------------------------------------------
  # PostgreSQL Exporter
  # -------------------------------------------------------------------
  - job_name: "v1bot_postgresql"
    scrape_interval: 10s
    scrape_timeout: 8s
    static_configs:
      - targets: ["10.10.40.10:9187"]
        labels:
          service: "postgresql"
          database: "v1bot_trading"

  # -------------------------------------------------------------------
  # Redis Exporter
  # -------------------------------------------------------------------
  - job_name: "v1bot_redis"
    scrape_interval: 10s
    scrape_timeout: 8s
    static_configs:
      - targets: ["10.10.40.10:9121"]
        labels:
          service: "redis"

  # -------------------------------------------------------------------
  # NVIDIA GPU Exporter (on Algo Engine VM)
  # -------------------------------------------------------------------
  - job_name: "v1bot_gpu"
    scrape_interval: 5s
    scrape_timeout: 3s
    static_configs:
      - targets: ["10.10.20.10:9835"]
        labels:
          service: "gpu"
          gpu_model: "nvidia"

  # -------------------------------------------------------------------
  # Alertmanager self-monitoring
  # -------------------------------------------------------------------
  - job_name: "alertmanager"
    static_configs:
      - targets: ["localhost:9093"]
        labels:
          service: "alertmanager"

  # -------------------------------------------------------------------
  # Grafana self-monitoring
  # -------------------------------------------------------------------
  - job_name: "grafana"
    scrape_interval: 30s
    static_configs:
      - targets: ["localhost:3000"]
        labels:
          service: "grafana"

  # -------------------------------------------------------------------
  # Loki self-monitoring
  # -------------------------------------------------------------------
  - job_name: "loki"
    scrape_interval: 30s
    static_configs:
      - targets: ["localhost:3100"]
        labels:
          service: "loki"
```

### 10.6.2 Prometheus Storage and Retention Configuration

Prometheus is started with the following flags to control storage behavior:

```bash
# /opt/monitoring/prometheus/start.sh
#!/bin/bash

exec /usr/local/bin/prometheus \
  --config.file="/opt/monitoring/prometheus/prometheus.yml" \
  --storage.tsdb.path="/data/prometheus/data" \
  --storage.tsdb.retention.time=15d \
  --storage.tsdb.retention.size=200GB \
  --storage.tsdb.min-block-duration=2h \
  --storage.tsdb.max-block-duration=36h \
  --storage.tsdb.wal-compression \
  --web.listen-address=":9090" \
  --web.enable-lifecycle \
  --web.enable-admin-api \
  --web.external-url="http://10.10.50.20:9090" \
  --query.max-concurrency=20 \
  --query.timeout=2m \
  --query.max-samples=50000000 \
  --log.level=info \
  --log.format=json
```

Key storage decisions:

- **`retention.time=15d`**: Raw metrics are retained for 15 days at full resolution. This covers two full trading weeks plus buffer for weekend analysis.
- **`retention.size=200GB`**: A hard cap ensures Prometheus never fills the disk. At an estimated 3-4 GB/day with current cardinality, this provides approximately 50-60 days of headroom beyond the time-based retention.
- **WAL compression**: Enabled to reduce write-ahead log size by approximately 50%, reducing disk I/O.
- **Block duration**: Min 2h / Max 36h controls TSDB compaction behavior. The 36-hour max block prevents excessive compaction CPU usage.

### 10.6.3 Recording Rules

Recording rules pre-compute frequently used expressions, reducing dashboard query latency and Prometheus load. These are evaluated every 10 seconds (matching `evaluation_interval`).

```yaml
# /opt/monitoring/prometheus/rules/recording_rules.yml
groups:
  # ===================================================================
  # Infrastructure Recording Rules
  # ===================================================================
  - name: v1bot_infra_recordings
    interval: 15s
    rules:
      # VM CPU usage (aggregated across all modes except idle)
      - record: v1bot:vm:cpu_usage:ratio
        expr: |
          1 - avg by (vm) (
            rate(node_cpu_seconds_total{mode="idle"}[5m])
          )

      # VM memory usage
      - record: v1bot:vm:memory_usage:ratio
        expr: |
          1 - (
            node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
          )

      # VM disk usage
      - record: v1bot:vm:disk_usage:ratio
        expr: |
          1 - (
            node_filesystem_avail_bytes{mountpoint="/"}
            /
            node_filesystem_size_bytes{mountpoint="/"}
          )

      # VM network throughput
      - record: v1bot:vm:network_rx:rate5m
        expr: rate(node_network_receive_bytes_total{device!~"lo|veth.*"}[5m])

      - record: v1bot:vm:network_tx:rate5m
        expr: rate(node_network_transmit_bytes_total{device!~"lo|veth.*"}[5m])

  # ===================================================================
  # Trading Service Recording Rules
  # ===================================================================
  - name: v1bot_trading_recordings
    interval: 5s
    rules:
      # Data ingestion throughput
      - record: v1bot:data:messages_per_second:rate1m
        expr: |
          sum(rate(v1bot_data_ingestion_messages_received_total[1m])) by (source)

      # AI prediction throughput
      - record: v1bot:ai:predictions_per_second:rate1m
        expr: |
          sum(rate(v1bot_algo_engine_prediction_requests_total[1m])) by (model_name)

      # AI prediction latency percentiles
      - record: v1bot:ai:prediction_latency_p50:seconds
        expr: |
          histogram_quantile(0.5,
            sum(rate(v1bot_algo_engine_prediction_latency_seconds_bucket[5m])) by (le, model_name)
          )

      - record: v1bot:ai:prediction_latency_p95:seconds
        expr: |
          histogram_quantile(0.95,
            sum(rate(v1bot_algo_engine_prediction_latency_seconds_bucket[5m])) by (le, model_name)
          )

      - record: v1bot:ai:prediction_latency_p99:seconds
        expr: |
          histogram_quantile(0.99,
            sum(rate(v1bot_algo_engine_prediction_latency_seconds_bucket[5m])) by (le, model_name)
          )

      # Order execution latency percentiles
      - record: v1bot:exec:order_latency_p50:seconds
        expr: |
          histogram_quantile(0.5,
            sum(rate(v1bot_execution_order_submission_latency_seconds_bucket[5m])) by (le)
          )

      - record: v1bot:exec:order_latency_p95:seconds
        expr: |
          histogram_quantile(0.95,
            sum(rate(v1bot_execution_order_submission_latency_seconds_bucket[5m])) by (le)
          )

      - record: v1bot:exec:order_latency_p99:seconds
        expr: |
          histogram_quantile(0.99,
            sum(rate(v1bot_execution_order_submission_latency_seconds_bucket[5m])) by (le)
          )

      # Fill rate
      - record: v1bot:exec:fill_rate:ratio
        expr: |
          sum(rate(v1bot_execution_orders_filled_total[15m]))
          /
          sum(rate(v1bot_execution_orders_submitted_total[15m]))

      # Average slippage
      - record: v1bot:exec:avg_slippage:pips
        expr: |
          histogram_quantile(0.5,
            sum(rate(v1bot_execution_slippage_pips_bucket[1h])) by (le, symbol)
          )

      # Risk manager veto rate
      - record: v1bot:risk:veto_rate:ratio
        expr: |
          sum(rate(v1bot_risk_signals_vetoed_total[15m]))
          /
          sum(rate(v1bot_risk_signals_evaluated_total[15m]))

      # Overall system trade throughput
      - record: v1bot:system:trades_per_hour:rate
        expr: |
          sum(rate(v1bot_trading_trades_closed_total[1h])) * 3600
```

### 10.6.4 Alert Rules

Alert rules are organized into separate files by domain. Each alert includes annotations for the Alertmanager to use when routing and rendering notifications.

```yaml
# /opt/monitoring/prometheus/rules/alert_rules_infrastructure.yml
groups:
  - name: v1bot_infrastructure_alerts
    rules:
      # -----------------------------------------------------------
      # VM Health Alerts
      # -----------------------------------------------------------
      - alert: V1Bot_VM_HighCPU
        expr: v1bot:vm:cpu_usage:ratio > 0.9
        for: 2m
        labels:
          severity: critical
          category: infrastructure
          team: devops
        annotations:
          summary: "VM {{ $labels.vm }} CPU usage is critically high"
          description: "CPU usage on {{ $labels.vm }} has been above 90% for 2 minutes. Current: {{ $value | humanizePercentage }}"
          runbook_url: "https://wiki.v1bot.internal/runbooks/high-cpu"
          dashboard_url: "http://10.10.50.20:3000/d/infra/infrastructure?var-vm={{ $labels.vm }}"

      - alert: V1Bot_VM_HighCPU_Warning
        expr: v1bot:vm:cpu_usage:ratio > 0.7
        for: 5m
        labels:
          severity: warning
          category: infrastructure
          team: devops
        annotations:
          summary: "VM {{ $labels.vm }} CPU usage is elevated"
          description: "CPU usage on {{ $labels.vm }} has been above 70% for 5 minutes. Current: {{ $value | humanizePercentage }}"

      - alert: V1Bot_VM_HighMemory
        expr: v1bot:vm:memory_usage:ratio > 0.95
        for: 1m
        labels:
          severity: critical
          category: infrastructure
          team: devops
        annotations:
          summary: "VM {{ $labels.vm }} memory is critically low"
          description: "Memory usage on {{ $labels.vm }} is {{ $value | humanizePercentage }}. OOM kill imminent."
          runbook_url: "https://wiki.v1bot.internal/runbooks/high-memory"

      - alert: V1Bot_VM_DiskSpaceLow
        expr: v1bot:vm:disk_usage:ratio > 0.9
        for: 5m
        labels:
          severity: critical
          category: infrastructure
          team: devops
        annotations:
          summary: "VM {{ $labels.vm }} disk space critically low"
          description: "Disk usage on {{ $labels.vm }} is {{ $value | humanizePercentage }}."

      - alert: V1Bot_NTP_ClockDrift
        expr: abs(node_timex_offset_seconds) > 0.05
        for: 1m
        labels:
          severity: critical
          category: infrastructure
          team: devops
        annotations:
          summary: "Clock drift detected on {{ $labels.vm }}"
          description: "NTP offset is {{ $value }}s. Trading timestamp accuracy compromised."

      - alert: V1Bot_ServiceDown
        expr: up == 0
        for: 30s
        labels:
          severity: critical
          category: infrastructure
          team: devops
        annotations:
          summary: "Scrape target {{ $labels.job }} is down"
          description: "Prometheus cannot reach {{ $labels.instance }} for job {{ $labels.job }}."

      # -----------------------------------------------------------
      # GPU Alerts
      # -----------------------------------------------------------
      - alert: V1Bot_GPU_HighTemperature
        expr: v1bot:gpu:temperature:celsius > 85
        for: 1m
        labels:
          severity: warning
          category: infrastructure
          team: devops
        annotations:
          summary: "GPU temperature is high: {{ $value }}C"
          description: "GPU on vm-algo-engine is running hot. Thermal throttling may begin at 90C."

      - alert: V1Bot_GPU_ThermalThrottle
        expr: v1bot:gpu:clock_throttle:bool == 1
        for: 30s
        labels:
          severity: critical
          category: infrastructure
          team: devops
        annotations:
          summary: "GPU is thermal throttling"
          description: "GPU clock speed has dropped below 90% of maximum. Processing latency is degraded."
```

```yaml
# /opt/monitoring/prometheus/rules/alert_rules_trading.yml
groups:
  - name: v1bot_trading_alerts
    rules:
      # -----------------------------------------------------------
      # Execution Alerts
      # -----------------------------------------------------------
      - alert: V1Bot_MT5_Disconnected
        expr: v1bot_execution_mt5_terminal_connected == 0
        for: 15s
        labels:
          severity: critical
          category: trading
          team: trading
          escalation: immediate
        annotations:
          summary: "MT5 terminal disconnected"
          description: "The MetaTrader 5 terminal connection has been lost. All trading is halted."
          runbook_url: "https://wiki.v1bot.internal/runbooks/mt5-disconnect"

      - alert: V1Bot_HighSlippage
        expr: |
          histogram_quantile(0.95,
            sum(rate(v1bot_execution_slippage_pips_bucket[30m])) by (le, symbol)
          ) > 3
        for: 5m
        labels:
          severity: warning
          category: trading
          team: trading
        annotations:
          summary: "High slippage detected on {{ $labels.symbol }}"
          description: "95th percentile slippage on {{ $labels.symbol }} is {{ $value }} pips over the last 30 minutes."

      - alert: V1Bot_LowFillRate
        expr: v1bot:exec:fill_rate:ratio < 0.9
        for: 10m
        labels:
          severity: warning
          category: trading
          team: trading
        annotations:
          summary: "Order fill rate is below 90%"
          description: "Fill rate is {{ $value | humanizePercentage }} over the last 15 minutes."

      - alert: V1Bot_OrderLatencyHigh
        expr: v1bot:exec:order_latency_p99:seconds > 0.5
        for: 2m
        labels:
          severity: critical
          category: trading
          team: trading
        annotations:
          summary: "Order submission latency is critically high"
          description: "p99 order latency is {{ $value }}s. Check MT5 terminal and network."

      # -----------------------------------------------------------
      # P&L and Drawdown Alerts
      # -----------------------------------------------------------
      - alert: V1Bot_DailyDrawdownWarning
        expr: v1bot_risk_current_drawdown_ratio{period="daily"} > 0.02
        for: 0s
        labels:
          severity: warning
          category: trading
          team: trading
        annotations:
          summary: "Daily drawdown exceeds 2%"
          description: "Current daily drawdown is {{ $value | humanizePercentage }}. Limit is 3%."

      - alert: V1Bot_DailyDrawdownCritical
        expr: v1bot_risk_current_drawdown_ratio{period="daily"} > 0.025
        for: 0s
        labels:
          severity: critical
          category: trading
          team: trading
          escalation: immediate
        annotations:
          summary: "Daily drawdown approaching limit"
          description: "Current daily drawdown is {{ $value | humanizePercentage }}. Kill switch activates at 3%."

      - alert: V1Bot_KillSwitchActivated
        expr: v1bot_risk_kill_switch_active == 1
        for: 0s
        labels:
          severity: critical
          category: trading
          team: trading
          escalation: immediate
        annotations:
          summary: "KILL SWITCH ACTIVATED - ALL TRADING HALTED"
          description: "The kill switch has been activated. Manual intervention required to resume trading."
          runbook_url: "https://wiki.v1bot.internal/runbooks/kill-switch"

      - alert: V1Bot_CircuitBreakerOpen
        expr: v1bot_risk_circuit_breaker_state{state="open"} == 1
        for: 0s
        labels:
          severity: warning
          category: trading
          team: trading
        annotations:
          summary: "Circuit breaker {{ $labels.breaker_name }} is OPEN"
          description: "Trading for {{ $labels.breaker_name }} is temporarily halted."

      # -----------------------------------------------------------
      # Risk Manager Health
      # -----------------------------------------------------------
      - alert: V1Bot_RiskManagerDown
        expr: up{job="v1bot_risk_manager"} == 0
        for: 10s
        labels:
          severity: critical
          category: trading
          team: trading
          escalation: immediate
        annotations:
          summary: "Risk Manager is DOWN - trading must halt"
          description: "The risk manager service is unreachable. Execution bridge should auto-activate kill switch."
```

```yaml
# /opt/monitoring/prometheus/rules/alert_rules_algo.yml
groups:
  - name: v1bot_algo_alerts
    rules:
      - alert: V1Bot_Algo_HighPredictionLatency
        expr: v1bot:algo:prediction_latency_p95:seconds > 0.5
        for: 2m
        labels:
          severity: warning
          category: algo
          team: trading
        annotations:
          summary: "Prediction latency is high"
          description: "p95 prediction latency for {{ $labels.model_name }} is {{ $value }}s."

      - alert: V1Bot_Algo_ModelDrift
        expr: v1bot_algo_engine_prediction_drift_score > 0.5
        for: 10m
        labels:
          severity: warning
          category: ai
          team: ml
        annotations:
          summary: "Model prediction distribution drift detected"
          description: "KL divergence for {{ $labels.model_name }} is {{ $value }}. Model may need retraining."

      - alert: V1Bot_AI_FeatureDrift
        expr: v1bot_algo_engine_feature_drift_score > 0.25
        for: 15m
        labels:
          severity: warning
          category: ai
          team: ml
        annotations:
          summary: "Feature drift detected for {{ $labels.feature_name }}"
          description: "PSI for feature {{ $labels.feature_name }} in model {{ $labels.model_name }} is {{ $value }}."

      - alert: V1Bot_AI_LowConfidence
        expr: |
          histogram_quantile(0.5,
            sum(rate(v1bot_algo_engine_prediction_confidence_bucket[30m])) by (le)
          ) < 0.3
        for: 15m
        labels:
          severity: warning
          category: ai
          team: ml
        annotations:
          summary: "AI model producing consistently low confidence predictions"
          description: "Median prediction confidence is {{ $value }}. Model may be uncertain or degraded."

      - alert: V1Bot_AI_HighFallbackRate
        expr: |
          rate(v1bot_algo_engine_fallback_tier_usage_total{tier=~"cpu_fallback|rule_based"}[15m])
          /
          rate(v1bot_algo_engine_prediction_requests_total[15m]) > 0.05
        for: 5m
        labels:
          severity: warning
          category: ai
          team: ml
        annotations:
          summary: "AI fallback tier usage is elevated"
          description: "More than 5% of predictions are using fallback tiers. Check GPU health."

      - alert: V1Bot_AI_LowEnsembleAgreement
        expr: v1bot_algo_engine_ensemble_agreement_ratio < 0.5
        for: 10m
        labels:
          severity: warning
          category: ai
          team: ml
        annotations:
          summary: "Ensemble model agreement is low on {{ $labels.symbol }}"
          description: "Ensemble agreement is {{ $value | humanizePercentage }}. Models are disagreeing significantly."
```

### 10.6.5 Custom Metric Naming Conventions

All V1_Bot custom metrics follow a strict naming convention to ensure consistency and discoverability:

```
v1bot_<subsystem>_<metric_name>_<unit_suffix>
```

| Prefix                       | Subsystem              | Examples                                           |
|------------------------------|------------------------|-----------------------------------------------------|
| `v1bot_data_ingestion_`      | Data Ingestion (Go)    | `v1bot_data_ingestion_messages_received_total`       |
| `v1bot_algo_engine_`            | Algo Engine (Python)      | `v1bot_algo_engine_prediction_latency_seconds`          |
| `v1bot_execution_`           | Execution Bridge       | `v1bot_execution_order_submission_latency_seconds`   |
| `v1bot_risk_`                | Risk Manager           | `v1bot_risk_circuit_breaker_state`                   |
| `v1bot_trading_`             | Cross-cutting trading  | `v1bot_trading_realized_pnl`                         |

Labels are constrained to prevent cardinality explosion. The following label guidelines apply:

- **symbol**: Limited to the configured trading symbols (typically 5-15). Acceptable.
- **direction**: Only `buy` or `sell`. Acceptable.
- **strategy**: Limited to configured strategy names (typically 3-5). Acceptable.
- **model_name**: Limited to deployed model identifiers (typically 2-4). Acceptable.
- **reason**: Enumerated error/veto reasons. Must be kept under 20 distinct values.
- **NEVER use as labels**: Trade IDs, order IDs, ticket numbers, timestamps, user-provided strings. These cause unbounded cardinality.

---

## 10.7 Grafana Dashboards

### 10.7.1 Dashboard Architecture

Grafana serves as the primary visualization layer for all Prometheus metrics, Loki logs, and Jaeger traces. The V1_Bot Grafana instance is configured with the following data sources:

| Data Source     | Type        | URL                       | Purpose                    |
|-----------------|-------------|---------------------------|----------------------------|
| Prometheus      | prometheus  | <http://localhost:9090>      | Metrics                    |
| Loki            | loki        | <http://localhost:3100>      | Logs                       |
| Jaeger          | jaeger      | <http://localhost:16686>     | Traces                     |
| PostgreSQL      | postgres    | 10.10.40.10:5432           | Trading data (direct)      |

Seven purpose-built dashboards provide comprehensive observability across all system dimensions.

### 10.7.2 Dashboard 1: System Overview

The System Overview dashboard is the landing page -- the first dashboard an operator sees when opening Grafana. It provides a single-pane-of-glass view of the entire V1_Bot ecosystem.

**Layout and Panels**

```
+-----------------------------------------------------------------------+
| ROW 1: Status Bar (stat panels)                                       |
| [System Status] [MT5 Status] [Kill Switch] [Daily P&L] [Equity]      |
| [Open Positions] [Win Rate] [Active Alerts] [Uptime]                  |
+-----------------------------------------------------------------------+
| ROW 2: Key Metrics (time series, 1h window)                           |
| [Equity Curve - 24h]                    | [P&L Today - bar chart]     |
| [Drawdown Gauge]                        | [Trade Count Today]         |
+-----------------------------------------------------------------------+
| ROW 3: Service Health (status map)                                    |
| [Data Ingestion] [Algo Engine] [Exec Bridge] [Risk Mgr] [PostgreSQL]    |
| [Redis] [Prometheus] [GPU]                                            |
+-----------------------------------------------------------------------+
| ROW 4: Latency Overview (time series)                                 |
| [Data Ingestion Latency]  [AI Prediction Latency]  [Order Latency]   |
+-----------------------------------------------------------------------+
| ROW 5: Recent Alerts (alert list panel)                               |
| [Active and recent alerts with severity colors]                       |
+-----------------------------------------------------------------------+
```

**Key Panel Definitions (JSON Excerpt)**

```json
{
  "dashboard": {
    "id": null,
    "uid": "v1bot-overview",
    "title": "V1_Bot - System Overview",
    "tags": ["v1bot", "overview"],
    "timezone": "browser",
    "refresh": "5s",
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "templating": {
      "list": [
        {
          "name": "symbol",
          "type": "query",
          "datasource": "Prometheus",
          "query": "label_values(v1bot_execution_open_positions_count, symbol)",
          "multi": true,
          "includeAll": true,
          "current": { "text": "All", "value": "$__all" }
        }
      ]
    },
    "annotations": {
      "list": [
        {
          "name": "Trade Executions",
          "datasource": "Prometheus",
          "expr": "changes(v1bot_execution_orders_filled_total[1m]) > 0",
          "tagKeys": "symbol",
          "titleFormat": "Trade Executed",
          "iconColor": "green"
        },
        {
          "name": "Kill Switch Events",
          "datasource": "Prometheus",
          "expr": "changes(v1bot_risk_kill_switch_activations_total[1m]) > 0",
          "titleFormat": "KILL SWITCH",
          "iconColor": "red"
        },
        {
          "name": "Circuit Breaker Trips",
          "datasource": "Prometheus",
          "expr": "changes(v1bot_risk_circuit_breaker_trips_total[1m]) > 0",
          "tagKeys": "breaker_name",
          "titleFormat": "Circuit Breaker Trip",
          "iconColor": "orange"
        }
      ]
    },
    "panels": [
      {
        "title": "System Status",
        "type": "stat",
        "gridPos": { "h": 4, "w": 3, "x": 0, "y": 0 },
        "targets": [
          {
            "expr": "min(up{job=~\"v1bot_.*\"})",
            "legendFormat": ""
          }
        ],
        "fieldConfig": {
          "defaults": {
            "mappings": [
              { "type": "value", "options": { "1": { "text": "ALL SYSTEMS OK", "color": "green" } } },
              { "type": "value", "options": { "0": { "text": "SYSTEM DOWN", "color": "red" } } }
            ],
            "thresholds": {
              "steps": [
                { "value": null, "color": "red" },
                { "value": 1, "color": "green" }
              ]
            }
          }
        }
      },
      {
        "title": "Daily P&L",
        "type": "stat",
        "gridPos": { "h": 4, "w": 3, "x": 6, "y": 0 },
        "targets": [
          {
            "expr": "v1bot_trading_realized_pnl{period=\"daily\"}",
            "legendFormat": "Realized"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "currencyUSD",
            "thresholds": {
              "steps": [
                { "value": null, "color": "red" },
                { "value": 0, "color": "green" }
              ]
            }
          }
        }
      },
      {
        "title": "Equity Curve (24h)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 4 },
        "targets": [
          {
            "expr": "v1bot_trading_equity_snapshot",
            "legendFormat": "Equity"
          },
          {
            "expr": "v1bot_trading_equity_high_water_mark",
            "legendFormat": "High Water Mark"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "currencyUSD",
            "custom": {
              "lineWidth": 2,
              "fillOpacity": 10,
              "drawStyle": "line"
            }
          }
        }
      }
    ]
  }
}
```

### 10.7.3 Dashboard 2: Infrastructure

The Infrastructure dashboard provides detailed views of all Proxmox VMs and the host itself.

**Panels Include**:

- CPU usage per VM (stacked time series with per-core breakdown)
- Memory usage per VM (gauge + time series)
- Disk I/O rates per VM (read/write bytes/second)
- Network traffic per VLAN (in/out bytes/second)
- ZFS pool health and ARC hit ratio
- GPU temperature and utilization (for Algo Engine VM)
- NTP clock offset per VM
- System load heatmap (all VMs over 24h)

**Template Variables**:

- `$vm`: Multi-select for VM filtering (default: All)
- `$interval`: Override for rate calculation window (default: `$__rate_interval`)

### 10.7.4 Dashboard 3: Trading Performance

This dashboard is the operator's primary tool for understanding trading results.

**Panels Include**:

- Equity curve with annotations for trade entries/exits
- Daily P&L bar chart (green for positive, red for negative)
- Win rate gauge (20-trade, 50-trade, 100-trade rolling)
- Sharpe ratio and Sortino ratio time series
- Maximum drawdown gauge with daily/weekly/monthly breakdown
- Profit factor time series
- Trade R-multiple distribution histogram
- Performance heatmap by day-of-week and hour
- Performance breakdown by symbol (table)
- Performance breakdown by trading session (bar chart)
- Trade duration distribution histogram
- Cumulative P&L by strategy (stacked area chart)

### 10.7.5 Dashboard 4: AI Model Health

**Panels Include**:

- Prediction latency (p50, p95, p99) by model
- Prediction confidence distribution histogram
- Prediction distribution drift (KL divergence over time)
- Feature drift PSI scores (heatmap by feature)
- GPU utilization and temperature
- Prediction batch size distribution
- Fallback tier usage (pie chart: primary_gpu / secondary_gpu / cpu_fallback / rule_based)
- Ensemble agreement ratio by symbol
- Model version info panel
- Feature cache hit/miss ratio
- Time since last model retrain

### 10.7.6 Dashboard 5: Risk Status

**Panels Include**:

- Circuit breaker state map (all breakers: closed=green, half_open=yellow, open=red)
- Kill switch status (large status indicator)
- Current drawdown gauges (daily, weekly, monthly, absolute) with limit markers
- Drawdown headroom visualization
- Veto rate by reason (bar chart)
- Signal approval vs. veto ratio (time series)
- Portfolio VaR gauge (95% and 99% confidence)
- Correlation exposure matrix
- Maximum single position risk
- Risk check latency (p50, p99)
- Recent veto log (table panel from Loki)

### 10.7.7 Dashboard 6: Execution Quality

**Panels Include**:

- Order submission latency (p50, p95, p99) by symbol
- Order fill latency by symbol
- End-to-end trade latency breakdown (stacked bar: data -> prediction -> risk_check -> submission -> fill)
- Slippage distribution histogram by symbol
- Fill rate gauge per symbol
- MT5 connection status timeline
- MT5 heartbeat latency
- Orders submitted vs. filled vs. rejected (stacked time series)
- Rejection reason breakdown (pie chart)
- Account margin level over time
- Open positions count over time

### 10.7.8 Dashboard 7: Data Pipeline

**Panels Include**:

- Messages per second by source and symbol
- WebSocket connection status per source
- Data freshness (age of last message per symbol)
- End-to-end data latency (exchange to local)
- Dropped message rate and reasons
- Buffer utilization gauges
- WebSocket reconnection events (annotations)
- Data gap detection (periods without messages during expected trading hours)
- Processing latency distribution
- Go runtime metrics (goroutines, GC pause time, heap usage)

### 10.7.9 Dashboard Design Principles

All V1_Bot Grafana dashboards follow these design principles:

1. **Top-to-bottom severity**: The most critical information appears at the top of each dashboard. Status indicators and alerts are always in the first row.
2. **Left-to-right flow**: On each row, panels flow from overview (left) to detail (right).
3. **Consistent color coding**: Green = healthy/profit, Yellow = warning, Red = critical/loss. This color scheme is enforced across all dashboards.
4. **Time window consistency**: All dashboards default to 1-hour window with 5-second auto-refresh during trading hours. A "Session View" variable switches to the full trading session window.
5. **Template variables**: Every dashboard supports `$symbol`, `$interval`, and dashboard-specific variables to enable drill-down without creating separate dashboards.
6. **Annotations**: Trade executions, circuit breaker trips, kill switch events, and model retraining events are displayed as annotations on relevant time series panels, providing immediate visual correlation between events and metric changes.
7. **Alert integration**: Panels that correspond to alerting rules display the alert threshold as a dashed red line, so operators can visually gauge proximity to alert conditions.
8. **Link navigation**: Each dashboard contains links to related dashboards. From the Overview, clicking on any service panel navigates to the detailed dashboard for that service.

---

## 10.8 Streamlit Trading Operations Center

### 10.8.1 Purpose and Architecture

While Grafana excels at metric visualization, trading operations require a more interactive, application-like interface that goes beyond what Grafana can provide. The Streamlit Trading Operations Center (TOC) is a custom-built Python web application that provides:

- Sub-second live trading data updates (fed from Redis, not Prometheus)
- Interactive trade journal with filtering and annotation
- AI decision log with explainability details
- Configuration management interface
- Point-and-click kill switch and circuit breaker controls

The Streamlit app runs on the monitoring VM at port 8501 and connects directly to Redis (for live data) and PostgreSQL (for historical data).

### 10.8.2 Redis Data Contract

The Streamlit app consumes data from Redis using a well-defined key and channel contract. Every key is prefixed with `v1bot:` and follows a consistent structure:

```python
# redis_contract.py -- Shared data contract for Redis keys/channels

REDIS_KEYS = {
    # Live price data (Hash per symbol)
    'prices': 'v1bot:live:prices:{symbol}',      # Fields: bid, ask, spread, timestamp

    # Current positions (Hash)
    'positions': 'v1bot:live:positions',           # JSON array of position objects

    # Account state (Hash)
    'account': 'v1bot:live:account',               # Fields: equity, balance, margin, free_margin

    # Real-time P&L (Hash)
    'pnl': 'v1bot:live:pnl',                       # Fields: realized, unrealized, total, daily

    # Service health heartbeats (String per service, with TTL)
    'health': 'v1bot:health:{service}',             # JSON: {status, timestamp, details}

    # Risk state (Hash)
    'risk_state': 'v1bot:live:risk_state',          # Fields: kill_switch, drawdown, breakers (JSON)

    # AI last predictions (List, capped)
    'predictions': 'v1bot:live:predictions',        # JSON list of recent predictions (max 100)

    # Trade journal entries (Sorted Set by timestamp)
    'trade_journal': 'v1bot:live:trade_journal',    # Score: unix timestamp, Value: JSON trade

    # System configuration (Hash)
    'config': 'v1bot:config:active',                # Current active configuration
}

REDIS_CHANNELS = {
    'equity_updates': 'v1bot:equity:update',
    'trade_events': 'v1bot:trades:event',
    'prediction_events': 'v1bot:predictions:event',
    'risk_events': 'v1bot:risk:event',
    'alert_events': 'v1bot:alerts:event',
}

# TTL for health heartbeats (seconds)
HEALTH_HEARTBEAT_TTL = 30

# Maximum items in capped lists
MAX_PREDICTIONS_STORED = 100
MAX_TRADE_JOURNAL_ENTRIES = 10000
```

### 10.8.3 Main Application Structure

```python
# streamlit_app/app.py
import streamlit as st
import redis
import asyncpg
import json
import time
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="V1_Bot Trading Operations Center",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Authentication (simple password-based for single-user system)
def check_password():
    """Check if the user has entered the correct password."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        password = st.text_input("Enter Operations Center Password", type="password")
        if password:
            import hashlib
            hashed = hashlib.sha256(password.encode()).hexdigest()
            expected = st.secrets.get("ops_password_hash", "")
            if hashed == expected:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
        return False
    return True

if not check_password():
    st.stop()

# Redis connection (cached)
@st.cache_resource
def get_redis():
    return redis.Redis(
        host='10.10.40.10',
        port=6379,
        db=0,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )

# PostgreSQL connection (cached)
@st.cache_resource
def get_db_pool():
    import asyncio
    loop = asyncio.new_event_loop()
    pool = loop.run_until_complete(
        asyncpg.create_pool(
            host='10.10.40.10',
            port=5432,
            database='v1bot_trading',
            user='v1bot_readonly',
            password=st.secrets['db_password'],
            min_size=2,
            max_size=5,
        )
    )
    return pool, loop

# Sidebar navigation
st.sidebar.title("V1_Bot Operations")
page = st.sidebar.radio(
    "Navigate",
    [
        "Live Trading",
        "AI Decision Log",
        "Risk Dashboard",
        "Model Performance",
        "System Health",
        "Trade Journal",
        "Configuration",
    ]
)

# Auto-refresh control
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
refresh_interval = st.sidebar.selectbox(
    "Refresh interval",
    [1, 2, 5, 10, 30],
    index=1,
    format_func=lambda x: f"{x}s"
)

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
```

### 10.8.4 Page: Live Trading

```python
# streamlit_app/pages/live_trading.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import datetime

def render_live_trading(redis_client):
    st.title("Live Trading Dashboard")

    # Row 1: Key metrics
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    # Fetch account data from Redis
    account = redis_client.hgetall('v1bot:live:account')
    pnl = redis_client.hgetall('v1bot:live:pnl')
    risk_state = redis_client.hgetall('v1bot:live:risk_state')

    with col1:
        equity = float(account.get('equity', 0))
        st.metric("Equity", f"${equity:,.2f}")

    with col2:
        daily_pnl = float(pnl.get('daily', 0))
        st.metric("Daily P&L", f"${daily_pnl:,.2f}",
                  delta=f"${daily_pnl:,.2f}",
                  delta_color="normal")

    with col3:
        unrealized = float(pnl.get('unrealized', 0))
        st.metric("Unrealized P&L", f"${unrealized:,.2f}",
                  delta=f"${unrealized:,.2f}",
                  delta_color="normal")

    with col4:
        positions_json = redis_client.get('v1bot:live:positions')
        positions = json.loads(positions_json) if positions_json else []
        st.metric("Open Positions", len(positions))

    with col5:
        drawdown = float(risk_state.get('drawdown', 0))
        st.metric("Drawdown", f"{drawdown*100:.2f}%")

    with col6:
        kill_switch = risk_state.get('kill_switch', '0') == '1'
        if kill_switch:
            st.error("KILL SWITCH: ACTIVE")
        else:
            st.success("KILL SWITCH: OFF")

    st.divider()

    # Row 2: Live positions table
    st.subheader("Open Positions")
    if positions:
        df_positions = pd.DataFrame(positions)
        df_positions['unrealized_pnl'] = df_positions['unrealized_pnl'].astype(float)

        # Color formatting for P&L
        def color_pnl(val):
            color = 'green' if val >= 0 else 'red'
            return f'color: {color}'

        styled = df_positions.style.applymap(color_pnl, subset=['unrealized_pnl'])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.info("No open positions")

    # Row 3: Live prices
    st.subheader("Market Prices")
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'US30']
    price_cols = st.columns(len(symbols))

    for i, symbol in enumerate(symbols):
        price_data = redis_client.hgetall(f'v1bot:live:prices:{symbol}')
        with price_cols[i]:
            if price_data:
                bid = float(price_data.get('bid', 0))
                ask = float(price_data.get('ask', 0))
                spread = float(price_data.get('spread', 0))
                st.metric(
                    symbol,
                    f"{bid:.5f}" if 'JPY' not in symbol else f"{bid:.3f}",
                    delta=f"Spread: {spread:.1f}"
                )
            else:
                st.metric(symbol, "N/A")

    # Row 4: Equity curve (from Redis recent data or DB)
    st.subheader("Equity Curve (Today)")
    # This would fetch from PostgreSQL for the full day
    # Simplified: show last 100 equity snapshots from Redis
    equity_data_raw = redis_client.lrange('v1bot:live:equity_history', 0, -1)
    if equity_data_raw:
        equity_records = [json.loads(e) for e in equity_data_raw]
        df_equity = pd.DataFrame(equity_records)
        df_equity['timestamp'] = pd.to_datetime(df_equity['timestamp'])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_equity['timestamp'],
            y=df_equity['equity'],
            name='Equity',
            line=dict(color='#00CC96', width=2),
            fill='tozeroy',
            fillcolor='rgba(0,204,150,0.1)'
        ))
        fig.add_trace(go.Scatter(
            x=df_equity['timestamp'],
            y=df_equity['hwm'],
            name='High Water Mark',
            line=dict(color='#636EFA', width=1, dash='dash')
        ))
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_title='Time',
            yaxis_title='Equity ($)',
            template='plotly_dark'
        )
        st.plotly_chart(fig, use_container_width=True)
```

### 10.8.5 Page: AI Decision Log

```python
# streamlit_app/pages/ai_decision_log.py
def render_ai_decision_log(redis_client, db_pool, loop):
    st.title("AI Decision Log")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        symbol_filter = st.selectbox("Symbol", ["All", "EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US30"])
    with col2:
        signal_filter = st.selectbox("Signal Type", ["All", "BUY", "SELL", "HOLD"])
    with col3:
        min_confidence = st.slider("Min Confidence", 0.0, 1.0, 0.0, 0.05)

    # Fetch recent predictions from Redis
    predictions_raw = redis_client.lrange('v1bot:live:predictions', 0, 99)
    predictions = [json.loads(p) for p in predictions_raw]

    # Apply filters
    if symbol_filter != "All":
        predictions = [p for p in predictions if p.get('symbol') == symbol_filter]
    if signal_filter != "All":
        predictions = [p for p in predictions if p.get('signal') == signal_filter]
    predictions = [p for p in predictions if p.get('confidence', 0) >= min_confidence]

    # Display as expandable cards
    for pred in predictions:
        timestamp = pred.get('timestamp', 'N/A')
        symbol = pred.get('symbol', 'N/A')
        signal = pred.get('signal', 'N/A')
        confidence = pred.get('confidence', 0)
        model = pred.get('model_name', 'N/A')

        signal_color = {
            'BUY': ':green[BUY]',
            'SELL': ':red[SELL]',
            'HOLD': ':orange[HOLD]'
        }.get(signal, signal)

        with st.expander(
            f"{timestamp} | {symbol} | {signal_color} | Confidence: {confidence:.1%} | Model: {model}"
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Prediction Details**")
                st.json({
                    'signal': signal,
                    'confidence': confidence,
                    'model': model,
                    'ensemble_agreement': pred.get('ensemble_agreement', 'N/A'),
                    'predicted_direction': pred.get('predicted_direction', 'N/A'),
                    'predicted_magnitude': pred.get('predicted_magnitude', 'N/A'),
                    'suggested_sl_pips': pred.get('suggested_sl', 'N/A'),
                    'suggested_tp_pips': pred.get('suggested_tp', 'N/A'),
                })

            with col2:
                st.write("**Top Feature Contributions**")
                features = pred.get('top_features', [])
                if features:
                    df_features = pd.DataFrame(features)
                    st.bar_chart(df_features.set_index('feature')['importance'])

            # Risk manager decision (if available)
            risk_decision = pred.get('risk_decision', {})
            if risk_decision:
                st.write("**Risk Manager Decision**")
                approved = risk_decision.get('approved', False)
                if approved:
                    st.success(f"APPROVED - Position size: {risk_decision.get('position_size', 'N/A')} lots")
                else:
                    st.error(f"VETOED - Reason: {risk_decision.get('veto_reason', 'N/A')}")
```

### 10.8.6 Page: Risk Dashboard

```python
# streamlit_app/pages/risk_dashboard.py
def render_risk_dashboard(redis_client):
    st.title("Risk Dashboard")

    risk_state = redis_client.hgetall('v1bot:live:risk_state')

    # Kill switch control
    st.subheader("Kill Switch Control")
    kill_active = risk_state.get('kill_switch', '0') == '1'

    col1, col2 = st.columns([3, 1])
    with col1:
        if kill_active:
            st.error("KILL SWITCH IS ACTIVE - ALL TRADING HALTED")
        else:
            st.success("Kill switch is OFF - Trading is active")

    with col2:
        if kill_active:
            if st.button("Deactivate Kill Switch", type="primary"):
                redis_client.publish('v1bot:risk:command', json.dumps({
                    'action': 'deactivate_kill_switch',
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'streamlit_ops_center',
                }))
                st.success("Kill switch deactivation command sent")
        else:
            if st.button("ACTIVATE Kill Switch", type="secondary"):
                redis_client.publish('v1bot:risk:command', json.dumps({
                    'action': 'activate_kill_switch',
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'streamlit_ops_center',
                    'reason': 'manual_operator_action',
                }))
                st.warning("Kill switch activation command sent")

    st.divider()

    # Circuit breakers
    st.subheader("Circuit Breakers")
    breakers = json.loads(risk_state.get('breakers', '{}'))
    breaker_cols = st.columns(len(breakers) if breakers else 1)

    for i, (name, state) in enumerate(breakers.items()):
        with breaker_cols[i]:
            if state == 'closed':
                st.success(f"{name}\nCLOSED")
            elif state == 'half_open':
                st.warning(f"{name}\nHALF-OPEN")
            elif state == 'open':
                st.error(f"{name}\nOPEN")

    st.divider()

    # Drawdown gauges
    st.subheader("Drawdown Levels")
    dd_col1, dd_col2, dd_col3, dd_col4 = st.columns(4)

    drawdown_configs = {
        'daily': {'limit': 0.03, 'label': 'Daily'},
        'weekly': {'limit': 0.05, 'label': 'Weekly'},
        'monthly': {'limit': 0.08, 'label': 'Monthly'},
        'absolute': {'limit': 0.15, 'label': 'Absolute'},
    }

    for (period, config), col in zip(drawdown_configs.items(),
                                      [dd_col1, dd_col2, dd_col3, dd_col4]):
        current = float(risk_state.get(f'drawdown_{period}', 0))
        limit = config['limit']
        usage_pct = (current / limit) * 100

        with col:
            st.metric(
                f"{config['label']} Drawdown",
                f"{current*100:.2f}%",
                delta=f"Limit: {limit*100:.1f}%"
            )
            st.progress(min(usage_pct / 100, 1.0))
```

### 10.8.7 Additional Streamlit Pages

**Model Performance Page**: Displays rolling Sharpe ratio, Sortino ratio, win rate, and profit factor charts sourced from PostgreSQL. Allows comparison between different model versions and strategies. Includes a backtest comparison feature that overlays live performance against backtested expectations.

**System Health Page**: Shows a service status matrix with last heartbeat times, health check results, and resource utilization. Displays recent error logs fetched from Loki via its HTTP API. Provides service restart buttons (sends commands to a management queue in Redis).

**Trade Journal Page**: A full trade log with search, filtering, and annotation capabilities. Each trade entry shows entry/exit prices, P&L, R-multiple, duration, the AI signal that triggered it, and the risk checks applied. Operators can add notes and tags to trades for post-session review.

**Configuration Page**: Displays the current active trading configuration (symbols, position sizes, risk limits, model parameters). Allows read-only viewing of configuration with a link to the version-controlled configuration repository for changes. Displays configuration change history from PostgreSQL audit logs.

### 10.8.8 Auto-Refresh and Authentication

The Streamlit app implements auto-refresh using `st.rerun()` with a configurable sleep interval (default 2 seconds). This provides near-real-time updates without WebSocket complexity. The sleep/rerun pattern is chosen because:

- It is simple and reliable
- It works with Streamlit's execution model (full re-render on each interaction)
- The Redis lookups are sub-millisecond, so the full page render is fast
- For truly real-time data (sub-second), the app subscribes to Redis Pub/Sub channels using a background thread that updates `st.session_state`

Authentication is implemented via a simple password hash check stored in Streamlit secrets (`.streamlit/secrets.toml`). Since the Operations Center runs on an internal management VLAN and is not exposed to the internet, this lightweight authentication is appropriate. The password is rotated monthly and stored in the team's password manager.

---

## 10.9 Alerting System

### 10.9.1 Alertmanager Configuration

Alertmanager receives alerts from Prometheus and routes them to appropriate notification channels based on severity, category, and time of day.

```yaml
# /opt/monitoring/alertmanager/alertmanager.yml

global:
  resolve_timeout: 5m
  http_config:
    follow_redirects: true

# Notification templates
templates:
  - '/opt/monitoring/alertmanager/templates/*.tmpl'

# Inhibition rules -- suppress lower severity if higher severity is active
inhibit_rules:
  # If a CRITICAL alert is firing, suppress the WARNING version
  - source_matchers:
      - severity = critical
    target_matchers:
      - severity = warning
    equal: ['alertname', 'vm', 'symbol']

  # If kill switch is active, suppress individual trading alerts
  - source_matchers:
      - alertname = V1Bot_KillSwitchActivated
    target_matchers:
      - category = trading
      - severity =~ "warning|info"

# Route tree
route:
  receiver: 'default-telegram'
  group_by: ['alertname', 'category']
  group_wait: 10s       # Wait before sending first notification for a new group
  group_interval: 5m    # Wait before sending subsequent notifications for same group
  repeat_interval: 4h   # Repeat notification for unresolved alert

  routes:
    # -----------------------------------------------------------
    # CRITICAL trading alerts -- immediate notification
    # -----------------------------------------------------------
    - matchers:
        - severity = critical
        - category = trading
      receiver: 'critical-telegram'
      group_wait: 0s           # Immediate -- no grouping delay
      group_interval: 1m
      repeat_interval: 15m
      continue: false

    # -----------------------------------------------------------
    # CRITICAL infrastructure alerts
    # -----------------------------------------------------------
    - matchers:
        - severity = critical
        - category = infrastructure
      receiver: 'critical-telegram'
      group_wait: 5s
      group_interval: 2m
      repeat_interval: 30m
      continue: false

    # -----------------------------------------------------------
    # WARNING trading alerts
    # -----------------------------------------------------------
    - matchers:
        - severity = warning
        - category = trading
      receiver: 'warning-telegram'
      group_wait: 30s
      group_interval: 10m
      repeat_interval: 2h
      continue: false

    # -----------------------------------------------------------
    # WARNING AI/ML alerts
    # -----------------------------------------------------------
    - matchers:
        - severity = warning
        - category = ai
      receiver: 'warning-telegram'
      group_wait: 1m
      group_interval: 15m
      repeat_interval: 4h
      continue: false

    # -----------------------------------------------------------
    # WARNING infrastructure alerts
    # -----------------------------------------------------------
    - matchers:
        - severity = warning
        - category = infrastructure
      receiver: 'warning-telegram'
      group_wait: 1m
      group_interval: 15m
      repeat_interval: 4h
      continue: false

    # -----------------------------------------------------------
    # INFO alerts -- log only, no immediate notification
    # -----------------------------------------------------------
    - matchers:
        - severity = info
      receiver: 'info-telegram'
      group_wait: 5m
      group_interval: 30m
      repeat_interval: 12h

# Receiver definitions
receivers:
  - name: 'default-telegram'
    webhook_configs:
      - url: 'http://localhost:9087/alert'
        send_resolved: true

  - name: 'critical-telegram'
    webhook_configs:
      - url: 'http://localhost:9087/alert/critical'
        send_resolved: true
        http_config:
          bearer_token_file: '/opt/monitoring/alertmanager/telegram_token'

  - name: 'warning-telegram'
    webhook_configs:
      - url: 'http://localhost:9087/alert/warning'
        send_resolved: true

  - name: 'info-telegram'
    webhook_configs:
      - url: 'http://localhost:9087/alert/info'
        send_resolved: true
```

### 10.9.2 Telegram Bot Integration

Alerts are delivered via a Telegram bot to dedicated channels. The bot is implemented as a lightweight webhook receiver that translates Alertmanager webhooks into formatted Telegram messages.

```python
# /opt/monitoring/telegram_bot/alert_bot.py
"""
V1_Bot Alert Telegram Bot
Receives webhooks from Alertmanager and sends formatted messages to Telegram.
"""

import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
logger = logging.getLogger('v1bot_alert_bot')

# Configuration
TELEGRAM_BOT_TOKEN = open('/opt/monitoring/alertmanager/telegram_token').read().strip()
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Channel IDs for different severity levels
CHANNELS = {
    'critical': '-1001234567890',   # V1Bot Critical Alerts
    'warning': '-1001234567891',    # V1Bot Warnings
    'info': '-1001234567892',       # V1Bot Info
}

# Severity to emoji mapping
SEVERITY_ICONS = {
    'critical': '\u26a0\ufe0f CRITICAL',   # warning sign
    'warning': '\u26a1 WARNING',            # lightning
    'info': '\u2139\ufe0f INFO',            # info
}

STATUS_ICONS = {
    'firing': '\U0001f534',     # red circle
    'resolved': '\U0001f7e2',   # green circle
}


def format_alert_message(alert_data: dict, severity: str) -> str:
    """Format an Alertmanager webhook payload into a Telegram message."""
    messages = []

    for alert in alert_data.get('alerts', []):
        status = alert.get('status', 'unknown')
        labels = alert.get('labels', {})
        annotations = alert.get('annotations', {})

        status_icon = STATUS_ICONS.get(status, '')
        severity_text = SEVERITY_ICONS.get(severity, severity.upper())

        alert_name = labels.get('alertname', 'Unknown')
        summary = annotations.get('summary', 'No summary')
        description = annotations.get('description', 'No description')
        runbook = annotations.get('runbook_url', '')
        dashboard = annotations.get('dashboard_url', '')

        # Build message
        lines = [
            f"{status_icon} {severity_text} | {status.upper()}",
            f"",
            f"<b>{alert_name}</b>",
            f"",
            f"{summary}",
            f"",
            f"<i>{description}</i>",
        ]

        # Add relevant labels
        relevant_labels = {k: v for k, v in labels.items()
                          if k not in ('alertname', 'severity', 'category', 'team')}
        if relevant_labels:
            lines.append("")
            lines.append("<b>Labels:</b>")
            for k, v in relevant_labels.items():
                lines.append(f"  {k}: {v}")

        # Add links
        if runbook:
            lines.append(f"\n<a href='{runbook}'>Runbook</a>")
        if dashboard:
            lines.append(f"<a href='{dashboard}'>Dashboard</a>")

        # Add timestamp
        starts_at = alert.get('startsAt', '')
        if starts_at:
            try:
                dt = datetime.fromisoformat(starts_at.replace('Z', '+00:00'))
                lines.append(f"\nTime: {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            except (ValueError, TypeError):
                pass

        messages.append('\n'.join(lines))

    return '\n\n---\n\n'.join(messages)


def send_telegram_message(chat_id: str, message: str):
    """Send a message to a Telegram chat."""
    url = f"{TELEGRAM_API_BASE}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Telegram message sent to {chat_id}")
    except requests.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")


@app.route('/alert/<severity>', methods=['POST'])
def handle_alert(severity: str):
    """Handle incoming Alertmanager webhook."""
    try:
        alert_data = request.json
        message = format_alert_message(alert_data, severity)
        chat_id = CHANNELS.get(severity, CHANNELS['info'])
        send_telegram_message(chat_id, message)
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        logger.error(f"Error handling alert: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/alert', methods=['POST'])
def handle_default_alert():
    """Handle alerts with no specific severity route."""
    return handle_alert('info')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='127.0.0.1', port=9087)
```

### 10.9.3 Alert Categories and Severity Levels

| Category        | CRITICAL                                      | WARNING                                           | INFO                                         |
|-----------------|-----------------------------------------------|---------------------------------------------------|----------------------------------------------|
| **Trading**     | MT5 disconnect, kill switch, margin call       | High slippage, low fill rate, drawdown approach    | Trade executed, position opened/closed        |
| **Infrastructure** | VM down, disk full, clock drift > 50ms     | High CPU/memory, disk space low, network errors    | Service restart, config reload                |
| **Algo Engine** | Strategy failure, all fallback                 | Model drift, feature drift, low confidence         | Model recalibrated, version updated           |
| **Risk**        | Kill switch activated, risk manager down       | Circuit breaker open, high veto rate               | Circuit breaker closed, drawdown recovered    |
| **Database**    | Connection pool exhausted, replication failed  | High connection usage, slow queries, bloat         | Maintenance completed, backup finished        |

### 10.9.4 Escalation Policies

Escalation is governed by the `for` duration in alert rules and the repeat interval in Alertmanager routing:

1. **Immediate (0s)**: Kill switch activation, MT5 disconnection, risk manager down. These fire instantly with no waiting period.
2. **Fast (15-30s)**: Service down (`up == 0`), critical margin level. Short `for` duration to allow for transient scrape failures.
3. **Standard (2-5m)**: High CPU, high latency, high slippage. The `for` duration filters out brief spikes.
4. **Slow (10-15m)**: Model drift, feature drift, low confidence. These are gradual phenomena that need sustained observation before alerting.

If a CRITICAL alert remains unresolved for 15 minutes, the repeat notification includes escalation text indicating that manual intervention is overdue. The system does not have an automated phone/SMS escalation path in the current single-operator deployment, but the Telegram channels are configured with persistent notifications that bypass device-level do-not-disturb settings.

---

## 10.10 Log Aggregation

### 10.10.1 Architecture Overview

Log aggregation in V1_Bot uses the Grafana Loki stack, which provides a cost-effective, horizontally-scalable log aggregation system that integrates natively with Grafana. Unlike Elasticsearch-based solutions (ELK/EFK), Loki indexes only log metadata (labels), not the full log content, resulting in dramatically lower storage and memory requirements -- a critical advantage for a single-server Proxmox deployment where resources are shared across trading workloads.

The log aggregation pipeline consists of three components:

```
  +-------------------+        +-------------------+        +-------------------+
  | Service VMs       |        | Monitoring VM      |        | Grafana           |
  |                   |        |                   |        |                   |
  | Promtail agent    | -----> | Loki              | <----- | Explore / Panels  |
  | (reads log files, |  push  | (stores chunks,   |  query | (LogQL queries,   |
  |  adds labels,     |        |  builds index)    |        |  correlation)     |
  |  ships to Loki)   |        |                   |        |                   |
  +-------------------+        +-------------------+        +-------------------+
```

### 10.10.2 Loki Server Configuration

```yaml
# /opt/monitoring/loki/loki-config.yml

auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: info

common:
  path_prefix: /data/loki
  storage:
    filesystem:
      chunks_directory: /data/loki/chunks
      rules_directory: /data/loki/rules
  replication_factor: 1
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: "2024-01-01"
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

storage_config:
  tsdb_shipper:
    active_index_directory: /data/loki/index
    cache_location: /data/loki/index_cache

ingester:
  chunk_encoding: snappy
  chunk_idle_period: 1h
  chunk_target_size: 1536000
  max_chunk_age: 2h
  wal:
    dir: /data/loki/wal
    replay_memory_ceiling: 1GB

limits_config:
  retention_period: 720h        # 30 days
  max_query_length: 720h
  max_query_parallelism: 8
  max_entries_limit_per_query: 10000
  ingestion_rate_mb: 10
  ingestion_burst_size_mb: 20
  per_stream_rate_limit: 5MB
  per_stream_rate_limit_burst: 15MB

compactor:
  working_directory: /data/loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150

query_range:
  align_queries_with_step: true
  cache_results: true
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 256

ruler:
  storage:
    type: local
    local:
      directory: /data/loki/rules
  rule_path: /data/loki/rules_tmp
  alertmanager_url: http://localhost:9093
  ring:
    kvstore:
      store: inmemory
  enable_api: true
```

### 10.10.3 Promtail Agent Configuration

Each VM runs a Promtail agent that tails log files, parses them, attaches labels, and pushes to Loki. The Promtail configuration is templated per-VM with the appropriate service labels.

```yaml
# /opt/monitoring/promtail/promtail-config.yml (example for vm-exec-bridge)

server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yml

clients:
  - url: http://10.10.50.20:3100/loki/api/v1/push
    tenant_id: v1bot
    batchwait: 1s
    batchsize: 1048576    # 1MB
    timeout: 10s
    external_labels:
      environment: production
      vm: vm-exec-bridge
      vlan: "30"

scrape_configs:
  # -----------------------------------------------------------
  # V1_Bot service logs (structured JSON)
  # -----------------------------------------------------------
  - job_name: v1bot_service
    static_configs:
      - targets:
          - localhost
        labels:
          job: v1bot_execution_bridge
          service: execution_bridge
          __path__: /var/log/v1bot/execution_bridge/*.log

    pipeline_stages:
      # Parse JSON log entries
      - json:
          expressions:
            timestamp: timestamp
            level: level
            message: message
            service: service
            trace_id: trace_id
            span_id: span_id
            symbol: symbol
            order_id: order_id
            error: error

      # Set timestamp from the log entry
      - timestamp:
          source: timestamp
          format: "2006-01-02T15:04:05.000000Z07:00"
          fallback_formats:
            - "2006-01-02T15:04:05Z07:00"
            - "2006-01-02 15:04:05"

      # Promote fields to labels (only low-cardinality fields!)
      - labels:
          level:
          service:
          symbol:

      # Add trace_id as label for trace correlation
      - labels:
          trace_id:

      # Drop debug logs in production to save storage
      - match:
          selector: '{level="DEBUG"}'
          action: drop
          drop_counter_reason: debug_logs_dropped

      # Rate limit high-volume info logs
      - limit:
          rate: 100
          burst: 200
          by_label_name: service

  # -----------------------------------------------------------
  # System logs (syslog, journald)
  # -----------------------------------------------------------
  - job_name: system
    journal:
      max_age: 12h
      labels:
        job: systemd
        service: system
    relabel_configs:
      - source_labels: ['__journal__systemd_unit']
        target_label: 'unit'
      - source_labels: ['__journal_priority_keyword']
        target_label: 'priority'

  # -----------------------------------------------------------
  # Node Exporter textfile logs (if any)
  # -----------------------------------------------------------
  - job_name: node_exporter_logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: node_exporter
          __path__: /var/log/node_exporter/*.log
```

### 10.10.4 Structured JSON Logging Standard

All V1_Bot services emit structured JSON logs with mandatory and optional fields. This standard ensures consistent parsing and querying across all services.

**Mandatory Fields**

| Field       | Type     | Description                                     | Example                                |
|-------------|----------|-------------------------------------------------|----------------------------------------|
| `timestamp` | ISO 8601 | UTC timestamp with microsecond precision        | `2026-02-21T14:30:05.123456Z`          |
| `level`     | string   | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)| `INFO`                                |
| `service`   | string   | Service identifier                              | `execution_bridge`                     |
| `message`   | string   | Human-readable log message                      | `Order submitted successfully`         |
| `trace_id`  | string   | OpenTelemetry trace ID (or empty)               | `abc123def456`                         |
| `span_id`   | string   | OpenTelemetry span ID (or empty)                | `span789`                              |

**Service-Specific Optional Fields**

| Field           | Services            | Description                              |
|-----------------|----------------------|------------------------------------------|
| `symbol`        | All trading services | Trading symbol involved                  |
| `order_id`      | Execution Bridge     | Internal order identifier                |
| `ticket`        | Execution Bridge     | MT5 ticket number                        |
| `signal`        | Algo Engine             | Prediction signal (BUY/SELL/HOLD)        |
| `confidence`    | Algo Engine             | Prediction confidence score              |
| `model_name`    | Algo Engine             | Model that produced the prediction       |
| `breaker_name`  | Risk Manager         | Circuit breaker involved                 |
| `veto_reason`   | Risk Manager         | Why a signal was vetoed                  |
| `latency_ms`    | All services         | Operation latency in milliseconds        |
| `error`         | All services         | Error message (when level >= ERROR)      |
| `stack_trace`   | All services         | Stack trace (when level >= ERROR)        |

**Python Logging Configuration**

```python
# shared/logging_config.py
import logging
import json
import sys
from datetime import datetime, timezone
from opentelemetry import trace


class V1BotJsonFormatter(logging.Formatter):
    """Structured JSON log formatter for V1_Bot services."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        # Get current trace context
        span = trace.get_current_span()
        span_context = span.get_span_context()

        trace_id = ""
        span_id = ""
        if span_context.is_valid:
            trace_id = format(span_context.trace_id, '032x')
            span_id = format(span_context.span_id, '016x')

        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'service': self.service_name,
            'message': record.getMessage(),
            'trace_id': trace_id,
            'span_id': span_id,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add extra fields from the log record
        extra_fields = [
            'symbol', 'order_id', 'ticket', 'signal', 'confidence',
            'model_name', 'breaker_name', 'veto_reason', 'latency_ms',
        ]
        for field in extra_fields:
            value = getattr(record, field, None)
            if value is not None:
                log_entry[field] = value

        # Add exception info
        if record.exc_info and record.exc_info[0] is not None:
            log_entry['error'] = str(record.exc_info[1])
            log_entry['stack_trace'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def configure_logging(service_name: str, log_level: str = 'INFO'):
    """Configure structured JSON logging for a V1_Bot service."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (stdout) with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(V1BotJsonFormatter(service_name))
    root_logger.addHandler(console_handler)

    # File handler for persistent logging
    file_handler = logging.FileHandler(
        f'/var/log/v1bot/{service_name}/{service_name}.log',
        mode='a',
        encoding='utf-8',
    )
    file_handler.setFormatter(V1BotJsonFormatter(service_name))
    root_logger.addHandler(file_handler)

    return root_logger
```

### 10.10.5 Log Retention Policies

| Log Category         | Retention | Storage Location      | Compression |
|----------------------|-----------|-----------------------|-------------|
| Trading decisions    | 90 days   | Loki + PostgreSQL     | Snappy      |
| Order execution      | 90 days   | Loki + PostgreSQL     | Snappy      |
| Risk events          | 90 days   | Loki + PostgreSQL     | Snappy      |
| AI predictions       | 30 days   | Loki                  | Snappy      |
| Service debug        | Dropped   | Not stored in Loki    | N/A         |
| Infrastructure       | 30 days   | Loki                  | Snappy      |
| System (journald)    | 14 days   | Loki                  | Snappy      |
| Audit trail          | 365 days  | PostgreSQL            | PostgreSQL  |

Logs that constitute a financial audit trail (trade executions, risk decisions, kill switch activations) are stored both in Loki (for operational querying) and in PostgreSQL (for long-term regulatory retention). The PostgreSQL audit log table is append-only with row-level security preventing any deletion or modification.

### 10.10.6 LogQL Query Examples

LogQL is Loki's query language, combining label matchers (like PromQL) with pipeline stages for filtering and transforming log content.

```logql
# Find all ERROR logs from the execution bridge in the last hour
{service="execution_bridge", level="ERROR"}

# Find all order rejections with the rejection reason
{service="execution_bridge"} |= "rejected" | json | reason != ""

# Find all risk manager vetoes for a specific symbol
{service="risk_manager", symbol="EURUSD"} |= "vetoed" | json | veto_reason != ""

# Count errors per service in the last 5 minutes
sum by (service) (count_over_time({level="ERROR"}[5m]))

# Find all log entries for a specific trade (by trace ID)
{trace_id="abc123def456789012345678"}

# P99 latency of order submissions from logs
quantile_over_time(0.99,
  {service="execution_bridge"} | json | latency_ms != "" | unwrap latency_ms [5m]
) by (symbol)

# Find kill switch activation events
{service="risk_manager"} |= "kill_switch" |= "activated" | json

# Detect log volume anomalies (spike detection)
sum(rate({service=~".+"}[1m])) by (service, level) > 100

# Find sequences of warnings followed by errors (correlation)
{service="execution_bridge", level=~"WARNING|ERROR"} | json |
  line_format "{{.timestamp}} [{{.level}}] {{.message}}"

# Find all logs between two timestamps for post-incident analysis
{service=~".+"} |= "" | json
  [2026-02-21T14:00:00Z to 2026-02-21T14:15:00Z]

# Extract and aggregate slippage values from execution logs
{service="execution_bridge"} |= "slippage" | json |
  unwrap slippage_pips | avg_over_time([15m]) by (symbol)
```

### 10.10.7 Log-Based Alerting

Loki supports alerting rules that trigger based on log content, providing a complementary alerting mechanism to Prometheus metric-based alerts:

```yaml
# /opt/monitoring/loki/rules/v1bot_log_alerts.yml
groups:
  - name: v1bot_log_alerts
    rules:
      - alert: V1Bot_HighErrorRate
        expr: |
          sum(rate({service=~".*", level="ERROR"}[5m])) by (service) > 0.5
        for: 2m
        labels:
          severity: warning
          category: infrastructure
        annotations:
          summary: "High error rate in {{ $labels.service }}"
          description: "Service {{ $labels.service }} is producing more than 0.5 errors/second."

      - alert: V1Bot_PanicDetected
        expr: |
          count_over_time({level="CRITICAL"} |= "panic" [1m]) > 0
        for: 0s
        labels:
          severity: critical
          category: infrastructure
        annotations:
          summary: "PANIC detected in logs"
          description: "A CRITICAL/panic log entry was detected. Investigate immediately."

      - alert: V1Bot_AuthenticationFailure
        expr: |
          count_over_time({service=~".*"} |= "authentication" |= "failed" [5m]) > 3
        for: 0s
        labels:
          severity: critical
          category: security
        annotations:
          summary: "Multiple authentication failures detected"
          description: "More than 3 authentication failures in the last 5 minutes."
```

---

## 10.11 Distributed Tracing

### 10.11.1 Tracing Architecture

Distributed tracing in V1_Bot is implemented using OpenTelemetry (OTel) for instrumentation and Jaeger as the trace collection and visualization backend. Tracing provides visibility into the end-to-end flow of operations across service boundaries, answering the critical question: "When a trade signal takes 2 seconds from data receipt to order fill, where exactly did that time go?"

```
  +------------------+     +------------------+     +------------------+
  | Data Ingestion   |     | Algo Engine         |     | Risk Manager     |
  | (Go + OTel SDK)  |     | (Python + OTel)  |     | (Python + OTel)  |
  |                  |     |                  |     |                  |
  | Span: receive    |     | Span: predict    |     | Span: evaluate   |
  | Span: parse      |---->| Span: preprocess |---->| Span: check_dd   |
  | Span: forward    |     | Span: evaluate   |     | Span: check_pos  |
  +------------------+     | Span: ensemble   |     | Span: approve    |
                           +------------------+     +--------+---------+
                                                             |
                           +------------------+              |
                           | Execution Bridge |              |
                           | (Python + OTel)  |<-------------+
                           |                  |
                           | Span: submit     |
                           | Span: wait_fill  |
                           | Span: confirm    |
                           +------------------+
                                    |
                                    v
                           +------------------+
                           | Jaeger Collector |
                           | (gRPC :14250)    |
                           | (HTTP :14268)    |
                           |                  |
                           | Storage: local   |
                           | UI: :16686       |
                           +------------------+
```

### 10.11.2 OpenTelemetry Instrumentation

**Python Services (Algo Engine, Execution Bridge, Risk Manager)**

```python
# shared/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor


def init_tracing(service_name: str, service_version: str = "1.0.0"):
    """Initialize OpenTelemetry tracing for a V1_Bot service."""

    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": "production",
        "service.namespace": "v1bot",
    })

    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name="10.10.50.20",
        agent_port=6831,
    )

    # Create TracerProvider with batch processing
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(
        jaeger_exporter,
        max_queue_size=2048,
        max_export_batch_size=512,
        schedule_delay_millis=5000,
    )
    provider.add_span_processor(processor)

    # Set global TracerProvider
    trace.set_tracer_provider(provider)

    # Use B3 propagation format (compatible with Go services)
    set_global_textmap(B3MultiFormat())

    # Auto-instrument libraries
    RedisInstrumentor().instrument()
    AioHttpClientInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()

    return trace.get_tracer(service_name)


# Usage in Algo Engine service
tracer = init_tracing("v1bot-algo-engine")

async def handle_prediction_request(market_data: dict) -> dict:
    """Handle a prediction request with full tracing."""

    with tracer.start_as_current_span(
        "predict",
        attributes={
            "v1bot.symbol": market_data['symbol'],
            "v1bot.timeframe": market_data['timeframe'],
        }
    ) as span:
        # Preprocessing
        with tracer.start_as_current_span("preprocess_features") as prep_span:
            features = await preprocess(market_data)
            prep_span.set_attribute("v1bot.feature_count", len(features))
            prep_span.set_attribute("v1bot.cache_hit", features.from_cache)

        # Strategy evaluation
        with tracer.start_as_current_span("strategy_evaluation") as eval_span:
            prediction = await run_strategy(features)
            eval_span.set_attribute("v1bot.strategy_name", prediction.strategy_name)
            eval_span.set_attribute("v1bot.execution_device", prediction.device)
            inf_span.set_attribute("v1bot.confidence", prediction.confidence)

        # Ensemble aggregation
        with tracer.start_as_current_span("ensemble_aggregate") as ens_span:
            final = await aggregate_ensemble(prediction)
            ens_span.set_attribute("v1bot.ensemble_agreement", final.agreement)
            ens_span.set_attribute("v1bot.signal", final.signal)

        # Set final attributes on parent span
        span.set_attribute("v1bot.final_signal", final.signal)
        span.set_attribute("v1bot.final_confidence", final.confidence)

        return final.to_dict()
```

**Go Service (Data Ingestion)**

```go
// tracing/tracing.go
package tracing

import (
    "context"
    "log"

    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/exporters/jaeger"
    "go.opentelemetry.io/otel/propagation"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
    "go.opentelemetry.io/otel/trace"
)

var Tracer trace.Tracer

func InitTracing(serviceName string) func() {
    exporter, err := jaeger.New(
        jaeger.WithAgentEndpoint(
            jaeger.WithAgentHost("10.10.50.20"),
            jaeger.WithAgentPort("6831"),
        ),
    )
    if err != nil {
        log.Fatalf("Failed to create Jaeger exporter: %v", err)
    }

    res, _ := resource.Merge(
        resource.Default(),
        resource.NewWithAttributes(
            semconv.SchemaURL,
            semconv.ServiceNameKey.String(serviceName),
            semconv.ServiceVersionKey.String("1.0.0"),
            attribute.String("deployment.environment", "production"),
            attribute.String("service.namespace", "v1bot"),
        ),
    )

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(res),
        sdktrace.WithSampler(sdktrace.ParentBased(
            sdktrace.TraceIDRatioBased(0.1), // Sample 10% of traces
        )),
    )

    otel.SetTracerProvider(tp)
    otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
        propagation.TraceContext{},
        propagation.Baggage{},
    ))

    Tracer = tp.Tracer(serviceName)

    return func() {
        if err := tp.Shutdown(context.Background()); err != nil {
            log.Printf("Error shutting down tracer: %v", err)
        }
    }
}
```

### 10.11.3 Tracing a Trade Decision End-to-End

The most valuable trace in V1_Bot follows a single trade decision from market data arrival to order fill confirmation. This trace spans four services and typically includes 12-20 spans:

```
Trade Decision Trace (example: ~450ms total)
============================================

[Data Ingestion]  receive_message ............... 0ms   -> 2ms    (2ms)
[Data Ingestion]    parse_tick .................. 2ms   -> 3ms    (1ms)
[Data Ingestion]    validate_data ............... 3ms   -> 4ms    (1ms)
[Data Ingestion]    publish_to_redis ............ 4ms   -> 6ms    (2ms)
[Data Ingestion]    forward_to_algo ............. 6ms   -> 8ms    (2ms)
[Algo Engine]        predict ....................... 10ms  -> 180ms  (170ms)
[Algo Engine]          preprocess_features ......... 10ms  -> 35ms   (25ms)
[Algo Engine]            fetch_cached_features ..... 10ms  -> 12ms   (2ms)
[Algo Engine]            compute_new_features ...... 12ms  -> 35ms   (23ms)
[Algo Engine]          strategy_evaluation ......... 35ms  -> 155ms  (120ms)
[Algo Engine]            compute_signals ........... 36ms  -> 150ms  (114ms)
[Algo Engine]            postprocess_output ........ 150ms -> 155ms  (5ms)
[Algo Engine]          ensemble_aggregate .......... 155ms -> 175ms  (20ms)
[Algo Engine]          publish_prediction .......... 175ms -> 180ms  (5ms)
[Risk Manager]    evaluate_signal ............... 182ms -> 210ms  (28ms)
[Risk Manager]      check_drawdown_limits ....... 182ms -> 188ms  (6ms)
[Risk Manager]      check_position_limits ....... 188ms -> 192ms  (4ms)
[Risk Manager]      check_correlation ........... 192ms -> 198ms  (6ms)
[Risk Manager]      calculate_position_size ..... 198ms -> 205ms  (7ms)
[Risk Manager]      approve_signal .............. 205ms -> 210ms  (5ms)
[Execution Bridge]  submit_order ................ 212ms -> 250ms  (38ms)
[Execution Bridge]    prepare_mt5_request ....... 212ms -> 215ms  (3ms)
[Execution Bridge]    send_to_mt5 ............... 215ms -> 240ms  (25ms)
[Execution Bridge]    wait_for_confirmation ..... 240ms -> 248ms  (8ms)
[Execution Bridge]    record_execution .......... 248ms -> 250ms  (2ms)
                                                            TOTAL: ~250ms
```

This trace structure makes it immediately visible that the signal computation dominates the latency budget at 114ms. If a performance regression occurs and end-to-end latency jumps to 800ms, the trace will immediately pinpoint which span grew -- whether it is the strategy evaluation, the MT5 submission (network issue?), or the risk evaluation (added complexity?).

### 10.11.4 Sampling Strategy

Not every operation is traced. With 5-second prediction cycles and continuous market data processing, tracing every operation would produce approximately 20,000 spans per minute, overwhelming storage. The V1_Bot sampling strategy uses a tiered approach:

| Operation Type        | Sampling Rate | Rationale                                      |
|-----------------------|---------------|-------------------------------------------------|
| Trade executions      | 100%          | Every trade must have a full trace for audit    |
| Trade signal vetoes   | 100%          | Every veto must be traceable for review         |
| Normal predictions    | 10%           | Statistical sampling sufficient for optimization|
| Market data ingestion | 1%            | Very high volume; only needed for debugging     |
| Health checks         | 0%            | No value in tracing routine health checks       |
| Error/exception paths | 100%          | All errors are traced for diagnosis             |

The sampling decision is made at the trace root (usually Data Ingestion) and propagated to all downstream services via trace context headers. This ensures that a sampled trace is complete across all services, not fragmentary.

```python
# Custom sampler for V1_Bot
from opentelemetry.sdk.trace.sampling import (
    Sampler, SamplingResult, Decision, ParentBased
)

class V1BotSampler(Sampler):
    """Custom sampler that always traces trade executions and errors."""

    def should_sample(self, parent_context, trace_id, name, kind, attributes, links):
        # Always sample trade-related operations
        if attributes and attributes.get('v1bot.operation_type') in (
            'trade_execution', 'trade_veto', 'kill_switch', 'circuit_breaker'
        ):
            return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes)

        # Always sample errors
        if attributes and attributes.get('v1bot.is_error', False):
            return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes)

        # Sample market data at 1%
        if name.startswith('receive_market_data'):
            if (trace_id % 100) == 0:
                return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes)
            return SamplingResult(Decision.DROP)

        # Default 10% sampling for everything else
        if (trace_id % 10) == 0:
            return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes)

        return SamplingResult(Decision.DROP)

    def get_description(self):
        return "V1BotSampler"
```

### 10.11.5 Jaeger Configuration

```yaml
# /opt/monitoring/jaeger/jaeger-config.yml

# Jaeger all-in-one configuration for single-node deployment
collector:
  queue-size: 2000
  num-workers: 50

processor:
  jaeger-compact:
    server-host-port: ":6831"
    server-max-packet-size: 65000
  jaeger-binary:
    server-host-port: ":6832"

storage:
  type: badger
  badger:
    ephemeral: false
    directory-key: /data/jaeger/keys
    directory-value: /data/jaeger/values
    span-store-ttl: 168h     # 7 days retention

query:
  base-path: /jaeger
  static-files: /opt/jaeger/jaeger-ui

# Resource limits
max-traces: 100000
```

### 10.11.6 Trace Correlation with Logs and Metrics

The power of the three-pillar observability approach is realized through correlation. V1_Bot ensures that every log entry includes `trace_id` and `span_id` fields, enabling operators to:

1. **Metric to Trace**: When a Grafana metric panel shows a latency spike, the operator clicks the time range to open Jaeger with a filtered query for traces in that window. Traces with anomalous latency are immediately identifiable.

2. **Trace to Logs**: Within a Jaeger trace view, clicking on a span opens the associated Loki logs for that `trace_id`, showing all log entries produced during that span's execution.

3. **Log to Trace**: When reviewing a suspicious log entry in Grafana Explore (Loki), the `trace_id` field is a clickable link that opens the full trace in Jaeger.

This three-way correlation is configured in Grafana via data source correlation rules:

```json
{
  "correlations": [
    {
      "sourceUID": "prometheus-uid",
      "targetUID": "jaeger-uid",
      "label": "View Traces",
      "description": "View traces for this time range"
    },
    {
      "sourceUID": "loki-uid",
      "targetUID": "jaeger-uid",
      "label": "View Trace",
      "description": "View the full trace for this log entry",
      "config": {
        "field": "trace_id",
        "target": { "traceId": "${__value.raw}" }
      }
    },
    {
      "sourceUID": "jaeger-uid",
      "targetUID": "loki-uid",
      "label": "View Logs",
      "description": "View logs for this trace",
      "config": {
        "target": { "query": "{trace_id=\"${__data.fields.traceID}\"}" }
      }
    }
  ]
}
```

---

## 10.12 Health Checks and Self-Healing

### 10.12.1 Health Check Endpoints

Every V1_Bot service exposes three standardized health check endpoints that serve different purposes:

| Endpoint   | Purpose                                    | Checked By                  | Expected Response Time |
|------------|--------------------------------------------|-----------------------------|------------------------|
| `/health`  | Deep health check (all dependencies)       | Monitoring, operators       | < 5s                   |
| `/ready`   | Readiness to accept traffic                | Load balancer, orchestrator | < 500ms                |
| `/live`    | Basic liveness (process is running)        | Systemd watchdog, Prometheus | < 100ms               |

**Implementation (Python Services)**

```python
# shared/health.py
import time
import asyncio
from datetime import datetime, timezone
from aiohttp import web
import aioredis
import asyncpg

class HealthCheckHandler:
    """Standardized health check handler for V1_Bot Python services."""

    def __init__(self, service_name: str, version: str):
        self.service_name = service_name
        self.version = version
        self.start_time = time.time()
        self._dependencies = {}
        self._ready = False

    def register_dependency(self, name: str, check_func):
        """Register a dependency health check function.

        check_func should be an async function that returns
        (healthy: bool, details: dict).
        """
        self._dependencies[name] = check_func

    def set_ready(self, ready: bool):
        """Set the service readiness state."""
        self._ready = ready

    async def handle_live(self, request: web.Request) -> web.Response:
        """Liveness check -- is the process running and responsive?"""
        return web.json_response({
            'status': 'alive',
            'service': self.service_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })

    async def handle_ready(self, request: web.Request) -> web.Response:
        """Readiness check -- can the service accept and process requests?"""
        if not self._ready:
            return web.json_response(
                {
                    'status': 'not_ready',
                    'service': self.service_name,
                    'reason': 'Service is still initializing',
                },
                status=503
            )

        return web.json_response({
            'status': 'ready',
            'service': self.service_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })

    async def handle_health(self, request: web.Request) -> web.Response:
        """Deep health check -- verify all dependencies are healthy."""
        results = {}
        overall_healthy = True

        for dep_name, check_func in self._dependencies.items():
            try:
                healthy, details = await asyncio.wait_for(
                    check_func(), timeout=5.0
                )
                results[dep_name] = {
                    'healthy': healthy,
                    'details': details,
                }
                if not healthy:
                    overall_healthy = False
            except asyncio.TimeoutError:
                results[dep_name] = {
                    'healthy': False,
                    'details': {'error': 'Health check timed out after 5s'},
                }
                overall_healthy = False
            except Exception as e:
                results[dep_name] = {
                    'healthy': False,
                    'details': {'error': str(e)},
                }
                overall_healthy = False

        uptime = time.time() - self.start_time

        response = {
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'service': self.service_name,
            'version': self.version,
            'uptime_seconds': round(uptime, 1),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'dependencies': results,
        }

        status_code = 200 if overall_healthy else 503
        return web.json_response(response, status=status_code)

    def register_routes(self, app: web.Application):
        """Register health check routes on an aiohttp application."""
        app.router.add_get('/health', self.handle_health)
        app.router.add_get('/ready', self.handle_ready)
        app.router.add_get('/live', self.handle_live)


# Example: Registering dependency checks for the Execution Bridge
async def check_mt5_connection() -> tuple:
    """Check MetaTrader 5 terminal connectivity."""
    try:
        import MetaTrader5 as mt5
        if mt5.terminal_info() is not None:
            info = mt5.terminal_info()._asdict()
            return True, {
                'connected': info.get('connected', False),
                'trade_allowed': info.get('trade_allowed', False),
                'ping_ms': info.get('ping_last', -1),
            }
        return False, {'error': 'Terminal info returned None'}
    except Exception as e:
        return False, {'error': str(e)}


async def check_redis_connection(redis_client) -> tuple:
    """Check Redis connectivity and responsiveness."""
    try:
        start = time.time()
        await redis_client.ping()
        latency_ms = (time.time() - start) * 1000
        return True, {'latency_ms': round(latency_ms, 2)}
    except Exception as e:
        return False, {'error': str(e)}


async def check_postgresql_connection(db_pool) -> tuple:
    """Check PostgreSQL connectivity."""
    try:
        start = time.time()
        async with db_pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        latency_ms = (time.time() - start) * 1000
        pool_size = db_pool.get_size()
        pool_free = db_pool.get_idle_size()
        return True, {
            'latency_ms': round(latency_ms, 2),
            'pool_size': pool_size,
            'pool_free': pool_free,
        }
    except Exception as e:
        return False, {'error': str(e)}


# Initialization in the Execution Bridge service
health = HealthCheckHandler('execution_bridge', '1.0.0')
health.register_dependency('mt5', check_mt5_connection)
health.register_dependency('redis', lambda: check_redis_connection(redis_client))
health.register_dependency('postgresql', lambda: check_postgresql_connection(db_pool))
health.register_routes(app)
```

### 10.12.2 Auto-Restart with Systemd

All V1_Bot services are managed by systemd with watchdog and automatic restart capabilities:

```ini
# /etc/systemd/system/v1bot-execution-bridge.service
[Unit]
Description=V1_Bot Execution Bridge Service
Documentation=https://wiki.v1bot.internal/services/execution-bridge
After=network-online.target redis.service postgresql.service
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=notify
User=v1bot
Group=v1bot
WorkingDirectory=/opt/v1bot/execution_bridge
ExecStart=/opt/v1bot/venv/bin/python -m execution_bridge.main
ExecReload=/bin/kill -HUP $MAINPID

# Watchdog: service must notify systemd every 30 seconds
WatchdogSec=30

# Restart policy
Restart=always
RestartSec=5
RestartPreventExitStatus=0

# Resource limits
MemoryMax=2G
CPUQuota=200%
TasksMax=512

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=v1bot-exec-bridge

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/v1bot /opt/v1bot/data
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

The `StartLimitBurst=5` and `StartLimitIntervalSec=300` settings allow up to 5 restarts within a 5-minute window. If the service crashes more than 5 times in 5 minutes, systemd will stop attempting restarts and the service enters a failed state, triggering a CRITICAL alert.

### 10.12.3 Self-Healing Actions

V1_Bot implements a hierarchy of automated self-healing responses, ordered from least disruptive to most disruptive:

**Level 1: Retry and Reconnect**

Transient failures (network timeouts, brief broker disconnections) are handled by the services themselves through exponential backoff retry logic. No external intervention is required.

```python
# shared/resilience.py
import asyncio
import random
import logging

logger = logging.getLogger(__name__)

async def retry_with_backoff(
    func,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    on_retry=None,
):
    """Execute a function with exponential backoff retry."""
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"All {max_retries} retry attempts exhausted: {e}")
                raise

            delay = min(base_delay * (2 ** attempt), max_delay)
            if jitter:
                delay *= (0.5 + random.random())

            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                f"Retrying in {delay:.1f}s",
                extra={'latency_ms': delay * 1000}
            )

            if on_retry:
                await on_retry(attempt, e, delay)

            await asyncio.sleep(delay)
```

**Level 2: Service Restart**

If a service becomes unresponsive (fails liveness checks or watchdog), systemd automatically restarts it. The restart sequence includes a 5-second delay to allow any in-flight operations to complete and to prevent restart storms.

**Level 3: Dependency Failover**

When a dependency becomes unavailable, services fall back to degraded operation:

| Service           | Dependency Failure        | Failover Action                                     |
|-------------------|---------------------------|------------------------------------------------------|
| Algo Engine          | GPU unavailable           | Switch to CPU-based computation (higher latency)     |
| Algo Engine          | Redis unavailable         | Disable feature caching, compute on-the-fly          |
| Algo Engine          | PostgreSQL unavailable    | Use last cached features, limit to short-term signals|
| Execution Bridge  | Risk Manager unavailable  | Activate local kill switch, halt new trades           |
| Execution Bridge  | Redis unavailable         | Continue execution, buffer state updates locally     |
| Data Ingestion    | Primary WebSocket down    | Failover to backup data source                       |
| Data Ingestion    | Redis unavailable         | Buffer data locally, retry publication               |

**Level 4: Graceful Degradation**

When multiple components are degraded, the system reduces its operational scope:

```python
# shared/degraded_mode.py
from enum import IntEnum
from prometheus_client import Gauge

class OperationalMode(IntEnum):
    FULL = 0          # All systems operational
    DEGRADED_AI = 1   # AI on fallback, reduced confidence threshold
    DEGRADED_DATA = 2 # Partial data, wider stops
    MINIMAL = 3       # Only close existing positions, no new trades
    EMERGENCY = 4     # Kill switch active, all positions closed

operational_mode = Gauge(
    'v1bot_system_operational_mode',
    'Current operational mode (0=full, 1=degraded_ai, 2=degraded_data, 3=minimal, 4=emergency)'
)

class DegradedModeManager:
    def __init__(self):
        self.current_mode = OperationalMode.FULL
        self._mode_reasons = {}

    def report_degradation(self, component: str, reason: str):
        """Report a component degradation."""
        self._mode_reasons[component] = reason
        self._recalculate_mode()

    def report_recovery(self, component: str):
        """Report a component recovery."""
        self._mode_reasons.pop(component, None)
        self._recalculate_mode()

    def _recalculate_mode(self):
        """Determine overall operational mode from component statuses."""
        if not self._mode_reasons:
            self.current_mode = OperationalMode.FULL
        elif 'risk_manager' in self._mode_reasons or 'mt5' in self._mode_reasons:
            self.current_mode = OperationalMode.EMERGENCY
        elif 'algo_engine' in self._mode_reasons and 'data_ingestion' in self._mode_reasons:
            self.current_mode = OperationalMode.MINIMAL
        elif 'algo_engine' in self._mode_reasons:
            self.current_mode = OperationalMode.DEGRADED_AI
        elif 'data_ingestion' in self._mode_reasons:
            self.current_mode = OperationalMode.DEGRADED_DATA
        else:
            self.current_mode = OperationalMode.DEGRADED_AI

        operational_mode.set(self.current_mode.value)
```

**Level 5: Kill Switch**

When automated self-healing cannot resolve the issue or the risk exposure is too great, the kill switch activates. The kill switch closes all open positions, cancels all pending orders, and halts all new trading activity. It requires manual intervention to deactivate, either through the Streamlit Operations Center or a direct Redis command.

### 10.12.4 Health Check Monitoring Dashboard

The health check results themselves are monitored. A Prometheus blackbox exporter probes each service's `/health`, `/ready`, and `/live` endpoints:

```yaml
# prometheus blackbox exporter module for health checks
modules:
  v1bot_health:
    prober: http
    timeout: 5s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      valid_status_codes: [200]
      method: GET
      fail_if_body_not_matches_regexp:
        - '"status":"healthy"'
      preferred_ip_protocol: "ip4"

  v1bot_ready:
    prober: http
    timeout: 1s
    http:
      valid_status_codes: [200]
      method: GET
      fail_if_body_not_matches_regexp:
        - '"status":"ready"'

  v1bot_live:
    prober: http
    timeout: 500ms
    http:
      valid_status_codes: [200]
      method: GET
```

---

## 10.13 Capacity Planning and Performance Baselines

### 10.13.1 Baseline Collection

Before the V1_Bot system goes live with real capital, a comprehensive baseline of all performance metrics is collected during paper trading. This baseline serves as the reference point for all future performance regression detection.

The baseline collection process runs for a minimum of two full trading weeks (10 trading days) covering all market sessions (Asian, London, New York). During this period, the following baselines are captured:

```python
# capacity_planning/baseline_collector.py
"""
Collects performance baselines from Prometheus and stores them
in PostgreSQL for future comparison.
"""

import asyncio
import asyncpg
from datetime import datetime, timezone, timedelta
from prometheus_api_client import PrometheusConnect

PROMETHEUS_URL = "http://10.10.50.20:9090"

BASELINE_METRICS = {
    # Latency baselines (capture p50, p95, p99)
    'data_ingestion_latency': {
        'query': 'histogram_quantile({quantile}, sum(rate(v1bot_data_ingestion_processing_latency_seconds_bucket[5m])) by (le))',
        'quantiles': [0.5, 0.95, 0.99],
        'unit': 'seconds',
    },
    'ai_prediction_latency': {
        'query': 'histogram_quantile({quantile}, sum(rate(v1bot_algo_engine_prediction_latency_seconds_bucket[5m])) by (le))',
        'quantiles': [0.5, 0.95, 0.99],
        'unit': 'seconds',
    },
    'order_submission_latency': {
        'query': 'histogram_quantile({quantile}, sum(rate(v1bot_execution_order_submission_latency_seconds_bucket[5m])) by (le))',
        'quantiles': [0.5, 0.95, 0.99],
        'unit': 'seconds',
    },
    'risk_check_latency': {
        'query': 'histogram_quantile({quantile}, sum(rate(v1bot_risk_check_latency_seconds_bucket[5m])) by (le))',
        'quantiles': [0.5, 0.95, 0.99],
        'unit': 'seconds',
    },

    # Resource utilization baselines
    'cpu_usage_per_vm': {
        'query': 'v1bot:vm:cpu_usage:ratio',
        'type': 'gauge',
        'unit': 'ratio',
    },
    'memory_usage_per_vm': {
        'query': 'v1bot:vm:memory_usage:ratio',
        'type': 'gauge',
        'unit': 'ratio',
    },
    'gpu_utilization': {
        'query': 'v1bot:gpu:utilization:ratio',
        'type': 'gauge',
        'unit': 'ratio',
    },

    # Throughput baselines
    'data_messages_per_second': {
        'query': 'sum(rate(v1bot_data_ingestion_messages_received_total[5m]))',
        'type': 'gauge',
        'unit': 'msg/s',
    },
    'predictions_per_second': {
        'query': 'sum(rate(v1bot_algo_engine_prediction_requests_total[5m]))',
        'type': 'gauge',
        'unit': 'pred/s',
    },

    # Database baselines
    'db_query_latency': {
        'query': 'pg_stat_activity_max_tx_duration{datname="v1bot_trading"}',
        'type': 'gauge',
        'unit': 'seconds',
    },
    'redis_hit_rate': {
        'query': 'v1bot:redis:hit_rate:ratio',
        'type': 'gauge',
        'unit': 'ratio',
    },
}


async def collect_baselines(
    prom: PrometheusConnect,
    db_pool: asyncpg.Pool,
    collection_period_days: int = 10
):
    """Collect baseline metrics and store summary statistics."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=collection_period_days)

    for metric_name, config in BASELINE_METRICS.items():
        if 'quantiles' in config:
            for q in config['quantiles']:
                query = config['query'].format(quantile=q)
                data = prom.custom_query_range(
                    query, start_time, end_time, step='5m'
                )
                values = [float(v[1]) for series in data for v in series['values']
                          if v[1] != 'NaN']

                if values:
                    import numpy as np
                    await db_pool.execute(
                        """
                        INSERT INTO v1bot.performance_baselines
                            (metric_name, quantile, mean, std, p50, p95, p99,
                             min_val, max_val, sample_count, collection_start,
                             collection_end, unit)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        """,
                        f"{metric_name}_p{int(q*100)}", q,
                        float(np.mean(values)), float(np.std(values)),
                        float(np.percentile(values, 50)),
                        float(np.percentile(values, 95)),
                        float(np.percentile(values, 99)),
                        float(np.min(values)), float(np.max(values)),
                        len(values), start_time, end_time, config['unit']
                    )
        else:
            data = prom.custom_query_range(
                config['query'], start_time, end_time, step='5m'
            )
            # Process similarly for gauge-type metrics
```

### 10.13.2 Performance Regression Detection

Prometheus alerting rules continuously compare current performance against established baselines. A performance regression is detected when a metric deviates significantly from its baseline:

```yaml
# /opt/monitoring/prometheus/rules/alert_rules_regression.yml
groups:
  - name: v1bot_performance_regression
    rules:
      - alert: V1Bot_LatencyRegression_AI
        expr: |
          (
            v1bot:ai:prediction_latency_p95:seconds
            /
            v1bot:baseline:ai_prediction_latency_p95:seconds
          ) > 2.0
        for: 10m
        labels:
          severity: warning
          category: performance
        annotations:
          summary: "AI prediction latency has regressed"
          description: >
            p95 AI prediction latency is {{ $value }}x the baseline.
            Current: {{ with printf "v1bot:ai:prediction_latency_p95:seconds" | query }}{{ . | first | value | humanizeDuration }}{{ end }}.
            This may indicate model changes, GPU degradation, or resource contention.

      - alert: V1Bot_ThroughputRegression_Data
        expr: |
          (
            sum(rate(v1bot_data_ingestion_messages_received_total[5m]))
            /
            v1bot:baseline:data_messages_per_second:mean
          ) < 0.5
        for: 5m
        labels:
          severity: warning
          category: performance
        annotations:
          summary: "Data ingestion throughput has dropped below 50% of baseline"
          description: "Current throughput is {{ $value }}x the baseline. Check data sources."
```

### 10.13.3 Capacity Trending

A weekly capacity report is generated automatically, projecting when current growth trends will exceed resource limits:

```python
# capacity_planning/trend_report.py
"""
Weekly capacity trend report generator.
Analyzes resource utilization trends and projects time-to-exhaustion.
"""

import numpy as np
from datetime import datetime, timedelta
from scipy import stats

def project_exhaustion(
    timestamps: list,
    values: list,
    limit: float,
    method: str = 'linear'
) -> dict:
    """
    Project when a metric will reach its limit based on current trend.

    Returns:
        dict with 'days_to_exhaustion', 'growth_rate_per_day',
        'confidence', and 'projection_date'
    """
    if len(values) < 7:
        return {'days_to_exhaustion': None, 'reason': 'Insufficient data (< 7 points)'}

    # Convert timestamps to days from start
    t0 = timestamps[0]
    x = np.array([(t - t0).total_seconds() / 86400 for t in timestamps])
    y = np.array(values)

    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    if slope <= 0:
        return {
            'days_to_exhaustion': float('inf'),
            'growth_rate_per_day': slope,
            'r_squared': r_value ** 2,
            'reason': 'No growth trend detected'
        }

    # Project when y = limit
    days_to_limit = (limit - (slope * x[-1] + intercept)) / slope
    projection_date = datetime.now() + timedelta(days=max(days_to_limit, 0))

    return {
        'days_to_exhaustion': round(days_to_limit, 1),
        'growth_rate_per_day': round(slope, 6),
        'r_squared': round(r_value ** 2, 4),
        'current_value': round(y[-1], 4),
        'limit': limit,
        'utilization_pct': round((y[-1] / limit) * 100, 1),
        'projection_date': projection_date.isoformat(),
    }


# Resources to track for capacity planning
CAPACITY_METRICS = [
    {
        'name': 'Prometheus TSDB Storage',
        'query': 'prometheus_tsdb_storage_blocks_bytes',
        'limit_bytes': 200 * 1024**3,  # 200 GB
        'unit': 'bytes',
    },
    {
        'name': 'Loki Storage',
        'query': 'loki_ingester_chunks_stored_total',
        'limit': 10_000_000,
        'unit': 'chunks',
    },
    {
        'name': 'PostgreSQL Database Size',
        'query': 'pg_database_size_bytes{datname="v1bot_trading"}',
        'limit_bytes': 100 * 1024**3,  # 100 GB
        'unit': 'bytes',
    },
    {
        'name': 'VM Disk Usage (per VM)',
        'query': 'v1bot:vm:disk_usage:ratio',
        'limit': 0.9,  # 90%
        'unit': 'ratio',
    },
    {
        'name': 'Prometheus Cardinality',
        'query': 'prometheus_tsdb_head_series',
        'limit': 500_000,
        'unit': 'series',
    },
]
```

### 10.13.4 Storage Planning

The following table provides estimated storage consumption for the monitoring stack, based on measured data from baseline collection:

| Component           | Daily Growth  | 30-Day Total | 365-Day Total | Notes                              |
|---------------------|---------------|--------------|---------------|------------------------------------|
| Prometheus TSDB     | 3-4 GB        | 60 GB        | N/A (15d ret) | ~50K active series                 |
| Loki log chunks     | 500 MB - 1 GB | 15-30 GB     | N/A (30d ret) | Depends on log volume              |
| Jaeger traces       | 200-500 MB    | 3-7 GB       | N/A (7d ret)  | With 10% sampling                  |
| PostgreSQL (trading)| 100-300 MB    | 3-9 GB       | 36-100 GB     | Includes market data, trades, audit|
| Redis (in-memory)   | N/A           | ~2 GB stable | ~2 GB stable  | Bounded by configured maxmemory   |
| Grafana (SQLite)    | < 10 MB       | < 300 MB     | < 3.6 GB      | Dashboard configs, annotations     |

**Total monitoring storage requirement**: 256 GB SSD on the monitoring VM is sufficient for all retention periods with 40% headroom for growth.

---

## 10.14 Deployment and Configuration

### 10.14.1 Docker Compose for Monitoring Stack

The entire monitoring stack on `vm-monitor` is deployed using Docker Compose for reproducibility and ease of management:

```yaml
# /opt/monitoring/docker-compose.yml

version: '3.8'

networks:
  monitoring:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/24

volumes:
  prometheus_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/prometheus
  loki_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/loki
  jaeger_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/jaeger
  grafana_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/grafana

services:
  # ---------------------------------------------------------------
  # Prometheus -- Metrics Collection and Storage
  # ---------------------------------------------------------------
  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: v1bot-prometheus
    restart: unless-stopped
    user: "65534:65534"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'
      - '--storage.tsdb.retention.size=200GB'
      - '--storage.tsdb.wal-compression'
      - '--web.listen-address=:9090'
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'
      - '--web.external-url=http://10.10.50.20:9090'
      - '--query.max-concurrency=20'
      - '--query.timeout=2m'
      - '--log.level=info'
      - '--log.format=json'
    volumes:
      - /opt/monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - /opt/monitoring/prometheus/rules:/etc/prometheus/rules:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      monitoring:
        ipv4_address: 172.28.0.10
    mem_limit: 4g
    cpus: 2.0
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  # ---------------------------------------------------------------
  # Alertmanager -- Alert Routing and Notification
  # ---------------------------------------------------------------
  alertmanager:
    image: prom/alertmanager:v0.27.0
    container_name: v1bot-alertmanager
    restart: unless-stopped
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
      - '--web.listen-address=:9093'
      - '--cluster.listen-address='
      - '--log.level=info'
    volumes:
      - /opt/monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - /opt/monitoring/alertmanager/templates:/etc/alertmanager/templates:ro
    ports:
      - "9093:9093"
    networks:
      monitoring:
        ipv4_address: 172.28.0.11
    mem_limit: 256m
    cpus: 0.5

  # ---------------------------------------------------------------
  # Grafana -- Visualization and Dashboards
  # ---------------------------------------------------------------
  grafana:
    image: grafana/grafana:11.0.0
    container_name: v1bot-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD__FILE=/run/secrets/grafana_admin_password
      - GF_SERVER_ROOT_URL=http://10.10.50.20:3000
      - GF_SERVER_SERVE_FROM_SUB_PATH=false
      - GF_AUTH_ANONYMOUS_ENABLED=false
      - GF_ALERTING_ENABLED=false
      - GF_UNIFIED_ALERTING_ENABLED=true
      - GF_FEATURE_TOGGLES_ENABLE=traceToLogs,correlations
      - GF_LOG_MODE=console
      - GF_LOG_LEVEL=info
      - GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/var/lib/grafana/dashboards/system-overview.json
    volumes:
      - grafana_data:/var/lib/grafana
      - /opt/monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - /opt/monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "3000:3000"
    networks:
      monitoring:
        ipv4_address: 172.28.0.12
    mem_limit: 1g
    cpus: 1.0
    secrets:
      - grafana_admin_password
    depends_on:
      prometheus:
        condition: service_healthy

  # ---------------------------------------------------------------
  # Loki -- Log Aggregation
  # ---------------------------------------------------------------
  loki:
    image: grafana/loki:3.0.0
    container_name: v1bot-loki
    restart: unless-stopped
    command: -config.file=/etc/loki/config.yml
    volumes:
      - /opt/monitoring/loki/loki-config.yml:/etc/loki/config.yml:ro
      - loki_data:/data/loki
    ports:
      - "3100:3100"
    networks:
      monitoring:
        ipv4_address: 172.28.0.13
    mem_limit: 2g
    cpus: 1.0
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3100/ready"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ---------------------------------------------------------------
  # Jaeger -- Distributed Tracing
  # ---------------------------------------------------------------
  jaeger:
    image: jaegertracing/all-in-one:1.57
    container_name: v1bot-jaeger
    restart: unless-stopped
    environment:
      - SPAN_STORAGE_TYPE=badger
      - BADGER_EPHEMERAL=false
      - BADGER_DIRECTORY_KEY=/data/jaeger/keys
      - BADGER_DIRECTORY_VALUE=/data/jaeger/values
      - BADGER_SPAN_STORE_TTL=168h
      - QUERY_BASE_PATH=/jaeger
    volumes:
      - jaeger_data:/data/jaeger
    ports:
      - "6831:6831/udp"     # Jaeger compact thrift (agent)
      - "6832:6832/udp"     # Jaeger binary thrift (agent)
      - "14250:14250"       # gRPC collector
      - "14268:14268"       # HTTP collector
      - "16686:16686"       # Jaeger UI
    networks:
      monitoring:
        ipv4_address: 172.28.0.14
    mem_limit: 1g
    cpus: 0.5

  # ---------------------------------------------------------------
  # Telegram Alert Bot -- Alert Notification
  # ---------------------------------------------------------------
  telegram-bot:
    build:
      context: /opt/monitoring/telegram_bot
      dockerfile: Dockerfile
    container_name: v1bot-telegram-bot
    restart: unless-stopped
    environment:
      - FLASK_ENV=production
    volumes:
      - /opt/monitoring/alertmanager/telegram_token:/run/secrets/telegram_token:ro
    ports:
      - "9087:9087"
    networks:
      monitoring:
        ipv4_address: 172.28.0.15
    mem_limit: 256m
    cpus: 0.25
    depends_on:
      - alertmanager

  # ---------------------------------------------------------------
  # Streamlit -- Trading Operations Center
  # ---------------------------------------------------------------
  streamlit:
    build:
      context: /opt/monitoring/streamlit_app
      dockerfile: Dockerfile
    container_name: v1bot-streamlit
    restart: unless-stopped
    environment:
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
      - STREAMLIT_SERVER_HEADLESS=true
      - STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
    volumes:
      - /opt/monitoring/streamlit_app:/app:ro
      - /opt/monitoring/streamlit_app/.streamlit:/app/.streamlit:ro
    ports:
      - "8501:8501"
    networks:
      monitoring:
        ipv4_address: 172.28.0.16
    mem_limit: 1g
    cpus: 1.0
    depends_on:
      - prometheus

secrets:
  grafana_admin_password:
    file: /opt/monitoring/secrets/grafana_admin_password
```

### 10.14.2 Grafana Provisioning

Grafana data sources and dashboards are provisioned automatically from configuration files, ensuring reproducibility:

```yaml
# /opt/monitoring/grafana/provisioning/datasources/datasources.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      httpMethod: POST
      timeInterval: "5s"
      exemplarTraceIdDestinations:
        - name: traceID
          datasourceUid: jaeger

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: false
    jsonData:
      derivedFields:
        - name: TraceID
          matcherRegex: '"trace_id":"(\\w+)"'
          url: '$${__value.raw}'
          datasourceUid: jaeger

  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
    uid: jaeger
    editable: false
    jsonData:
      tracesToLogs:
        datasourceUid: loki
        tags: ['service']
        mappedTags: [{ key: 'service.name', value: 'service' }]
        mapTagNamesEnabled: true
        filterByTraceID: true

  - name: PostgreSQL
    type: postgres
    access: proxy
    url: 10.10.40.10:5432
    database: v1bot_trading
    user: v1bot_readonly
    editable: false
    secureJsonData:
      password: "${POSTGRES_READONLY_PASSWORD}"
    jsonData:
      sslmode: require
      maxOpenConns: 5
      maxIdleConns: 2
      connMaxLifetime: 14400
      postgresVersion: 1600
      timescaledb: true
```

```yaml
# /opt/monitoring/grafana/provisioning/dashboards/dashboards.yml
apiVersion: 1

providers:
  - name: V1_Bot Dashboards
    orgId: 1
    folder: V1_Bot
    type: file
    disableDeletion: true
    updateIntervalSeconds: 30
    allowUiUpdates: false
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
```

### 10.14.3 Backup Procedures

The monitoring infrastructure itself requires backup procedures to ensure that dashboards, alert configurations, and historical data can be recovered.

**Daily Backup Script**

```bash
#!/bin/bash
# /opt/monitoring/scripts/backup_monitoring.sh
# Runs daily at 02:00 UTC via cron

set -euo pipefail

BACKUP_DIR="/data/backups/monitoring/$(date +%Y-%m-%d)"
RETENTION_DAYS=30

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting monitoring stack backup..."

# 1. Backup Grafana dashboards and configuration
echo "  Backing up Grafana..."
docker exec v1bot-grafana grafana-cli admin data-migration encrypt \
  2>/dev/null || true
cp -r /opt/monitoring/grafana/provisioning "${BACKUP_DIR}/grafana_provisioning"
cp -r /opt/monitoring/grafana/dashboards "${BACKUP_DIR}/grafana_dashboards"
# Backup Grafana SQLite database
docker cp v1bot-grafana:/var/lib/grafana/grafana.db "${BACKUP_DIR}/grafana.db"

# 2. Backup Prometheus configuration and rules
echo "  Backing up Prometheus config..."
cp /opt/monitoring/prometheus/prometheus.yml "${BACKUP_DIR}/prometheus.yml"
cp -r /opt/monitoring/prometheus/rules "${BACKUP_DIR}/prometheus_rules"

# 3. Backup Alertmanager configuration
echo "  Backing up Alertmanager config..."
cp /opt/monitoring/alertmanager/alertmanager.yml "${BACKUP_DIR}/alertmanager.yml"
cp -r /opt/monitoring/alertmanager/templates "${BACKUP_DIR}/alertmanager_templates"

# 4. Backup Loki configuration
echo "  Backing up Loki config..."
cp /opt/monitoring/loki/loki-config.yml "${BACKUP_DIR}/loki-config.yml"

# 5. Backup Streamlit application
echo "  Backing up Streamlit app..."
cp -r /opt/monitoring/streamlit_app "${BACKUP_DIR}/streamlit_app"

# 6. Create Prometheus TSDB snapshot (if API enabled)
echo "  Creating Prometheus TSDB snapshot..."
SNAPSHOT_NAME=$(curl -s -XPOST http://localhost:9090/api/v1/admin/tsdb/snapshot \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['name'])")
if [ -n "${SNAPSHOT_NAME}" ]; then
    mv "/data/prometheus/data/snapshots/${SNAPSHOT_NAME}" \
       "${BACKUP_DIR}/prometheus_snapshot"
fi

# 7. Compress the backup
echo "  Compressing backup..."
cd "$(dirname ${BACKUP_DIR})"
tar -czf "$(basename ${BACKUP_DIR}).tar.gz" "$(basename ${BACKUP_DIR})"
rm -rf "${BACKUP_DIR}"

# 8. Clean up old backups
echo "  Cleaning old backups..."
find /data/backups/monitoring -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Monitoring backup completed: ${BACKUP_DIR}.tar.gz"
```

### 10.14.4 Disaster Recovery Plan

In the event of a complete monitoring VM failure, the following recovery procedure restores full monitoring capability:

**Recovery Time Objective (RTO)**: 30 minutes
**Recovery Point Objective (RPO)**: 24 hours (last backup)

**Recovery Steps**:

1. **Create new VM** (5 minutes): Provision a new VM on Proxmox with the same resource allocation (4 vCPU, 8 GB RAM, 256 GB SSD). Assign it to VLAN 50 with the same IP address (10.10.50.20).

2. **Install prerequisites** (5 minutes): Install Docker, Docker Compose, and required system packages from the Ansible playbook stored in the infrastructure repository.

3. **Restore configuration** (5 minutes): Extract the latest backup tarball and copy configuration files to `/opt/monitoring/`.

4. **Deploy monitoring stack** (5 minutes): Run `docker compose up -d` from `/opt/monitoring/`. All containers will start with the restored configurations.

5. **Restore Grafana state** (2 minutes): Copy the backed-up `grafana.db` into the Grafana container volume. Restart the Grafana container.

6. **Verify scrape targets** (3 minutes): Open Prometheus UI at `:9090/targets` and verify all scrape targets are UP. Prometheus will begin collecting fresh data immediately; historical data from the TSDB snapshot (if available) will be accessible.

7. **Verify alerting** (2 minutes): Trigger a test alert via `amtool alert add test-alert severity=info` and confirm delivery to Telegram.

8. **Verify dashboards** (3 minutes): Open each Grafana dashboard and confirm data is flowing. New data will appear within the first scrape interval (5-15 seconds). Historical data gaps will be visible for the period between the last backup and the recovery.

**Important Notes on Monitoring DR**:

- The trading system continues to operate normally during a monitoring outage. Services buffer metrics internally until Prometheus resumes scraping.
- The kill switch and risk manager operate independently of the monitoring stack. They do not depend on Prometheus or Grafana.
- Redis live state is unaffected by monitoring VM failure, so the Execution Bridge and Risk Manager continue to use Redis for inter-service communication.
- The only operational impact of a monitoring outage is loss of visibility (no dashboards, no alerts). This is mitigated by the services' own local logging and the fact that critical safety mechanisms (kill switch, circuit breakers) are embedded in the trading services, not in the monitoring infrastructure.

### 10.14.5 Configuration Management and Version Control

All monitoring configuration files are stored in a Git repository alongside the V1_Bot application code. Changes to monitoring configuration follow the same review and deployment process as application code:

```
v1bot-monitoring/
  docker-compose.yml
  prometheus/
    prometheus.yml
    rules/
      recording_rules.yml
      alert_rules_infrastructure.yml
      alert_rules_trading.yml
      alert_rules_ai.yml
      alert_rules_risk.yml
      alert_rules_database.yml
      alert_rules_regression.yml
  alertmanager/
    alertmanager.yml
    templates/
      telegram.tmpl
  grafana/
    provisioning/
      datasources/datasources.yml
      dashboards/dashboards.yml
    dashboards/
      system-overview.json
      infrastructure.json
      trading-performance.json
      ai-model-health.json
      risk-status.json
      execution-quality.json
      data-pipeline.json
  loki/
    loki-config.yml
    rules/
      v1bot_log_alerts.yml
  jaeger/
    jaeger-config.yml
  streamlit_app/
    app.py
    pages/
      live_trading.py
      ai_decision_log.py
      risk_dashboard.py
      model_performance.py
      system_health.py
      trade_journal.py
      configuration.py
    Dockerfile
    requirements.txt
    .streamlit/
      config.toml
  telegram_bot/
    alert_bot.py
    Dockerfile
    requirements.txt
  scripts/
    backup_monitoring.sh
    deploy.sh
    validate_config.sh
  README.md
```

Configuration changes are deployed via a simple script that validates configurations before applying them:

```bash
#!/bin/bash
# /opt/monitoring/scripts/deploy.sh
set -euo pipefail

echo "=== V1_Bot Monitoring Deployment ==="

# 1. Validate Prometheus configuration
echo "[1/5] Validating Prometheus config..."
docker run --rm -v /opt/monitoring/prometheus:/etc/prometheus:ro \
  prom/prometheus:v2.51.0 \
  promtool check config /etc/prometheus/prometheus.yml

# 2. Validate alerting rules
echo "[2/5] Validating alert rules..."
docker run --rm -v /opt/monitoring/prometheus/rules:/rules:ro \
  prom/prometheus:v2.51.0 \
  promtool check rules /rules/*.yml

# 3. Validate Alertmanager configuration
echo "[3/5] Validating Alertmanager config..."
docker run --rm -v /opt/monitoring/alertmanager:/etc/alertmanager:ro \
  prom/alertmanager:v0.27.0 \
  amtool check-config /etc/alertmanager/alertmanager.yml

# 4. Deploy with zero-downtime reload where possible
echo "[4/5] Deploying configuration changes..."

# Reload Prometheus (supports hot reload)
curl -s -XPOST http://localhost:9090/-/reload
echo "  Prometheus reloaded"

# Reload Alertmanager (supports hot reload)
curl -s -XPOST http://localhost:9093/-/reload
echo "  Alertmanager reloaded"

# Restart containers that don't support hot reload
docker compose restart loki streamlit telegram-bot
echo "  Loki, Streamlit, Telegram bot restarted"

# 5. Verify all services are healthy
echo "[5/5] Verifying service health..."
sleep 10

services=("prometheus:9090/-/healthy" "alertmanager:9093/-/healthy" \
          "loki:3100/ready" "grafana:3000/api/health")
all_healthy=true

for svc in "${services[@]}"; do
    if curl -sf "http://localhost:${svc}" > /dev/null 2>&1; then
        echo "  $(echo $svc | cut -d: -f1): OK"
    else
        echo "  $(echo $svc | cut -d: -f1): FAILED"
        all_healthy=false
    fi
done

if $all_healthy; then
    echo ""
    echo "=== Deployment successful ==="
else
    echo ""
    echo "=== WARNING: Some services are unhealthy ==="
    exit 1
fi
```

---

## Summary

The V1_Bot monitoring, observability, and dashboard infrastructure provides comprehensive visibility into every layer of the trading ecosystem -- from Proxmox host hardware to individual trade decisions. The architecture is built on the three pillars of observability (metrics, logs, traces) with trading-specific extensions for P&L tracking, risk monitoring, and AI model health.

Key architectural decisions include:

- **Prometheus pull model** for reliable metric collection with differentiated scrape intervals per service criticality
- **Dual data path** (Prometheus for historical metrics, Redis for sub-second live state) enabling both Grafana dashboards and Streamlit real-time operations
- **Seven purpose-built Grafana dashboards** covering system overview, infrastructure, trading performance, AI health, risk status, execution quality, and data pipeline
- **Streamlit Trading Operations Center** providing interactive, application-like trading operations interface with kill switch controls, AI decision logs, and trade journal
- **Tiered alerting** through Alertmanager with Telegram notification, severity-based routing, and actionable runbooks for every alert
- **Structured JSON logging** via Loki with trace correlation for end-to-end diagnosis
- **Distributed tracing** via Jaeger with intelligent sampling (100% for trades, 10% for predictions, 1% for data ingestion)
- **Self-healing hierarchy** from automatic retries through service restarts to graceful degradation and kill switch activation
- **Capacity planning** with baseline collection, regression detection, and storage growth projection

The monitoring system is designed to be independent of the trading system's operation -- monitoring failures never affect trading safety mechanisms, which are embedded directly in the trading services.

*fine del documento 10 -- Monitoring, Observability, and Dashboard*
