# Guida Proxmox — VM, Indirizzi e Ruoli

**Per**: Renan (operatore del sistema)
**Data**: 2026-02-28

---

## Mappa della Rete

```
PROXMOX HOST (bare metal, il tuo PC fisico)
IP: 10.0.0.1 (gateway)
│
├── VM 100: "macena-docker"    IP: 10.0.0.100
│   Ubuntu 24.04 LTS
│   8 CPU, 16GB RAM, 60GB disk
│   ┌──────────────────────────────────────────────┐
│   │  TUTTI i servizi MONEYMAKER girano QUI dentro   │
│   │                                              │
│   │  PostgreSQL (TimescaleDB)  → porta 5432      │
│   │  Redis 7                   → porta 6379      │
│   │  Data Ingestion (Go)       → porta 5555/8081 │
│   │  Algo Engine (Python)         → porta 8080/50054│
│   │  MT5 Bridge (Python)       → porta 50055     │
│   │  Prometheus                → porta 9091      │
│   │  Grafana                   → porta 3000      │
│   │  TensorBoard               → porta 6006      │
│   └──────────────────────────────────────────────┘
│
├── VM 101: "macena-mt5"       IP: 10.0.0.101
│   Windows 10/11
│   4 CPU, 8GB RAM, 40GB disk
│   ┌──────────────────────────────────────────────┐
│   │  MetaTrader 5 Terminal                       │
│   │  Si collega a: 10.0.0.100:50055 (gRPC)      │
│   │  Esegue gli ordini sul broker                │
│   └──────────────────────────────────────────────┘
│
├── LXC 200: "macena-ci"       IP: 10.0.0.200
│   Debian 12 (container leggero)
│   2 CPU, 4GB RAM, 30GB disk
│   ┌──────────────────────────────────────────────┐
│   │  Forgejo (git server self-hosted)  → :3000   │
│   │  CI Runner (esegue test automatici)          │
│   └──────────────────────────────────────────────┘
│
└── (Futuro) VM 102: "macena-ml-lab"  IP: 10.0.0.102
    Ubuntu + GPU passthrough (RX 9070 XT)
    8 CPU, 16GB RAM
    ┌──────────────────────────────────────────────┐
    │  ML Training Lab (PyTorch + ROCm)            │
    │  Addestra i modelli neurali                  │
    │  Serve predizioni via gRPC → :50056          │
    └──────────────────────────────────────────────┘
```

---

## Cosa Fa Ogni VM

### VM 100: macena-docker — Il Cuore del Sistema

**Ruolo**: Ospita TUTTI i container Docker. E' il cervello operativo.

**Cosa succede quando la accendi**:
1. `docker compose up -d` avvia 8 container nell'ordine corretto
2. PostgreSQL parte per primo (database)
3. Redis parte secondo (cache veloce)
4. Data Ingestion si connette a Polygon.io e inizia a ricevere tick
5. Algo Engine si sveglia, carica i modelli, sottoscrive i dati ZMQ
6. MT5 Bridge si mette in ascolto di segnali dall'Algo Engine
7. Prometheus inizia a raccogliere metriche da tutti i servizi
8. Grafana diventa accessibile per la dashboard

**Come accedi**:
- SSH: `ssh moneymaker@10.0.0.100`
- Grafana: apri il browser su `http://10.0.0.100:3000`
- TensorBoard: `http://10.0.0.100:6006`
- Health check Brain: `http://10.0.0.100:8080/health`
- Health check Data: `http://10.0.0.100:8081/healthz`

**Comandi utili**:
```bash
# Vedere lo stato dei container
docker compose ps

# Vedere i log in tempo reale
docker compose logs -f macena-brain
docker compose logs -f macena-data-ingestion

# Riavviare un servizio
docker compose restart macena-brain

# Fermare tutto
docker compose down

# Ricostruire dopo un aggiornamento del codice
git pull && docker compose build --parallel && docker compose up -d
```

---

### VM 101: macena-mt5 — Il Braccio Esecutivo

**Ruolo**: Esegue materialmente gli ordini sul broker via MetaTrader 5.

**Perche' una VM Windows separata**:
- MetaTrader 5 gira SOLO su Windows
- Isolamento: se MT5 crasha, il Brain continua a funzionare
- La VM Windows non ha bisogno di GPU o molta RAM

**Cosa succede quando la accendi**:
1. Windows si avvia
2. MT5 si apre automaticamente (auto-start)
3. MT5 si connette al broker (demo o live)
4. Il servizio mt5-bridge (dentro VM 100) si collega a MT5 via gRPC
5. Quando l'Algo Engine genera un segnale BUY/SELL, il segnale viaggia:
   `Algo Engine → gRPC → MT5 Bridge → MetaTrader5 Python API → MT5 Terminal → Broker`

**Come accedi**:
- RDP (Remote Desktop): `mstsc /v:10.0.0.101`
- Oppure dalla console Proxmox web: `https://IP_PROXMOX:8006` → VM 101 → Console

**Cosa guardare**:
- MT5 deve mostrare "Connected" in basso a destra
- Tab "Trade": vedi le posizioni aperte da MONEYMAKER (magic number 123456)
- Tab "Journal": log degli ordini eseguiti

---

### LXC 200: macena-ci — Il Guardiano della Qualita'

**Ruolo**: Server git + test automatici. Ogni volta che fai push, esegue i test.

**In fase di sviluppo**: Non e' indispensabile — puoi usare GitHub come stai facendo ora.

**In produzione**: Utile per avere un git server locale (Forgejo) che non dipende da Internet.

---

### VM 102 (futura): macena-ml-lab — La Palestra del Neural Network

**Ruolo**: Addestra i modelli neurali con la GPU AMD RX 9070 XT.

**Non esiste ancora** — e' la prossima cosa da costruire dopo che il sistema base funziona.

**Cosa fara'**:
1. Riceve dati storici da TimescaleDB (VM 100)
2. Addestra MarketRAPCoach (Perception → Memory → Strategy → Pedagogy)
3. Salva i checkpoint (file .pt)
4. Serve predizioni in tempo reale via gRPC sulla porta 50056
5. L'Algo Engine (VM 100) chiama `MLProxy.predict()` che va a VM 102

---

## Flusso dei Dati (Semplificato)

```
Internet (Polygon.io)
    │
    ▼
VM 100: Data Ingestion riceve tick ogni ~1ms
    │
    ▼
VM 100: Algo Engine analizza → genera segnale BUY/SELL/HOLD
    │
    ▼
VM 100: MT5 Bridge riceve il segnale via gRPC
    │
    ▼
VM 101: MetaTrader 5 esegue l'ordine sul broker
    │
    ▼
Broker: ordine eseguito, conferma ritorna indietro
    │
    ▼
VM 100: Database registra tutto (audit trail)
    ▼
VM 100: Grafana mostra la dashboard in tempo reale
```

---

## In Fase di Sviluppo (Adesso, sul tuo PC Windows)

Adesso non hai Proxmox. Lavori direttamente sul PC. Ecco la differenza:

| Aspetto | Adesso (Dev) | Proxmox (Produzione) |
|---------|-------------|---------------------|
| Dove gira Docker | Sul tuo PC Windows | VM 100 (Ubuntu) |
| Dove gira MT5 | Sul tuo PC Windows | VM 101 (Windows) |
| Database | Container Docker locale | Container dentro VM 100 |
| Dati di mercato | Mock/replay | Live da Polygon.io |
| Trading | Paper (nessun ordine reale) | Demo account → poi Live |
| GPU ML | Non usata | VM 102 con passthrough |
| Monitoring | Log a terminale | Grafana + Prometheus |

**Per passare a Proxmox**: Installi Proxmox sul bare metal, crei le VM, cloni il repo dentro VM 100, e fai `docker compose up -d`. Il codice e' lo stesso — cambia solo dove gira.

---

## Porte da Ricordare

| Porta | Servizio | Cosa Ci Trovi |
|-------|----------|---------------|
| 3000 | Grafana | Dashboard grafiche (P&L, segnali, latenza) |
| 5432 | PostgreSQL | Database (non aprire nel browser) |
| 6379 | Redis | Cache (non aprire nel browser) |
| 5555 | ZeroMQ | Stream dati di mercato (non e' HTTP) |
| 8080 | Algo Engine REST | Health check + API status |
| 8081 | Data Ingestion | Health check |
| 9091 | Prometheus | Metriche raw (JSON) |
| 50054 | Algo Engine gRPC | Comunicazione ML Lab → Brain |
| 50055 | MT5 Bridge gRPC | Comunicazione Brain → MT5 |
| 6006 | TensorBoard | Grafici training ML |
