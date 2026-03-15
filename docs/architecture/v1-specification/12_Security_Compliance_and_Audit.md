# MONEYMAKER V1 -- Security, Compliance, and Audit

> **Autore** | Renan Augusto Macena
---

## Table of Contents

1. [Security Philosophy](#1-security-philosophy)
2. [Threat Model](#2-threat-model)
3. [Network Security](#3-network-security)
4. [Authentication and Authorization](#4-authentication-and-authorization)
5. [Secrets Management](#5-secrets-management)
6. [Data Security](#6-data-security)
7. [Application Security](#7-application-security)
8. [Container and VM Security](#8-container-and-vm-security)
9. [Audit Trail System](#9-audit-trail-system)
10. [NIST Cybersecurity Framework Alignment](#10-nist-cybersecurity-framework-alignment)
11. [Incident Response Plan](#11-incident-response-plan)
12. [Disaster Recovery](#12-disaster-recovery)
13. [Security Monitoring and Detection](#13-security-monitoring-and-detection)
14. [Operational Security](#14-operational-security)

---

## 1. Security Philosophy

### 1.1 Why Security Is Non-Negotiable

MONEYMAKER V1 is not a toy project. It is not a weekend experiment. It is not a proof of concept that will be discarded next month. MONEYMAKER is an autonomous trading ecosystem that handles real money, communicates with live broker servers using real credentials, and makes financial decisions that have irreversible consequences. A compromised MONEYMAKER installation does not produce a funny error message or a broken web page -- it produces unauthorized trades on a live brokerage account, stolen credentials that can be used to drain the account entirely, or manipulated AI models that systematically destroy capital while appearing to function normally. The financial and personal consequences of a security breach in this system are severe, immediate, and potentially unrecoverable.

Every architectural decision, every configuration parameter, every line of code in MONEYMAKER must be evaluated through a security lens. This is not a burden to be minimized or a checkbox to be ticked at the end of the project. Security is a first-class architectural concern that influences technology choices, communication patterns, deployment procedures, and operational workflows from the very beginning. The cost of implementing security correctly during design is a fraction of the cost of retrofitting it after a breach.

This document is the comprehensive security specification for MONEYMAKER V1. It defines the threat model, the defensive architecture, the compliance framework, the audit system, and the operational security procedures that together form the security posture of the ecosystem. It is intended to be read, understood, and followed by every person who builds, deploys, operates, or has access to any part of the system.

### 1.2 Defense in Depth

MONEYMAKER's security architecture is built on the principle of defense in depth: no single security control is trusted to prevent all attacks. Instead, multiple independent layers of defense are arranged so that an attacker who penetrates one layer encounters another. If the network firewall fails, host-based firewalls still protect individual VMs. If a host-based firewall is misconfigured, application-level authentication rejects unauthorized requests. If an application-level token is leaked, mutual TLS (mTLS) prevents its use from an unauthorized host. If mTLS is bypassed through a compromised service, database-level permissions restrict what the compromised service can access. If database permissions are insufficient, encryption at rest prevents a disk-level attacker from reading the data.

The security layers in MONEYMAKER, from outermost to innermost, are:

```
+=========================================================================+
|                   LAYER 1: PHYSICAL SECURITY                            |
|   Server locked in a secure location, UPS, access control              |
+=========================================================================+
|                   LAYER 2: NETWORK PERIMETER                            |
|   WireGuard VPN, no direct internet-facing services                    |
+=========================================================================+
|                   LAYER 3: VLAN SEGMENTATION                            |
|   4 VLANs, inter-VLAN firewall rules, DROP ALL default                 |
+=========================================================================+
|                   LAYER 4: HOST FIREWALL                                |
|   Per-VM nftables rules, rate limiting, SYN flood protection           |
+=========================================================================+
|                   LAYER 5: TLS/mTLS ENCRYPTION                          |
|   All inter-service communication encrypted, mutual authentication     |
+=========================================================================+
|                   LAYER 6: APPLICATION AUTHENTICATION                   |
|   API tokens, service accounts, RBAC, session management               |
+=========================================================================+
|                   LAYER 7: APPLICATION AUTHORIZATION                    |
|   Least-privilege permissions, input validation, output sanitization   |
+=========================================================================+
|                   LAYER 8: DATA ENCRYPTION                              |
|   ZFS AES-256-GCM at rest, column-level encryption for credentials     |
+=========================================================================+
|                   LAYER 9: AUDIT AND DETECTION                          |
|   Immutable audit logs, anomaly detection, integrity verification      |
+=========================================================================+
```

Each layer is independently effective and does not depend on the correctness of any other layer. An attacker must penetrate all nine layers to achieve full compromise of the system.

### 1.3 Principle of Least Privilege

Every component in MONEYMAKER -- every VM, every container, every service process, every database user, every API token -- receives the minimum set of permissions required to perform its designated function, and nothing more. The Data Ingestion Service can INSERT into market data tables but cannot SELECT from the trades table. The Algo Engine can SELECT from market data and INSERT into the signals table but cannot DROP tables or ALTER schemas. The MT5 Bridge can INSERT into the trades table but cannot access the model registry. The monitoring dashboard can SELECT from all tables but cannot INSERT, UPDATE, or DELETE from any.

This principle extends beyond database permissions. At the network level, each VLAN allows only the specific traffic flows required by the services within it. At the container level, Docker containers run as non-root users with read-only filesystems where possible. At the system level, SSH access is limited to specific authorized keys, and sudo access is granted only where explicitly required.

The rationale is containment. If any single component is compromised -- through a software vulnerability, a leaked credential, a supply chain attack on a dependency -- the blast radius is limited to the permissions of that component. A compromised Data Ingestion Service cannot execute trades. A compromised monitoring dashboard cannot modify AI models. A compromised Training Lab cannot access broker credentials. Least privilege ensures that compromise of one component does not automatically grant the attacker access to the entire system.

### 1.4 Zero Trust

MONEYMAKER does not trust any component based solely on its network location or identity. Being inside the VLAN does not grant access. Having a valid IP address does not prove identity. Every request between services must be authenticated (the requester proves who it is) and authorized (the requester is verified to have permission for the requested action). This is the zero trust principle: verify explicitly, assume nothing.

In practice, this means that inter-service communication uses mTLS (both the client and the server present certificates), API requests include bearer tokens that are validated on every call, and database connections require both network-level access (correct VLAN) and credential-level authentication (username and password or certificate). Even if an attacker gains access to the DATA VLAN through a misconfigured firewall rule, they cannot issue queries to PostgreSQL without valid credentials, and they cannot issue gRPC calls to the MT5 Bridge without a valid mTLS certificate.

### 1.5 Assume Breach

MONEYMAKER is designed under the assumption that a breach will eventually occur. This is not pessimism -- it is realism. No system is perfectly secure, and the question is not whether a breach will happen but when. The assume-breach mentality drives several critical design decisions:

- **Segmentation for containment.** VLANs isolate services so that a breach in one segment does not automatically propagate to others.
- **Immutable audit logs.** Even if an attacker gains write access to the database, the append-only audit log with its hash chain provides evidence of what occurred before, during, and after the breach.
- **Secret rotation.** Credentials are rotated on a schedule, so a leaked credential has a limited window of usefulness.
- **Monitoring for detection.** Security-specific alerts detect anomalous behavior (unusual login patterns, unexpected network connections, file integrity changes) so that breaches are detected quickly rather than persisting unnoticed for months.
- **Incident response plan.** A documented, rehearsed plan ensures that when a breach is detected, the response is swift, coordinated, and effective rather than panicked and ad hoc.

### 1.6 Security Must Not Impede but Must Never Be Bypassed

There is an inherent tension between security and operational efficiency. Requiring 2FA for every API call would make the system unusable. Encrypting every Redis cache entry would add latency to the critical trading path. Requiring manual approval for every trade would defeat the purpose of automation. MONEYMAKER resolves this tension through risk-proportional controls: the strictness of a security control is proportional to the sensitivity of the asset it protects.

Broker credentials (CRITICAL classification) are encrypted at rest, encrypted in transit, stored in a dedicated secrets manager, rotated every 90 days, and accessed only through audited API calls. Market data cache (INTERNAL classification) is protected by VLAN segmentation and TLS but not encrypted at rest in Redis, because the data is ephemeral, non-sensitive, and latency-critical. This proportional approach ensures that security controls are strongest where the risk is highest and lightest where the data is least sensitive.

What is never acceptable is bypassing security controls for convenience. No "just this once" exceptions to credential rotation. No "temporary" firewall rules that allow all traffic. No hardcoded passwords "until we set up the secrets manager." Security shortcuts have a way of becoming permanent, and in a financial system, a permanent shortcut is an invitation to disaster.

---

## 2. Threat Model

### 2.1 Threat Modeling Methodology

MONEYMAKER uses a combination of STRIDE threat modeling (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) and a risk assessment matrix to systematically identify, categorize, and prioritize threats. Each threat is evaluated along two axes: likelihood (how probable is it that this threat materializes?) and impact (how severe are the consequences if it does?). The product of likelihood and impact determines the risk level, which in turn determines the priority and investment in countermeasures.

### 2.2 External Threats

External threats originate from actors outside the MONEYMAKER infrastructure who are attempting to gain unauthorized access, steal data, or disrupt operations.

**Unauthorized Access to Proxmox Management.** The Proxmox web UI (port 8006) provides full control over all VMs: creating, destroying, configuring, snapshotting, and migrating. An attacker who gains access to the Proxmox UI can destroy the entire infrastructure, extract VM disk images (containing all data, credentials, and models), or modify VM configurations to insert backdoors. This is the highest-impact external threat.

- **Likelihood:** LOW (mitigated by VPN-only access, 2FA, no direct internet exposure)
- **Impact:** CRITICAL (full system compromise)
- **Risk Level:** HIGH
- **Countermeasures:** Proxmox UI accessible only via WireGuard VPN. No port 8006 exposed to the internet. Local accounts with TOTP 2FA. Failed login lockout. Session timeout.

**Broker Account Compromise.** An attacker who obtains MT5 broker credentials (login number, password, server address) can execute trades on the live account, withdraw funds (if the broker allows API-initiated withdrawals), or modify account settings.

- **Likelihood:** LOW (credentials stored in secrets manager, not in code or config files)
- **Impact:** CRITICAL (direct financial loss)
- **Risk Level:** HIGH
- **Countermeasures:** Credentials stored in encrypted secrets manager. Rotated every 90 days. Never in version control, environment files on disk, or logs. MT5 VM isolated on TRADE VLAN. Broker-side IP whitelist where supported.

**Data Interception (Man-in-the-Middle).** An attacker positioned on the network path between MONEYMAKER and the broker (or between MONEYMAKER and data providers) could intercept, modify, or replay network traffic. Modified market data could cause the Algo Engine to make incorrect trading decisions. Intercepted broker credentials could be used for account takeover.

- **Likelihood:** LOW (all external communication uses TLS 1.3)
- **Impact:** HIGH (incorrect trades, credential theft)
- **Risk Level:** MEDIUM
- **Countermeasures:** TLS 1.3 for all external connections. Certificate pinning for broker connections where possible. Anomaly detection for unexpected data patterns.

**Brute Force and Credential Stuffing.** Automated attacks attempting to guess SSH passwords, Proxmox UI passwords, or dashboard passwords.

- **Likelihood:** MEDIUM (automated attacks are constant on the internet)
- **Impact:** MEDIUM to CRITICAL (depends on which credential is compromised)
- **Risk Level:** MEDIUM
- **Countermeasures:** SSH key-based authentication only (password authentication disabled). fail2ban on all externally reachable services. Rate limiting. Account lockout after 5 failed attempts.

### 2.3 Internal Threats

Internal threats originate from within the MONEYMAKER infrastructure itself, either from misconfiguration, software vulnerabilities, or compromised components.

**Misconfigured Services.** A firewall rule that accidentally allows all traffic, a database user with excessive permissions, a Docker container running as root, or a TLS certificate that has expired without detection.

- **Likelihood:** MEDIUM (configuration is complex and errors are inevitable)
- **Impact:** VARIES (depends on the specific misconfiguration)
- **Risk Level:** MEDIUM
- **Countermeasures:** Infrastructure as Code (all configurations version-controlled and reviewed). Automated configuration validation. Regular security audits. Principle of least privilege as the default.

**Credential Leaks.** Secrets accidentally committed to version control, printed in log messages, included in error reports, or stored in plaintext configuration files.

- **Likelihood:** MEDIUM (this is one of the most common security failures in real-world systems)
- **Impact:** HIGH to CRITICAL (depends on which credential is leaked)
- **Risk Level:** HIGH
- **Countermeasures:** Pre-commit hooks with gitleaks to detect secrets in code. Log sanitization to redact sensitive values. Secrets injected via environment variables at runtime, never stored on disk. Regular scanning of all repositories and configuration files.

**Supply Chain Attacks via Dependencies.** A malicious or compromised Python package, Go module, or Docker base image that introduces a backdoor, steals credentials, or exfiltrates data.

- **Likelihood:** LOW to MEDIUM (increasing trend in the industry)
- **Impact:** CRITICAL (full system compromise through trusted code)
- **Risk Level:** HIGH
- **Countermeasures:** Pin all dependency versions. Verify package checksums. Use pip-audit, safety, and Snyk for vulnerability scanning. Minimal dependencies -- only include what is strictly necessary. Review changelogs before updating dependencies. Use official Docker base images only.

### 2.4 Operational Threats

Operational threats arise from the normal operation and maintenance of the system.

**Accidental Deletion.** An operator accidentally drops a database table, deletes a VM, or removes a critical configuration file.

- **Likelihood:** LOW to MEDIUM (higher during manual maintenance)
- **Impact:** HIGH (data loss, service outage)
- **Risk Level:** MEDIUM
- **Countermeasures:** ZFS snapshots every 15 minutes (point-in-time recovery). Daily backups with 30-day retention. Database users for services have no DROP or TRUNCATE permissions. Proxmox protection flags on critical VMs (prevent accidental deletion). Change management process for all manual operations.

**Configuration Errors.** Deploying an incorrect configuration that causes services to malfunction, connect to the wrong endpoints, or use incorrect parameters.

- **Likelihood:** MEDIUM
- **Impact:** MEDIUM to HIGH (incorrect trading behavior, service outages)
- **Risk Level:** MEDIUM
- **Countermeasures:** Configuration validation at service startup. Paper trading environment for testing configuration changes before live deployment. Rollback capability via Docker image versioning and VM snapshots. Configuration changes logged in the audit trail.

**Runaway Trading.** A software bug, misconfigured risk parameter, or corrupted model that causes the system to execute an excessive number of trades, trade with inappropriate position sizes, or trade in a single direction without regard to risk limits.

- **Likelihood:** LOW to MEDIUM
- **Impact:** CRITICAL (rapid capital destruction)
- **Risk Level:** HIGH
- **Countermeasures:** Multi-layer risk management: per-trade size limits, daily loss limits, maximum open positions, maximum drawdown circuit breaker, kill switch. All limits enforced at both the Algo Engine level and the MT5 Bridge level (defense in depth). Rate limiting on order submission. Monitoring alerts for unusual trading patterns.

### 2.5 Physical Threats

**Server Theft.** An attacker who gains physical access to the server can steal the drives, extract the VMs, and access all data including encrypted data if the encryption keys are also on the stolen drives.

- **Likelihood:** LOW (server in a controlled location)
- **Impact:** CRITICAL (complete data and credential exposure)
- **Risk Level:** MEDIUM
- **Countermeasures:** ZFS encryption with AES-256-GCM. Encryption keys not stored on the same drives as the encrypted data (loaded from a separate, secure source at boot). Physical access controls. Hardware security considerations documented below.

**Hardware Failure.** Disk failure, memory failure, power supply failure, motherboard failure, or fan failure leading to thermal shutdown.

- **Likelihood:** MEDIUM (hardware fails eventually)
- **Impact:** HIGH (service outage, potential data corruption)
- **Risk Level:** MEDIUM
- **Countermeasures:** ZFS mirroring for data integrity. UPS for power continuity. Hardware health monitoring (SMART, temperature sensors). Spare hardware for critical components. DR plan with RTO of 4 hours.

**Power Loss.** Extended power outage beyond UPS capacity.

- **Likelihood:** LOW to MEDIUM (depends on location and grid reliability)
- **Impact:** MEDIUM (graceful shutdown if UPS signals; abrupt shutdown if UPS fails)
- **Risk Level:** MEDIUM
- **Countermeasures:** UPS with NUT (Network UPS Tools) integration for automated graceful shutdown. ZFS and PostgreSQL WAL ensure data integrity through abrupt shutdowns. Broker-side stop-losses protect open positions during extended outages.

### 2.6 Attack Surface Analysis

The attack surface of MONEYMAKER can be divided into four domains:

**Network Attack Surface:**

- WireGuard VPN endpoint (single UDP port, exposed to internet)
- Outbound connections to broker servers (MT5 protocol over TCP)
- Outbound connections to data providers (WebSocket, REST over HTTPS)
- Internal inter-VM communication (gRPC, ZeroMQ, PostgreSQL, Redis)

**Application Attack Surface:**

- Proxmox web UI (port 8006, VPN-only)
- Grafana dashboard (port 3000, MGMT and GUEST VLANs)
- Custom Streamlit dashboard (port 8501, MGMT and GUEST VLANs)
- gRPC endpoints on each service
- Prometheus metrics endpoints (port 9090 variants, DATA VLAN only)

**Data Attack Surface:**

- PostgreSQL database (broker credentials, trade history, strategy configurations)
- Redis cache (current positions, recent signals)
- ZFS filesystems (VM disk images, backups)
- Strategy artifacts (configuration files, calibration parameters)
- Audit logs (system activity records)

**Physical Attack Surface:**

- Server hardware (physical access to drives, USB ports, console)
- Network equipment (switch, router, cables)
- UPS (power supply chain)

### 2.7 STRIDE Analysis per Service

| Service | Spoofing | Tampering | Repudiation | Info Disclosure | DoS | Elevation |
|---------|----------|-----------|-------------|-----------------|-----|-----------|
| **Data Ingestion** | Fake data source sends malicious data | Modified market data in transit | Service denies sending bad data | Market data intercepted | Flood of fake data overwhelms ingestion | Compromised ingestion writes to unauthorized tables |
| **Database** | Unauthorized client connects | Data modified at rest or in transit | Audit log entries deleted | Query results intercepted | Resource exhaustion via expensive queries | DB user escalates to superuser |
| **Algo Engine** | Spoofed signals sent to MT5 Bridge | Strategy parameters tampered | Engine denies generating a signal | Strategy logic leaked | CPU exhaustion prevents signal generation | Engine process gains root access |
| **MT5 Bridge** | Fake signal causes unauthorized trade | Trade parameters modified in transit | Bridge denies executing a trade | Broker credentials leaked | Bridge overwhelmed, cannot execute | Bridge gains broker admin access |
| **Monitoring** | Fake metrics hide real problems | Alert rules tampered to suppress alerts | Dashboard shows false history | Performance data leaked to competitors | Dashboard overwhelmed, operator blind | Dashboard gains write access to trading systems |

### 2.8 Risk Assessment Matrix

| Risk Level | Likelihood | Impact | Response |
|------------|-----------|--------|----------|
| **CRITICAL** | Any | CRITICAL | Immediate mitigation required. No deployment without countermeasures. |
| **HIGH** | HIGH | HIGH | Mitigation required before production. Accept residual risk with monitoring. |
| **MEDIUM** | MEDIUM | MEDIUM | Mitigation planned. Monitor and review quarterly. |
| **LOW** | LOW | LOW | Accept with documentation. Review annually. |

---

## 3. Network Security

### 3.1 VLAN Architecture

The MONEYMAKER infrastructure is segmented into four VLANs, each serving a distinct purpose with distinct security requirements. VLANs are enforced at the Proxmox virtual switch level, providing Layer 2 isolation between segments. Traffic between VLANs must traverse the Proxmox firewall, where it is subject to explicit allow rules.

```
+============================================================================+
|                        PROXMOX VE HOST                                     |
|                                                                            |
|   +--------------------------+    +--------------------------+             |
|   |    VLAN 10 (MGMT)       |    |    VLAN 20 (TRADE)       |             |
|   |    10.10.10.0/24         |    |    10.20.20.0/24         |             |
|   |                          |    |                          |             |
|   |  - Proxmox Web UI        |    |  - MT5 Bridge VM         |             |
|   |  - SSH Access Point      |    |  - Broker Connections    |             |
|   |  - WireGuard VPN         |    |  - OUTBOUND ONLY         |             |
|   |  - Grafana Dashboard     |    |  - No inbound from       |             |
|   |  - Alertmanager          |    |    internet               |             |
|   +-----------+--------------+    +-----------+--------------+             |
|               |                               |                            |
|               |   Proxmox Firewall            |                            |
|               +-------------------------------+                            |
|               |                               |                            |
|   +-----------+--------------+    +-----------+--------------+             |
|   |    VLAN 30 (DATA)        |    |    VLAN 40 (GUEST)       |             |
|   |    10.30.30.0/24         |    |    10.40.40.0/24         |             |
|   |                          |    |                          |             |
|   |  - PostgreSQL + Redis    |    |  - Read-Only Dashboard   |             |
|   |  - Algo Engine           |    |  - Guest Monitoring      |             |
|   |                          |    |  - No access to          |             |
|   |  - Data Ingestion        |    |    TRADE or DATA VLANs   |             |
|   |  - NO INTERNET ACCESS    |    |                          |             |
|   +--------------------------+    +--------------------------+             |
|                                                                            |
+============================================================================+
```

**VLAN 10 (MGMT) -- Management Network.** This VLAN hosts the management interfaces: Proxmox web UI, SSH access to all VMs (via jump host), WireGuard VPN endpoint, Grafana, and Alertmanager. Access to this VLAN is restricted to the WireGuard VPN. No services on this VLAN are directly reachable from the public internet. Only trusted administrators who possess the WireGuard private key and pass 2FA can reach this VLAN.

**VLAN 20 (TRADE) -- Trading Network.** This VLAN hosts the MT5 Bridge and its outbound connections to broker servers. The defining characteristic of this VLAN is that it allows outbound connections to the broker but allows no inbound connections from the internet. Internal traffic to this VLAN is restricted to gRPC signals from the Algo Engine (VLAN 30) and monitoring scrapes from Prometheus (VLAN 10). The MT5 Bridge is the only service with a legitimate need to communicate with external financial infrastructure, and this VLAN ensures that communication path is isolated.

**VLAN 30 (DATA) -- Internal Data Network.** This VLAN hosts all internal services: PostgreSQL, Redis, the Algo Engine, and the Data Ingestion Service. This VLAN has no direct internet access. Outbound internet connections for the Data Ingestion Service (to reach exchange APIs) are routed through a NAT gateway on the MGMT VLAN with strict destination whitelisting. All inter-service communication (database queries, cache operations, ZeroMQ data feeds, gRPC requests) occurs within this VLAN.

**VLAN 40 (GUEST) -- Guest Monitoring Network.** This VLAN provides read-only access to monitoring dashboards for observers who do not need administrative access. The GUEST VLAN can reach Grafana and the Streamlit dashboard (via proxied connections from the MGMT VLAN) but cannot reach any service on the TRADE or DATA VLANs directly. This VLAN exists to provide visibility without granting access to sensitive systems.

### 3.2 Firewall Rules

The default firewall policy for MONEYMAKER is DROP ALL. Every packet that does not match an explicit allow rule is silently dropped. This applies to all directions: inbound, outbound, and forwarded. Each allowed traffic flow is documented, justified, and implemented as a specific rule.

#### VLAN 10 (MGMT) Firewall Rules

| # | Direction | Source | Destination | Protocol | Port | Action | Purpose |
|---|-----------|--------|-------------|----------|------|--------|---------|
| M1 | IN | WireGuard tunnel | MGMT VLAN | TCP | 8006 | ALLOW | Proxmox web UI access |
| M2 | IN | WireGuard tunnel | MGMT VLAN | TCP | 22 | ALLOW | SSH access to jump host |
| M3 | IN | WireGuard tunnel | MGMT VLAN | TCP | 3000 | ALLOW | Grafana dashboard |
| M4 | IN | WireGuard tunnel | MGMT VLAN | TCP | 9093 | ALLOW | Alertmanager UI |
| M5 | IN | WireGuard tunnel | MGMT VLAN | TCP | 8501 | ALLOW | Streamlit dashboard |
| M6 | IN | Any | MGMT VLAN | UDP | 51820 | ALLOW | WireGuard VPN endpoint |
| M7 | OUT | MGMT VLAN | Any | TCP | 443 | ALLOW | HTTPS for updates, Let's Encrypt |
| M8 | OUT | MGMT VLAN | Any | UDP | 53 | ALLOW | DNS resolution |
| M9 | OUT | MGMT VLAN | Any | TCP | 53 | ALLOW | DNS resolution (TCP fallback) |
| M10 | OUT | MGMT VLAN | DATA VLAN | TCP | 9090-9099 | ALLOW | Prometheus scraping targets |
| M11 | OUT | MGMT VLAN | TRADE VLAN | TCP | 9090-9099 | ALLOW | Prometheus scraping MT5 Bridge |
| M12 | FWD | GUEST VLAN | MGMT VLAN | TCP | 3000 | ALLOW | Guest access to Grafana |
| M13 | FWD | GUEST VLAN | MGMT VLAN | TCP | 8501 | ALLOW | Guest access to Streamlit |
| M99 | ANY | Any | Any | Any | Any | DROP | Default deny (implicit) |

#### VLAN 20 (TRADE) Firewall Rules

| # | Direction | Source | Destination | Protocol | Port | Action | Purpose |
|---|-----------|--------|-------------|----------|------|--------|---------|
| T1 | IN | DATA VLAN (Algo Engine) | MT5 Bridge | TCP | 50051 | ALLOW | gRPC trading signals |
| T2 | IN | MGMT VLAN (Prometheus) | MT5 Bridge | TCP | 9091 | ALLOW | Metrics scraping |
| T3 | OUT | MT5 Bridge | Broker servers | TCP | 443,444,1950 | ALLOW | MT5 broker connection |
| T4 | OUT | MT5 Bridge | DATA VLAN (DB) | TCP | 5432 | ALLOW | Trade result logging |
| T5 | OUT | MT5 Bridge | DATA VLAN (Redis) | TCP | 6379 | ALLOW | State updates |
| T99 | ANY | Any | Any | Any | Any | DROP | Default deny (implicit) |

#### VLAN 30 (DATA) Firewall Rules

| # | Direction | Source | Destination | Protocol | Port | Action | Purpose |
|---|-----------|--------|-------------|----------|------|--------|---------|
| D1 | IN | DATA VLAN | PostgreSQL | TCP | 5432 | ALLOW | Database queries (internal) |
| D2 | IN | DATA VLAN | Redis | TCP | 6379 | ALLOW | Cache and pub/sub (internal) |
| D3 | IN | TRADE VLAN | PostgreSQL | TCP | 5432 | ALLOW | MT5 Bridge trade logging |
| D4 | IN | TRADE VLAN | Redis | TCP | 6379 | ALLOW | MT5 Bridge state updates |
| D5 | IN | MGMT VLAN | DATA VLAN | TCP | 9090-9099 | ALLOW | Prometheus scraping |
| D6 | IN | MGMT VLAN | DATA VLAN | TCP | 22 | ALLOW | SSH from jump host |
| D7 | OUT | Data Ingestion | Whitelisted IPs | TCP | 443 | ALLOW | Exchange API connections |
| D8 | OUT | Data Ingestion | Whitelisted IPs | TCP | 80 | ALLOW | REST API fallback |
| D9 | OUT | Any DATA VLAN | MGMT VLAN (DNS) | UDP | 53 | ALLOW | DNS resolution |
| D99 | ANY | Any | Any | Any | Any | DROP | Default deny (implicit) |

#### VLAN 40 (GUEST) Firewall Rules

| # | Direction | Source | Destination | Protocol | Port | Action | Purpose |
|---|-----------|--------|-------------|----------|------|--------|---------|
| G1 | OUT | GUEST VLAN | MGMT VLAN | TCP | 3000 | ALLOW | Grafana access |
| G2 | OUT | GUEST VLAN | MGMT VLAN | TCP | 8501 | ALLOW | Streamlit access |
| G3 | OUT | GUEST VLAN | MGMT VLAN (DNS) | UDP | 53 | ALLOW | DNS resolution |
| G99 | ANY | Any | Any | Any | Any | DROP | Default deny (implicit) |

#### Rate Limiting and SYN Flood Protection

All externally reachable ports (WireGuard UDP 51820) are protected by rate limiting at the firewall level. The following nftables rules are applied on the Proxmox host:

```nft
table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;

        # Allow established and related connections
        ct state established,related accept

        # Rate limit WireGuard (UDP 51820)
        udp dport 51820 limit rate 100/second burst 200 packets accept
        udp dport 51820 drop

        # SYN flood protection for all TCP services
        tcp flags syn limit rate 50/second burst 100 packets accept
        tcp flags syn drop

        # ICMP rate limiting (allow ping but prevent flood)
        icmp type echo-request limit rate 5/second burst 10 packets accept
        icmp type echo-request drop

        # Allow loopback
        iif lo accept
    }

    chain forward {
        type filter hook forward priority 0; policy drop;

        # Allow established and related forwarded connections
        ct state established,related accept

        # Inter-VLAN rules are defined per the tables above
        # Each rule is implemented as a specific nftables rule
        # with source/destination VLAN interface matching
    }
}
```

### 3.3 Network Segmentation Enforcement

Network segmentation is not merely a recommendation -- it is an enforced architectural constraint. Each VM is assigned to exactly one VLAN, and the Proxmox virtual switch does not permit traffic to cross VLAN boundaries without passing through the firewall. The following table documents which VMs reside on which VLANs:

| VM | Service | VLAN | IP Address | Internet Access |
|----|---------|------|------------|-----------------|
| proxmox-host | Proxmox VE | MGMT (10) | 10.10.10.1 | Yes (updates, VPN) |
| vm-100 | Data Ingestion (Go) | DATA (30) | 10.30.30.100 | Restricted (whitelisted IPs only) |
| vm-101 | Algo Engine | DATA (30) | 10.30.30.101 | No |
| vm-103 | PostgreSQL + Redis | DATA (30) | 10.30.30.103 | No |
| vm-104 | MT5 Bridge | TRADE (20) | 10.20.20.104 | Restricted (broker servers only) |
| vm-105 | Monitoring (Prometheus/Grafana) | MGMT (10) | 10.10.10.105 | No |
| vm-106 | Guest Dashboard | GUEST (40) | 10.40.40.106 | No |

Key isolation constraints:

- **Database VM (vm-103)** is only accessible from the DATA VLAN (services that need it) and the TRADE VLAN (MT5 Bridge for logging trades). It is not accessible from MGMT or GUEST VLANs directly. Administrative database access is performed by SSH-ing to the jump host on MGMT, then SSH-ing to vm-103 on DATA.
- **MT5 Bridge (vm-104)** is only accessible from the Algo Engine (gRPC signals on TRADE VLAN) and Prometheus (metrics scraping from MGMT VLAN). It cannot be reached from the GUEST VLAN.
- **Algo Engine (vm-101)** is isolated on the DATA VLAN. It communicates outbound to the MT5 Bridge (TRADE VLAN) via gRPC and to the Database (DATA VLAN) via SQL and Redis. It has no internet access.
- **Monitoring Dashboard** on the GUEST VLAN can only see Grafana and Streamlit through firewall-forwarded connections. It has no visibility into the underlying infrastructure.

### 3.4 TLS and mTLS

All inter-service communication within MONEYMAKER is encrypted using TLS 1.3. Services that communicate with each other use mutual TLS (mTLS), where both the client and the server present X.509 certificates to authenticate each other.

**Internal Certificate Authority.** MONEYMAKER operates its own internal Certificate Authority (CA) for issuing certificates to services. The CA root key is generated offline, stored encrypted, and used only to sign intermediate CA certificates. The intermediate CA is used for day-to-day certificate issuance. This approach avoids dependency on external certificate authorities for internal communication and ensures that only certificates issued by the MONEYMAKER CA are trusted within the ecosystem.

**Certificate Hierarchy:**

```
MONEYMAKER Root CA (offline, encrypted, AES-256)
    |
    +-- MONEYMAKER Intermediate CA (online, used for signing)
            |
            +-- data-ingestion.moneymaker.internal
            +-- algo-engine.moneymaker.internal
            +-- mt5-bridge.moneymaker.internal
            +-- postgresql.moneymaker.internal
            +-- redis.moneymaker.internal
            +-- prometheus.moneymaker.internal
            +-- grafana.moneymaker.internal
```

**Certificate Specifications:**

- Algorithm: ECDSA P-256 (for service certificates), RSA 4096 (for CA certificates)
- Validity: 365 days for service certificates, 10 years for Root CA, 3 years for Intermediate CA
- Key Usage: Digital Signature, Key Encipherment
- Extended Key Usage: Server Authentication, Client Authentication (for mTLS)
- Subject Alternative Names: Include both DNS name and IP address for each service

**Certificate Rotation Schedule:**

- Service certificates: Renewed automatically 30 days before expiry using a cron job that requests a new certificate from the Intermediate CA
- Intermediate CA: Renewed manually every 2 years (well before the 3-year expiry)
- Root CA: Renewed every 8 years (well before the 10-year expiry)

**TLS Configuration for Services:**

PostgreSQL (`postgresql.conf`):

```ini
ssl = on
ssl_cert_file = '/etc/ssl/certs/postgresql.moneymaker.internal.crt'
ssl_key_file = '/etc/ssl/private/postgresql.moneymaker.internal.key'
ssl_ca_file = '/etc/ssl/certs/moneymaker-ca-chain.crt'
ssl_min_protocol_version = 'TLSv1.3'
```

PostgreSQL (`pg_hba.conf`) -- require client certificates:

```
hostssl  all  all  10.30.30.0/24  cert  clientcert=verify-full
hostssl  all  all  10.20.20.0/24  cert  clientcert=verify-full
```

Redis (`redis.conf`):

```ini
tls-port 6379
port 0
tls-cert-file /etc/ssl/certs/redis.moneymaker.internal.crt
tls-key-file /etc/ssl/private/redis.moneymaker.internal.key
tls-ca-cert-file /etc/ssl/certs/moneymaker-ca-chain.crt
tls-auth-clients yes
tls-protocols "TLSv1.3"
```

### 3.5 VPN Access

Remote administration of MONEYMAKER is performed exclusively through a WireGuard VPN tunnel. There is no direct SSH from the internet, no exposed web interfaces, and no port forwarding to internal services.

**WireGuard Configuration:**

```ini
# /etc/wireguard/wg0.conf on Proxmox host

[Interface]
Address = 10.10.10.1/24
ListenPort = 51820
PrivateKey = <PROXMOX_PRIVATE_KEY>
PostUp = nft add rule inet filter input udp dport 51820 accept
PostDown = nft delete rule inet filter input udp dport 51820 accept

[Peer]
# Administrator laptop
PublicKey = <ADMIN_PUBLIC_KEY>
PresharedKey = <PRESHARED_KEY>
AllowedIPs = 10.10.10.2/32
```

**VPN Security Properties:**

- **Authentication:** WireGuard uses Curve25519 key pairs. Authentication requires possession of the private key. An additional pre-shared key (PSK) adds a layer of post-quantum resistance.
- **Encryption:** ChaCha20-Poly1305 for all tunnel traffic.
- **No attack surface when idle:** WireGuard does not respond to unauthenticated packets. A port scan of the WireGuard port returns nothing -- the port appears closed to anyone without a valid key pair.
- **Peer limit:** Only explicitly configured peers can connect. There is no concept of "open registration."

---

## 4. Authentication and Authorization

### 4.1 Service-to-Service Authentication

All inter-service communication uses mTLS certificates as the primary authentication mechanism, supplemented by API tokens for application-level identity verification.

**mTLS Flow:**

1. Service A (client) connects to Service B (server).
2. Service B presents its TLS certificate. Service A verifies it against the MONEYMAKER CA chain.
3. Service B requests Service A's client certificate. Service A presents it.
4. Service B verifies Service A's certificate against the MONEYMAKER CA chain.
5. Both sides are now authenticated. The TLS session is established.
6. Service A includes an API token in the request header (gRPC metadata or HTTP header).
7. Service B validates the API token against its local token store and checks the associated permissions.

The dual authentication (mTLS certificate + API token) provides defense in depth. A stolen API token cannot be used from a host that does not have the corresponding mTLS certificate. A compromised mTLS certificate cannot access services without a valid API token.

### 4.2 Human Access Authentication

**SSH Access:**

- Password authentication is disabled on all VMs (`PasswordAuthentication no` in `sshd_config`)
- Only key-based authentication is permitted (`PubkeyAuthentication yes`)
- SSH keys must be ED25519 or RSA 4096-bit minimum
- SSH agent forwarding is disabled to prevent key theft from compromised intermediate hosts
- Root login via SSH is disabled (`PermitRootLogin no`)
- SSH access is only possible through the WireGuard VPN to the jump host on MGMT VLAN, then to individual VMs from the jump host

**Proxmox Web UI:**

- Accessible only via WireGuard VPN
- Local accounts with TOTP (Time-based One-Time Password) 2FA
- Session timeout: 30 minutes of inactivity
- Maximum concurrent sessions: 2 per user
- All login attempts logged with source IP and timestamp

**Grafana Dashboard:**

- Username/password authentication with TOTP 2FA
- OAuth2/OIDC integration available for future use
- Session timeout: 60 minutes of inactivity
- Anonymous access disabled
- API keys for programmatic access (with scoped permissions)

**Streamlit Dashboard:**

- Proxied through reverse proxy with HTTP Basic Authentication over TLS
- Read-only data access only
- No administrative functions exposed

### 4.3 Role-Based Access Control (RBAC)

MONEYMAKER defines four roles, each with explicitly enumerated permissions:

**Admin:**

- Full access to all systems: Proxmox, SSH, databases, dashboards, configurations
- Can modify firewall rules, create VMs, manage certificates
- Can trigger kill switch, modify risk parameters, promote models
- Can access secrets manager and rotate credentials
- Can view and query audit logs
- Maximum of 2 Admin accounts

**Operator:**

- Can view all dashboards and metrics
- Can trigger the kill switch (emergency stop trading)
- Can view audit logs and generate reports
- Cannot modify AI model parameters or promote models
- Cannot access secrets manager directly
- Cannot modify firewall rules or VM configurations
- Cannot modify database schemas

**Viewer:**

- Read-only access to Grafana dashboards and Streamlit dashboard
- Cannot trigger any actions
- Cannot view detailed trade parameters or broker credentials
- Suitable for observers or stakeholders

**Service:**

- Automated service accounts for inter-service communication
- Each service has its own account with specific database permissions
- No interactive login capability
- Permissions are the minimum required for the service's function

| Permission | Admin | Operator | Viewer | Service |
|-----------|-------|----------|--------|---------|
| Proxmox management | YES | NO | NO | NO |
| SSH to any VM | YES | Jump host only | NO | NO |
| View dashboards | YES | YES | YES | NO |
| Trigger kill switch | YES | YES | NO | NO |
| Modify AI parameters | YES | NO | NO | NO |
| Promote models | YES | NO | NO | NO |
| Rotate secrets | YES | NO | NO | NO |
| View audit logs | YES | YES | NO | NO |
| Modify firewall rules | YES | NO | NO | NO |
| Database: SELECT | YES | YES (read-only) | NO | Per-service |
| Database: INSERT | YES | NO | NO | Per-service |
| Database: UPDATE | YES | NO | NO | Per-service (limited) |
| Database: DELETE | YES | NO | NO | NO (except cleanup jobs) |
| Database: DDL | YES | NO | NO | NO |

### 4.4 Session Management and Lockout

**Session Timeout:**

- Proxmox web UI: 30 minutes inactivity
- Grafana: 60 minutes inactivity
- SSH: 15 minutes inactivity (`ClientAliveInterval 300`, `ClientAliveCountMax 3`)
- WireGuard: Persistent (keys do not expire, but can be revoked)

**Failed Login Lockout:**

- SSH: fail2ban monitors `/var/log/auth.log`. After 5 failed attempts within 10 minutes, the source IP is banned for 15 minutes. After 15 cumulative failed attempts, the IP is banned for 24 hours.
- Proxmox UI: Built-in lockout after 5 failed attempts for 15 minutes.
- Grafana: fail2ban monitors Grafana logs. Same thresholds as SSH.
- All lockout events are logged to the audit trail and trigger an alert in Alertmanager.

---

## 5. Secrets Management

### 5.1 Secrets Architecture

MONEYMAKER uses a layered secrets management approach. For V1, the primary mechanism is SOPS (Secrets OPerationS) combined with age encryption, which provides encrypted-at-rest secrets that can be decrypted at deployment time and injected into services as environment variables. This approach balances security with operational simplicity -- it does not require running a dedicated secrets server (like HashiCorp Vault) but provides meaningful protection over plaintext configuration files.

For future versions, migration to HashiCorp Vault is planned when operational maturity justifies the additional complexity.

```
+=========================================================================+
|                    SECRETS MANAGEMENT ARCHITECTURE                       |
|                                                                         |
|   +-------------------+    +-------------------+    +----------------+  |
|   | SOPS-encrypted    |    | Deployment Script |    | Running        |  |
|   | secrets files     |--->| (decrypts with    |--->| Service        |  |
|   | (in Git repo)     |    |  age private key) |    | (env vars)     |  |
|   +-------------------+    +-------------------+    +----------------+  |
|          |                        |                        |            |
|   Encrypted at rest        Key stored in           Secrets in memory   |
|   AES-256 via age          operator's keyring      only, not on disk   |
|                            or HSM                                       |
+=========================================================================+
```

### 5.2 Secrets Inventory

Every secret in the MONEYMAKER ecosystem is cataloged, classified, and assigned a rotation schedule:

| Secret | Classification | Storage | Rotation | Access |
|--------|---------------|---------|----------|--------|
| MT5 broker login | CRITICAL | SOPS/age | 90 days | MT5 Bridge only |
| MT5 broker password | CRITICAL | SOPS/age | 90 days | MT5 Bridge only |
| MT5 broker server | SENSITIVE | SOPS/age | On change | MT5 Bridge only |
| PostgreSQL superuser password | CRITICAL | SOPS/age | 90 days | Admin only |
| PostgreSQL service passwords | SENSITIVE | SOPS/age | 90 days | Per-service |
| Redis password | SENSITIVE | SOPS/age | 90 days | All services |
| Exchange API keys (Binance, etc.) | SENSITIVE | SOPS/age | 30 days | Data Ingestion only |
| Exchange API secrets | CRITICAL | SOPS/age | 30 days | Data Ingestion only |
| Telegram bot token | SENSITIVE | SOPS/age | 180 days | Alertmanager only |
| TLS CA root private key | CRITICAL | Offline, encrypted USB | Never (10yr cert) | Admin only (offline) |
| TLS Intermediate CA key | CRITICAL | SOPS/age | 2 years | Cert renewal script only |
| TLS service certificate keys | SENSITIVE | Per-VM filesystem | 365 days (auto) | Per-service |
| WireGuard private keys | CRITICAL | Per-device keyring | On compromise | Per-device |
| ZFS encryption key | CRITICAL | Separate USB/TPM | Never (unless compromised) | Boot process only |
| age private key (SOPS decryption) | CRITICAL | Operator keyring | On compromise | Admin only |
| Grafana admin password | SENSITIVE | SOPS/age | 90 days | Admin only |

### 5.3 Secret Injection

Secrets are never stored in code, configuration files committed to version control, Docker images, or VM disk images. The injection flow is:

1. **At deployment time:** The deployment script (Ansible or shell script) decrypts the SOPS-encrypted secrets file using the operator's age private key.
2. **Injection into Docker:** Decrypted secrets are passed to Docker containers as environment variables via `docker run -e` or Docker Compose `environment:` directives. The environment variables exist only in the container's memory space and are not written to the container filesystem.
3. **Application consumption:** Services read secrets from environment variables at startup (e.g., `os.environ["DB_PASSWORD"]` in Python, `os.Getenv("DB_PASSWORD")` in Go).
4. **Cleanup:** The deployment script removes any temporary decrypted files from disk after injection.

**What is explicitly forbidden:**

- Hardcoded secrets in source code
- Secrets in `.env` files committed to version control
- Secrets in Docker image layers (no `ENV SECRET=value` in Dockerfiles)
- Secrets in Proxmox VM configuration notes
- Secrets logged to stdout, stderr, or log files
- Secrets in error messages or stack traces
- Secrets transmitted in URL query parameters

### 5.4 Secret Rotation Procedure

**Routine Rotation (scheduled):**

1. Generate new credential value (random, sufficient entropy: minimum 32 characters for passwords, 256-bit for keys)
2. Update the SOPS-encrypted secrets file with the new value
3. Apply the new credential to the target system (e.g., ALTER USER in PostgreSQL, update API key in exchange settings)
4. Re-deploy the affected service(s) with the new environment variable
5. Verify the service starts successfully and can authenticate
6. Log the rotation event in the audit trail (timestamp, which secret, who rotated, success/failure)
7. Monitor for authentication failures that might indicate the old credential is still cached somewhere

**Emergency Rotation (after suspected compromise):**

1. Immediately rotate the compromised credential (steps 1-5 above, executed with urgency)
2. Revoke the old credential at the target system (not just replace -- actively invalidate)
3. Review audit logs for unauthorized access using the compromised credential
4. If unauthorized access is confirmed, escalate to the incident response plan (Section 11)
5. Review how the compromise occurred and implement countermeasures to prevent recurrence
6. Document the incident in the post-mortem

### 5.5 Secret Access Audit

Every access to a secret is logged. The SOPS decryption command logs which file was decrypted, by which user, at what time, and from which host. At the application level, services log when they read environment variables containing secrets (logging the variable name, not the value) during startup. The audit log records:

```json
{
    "event_type": "secret_access",
    "timestamp": "2026-02-21T14:30:00Z",
    "actor": "deploy-script",
    "host": "proxmox-host",
    "action": "decrypt",
    "secret_file": "secrets/production.enc.yaml",
    "secret_keys_accessed": ["db_password", "redis_password", "mt5_login"],
    "result": "success"
}
```

---

## 6. Data Security

### 6.1 Encryption at Rest

**ZFS Native Encryption.** All ZFS datasets on the Proxmox host are encrypted with AES-256-GCM. This encryption is transparent to applications -- VMs read and write data normally, and the encryption/decryption is handled by ZFS at the block level. The encryption key is loaded at boot time from a separate source (USB key or TPM, depending on the hardware configuration) and remains in kernel memory for the lifetime of the system.

```bash
# ZFS dataset creation with encryption
zfs create -o encryption=aes-256-gcm \
           -o keylocation=file:///root/zfs.key \
           -o keyformat=raw \
           rpool/data

# Verify encryption status
zfs get encryption,keystatus rpool/data
# NAME         PROPERTY     VALUE          SOURCE
# rpool/data   encryption   aes-256-gcm    local
# rpool/data   keystatus    available      -
```

**Database-Level Encryption.** Sensitive columns in PostgreSQL (specifically, any column that stores broker credentials or API keys) use pgcrypto for column-level encryption. This provides an additional layer of protection: even if an attacker gains access to the database (through SQL injection, a compromised service account, or a stolen backup), the encrypted columns remain unreadable without the pgcrypto encryption key.

```sql
-- Example: encrypting broker credentials
CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO broker_credentials (broker_name, encrypted_login, encrypted_password)
VALUES (
    'primary_broker',
    pgp_sym_encrypt('12345678', current_setting('app.encryption_key')),
    pgp_sym_encrypt('s3cur3P@ss', current_setting('app.encryption_key'))
);

-- Decryption requires the key
SELECT broker_name,
       pgp_sym_decrypt(encrypted_login::bytea,
                       current_setting('app.encryption_key')) AS login,
       pgp_sym_decrypt(encrypted_password::bytea,
                       current_setting('app.encryption_key')) AS password
FROM broker_credentials;
```

**Encrypted Backups.** All backups (ZFS snapshots sent to external storage, PostgreSQL logical backups) are encrypted before leaving the Proxmox host. ZFS send/receive preserves the dataset encryption. PostgreSQL pg_dump output is encrypted with age before being written to the backup destination.

### 6.2 Encryption in Transit

All network communication within MONEYMAKER is encrypted:

| Communication Path | Protocol | Encryption | Authentication |
|-------------------|----------|------------|----------------|
| Admin laptop to Proxmox | WireGuard | ChaCha20-Poly1305 | Curve25519 keys |
| Service to PostgreSQL | PostgreSQL wire protocol | TLS 1.3 | Client certificates (mTLS) |
| Service to Redis | Redis protocol | TLS 1.3 | Client certificates + password |
| Algo Engine to MT5 Bridge | gRPC | TLS 1.3 | mTLS certificates + API token |
| Data Ingestion to Algo Engine | ZeroMQ | TLS 1.3 (CurveZMQ) | ZeroMQ CURVE certificates |
| Prometheus to services | HTTP | TLS 1.3 | mTLS certificates |
| Data Ingestion to exchanges | WebSocket/HTTPS | TLS 1.2+ | Server certificate validation |
| MT5 Bridge to broker | MT5 protocol | Broker-provided encryption | MT5 login credentials |

### 6.3 Data Classification

All data in MONEYMAKER is classified into four tiers, each with specific handling requirements:

**CRITICAL -- Immediate financial or security impact if compromised:**

- Broker credentials (MT5 login, password, server)
- Encryption keys (ZFS key, age private key, CA root key)
- Account balances and equity
- WireGuard private keys
- Handling: Encrypted at rest (multiple layers), encrypted in transit, access logged, rotation enforced, never cached in plaintext, never logged

**SENSITIVE -- Significant impact if compromised:**

- Trading history (reveals strategy profitability and patterns)
- AI model weights (reveal proprietary trading logic)
- Performance data (reveals system capabilities)
- API keys for data providers
- Database service passwords
- Handling: Encrypted at rest (ZFS level), encrypted in transit, access controlled by RBAC, rotation scheduled

**INTERNAL -- Limited impact if compromised, but not intended for external access:**

- Market data (publicly available but aggregated collection has value)
- System configuration (reveals architecture details)
- Application logs (may reveal operational patterns)
- Prometheus metrics
- Handling: Encrypted at rest (ZFS level), encrypted in transit, access controlled by VLAN, no special rotation

**PUBLIC -- No impact if disclosed:**

- Nothing. MONEYMAKER has no public-facing data. Even the existence and nature of the system should be treated as INTERNAL information.

### 6.4 Data Retention Policy

| Data Type | Hot Storage | Cold Storage | Archive | Total Retention |
|-----------|------------|-------------|---------|-----------------|
| Trading decisions and signals | 90 days (PostgreSQL) | 1 year (Parquet on ZFS) | 7 years (encrypted off-site) | 7 years |
| Trade execution records | 90 days (PostgreSQL) | 1 year (Parquet on ZFS) | 7 years (encrypted off-site) | 7 years |
| Market data (OHLCV) | 1 year (TimescaleDB) | Indefinite (compressed TimescaleDB) | N/A | Indefinite |
| Market data (tick) | 30 days (TimescaleDB) | 1 year (Parquet) | N/A | 1 year |
| Application logs | 90 days (filesystem) | 1 year (compressed) | 7 years (encrypted off-site) | 7 years |
| Audit logs | 90 days (PostgreSQL, queryable) | 7 years (Parquet on ZFS) | 7 years (encrypted off-site) | 7 years |
| Prometheus metrics | 90 days (high-res, 15s) | 1 year (aggregated, 5m) | N/A | 1 year |
| AI model artifacts | Current + 10 previous versions (filesystem) | Indefinite (versioned archive) | N/A | Indefinite |
| AI training data | 2 years (PostgreSQL) | Indefinite (Parquet) | N/A | Indefinite |

Retention periods for trading data and audit logs are set at 7 years to align with common financial regulatory retention requirements, even though MONEYMAKER V1 is a personal trading system. This conservative approach ensures that if regulatory requirements ever apply, the data is already available.

### 6.5 Data Backup Strategy

**ZFS Snapshots (Point-in-Time Recovery):**

- Frequency: Every 15 minutes
- Retention: 96 snapshots (24 hours of 15-minute granularity)
- Purpose: Rapid recovery from accidental deletion or corruption
- Recovery time: Seconds (ZFS rollback is nearly instantaneous)

**Daily Backups:**

- Method: ZFS send to secondary storage pool or Proxmox Backup Server (PBS)
- Frequency: Daily at 02:00 UTC (outside peak trading hours)
- Retention: 30 days
- Includes: Full VM disk images, PostgreSQL WAL archives
- Verification: Automated restore test on the first Sunday of each month

**Weekly Backups:**

- Method: Full ZFS send to off-site encrypted storage
- Frequency: Weekly (Sunday 04:00 UTC)
- Retention: 52 weeks
- Encryption: age-encrypted before transfer
- Transfer: Via rsync over SSH to remote backup server (or encrypted cloud storage)

**Monthly Backups:**

- Method: Full backup to separate physical media
- Frequency: Monthly (1st of the month, 04:00 UTC)
- Retention: 24 months
- Storage: Encrypted external drive, stored in a separate physical location

**Backup Verification:**

- Monthly: Full restore test of one randomly selected VM to a temporary VM slot
- Quarterly: Full DR test (restore all VMs, verify service connectivity, execute paper trades)
- Every restore test is documented in the audit log with results

---

## 7. Application Security

### 7.1 Input Validation

Every piece of data that enters MONEYMAKER from an external source is treated as untrusted and must be validated before processing. The validation strategy follows a "validate at the boundary, trust internally" pattern: data is rigorously validated at the point of entry (Data Ingestion Service for market data, MT5 Bridge for gRPC signals, dashboard for user input) and can be trusted by internal services after validation.

**Market Data Validation (Data Ingestion Service):**

```go
// Validation rules for incoming OHLCV data
func validateOHLCV(bar *OHLCVBar) error {
    // Price must be positive
    if bar.Open.LessThanOrEqual(decimal.Zero) ||
       bar.High.LessThanOrEqual(decimal.Zero) ||
       bar.Low.LessThanOrEqual(decimal.Zero) ||
       bar.Close.LessThanOrEqual(decimal.Zero) {
        return fmt.Errorf("price must be positive: %v", bar)
    }

    // High must be >= Open, Close, Low
    if bar.High.LessThan(bar.Open) || bar.High.LessThan(bar.Close) ||
       bar.High.LessThan(bar.Low) {
        return fmt.Errorf("high price inconsistency: %v", bar)
    }

    // Low must be <= Open, Close, High
    if bar.Low.GreaterThan(bar.Open) || bar.Low.GreaterThan(bar.Close) ||
       bar.Low.GreaterThan(bar.High) {
        return fmt.Errorf("low price inconsistency: %v", bar)
    }

    // Volume must be non-negative
    if bar.Volume.LessThan(decimal.Zero) {
        return fmt.Errorf("negative volume: %v", bar)
    }

    // Timestamp must be recent (within last 5 minutes for real-time data)
    if time.Since(bar.Timestamp) > 5*time.Minute {
        return fmt.Errorf("stale timestamp: %v", bar.Timestamp)
    }

    // Timestamp must not be in the future
    if bar.Timestamp.After(time.Now().Add(1 * time.Minute)) {
        return fmt.Errorf("future timestamp: %v", bar.Timestamp)
    }

    // Price change sanity check (no single bar should move > 20%)
    priceChange := bar.Close.Sub(bar.Open).Abs().Div(bar.Open)
    if priceChange.GreaterThan(decimal.NewFromFloat(0.20)) {
        return fmt.Errorf("suspicious price change (>20%%): %v", priceChange)
    }

    return nil
}
```

**Trading Signal Validation (MT5 Bridge):**

```python
from pydantic import BaseModel, validator, Field
from decimal import Decimal
from enum import Enum

class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class TradingSignal(BaseModel):
    signal_id: str = Field(..., min_length=36, max_length=36)  # UUID format
    symbol: str = Field(..., regex=r'^[A-Z]{6,10}$')
    direction: SignalDirection
    confidence: Decimal = Field(..., ge=0, le=1)
    suggested_lots: Decimal = Field(..., gt=0, le=10)  # Hard max 10 lots
    stop_loss: Decimal = Field(..., gt=0)
    take_profit: Decimal = Field(..., gt=0)
    model_version: str = Field(..., min_length=1, max_length=50)

    @validator('suggested_lots')
    def validate_lot_size(cls, v):
        if v > Decimal('10'):
            raise ValueError('Lot size exceeds maximum allowed (10)')
        return v

    @validator('stop_loss')
    def validate_stop_loss(cls, v, values):
        if 'direction' in values:
            # SL must be on the correct side of the current price
            # Additional validation happens with current market price
            pass
        return v
```

**SQL Injection Prevention.** All database queries use parameterized queries through SQLAlchemy ORM. Raw SQL string concatenation is explicitly prohibited. The SQLAlchemy session is configured with `autocommit=False` to prevent accidental data modification outside transactions.

```python
# CORRECT: Parameterized query
result = session.execute(
    text("SELECT * FROM trades WHERE symbol = :symbol AND timestamp > :start"),
    {"symbol": symbol, "start": start_time}
)

# FORBIDDEN: String concatenation (SQL injection vulnerable)
# result = session.execute(f"SELECT * FROM trades WHERE symbol = '{symbol}'")
```

### 7.2 Dependency Security

**Version Pinning.** All dependencies in every service are pinned to exact versions. Python services use `pip freeze > requirements.txt` with exact version specifications. Go services use `go.sum` for cryptographic verification of module contents. Docker images specify exact digest hashes, not just tags.

```
# requirements.txt -- exact pins, no ranges
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
redis==5.0.1
pydantic==2.5.3
torch==2.2.0+rocm5.7
grpcio==1.60.0
```

**Vulnerability Scanning.** Automated vulnerability scanning is performed on every dependency update and on a weekly schedule:

```bash
# Python dependency scanning
pip-audit --requirement requirements.txt --output json > audit_results.json
safety check --file requirements.txt --output json > safety_results.json

# Docker image scanning
trivy image --severity HIGH,CRITICAL moneymaker/algo-engine:latest
trivy image --severity HIGH,CRITICAL moneymaker/mt5-bridge:latest
trivy image --severity HIGH,CRITICAL moneymaker/data-ingestion:latest

# Go module vulnerability check
govulncheck ./...
```

**Dependency Update Schedule:**

- Weekly: Automated vulnerability scan. If CRITICAL vulnerabilities are found, update immediately.
- Monthly: Review all available updates. Test in paper trading environment. Deploy if tests pass.
- On-demand: If a zero-day vulnerability is disclosed in a critical dependency (e.g., gRPC, PostgreSQL driver), patch within 24 hours.

**Minimal Dependencies.** Each service includes only the dependencies it strictly requires. No "utility" packages that provide broad functionality when only one function is needed. The attack surface of the supply chain is proportional to the number of dependencies, so minimizing dependencies directly reduces supply chain risk.

### 7.3 Code Security

**Static Analysis.** Python code is analyzed with bandit, which detects common security issues: use of `eval()`, `exec()`, `assert` statements used for validation (which are stripped in optimized mode), weak cryptographic functions, hardcoded passwords, and SQL injection patterns.

```bash
# Run bandit on all Python services
bandit -r services/ -f json -o bandit_results.json

# Expected: no HIGH or MEDIUM findings
```

**Secret Scanning.** gitleaks runs as a pre-commit hook and in the CI pipeline to detect accidentally committed secrets:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.1
    hooks:
      - id: gitleaks
```

**Prohibited Patterns.** The following code patterns are explicitly prohibited in MONEYMAKER and enforced through code review and static analysis:

- `eval()` or `exec()` -- no dynamic code execution
- `subprocess.Popen(..., shell=True)` -- no shell injection surface
- `pickle.loads()` on untrusted data -- no deserialization attacks
- `yaml.load()` without `Loader=yaml.SafeLoader` -- no YAML deserialization attacks
- `os.system()` -- use `subprocess.run()` with explicit arguments instead
- String formatting in SQL queries -- use parameterized queries only
- `requests.get(..., verify=False)` -- no TLS certificate bypass
- `DEBUG = True` in production configuration -- no debug mode in production
- Logging of secret values at any log level

---

## 8. Container and VM Security

### 8.1 Docker Security

**Base Images.** All Docker containers use official base images from Docker Hub or the official Python/Go image repositories. No community or third-party base images are permitted. Base images specify exact version tags with digest verification:

```dockerfile
# CORRECT: Official image with exact version
FROM python:3.11.7-slim-bookworm@sha256:abc123...

# FORBIDDEN: Latest tag (unpredictable content)
# FROM python:latest

# FORBIDDEN: Community image (unverified)
# FROM someuser/python-trading:v1
```

**Non-Root User.** All containers run as a non-root user. The Dockerfile creates a dedicated user with minimal permissions:

```dockerfile
# Create non-root user
RUN groupadd -r moneymaker && useradd -r -g moneymaker -d /app -s /sbin/nologin moneymaker

# Set working directory
WORKDIR /app

# Copy application code (owned by root, read-only for moneymaker)
COPY --chown=root:moneymaker . /app/

# Switch to non-root user
USER moneymaker

# Run application
CMD ["python", "-m", "algo_engine.main"]
```

**Read-Only Filesystem.** Containers that do not need to write to the filesystem are started with `--read-only`:

```yaml
# docker-compose.yml
services:
  algo-engine:
    image: moneymaker/algo-engine:v1.0.0
    read_only: true
    tmpfs:
      - /tmp:size=100M  # Writable tmpfs for temporary files
    security_opt:
      - no-new-privileges:true
```

**Resource Limits.** Every container has explicit CPU, memory, and PID limits to prevent resource exhaustion (whether from bugs or attacks):

```yaml
services:
  algo-engine:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
          pids: 256
        reservations:
          cpus: '2.0'
          memory: 4G
```

**Docker Socket.** The Docker socket (`/var/run/docker.sock`) is never mounted into any container. Access to the Docker socket grants root-equivalent access to the host, which would negate all container isolation.

**Image Scanning.** All Docker images are scanned with Trivy before deployment:

```bash
# Scan for vulnerabilities
trivy image --severity HIGH,CRITICAL --exit-code 1 moneymaker/algo-engine:v1.0.0

# A non-zero exit code blocks deployment
```

### 8.2 Proxmox VM Security

**VM Isolation.** Each VM is assigned to a single VLAN with a dedicated virtual network interface. VMs cannot communicate across VLANs without passing through the Proxmox firewall. VM-to-VM communication within the same VLAN is permitted but restricted by host-level firewalls.

**Minimal OS Installation.** VMs run Debian 12 (Bookworm) minimal installation with no desktop environment, no graphical packages, no development tools (except where required for the service). The installed package count is minimized to reduce the attack surface.

**Automatic Security Updates.** All VMs run `unattended-upgrades` configured to automatically install security updates from the Debian security repository:

```bash
# /etc/apt/apt.conf.d/50unattended-upgrades
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Mail "root";
```

Automatic reboot is disabled to prevent service disruption. Security updates that require a reboot are scheduled during maintenance windows.

**Host Firewall.** Each VM runs its own nftables firewall in addition to the Proxmox-level VLAN firewall. This provides defense in depth: even if the Proxmox firewall is misconfigured, the host firewall provides a second layer of protection.

**Disabled Unused Features:**

- USB passthrough: Disabled on all VMs except where explicitly required
- Serial ports: Disabled
- Audio devices: Disabled
- Clipboard sharing: Disabled
- Display: VNC only (for emergency console access), not accessible from network
- Ballooning: Enabled but with minimum memory set equal to allocation (prevents memory starvation)

**VM Protection Flags.** Critical VMs have Proxmox protection enabled, which prevents accidental deletion or modification through the Proxmox UI:

```bash
# Set protection on critical VMs
qm set 103 --protection 1  # Database VM
qm set 104 --protection 1  # MT5 Bridge VM
```

---

## 9. Audit Trail System

### 9.1 Immutable Audit Log Design

The audit trail is the authoritative, tamper-evident record of every significant event in the MONEYMAKER ecosystem. It is implemented as an append-only table in PostgreSQL with a SHA-256 hash chain that links each entry to its predecessor, making any modification or deletion detectable.

**Design Principles:**

- **Append-only:** The audit table permits INSERT only. UPDATE and DELETE are denied at the database permission level.
- **Hash chain:** Each entry includes the SHA-256 hash of the previous entry, creating a verifiable chain of integrity.
- **Comprehensive:** Every trading decision, risk event, system event, access event, and configuration change is recorded.
- **Queryable:** The hot audit log (90 days) is stored in PostgreSQL with indexes for efficient querying by event type, service, actor, and time range.
- **Durable:** Cold audit data is exported to Parquet files on ZFS with 7-year retention.

### 9.2 Audit Log Schema

```sql
CREATE TABLE audit_log (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sequence_num    BIGSERIAL NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type      TEXT NOT NULL,
    severity        TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    service         TEXT NOT NULL,
    actor           TEXT NOT NULL,       -- service name, username, or 'system'
    action          TEXT NOT NULL,
    resource        TEXT,                -- what was acted upon
    details         JSONB NOT NULL DEFAULT '{}',
    previous_hash   TEXT NOT NULL,       -- SHA-256 of previous entry
    entry_hash      TEXT NOT NULL,       -- SHA-256 of this entry
    source_ip       INET,
    correlation_id  UUID,               -- links related events across services
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_audit_timestamp ON audit_log (timestamp DESC);
CREATE INDEX idx_audit_event_type ON audit_log (event_type);
CREATE INDEX idx_audit_service ON audit_log (service);
CREATE INDEX idx_audit_actor ON audit_log (actor);
CREATE INDEX idx_audit_severity ON audit_log (severity);
CREATE INDEX idx_audit_correlation_id ON audit_log (correlation_id);
CREATE INDEX idx_audit_sequence ON audit_log (sequence_num);

-- Enforce append-only: audit service account can only INSERT
GRANT INSERT ON audit_log TO audit_writer;
REVOKE UPDATE, DELETE ON audit_log FROM audit_writer;
REVOKE TRUNCATE ON audit_log FROM audit_writer;

-- Read access for reporting
GRANT SELECT ON audit_log TO audit_reader;
REVOKE INSERT, UPDATE, DELETE ON audit_log FROM audit_reader;
```

### 9.3 Event Types

The audit system records the following event categories:

**Trading Events:**

- `SIGNAL_GENERATED`: Algo Engine produced a trading signal (includes symbol, direction, confidence, model version)
- `SIGNAL_VETOED`: Risk Manager vetoed a trading signal (includes reason for veto)
- `ORDER_SUBMITTED`: MT5 Bridge submitted an order to the broker (includes order parameters)
- `ORDER_FILLED`: Broker confirmed order execution (includes fill price, slippage)
- `ORDER_REJECTED`: Broker rejected the order (includes rejection reason)
- `POSITION_OPENED`: New position established (includes entry details)
- `POSITION_MODIFIED`: Stop-loss or take-profit modified (includes old and new values)
- `POSITION_CLOSED`: Position closed (includes exit details, P&L)

**Risk Events:**

- `CIRCUIT_BREAKER_TRIGGERED`: Daily loss limit or drawdown limit reached (includes threshold and current value)
- `KILL_SWITCH_ACTIVATED`: Emergency stop triggered by operator or automated rule
- `KILL_SWITCH_DEACTIVATED`: Trading resumed after kill switch
- `RISK_LIMIT_BREACH`: A risk parameter was exceeded (includes which parameter)
- `POSITION_SIZE_REDUCED`: Risk Manager reduced a signal's position size (includes original and reduced size)

**System Events:**

- `SERVICE_STARTED`: A service process started (includes version, configuration hash)
- `SERVICE_STOPPED`: A service process stopped (includes reason: normal, crash, kill)
- `SERVICE_HEALTH_CHECK`: Periodic health check result (includes status)
- `CONFIG_CHANGED`: Configuration parameter modified (includes parameter name, old value, new value)
- `MODEL_PROMOTED`: AI model promoted to production (includes model version, validation metrics)
- `MODEL_DEMOTED`: AI model removed from production (includes reason)
- `BACKUP_COMPLETED`: Scheduled backup finished (includes backup type, size, duration)
- `BACKUP_FAILED`: Scheduled backup failed (includes error details)

**Access Events:**

- `LOGIN_SUCCESS`: Successful authentication (includes user, source IP, method)
- `LOGIN_FAILED`: Failed authentication attempt (includes user, source IP, method)
- `LOGIN_LOCKED`: Account locked due to repeated failures (includes user, attempt count)
- `SECRET_ACCESSED`: Secret retrieved from secrets manager (includes secret name, accessor)
- `SECRET_ROTATED`: Secret value was rotated (includes secret name, rotator)
- `SSH_SESSION_OPENED`: SSH session established (includes user, source IP)
- `SSH_SESSION_CLOSED`: SSH session ended (includes user, duration)

### 9.4 Hash Chain Implementation

```python
import hashlib
import json
from datetime import datetime, timezone

def compute_entry_hash(entry: dict, previous_hash: str) -> str:
    """Compute SHA-256 hash for an audit log entry."""
    # Canonical representation: sorted keys, deterministic JSON
    hash_input = json.dumps({
        "sequence_num": entry["sequence_num"],
        "timestamp": entry["timestamp"].isoformat(),
        "event_type": entry["event_type"],
        "service": entry["service"],
        "actor": entry["actor"],
        "action": entry["action"],
        "details": entry["details"],
        "previous_hash": previous_hash,
    }, sort_keys=True, separators=(',', ':'))

    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

def verify_chain_integrity(entries: list) -> tuple[bool, int]:
    """Verify the hash chain integrity of audit log entries.

    Returns (is_valid, first_broken_sequence_num).
    """
    for i in range(1, len(entries)):
        expected_hash = compute_entry_hash(entries[i], entries[i-1]["entry_hash"])
        if entries[i]["entry_hash"] != expected_hash:
            return False, entries[i]["sequence_num"]

        if entries[i]["previous_hash"] != entries[i-1]["entry_hash"]:
            return False, entries[i]["sequence_num"]

    return True, -1
```

**Integrity Verification Schedule:**

- Automated daily verification at 06:00 UTC: verifies the hash chain for the previous 24 hours
- Automated weekly verification: verifies the entire hot audit log (90 days)
- Manual verification: on-demand through the Streamlit dashboard or CLI tool
- Any chain break triggers a CRITICAL alert via Alertmanager

### 9.5 Audit Log Storage Tiers

```
+============================================================================+
|                     AUDIT LOG STORAGE ARCHITECTURE                         |
|                                                                            |
|   HOT (0-90 days)          COLD (90 days - 7 years)     ARCHIVE (7 years) |
|   +------------------+    +---------------------+    +------------------+  |
|   | PostgreSQL       |    | Parquet files on     |    | Encrypted off-   |  |
|   | audit_log table  |--->| ZFS (compressed)     |--->| site storage     |  |
|   |                  |    |                      |    |                  |  |
|   | Full SQL query   |    | Queryable via DuckDB |    | Restore to query |  |
|   | capability       |    | or Pandas            |    | if needed        |  |
|   |                  |    |                      |    |                  |  |
|   | ~50MB/day        |    | ~5MB/day (compressed)|    | ~5MB/day (enc.)  |  |
|   +------------------+    +---------------------+    +------------------+  |
|                                                                            |
|   Transition: Automated cron job exports entries older than 90 days        |
|   to Parquet, verifies hash chain integrity, then deletes from PostgreSQL  |
+============================================================================+
```

### 9.6 Audit Reports

**Daily Trading Summary (automated, emailed via Telegram):**

- Total signals generated (by direction: BUY, SELL, HOLD)
- Signals vetoed by risk manager (with reasons)
- Orders submitted and filled (with slippage analysis)
- Positions opened and closed (with P&L)
- Risk events (circuit breaker triggers, limit breaches)
- Hash chain integrity verification result

**Weekly Security Report (automated):**

- Failed login attempts (by source IP, by username)
- Secret access events
- Configuration changes
- Service restarts and crashes
- Network anomalies detected
- Dependency vulnerability scan results

**Monthly Compliance Report (semi-automated, reviewed by Admin):**

- Complete trading activity summary with statistics
- Risk management effectiveness analysis
- Audit log integrity verification (full chain)
- Backup verification test results
- Security patch status across all VMs
- Open security findings and remediation status
- NIST CSF control assessment update

---

## 10. NIST Cybersecurity Framework Alignment

MONEYMAKER V1 aligns its security posture with the NIST Cybersecurity Framework (CSF), which provides a structured approach to managing cybersecurity risk through five core functions: Identify, Protect, Detect, Respond, and Recover.

### 10.1 Identify (ID)

| NIST Subcategory | MONEYMAKER Implementation | Status |
|-----------------|----------------------|--------|
| ID.AM-1: Physical devices inventoried | Server hardware inventory documented in Document 02 | Implemented |
| ID.AM-2: Software platforms inventoried | All services, versions, and dependencies documented per service doc | Implemented |
| ID.AM-3: Data flows mapped | Communication protocol map in Document 01 and this document | Implemented |
| ID.AM-4: External systems cataloged | Broker servers, exchange APIs, data providers listed | Implemented |
| ID.AM-5: Resources prioritized by classification | Data classification scheme (Section 6.3) | Implemented |
| ID.RA-1: Vulnerabilities identified | Automated scanning (pip-audit, Trivy, bandit) | Implemented |
| ID.RA-2: Threat intelligence received | Manual review of security advisories for dependencies | Planned |
| ID.RA-3: Threats identified | STRIDE analysis per service (Section 2.7) | Implemented |
| ID.RA-4: Business impacts identified | Risk assessment matrix (Section 2.8) | Implemented |
| ID.RA-5: Risk responses determined | Countermeasures documented for each threat | Implemented |
| ID.GV-1: Security policy established | This document | Implemented |
| ID.GV-2: Security roles defined | RBAC roles (Section 4.3) | Implemented |

### 10.2 Protect (PR)

| NIST Subcategory | MONEYMAKER Implementation | Status |
|-----------------|----------------------|--------|
| PR.AC-1: Identities managed | Service accounts, human accounts, RBAC | Implemented |
| PR.AC-2: Physical access managed | Server location, access controls | Implemented |
| PR.AC-3: Remote access managed | WireGuard VPN, no direct SSH from internet | Implemented |
| PR.AC-4: Access permissions managed | Least privilege, RBAC, database permissions | Implemented |
| PR.AC-5: Network integrity protected | VLAN segmentation, firewall rules | Implemented |
| PR.DS-1: Data-at-rest protected | ZFS AES-256-GCM, pgcrypto for credentials | Implemented |
| PR.DS-2: Data-in-transit protected | TLS 1.3, mTLS, WireGuard | Implemented |
| PR.DS-3: Assets managed through removal/transfer | Data retention policies, secure disposal | Planned |
| PR.DS-5: Protections against data leaks | Network segmentation, output validation | Implemented |
| PR.IP-1: Baseline configuration created | Infrastructure as Code, Dockerfiles | Implemented |
| PR.IP-3: Configuration change control | Audit log, change management process | Implemented |
| PR.IP-4: Backups conducted | ZFS snapshots, daily/weekly/monthly backups | Implemented |
| PR.IP-9: Response/recovery plans tested | Quarterly DR test | Planned |
| PR.IP-12: Vulnerability management plan | Automated scanning, update schedule | Implemented |
| PR.MA-1: Maintenance performed | Unattended-upgrades, scheduled maintenance windows | Implemented |
| PR.PT-1: Audit logs determined and documented | Comprehensive audit trail (Section 9) | Implemented |
| PR.PT-3: Least functionality principle | Minimal OS, minimal dependencies, minimal permissions | Implemented |
| PR.PT-4: Communication networks protected | TLS 1.3, VLAN isolation, firewall rules | Implemented |

### 10.3 Detect (DE)

| NIST Subcategory | MONEYMAKER Implementation | Status |
|-----------------|----------------------|--------|
| DE.AE-1: Baseline of network operations established | Prometheus metrics baselines | Implemented |
| DE.AE-2: Detected events analyzed | Alertmanager correlation, Grafana dashboards | Implemented |
| DE.AE-3: Event data aggregated | Centralized audit log, Prometheus | Implemented |
| DE.AE-5: Incident alert thresholds established | Alert rules in Alertmanager | Implemented |
| DE.CM-1: Network monitored | nftables logging, traffic analysis | Implemented |
| DE.CM-4: Malicious code detected | Trivy, pip-audit, dependency scanning | Implemented |
| DE.CM-7: Unauthorized activity monitored | fail2ban, audit logs, anomaly detection | Implemented |
| DE.CM-8: Vulnerability scans performed | Weekly automated scans | Implemented |
| DE.DP-4: Event detection communicated | Telegram alerts, Grafana dashboards | Implemented |

### 10.4 Respond (RS)

| NIST Subcategory | MONEYMAKER Implementation | Status |
|-----------------|----------------------|--------|
| RS.RP-1: Response plan executed | Incident response plan (Section 11) | Documented |
| RS.CO-2: Incidents reported | Incident severity levels and communication | Documented |
| RS.AN-1: Notifications from detection systems investigated | Alert investigation runbook | Planned |
| RS.MI-1: Incidents contained | Kill switch, VLAN isolation, service shutdown | Implemented |
| RS.MI-2: Incidents mitigated | Root cause analysis, countermeasure deployment | Documented |
| RS.IM-1: Response plans incorporate lessons learned | Post-mortem process | Documented |

### 10.5 Recover (RC)

| NIST Subcategory | MONEYMAKER Implementation | Status |
|-----------------|----------------------|--------|
| RC.RP-1: Recovery plan executed | Disaster recovery plan (Section 12) | Documented |
| RC.IM-1: Recovery plans incorporate lessons learned | Post-incident review updates DR plan | Documented |
| RC.IM-2: Recovery strategies updated | Quarterly DR test drives improvements | Planned |

---

## 11. Incident Response Plan

### 11.1 Incident Severity Levels

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **P1 - Critical** | Active financial loss, system compromise, credential exposure | Immediate (< 15 min) | Unauthorized trades executing, broker credentials leaked, full system compromise |
| **P2 - High** | Service outage affecting trading, security vulnerability being exploited | < 1 hour | MT5 Bridge down during market hours, Algo Engine producing invalid signals, detected intrusion attempt |
| **P3 - Medium** | Degraded functionality, non-critical security issue | < 4 hours | One data feed down, monitoring dashboard unavailable, non-critical dependency vulnerability |
| **P4 - Low** | Minor issue, informational security event | < 24 hours | Non-critical service restart, single failed login attempt, cosmetic dashboard bug |

### 11.2 Incident Response Phases

**Phase 1: Preparation (Ongoing)**

Preparation ensures that when an incident occurs, the response team has the tools, knowledge, and procedures to act effectively.

- Incident response runbook is documented, reviewed quarterly, and accessible (this document)
- Contact information for all stakeholders is current
- Kill switch procedures are tested monthly
- Backup restore procedures are verified quarterly
- Security monitoring dashboards are operational
- Communication channels (Telegram alert group) are tested weekly

**Phase 2: Detection**

Incidents are detected through multiple channels:

- **Automated alerts:** Alertmanager triggers on predefined conditions (service down, unusual trade volume, failed logins, risk limit breaches, hash chain integrity failure)
- **Monitoring dashboards:** Grafana dashboards display real-time system health; anomalies visible to human operators
- **Audit log analysis:** Automated daily review of audit logs for anomalous patterns
- **External notification:** Broker or exchange contacts the operator about unusual activity

**Phase 3: Analysis**

Upon detection, the responder must quickly determine:

1. **Scope:** Which systems are affected? Is the incident contained to one service/VM/VLAN, or has it spread?
2. **Impact:** Is there active financial loss? Is data being exfiltrated? Are credentials compromised?
3. **Root cause (preliminary):** Is this a software bug, a configuration error, a security breach, or a hardware failure?
4. **Severity classification:** Assign P1-P4 based on the analysis.

Analysis tools:

- Audit log queries (PostgreSQL for hot data, DuckDB for cold Parquet data)
- Grafana dashboards and Prometheus queries
- Service logs (`journalctl`, Docker container logs)
- Network traffic analysis (nftables logs, `tcpdump` if necessary)

**Phase 4: Containment**

Immediate actions to prevent the incident from causing further damage:

| Scenario | Containment Action |
|----------|--------------------|
| Unauthorized trading | Activate kill switch. Close all positions. Disable MT5 Bridge. |
| Broker credential leak | Emergency rotation of broker credentials. Disable MT5 Bridge. Contact broker to freeze account. |
| Compromised VM | Isolate VM by removing its network interface in Proxmox. Snapshot VM for forensic analysis. |
| Data exfiltration | Block all outbound traffic from affected VLAN. Snapshot affected systems. |
| Ransomware/malware | Isolate all affected VMs. Do NOT reboot (preserves volatile evidence). |
| DDoS on VPN | Rate limit or temporarily disable WireGuard. Assess if trading is affected. |
| Database compromise | Revoke all database credentials. Restore from last verified backup. |

**Phase 5: Eradication**

Remove the root cause of the incident:

- Patch the vulnerability that was exploited
- Remove any malware, backdoors, or unauthorized accounts
- Rotate all potentially compromised credentials
- Rebuild affected VMs from known-good images if the extent of compromise is uncertain
- Update firewall rules to block the attack vector

**Phase 6: Recovery**

Restore normal operations with verification:

1. Restore services from clean backups or rebuilt images
2. Verify audit log integrity (hash chain check)
3. Verify database integrity (data checksums, row counts)
4. Re-enable services one at a time, monitoring for anomalies
5. Resume paper trading first, verify correct behavior
6. Resume live trading only after paper trading confirms normal operation
7. Continue enhanced monitoring for 72 hours after recovery

**Phase 7: Post-Incident Review**

Every P1 and P2 incident requires a written post-mortem within 72 hours:

```
POST-MORTEM TEMPLATE
====================

Incident ID: INC-YYYY-MM-DD-NNN
Severity: P1/P2/P3/P4
Duration: [start time] to [end time] (total: X hours Y minutes)

Summary:
[One-paragraph description of what happened]

Timeline:
[Chronological list of events with timestamps]
- HH:MM:SS - First indicator of problem
- HH:MM:SS - Alert triggered
- HH:MM:SS - Responder acknowledged
- HH:MM:SS - Containment action taken
- HH:MM:SS - Root cause identified
- HH:MM:SS - Fix deployed
- HH:MM:SS - Normal operation restored

Root Cause:
[Detailed technical explanation of why the incident occurred]

Impact:
- Financial impact: $X (if any)
- Data impact: [describe any data loss or corruption]
- Service impact: [which services were affected, for how long]
- Reputational impact: [if applicable]

What Went Well:
- [Things the response team did correctly]

What Could Be Improved:
- [Things that slowed down detection, response, or recovery]

Action Items:
1. [Specific action] - Owner: [name] - Deadline: [date]
2. [Specific action] - Owner: [name] - Deadline: [date]
3. [Specific action] - Owner: [name] - Deadline: [date]
```

---

## 12. Disaster Recovery

### 12.1 Recovery Objectives

**Recovery Point Objective (RPO): 15 minutes.** In a disaster scenario, the maximum acceptable data loss is 15 minutes of data. This is achievable because ZFS snapshots are taken every 15 minutes and PostgreSQL WAL ensures transaction-level durability for committed transactions.

**Recovery Time Objective (RTO): 4 hours.** The maximum acceptable time from disaster declaration to full operational recovery is 4 hours. This includes hardware provisioning (if necessary), VM restoration, service startup, connectivity verification, and paper trading validation.

### 12.2 DR Scenarios and Runbooks

**Scenario 1: Single Service Failure**

- Detection: Prometheus health check alerts, service process exits
- Impact: One function degraded (e.g., no data ingestion, no monitoring)
- Recovery: Automatic container restart via Docker restart policy (< 1 minute). If restart fails, manual investigation and container rebuild (< 15 minutes).
- RTO: < 5 minutes (automatic), < 30 minutes (manual)

**Scenario 2: Single VM Failure**

- Detection: Proxmox reports VM as stopped, Prometheus loses target
- Impact: All services on that VM are offline
- Recovery: Restore from latest ZFS snapshot (< 5 minutes). If snapshot is corrupted, restore from daily backup via PBS (< 30 minutes).
- RTO: < 30 minutes

**Scenario 3: Database Corruption**

- Detection: PostgreSQL reports checksum errors, application queries return unexpected results, audit hash chain verification fails
- Impact: Data integrity compromised, potential incorrect trading decisions
- Recovery: Stop all trading immediately. Identify the corruption scope. Restore PostgreSQL from last verified backup (pg_dump or PBS). Replay WAL to minimize data loss. Verify audit log integrity. Resume trading in paper mode, then live.
- RTO: < 2 hours

**Scenario 4: Full Server Hardware Failure**

- Detection: Server unresponsive, all monitoring offline
- Impact: Complete system outage
- Recovery procedure:
  1. Acquire replacement hardware (assumes spare hardware is available or can be procured within 2 hours)
  2. Install Proxmox VE on replacement hardware (30 minutes)
  3. Restore all VMs from off-site backup (1-2 hours depending on network speed)
  4. Restore ZFS encryption key from secure off-site copy
  5. Verify each service starts and can communicate
  6. Run paper trading for 1 hour to verify correct behavior
  7. Resume live trading
- RTO: < 4 hours (assumes spare hardware available)

**Scenario 5: Network Outage**

- Detection: Data Ingestion Service reports all feeds disconnected, MT5 Bridge reports broker unreachable
- Impact: No new data, no trade execution (existing positions protected by broker-side stop-losses)
- Recovery: Wait for network restoration. If outage persists > 30 minutes, tighten stop-losses on all positions. If outage persists > 2 hours, attempt to close positions via mobile broker app.
- RTO: Depends on ISP/network provider

### 12.3 DR Testing Schedule

- **Monthly:** Single VM restore test (rotate which VM is tested each month)
- **Quarterly:** Full DR test -- simulate complete server loss, restore all VMs to temporary hardware or secondary Proxmox instance, verify end-to-end trading pipeline in paper mode
- **Annually:** Network isolation DR test -- disconnect the server from the internet, verify graceful degradation and position protection behavior

All DR test results are documented in the audit log with detailed findings and any improvements identified.

---

## 13. Security Monitoring and Detection

### 13.1 Security Monitoring Architecture

```
+============================================================================+
|                   SECURITY MONITORING STACK                                |
|                                                                            |
|   +------------------+    +------------------+    +------------------+     |
|   | fail2ban         |    | AIDE             |    | Prometheus       |     |
|   | (login attempts) |    | (file integrity) |    | (system metrics) |     |
|   +--------+---------+    +--------+---------+    +--------+---------+     |
|            |                       |                       |               |
|            v                       v                       v               |
|   +--------+-----------------------+-----------------------+---------+     |
|   |                    Alertmanager                                  |     |
|   |              (alert routing, deduplication, silencing)           |     |
|   +--------+-----------------------+-----------------------+---------+     |
|            |                       |                       |               |
|            v                       v                       v               |
|   +------------------+    +------------------+    +------------------+     |
|   | Telegram Bot     |    | Grafana          |    | Audit Log        |     |
|   | (instant alerts) |    | (visual dashboards)   | (permanent record)|    |
|   +------------------+    +------------------+    +------------------+     |
|                                                                            |
+============================================================================+
```

### 13.2 Failed Login Monitoring

fail2ban monitors authentication logs on every VM:

```ini
# /etc/fail2ban/jail.local

[DEFAULT]
bantime = 900         # 15 minute ban
findtime = 600        # 10 minute window
maxretry = 5          # 5 attempts before ban
banaction = nftables

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 900

[sshd-aggressive]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 15
bantime = 86400       # 24 hour ban after 15 cumulative failures
```

Every ban event is forwarded to the audit log and triggers a Telegram alert:

```bash
# /etc/fail2ban/action.d/notify-audit.conf
actionban = curl -s -X POST http://10.30.30.103:8080/audit \
    -H 'Content-Type: application/json' \
    -d '{"event_type":"LOGIN_LOCKED","service":"fail2ban","actor":"<ip>","action":"ban","details":{"jail":"<name>","failures":<failures>}}'
```

### 13.3 File Integrity Monitoring

AIDE (Advanced Intrusion Detection Environment) monitors critical system files for unexpected changes on every VM:

```ini
# /etc/aide/aide.conf

# Monitor critical directories
/etc        p+i+n+u+g+s+m+c+acl+xattrs+sha256
/usr/bin    p+i+n+u+g+s+m+c+sha256
/usr/sbin   p+i+n+u+g+s+m+c+sha256
/boot       p+i+n+u+g+s+m+c+sha256

# Monitor application configuration
/app/config p+i+n+u+g+s+m+c+sha256

# Exclude dynamic directories
!/var/log
!/var/cache
!/tmp
!/proc
!/sys
```

AIDE runs a daily integrity check at 05:00 UTC. Any changes detected outside of scheduled maintenance windows trigger a WARNING alert.

### 13.4 Process Monitoring

Each VM runs a lightweight process monitor that maintains a whitelist of expected processes and alerts on any unexpected process execution:

Expected process whitelist for vm-101 (Algo Engine):

```
/usr/bin/python3 /app/algo_engine/main.py
/usr/bin/dockerd
/usr/bin/containerd
/usr/sbin/sshd
/usr/sbin/nftables
/usr/bin/node_exporter
/usr/sbin/cron
/lib/systemd/systemd
```

Any process not on the whitelist that persists for more than 60 seconds triggers an alert. This detects cryptominers, reverse shells, and other unauthorized processes that an attacker might deploy after gaining access.

### 13.5 Outbound Connection Monitoring

Unexpected outbound connections can indicate data exfiltration or command-and-control communication. Each VM's nftables configuration logs all outbound connections that are not to whitelisted destinations:

```nft
# Log unexpected outbound connections
chain output {
    type filter hook output priority 0; policy drop;

    # Allow established connections
    ct state established,related accept

    # Allow whitelisted destinations (per-VM configuration)
    # vm-100 (Data Ingestion): exchange APIs
    ip daddr { 18.179.20.0/24, 52.84.0.0/16 } tcp dport 443 accept

    # Log and drop everything else
    log prefix "UNEXPECTED_OUTBOUND: " level warn
    drop
}
```

Outbound connection logs are aggregated by Prometheus and displayed on the security Grafana dashboard. Any unexpected outbound connection triggers an immediate alert.

### 13.6 Security Grafana Dashboard

A dedicated security dashboard in Grafana displays:

- **Failed Login Heatmap:** Failed login attempts by source IP and time, visualized as a heatmap to reveal patterns (e.g., brute force attacks concentrated at specific times)
- **fail2ban Ban Timeline:** Active bans over time, by jail and source IP
- **File Integrity Status:** AIDE check results, with any changes highlighted in red
- **Unexpected Process Alerts:** Timeline of unexpected process detections
- **Outbound Connection Map:** Non-whitelisted outbound connections by destination IP and port
- **Audit Log Event Rate:** Events per minute by category, with anomaly detection threshold
- **Secret Access Frequency:** Secret access events over time, with baseline comparison
- **Certificate Expiry Countdown:** Days until expiry for each TLS certificate
- **Vulnerability Scan Results:** Latest scan findings by severity

### 13.7 Security Alert Rules

```yaml
# Alertmanager rules for security events

groups:
  - name: security_alerts
    rules:
      - alert: BruteForceDetected
        expr: rate(fail2ban_bans_total[5m]) > 0
        for: 0s
        labels:
          severity: warning
        annotations:
          summary: "Brute force attack detected"
          description: "fail2ban has issued {{ $value }} bans in the last 5 minutes"

      - alert: AuditChainBroken
        expr: audit_chain_integrity_check == 0
        for: 0s
        labels:
          severity: critical
        annotations:
          summary: "Audit log hash chain integrity failure"
          description: "The audit log hash chain has been broken. Possible tampering."

      - alert: UnexpectedProcess
        expr: unexpected_process_count > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Unexpected process detected on {{ $labels.instance }}"

      - alert: CertificateExpiringSoon
        expr: tls_certificate_expiry_days < 30
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "TLS certificate for {{ $labels.cn }} expires in {{ $value }} days"

      - alert: CertificateExpired
        expr: tls_certificate_expiry_days <= 0
        for: 0s
        labels:
          severity: critical
        annotations:
          summary: "TLS certificate for {{ $labels.cn }} has expired"

      - alert: UnauthorizedOutboundConnection
        expr: rate(unexpected_outbound_connections_total[5m]) > 0
        for: 0s
        labels:
          severity: critical
        annotations:
          summary: "Unexpected outbound connection from {{ $labels.instance }}"

      - alert: HighSecretAccessRate
        expr: rate(secret_access_total[1h]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Unusually high rate of secret access"

      - alert: FileIntegrityViolation
        expr: aide_integrity_check_changed > 0
        for: 0s
        labels:
          severity: critical
        annotations:
          summary: "File integrity violation detected on {{ $labels.instance }}"
```

---

## 14. Operational Security

### 14.1 Change Management Process

All changes to the MONEYMAKER production environment follow a defined change management process:

**Standard Changes (pre-approved, low-risk):**

- Applying OS security patches (via unattended-upgrades)
- Rotating secrets on schedule
- Deploying a pre-tested Docker image update
- Adjusting non-critical monitoring thresholds

Process: Execute the change. Log in the audit trail. Verify success.

**Normal Changes (require review):**

- Modifying firewall rules
- Promoting a new AI model to production
- Changing risk parameters
- Adding or removing data sources
- Updating dependency versions

Process:

1. Document the proposed change (what, why, risk assessment, rollback plan)
2. Test in paper trading environment
3. Review by a second person (if available) or self-review after 24-hour cooling period
4. Execute the change during a scheduled maintenance window
5. Verify correct behavior
6. Log the change in the audit trail
7. Monitor for anomalies for 24 hours

**Emergency Changes (bypasses normal process due to urgency):**

- Patching an actively exploited vulnerability
- Activating the kill switch
- Rotating a compromised credential
- Isolating a compromised VM

Process: Execute immediately. Document retroactively within 24 hours. Review whether the emergency could have been prevented with better preparation.

### 14.2 Separation of Duties

In a single-operator system, true separation of duties is challenging. MONEYMAKER implements pragmatic separation through the following measures:

- **Automated vs. manual actions:** The system performs routine operations (trading, data ingestion, monitoring) automatically. Human intervention is required for changes to the system itself (deployments, configuration changes, model promotion). This separates the "operator" from the "trader."
- **Multiple authentication factors:** Even a single operator must authenticate through multiple factors (VPN key + SSH key + 2FA for Proxmox). Compromise of one factor is insufficient.
- **Audit trail for accountability:** Every action is logged, creating accountability even when one person fills multiple roles. The audit trail can be reviewed to verify that changes were appropriate and authorized.
- **Automated guardrails:** Risk limits, circuit breakers, and position size caps are enforced by code, not by human discipline. Even the operator cannot override these limits without modifying the code, which is itself a logged and reviewable action.

### 14.3 Regular Security Review Schedule

| Review | Frequency | Scope | Deliverable |
|--------|-----------|-------|-------------|
| Dependency vulnerability scan | Weekly | All service dependencies | Automated report |
| Docker image scan | Weekly | All Docker images | Trivy report |
| AIDE integrity check | Daily | All VM filesystems | Pass/fail log |
| Audit log integrity | Daily (automated) | Hash chain verification | Pass/fail alert |
| Firewall rule review | Monthly | All VLAN firewall rules | Updated rule documentation |
| Access review | Quarterly | All user accounts, service accounts, SSH keys | Deactivate unused accounts |
| Full security audit | Semi-annually | Entire system | Written report with findings |
| DR test | Quarterly | Full disaster recovery | Test results and improvements |
| Penetration test (self-assessment) | Annually | External attack surface | Findings and remediation |
| NIST CSF self-assessment | Annually | All five functions | Updated compliance matrix |

### 14.4 Security Update Procedure

1. **Monitor:** Subscribe to security mailing lists for all critical dependencies (PostgreSQL, Redis, Python, Go, Docker, Proxmox, Linux kernel)
2. **Assess:** When a security update is released, assess its relevance to MONEYMAKER within 24 hours. Determine severity and exploitability.
3. **Test:** Apply the update in a test environment (or paper trading mode) and verify that services function correctly.
4. **Schedule:** For non-critical updates, schedule deployment during the next maintenance window. For critical updates (actively exploited vulnerabilities), deploy within 24 hours.
5. **Deploy:** Apply the update to all affected VMs/containers.
6. **Verify:** Confirm that services start correctly and pass health checks.
7. **Document:** Log the update in the audit trail with the CVE number, affected component, and verification result.

### 14.5 Password Policy

For any human-facing authentication (Proxmox UI, Grafana, Streamlit):

- Minimum length: 16 characters
- Complexity: Must include uppercase, lowercase, digits, and special characters
- History: Cannot reuse last 12 passwords
- Expiration: 90 days (prompted, not forced -- to avoid weak password selection under time pressure)
- Multi-factor: All human-facing services require TOTP 2FA in addition to password
- Storage: Passwords are hashed with bcrypt (cost factor 12) or Argon2id

For service accounts and machine-to-machine authentication, passwords are randomly generated with minimum 32 characters of alphanumeric and special characters, stored in the encrypted secrets manager, and rotated on the schedules defined in Section 5.2.

### 14.6 Physical Security

The Proxmox server that hosts MONEYMAKER must be physically secured:

- **Location:** The server should be in a locked room, cabinet, or closet with restricted access. If in a home office, the room should have a locked door.
- **Access control:** Only authorized operators should have physical access to the server. Document who has physical access.
- **USB ports:** Disable or physically block unused USB ports to prevent unauthorized device connection. BIOS should be configured to not boot from USB.
- **BIOS password:** Set a BIOS administrator password to prevent boot order changes or BIOS configuration modification.
- **Console access:** The server console (keyboard/monitor) should not be in a publicly accessible area.
- **Network ports:** Unused network ports on the switch should be disabled.
- **Environmental:** Ensure adequate cooling, protection from water damage, and fire suppression (or at minimum, a fire extinguisher rated for electrical equipment).

### 14.7 Secure Disposal

When hardware is retired or data storage is decommissioned:

- **Hard drives / SSDs:** Overwrite with random data (3 passes minimum) using `nwipe` or equivalent, or physically destroy the drive. For SSDs, use the manufacturer's secure erase command (ATA Secure Erase) which triggers the drive's internal secure erase mechanism.
- **USB drives:** Overwrite with random data or physically destroy.
- **Paper documents:** Cross-cut shred any printed configuration information, passwords, or network diagrams.
- **Cloud storage:** If any backups were stored in cloud storage, delete the objects and verify deletion. Encryption ensures that even if deletion is incomplete, the data remains unreadable without the key.
- **Log the disposal:** Record in the audit trail what was disposed of, how, when, and by whom.

---

## Appendix A: Security Architecture Diagram

```
+============================================================================+
|                     MONEYMAKER V1 SECURITY ARCHITECTURE                       |
|                                                                            |
|  INTERNET                                                                  |
|  --------                                                                  |
|     |                                                                      |
|     | UDP 51820 (WireGuard only)                                          |
|     |                                                                      |
|  +--v--------------------------------------------------------------------+ |
|  |  PROXMOX HOST FIREWALL (nftables)                                     | |
|  |  Default: DROP ALL                                                    | |
|  |  Rate limiting | SYN flood protection | Connection tracking          | |
|  +--+--------------------------------------------------------------------+ |
|     |                                                                      |
|  +--v--------------------------------------------------------------------+ |
|  |  WireGuard VPN Tunnel                                                 | |
|  |  ChaCha20-Poly1305 | Curve25519 auth | Pre-shared key               | |
|  +--+--------------------------------------------------------------------+ |
|     |                                                                      |
|  +--v-------------------+  +--------------------+  +------------------+   |
|  | VLAN 10 (MGMT)       |  | VLAN 20 (TRADE)    |  | VLAN 30 (DATA)  |   |
|  |                      |  |                    |  |                  |   |
|  | [Proxmox UI + 2FA]   |  | [MT5 Bridge]       |  | [PostgreSQL]     |   |
|  | [SSH jump host]      |  |   |                |  |   TLS 1.3+mTLS  |   |
|  | [Grafana + 2FA]      |  |   | TLS to broker  |  | [Redis]          |   |
|  | [Prometheus]         |  |   v                |  |   TLS 1.3        |   |
|  | [Alertmanager]       |  | [Broker Servers]   |  | [Algo Engine]    |   |
|  +----------+-----------+  +---------+----------+  | [Data Ingestion] |   |
|             |                        |             +--------+---------+   |
|             |    INTER-VLAN FIREWALL RULES         |                     |
|             +-------- (explicit allow only) -------+                     |
|                                                                          |
|  +--v-------------------+                                                |
|  | VLAN 40 (GUEST)      |                                                |
|  | [Read-only dashboard]|                                                |
|  | No TRADE/DATA access |                                                |
|  +-----------------------+                                                |
|                                                                          |
|  +----------------------------------------------------------------------+|
|  | DATA AT REST                                                          ||
|  | ZFS AES-256-GCM encryption on all datasets                           ||
|  | pgcrypto column-level encryption for broker credentials              ||
|  | Encrypted backups (age + ZFS native encryption)                      ||
|  +----------------------------------------------------------------------+|
|                                                                          |
|  +----------------------------------------------------------------------+|
|  | AUDIT TRAIL                                                           ||
|  | Append-only PostgreSQL table | SHA-256 hash chain                    ||
|  | INSERT-only permissions | Daily integrity verification               ||
|  | 7-year retention | Parquet cold storage | Encrypted off-site archive ||
|  +----------------------------------------------------------------------+|
|                                                                            |
+============================================================================+
```

---

## Appendix B: Security Checklist

This checklist should be reviewed before every production deployment and during quarterly security audits.

### Network Security

- [ ] Default firewall policy is DROP ALL on all VLANs
- [ ] WireGuard VPN is the only path to MGMT VLAN from outside
- [ ] No services are directly exposed to the internet (except WireGuard UDP)
- [ ] All inter-service communication uses TLS 1.3
- [ ] mTLS certificates are valid and not expiring within 30 days
- [ ] Firewall rules match the documented rule tables (no extra rules)
- [ ] Rate limiting is active on all external-facing ports

### Authentication and Access Control

- [ ] SSH password authentication is disabled on all VMs
- [ ] Proxmox UI requires 2FA
- [ ] Grafana requires 2FA
- [ ] All SSH keys are ED25519 or RSA 4096-bit
- [ ] No default or shared accounts exist
- [ ] All service accounts have minimum required permissions
- [ ] fail2ban is running on all VMs

### Secrets Management

- [ ] No secrets in version control (verify with gitleaks)
- [ ] No secrets in Docker images (verify with trivy)
- [ ] No secrets in log files (verify with grep)
- [ ] All secrets are within their rotation schedule
- [ ] SOPS encrypted files are current and accessible
- [ ] Emergency rotation procedure is documented and tested

### Data Security

- [ ] ZFS encryption is active on all datasets
- [ ] PostgreSQL SSL is required (no plaintext connections allowed)
- [ ] Redis TLS is enabled
- [ ] Backups are encrypted
- [ ] Backup restore test was performed this month
- [ ] Data retention policies are being enforced

### Application Security

- [ ] All dependencies are pinned to exact versions
- [ ] pip-audit / safety shows no HIGH/CRITICAL vulnerabilities
- [ ] Trivy scan shows no HIGH/CRITICAL vulnerabilities in Docker images
- [ ] bandit scan shows no HIGH/MEDIUM findings
- [ ] No eval(), exec(), shell=True, or pickle.loads() in codebase
- [ ] All Docker containers run as non-root

### Monitoring and Audit

- [ ] Audit log hash chain integrity is verified (daily automated check passing)
- [ ] AIDE integrity checks are running daily
- [ ] fail2ban is active and logging
- [ ] Security Grafana dashboard is accessible and showing data
- [ ] Alertmanager is routing security alerts to Telegram
- [ ] All alert rules are active and tested

### Operational

- [ ] Incident response plan is reviewed and current
- [ ] DR plan is reviewed and current
- [ ] Last DR test date is within the quarterly schedule
- [ ] All VMs are running latest security patches
- [ ] Physical access to server is controlled
- [ ] BIOS password is set

---

## Appendix C: Glossary of Security Terms

| Term | Definition |
|------|-----------|
| **AIDE** | Advanced Intrusion Detection Environment -- a file integrity checking tool that creates a database of file attributes and verifies them against the filesystem. |
| **AES-256-GCM** | Advanced Encryption Standard with 256-bit key and Galois/Counter Mode -- an authenticated encryption algorithm that provides both confidentiality and integrity. |
| **age** | A simple, modern file encryption tool used with SOPS for encrypting secrets files. Uses X25519 key agreement and ChaCha20-Poly1305 encryption. |
| **Bandit** | A Python static analysis tool designed to find common security issues in Python code. |
| **bcrypt** | A password hashing function based on the Blowfish cipher, designed to be computationally expensive to resist brute-force attacks. |
| **Defense in Depth** | A security strategy that uses multiple layers of defense so that if one layer fails, others still provide protection. |
| **fail2ban** | An intrusion prevention daemon that monitors log files and bans IP addresses that show malicious signs (too many password failures, seeking for exploits, etc.). |
| **gitleaks** | A tool for detecting hardcoded secrets like passwords, API keys, and tokens in git repositories. |
| **HashiCorp Vault** | A secrets management tool that provides a centralized service for storing, accessing, and distributing secrets with access control and audit logging. |
| **mTLS** | Mutual TLS -- a TLS connection where both the client and the server present certificates to authenticate each other, as opposed to standard TLS where only the server presents a certificate. |
| **NIST CSF** | National Institute of Standards and Technology Cybersecurity Framework -- a framework for organizing and improving cybersecurity risk management. |
| **nftables** | The successor to iptables, nftables is the standard firewall framework in modern Linux kernels, providing packet filtering, NAT, and traffic classification. |
| **OWASP** | Open Web Application Security Project -- a nonprofit that produces security resources including the OWASP Top 10 list of web application security risks. |
| **pgcrypto** | A PostgreSQL extension that provides cryptographic functions for encrypting and decrypting data within the database. |
| **pip-audit** | A tool for scanning Python packages for known vulnerabilities using the OSV (Open Source Vulnerabilities) database. |
| **RBAC** | Role-Based Access Control -- an access control model where permissions are assigned to roles, and users are assigned to roles, rather than assigning permissions directly to users. |
| **RPO** | Recovery Point Objective -- the maximum acceptable amount of data loss measured in time. An RPO of 15 minutes means you can afford to lose at most 15 minutes of data. |
| **RTO** | Recovery Time Objective -- the maximum acceptable amount of time to restore a service after a disaster. An RTO of 4 hours means the service must be back within 4 hours. |
| **SOPS** | Secrets OPerationS -- a tool developed by Mozilla for managing encrypted secrets files, supporting multiple encryption backends including age, PGP, and cloud KMS. |
| **STRIDE** | A threat modeling framework: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege. |
| **TOTP** | Time-based One-Time Password -- a 2FA method that generates a short-lived code based on a shared secret and the current time. |
| **Trivy** | An open-source vulnerability scanner for containers, filesystems, and code repositories. |
| **WireGuard** | A modern VPN protocol designed for simplicity and performance, using Curve25519 for key exchange and ChaCha20-Poly1305 for encryption. |
| **Zero Trust** | A security model that requires strict identity verification for every person and device trying to access resources, regardless of whether they are inside or outside the network perimeter. |

---

*fine del documento 12 -- Security, Compliance, and Audit*
