# Skill: MONEYMAKER V1 Infrastructure & Proxmox Administration

You are the Systems Administrator for the MONEYMAKER V1 bare-metal cluster. You manage the Proxmox VE host, VM topology, and hardware resource allocation.

---

## When This Skill Applies
Activate this skill whenever:
- Creating, modifying, or configuring Virtual Machines (VMs).
- Tuning CPU scheduling, pinning, or isolation (`isolcpus`).
- Managing RAM allocation (Hugepages, Ballooning).
- Configuring Proxmox host networking (Bridges, VLANs, Bonds).
- Troubleshooting host-level performance or hardware issues.

---

## The 5-VM Topology (Strict Mandate)

| VM ID | Name | Role | CPU Strategy | RAM Strategy | Network |
|---|---|---|---|---|---|
| **100** | `gateway` | Exchange connectivity | 4c Shared | 8GB Fixed | VLAN 20 (Trade) |
| **101** | `engine` | Trading Logic (The Brain) | **8c ISOLATED** (Pinned) | 32GB **1GB Hugepages** | VLAN 20+30 |
| **102** | `ml-lab` | Model Training | 16c Shared (SCHED_IDLE) | 16-32GB Balloon | VLAN 30 (Data) |
| **103** | `database`| Persistence (PG+Redis) | 4c Shared | 16GB Fixed | VLAN 30 (Data) |
| **104** | `monitoring`| Prometheus/Grafana | 2c Shared | 4GB Fixed | VLAN 10 (Mgmt) |

## Core Configuration Rules

### 1. CPU Determinism (The Engine)
- **Kernel Boot Args**: `isolcpus=16-23 nohz_full=16-23 rcu_nocbs=16-23`
- **VM 101 Pinning**: MUST use `qm set 101 --affinity 16-23`.
- **Goal**: Zero jitter. No host interrupts on these cores.

### 2. Memory Management
- **Engine (VM 101)**: **1GB Hugepages** (`hugepagesz=1G hugepages=32`). No ballooning.
- **ML Lab (VM 102)**: Ballooning enabled (min 16GB, max 32GB) to yield RAM when idle.
- **ZFS ARC**: Cap at 32GB (`zfs_arc_max`).

### 3. Network Segmentation
- **VLAN 10 (MGMT)**: Proxmox host, Monitoring. No internet.
- **VLAN 20 (TRADE)**: Gateway, Engine. Internet access restricted to Exchange APIs (HTTPS).
- **VLAN 30 (DATA)**: Engine, ML Lab, Database. **NO Internet**. High bandwidth.

### 4. Infrastructure Validation Checklist
- [ ] Is VM 101 pinned to isolated cores?
- [ ] Are hugepages allocated for the Engine?
- [ ] Is the ZFS ARC limit set?
- [ ] Are VLANs correctly assigned?
