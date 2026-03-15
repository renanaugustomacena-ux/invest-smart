# Configuration

Per-environment YAML configuration files for all MONEYMAKER services.

## Structure

```
configs/
├── moneymaker_services.yaml   # Static service discovery (IPs & ports)
├── development/            # Dev environment overrides
│   ├── algo-engine.yaml
│   ├── data-ingestion.yaml
│   └── mt5-bridge.yaml
└── production/             # Production environment overrides
    ├── algo-engine.yaml
    └── mt5-bridge.yaml
```

## Service Discovery

`moneymaker_services.yaml` defines the static IP and port map for Proxmox deployment:

| Service | Host | Key Ports |
|---|---|---|
| Data Ingestion | `10.0.1.10` | ZMQ: 5555, Metrics: 9090 |
| Database | `10.0.2.10` | PG: 5432, Redis: 6379 |
| Algo Engine | `10.0.4.10` | gRPC: 50054, REST: 8080 |
| MT5 Bridge | `10.0.4.11` | gRPC: 50055 |
| Monitoring | `10.0.5.10` | Prometheus: 9090, Grafana: 3000 |

> In Docker Compose, container names are used instead of static IPs.

## Usage

Services load config by environment:

- **Development**: Docker container names, relaxed timeouts
- **Production**: Static IPs, tuned performance parameters

Sensitive values (passwords, API keys) are set via environment variables — see `.env.example`.
