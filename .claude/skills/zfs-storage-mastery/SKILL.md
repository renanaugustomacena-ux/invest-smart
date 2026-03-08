# Skill: ZFS Storage Architecture & Data Integrity

You are the Storage Engineer responsible for MONEYMAKER's data persistence. You prioritize data integrity above all else.

---

## When This Skill Applies
Activate this skill whenever:
- Creating or modifying ZFS pools or datasets.
- Tuning storage performance (recordsize, compression).
- Managing snapshots, backups, or replication.
- Diagnosing I/O performance or disk space issues.

---

## Storage Pool Architecture

### 1. `rpool` (NVMe Mirror)
- **Physical**: 2x NVMe Gen5 (RAID1 Mirror).
- **Purpose**: Host OS, VM Disk Images, fast scratch.
- **Performance**: High IOPS, low latency.

### 2. `tank` (HDD RAID10)
- **Physical**: 4x Enterprise HDD (Striped Mirrors).
- **Purpose**: Bulk data, Historical Market Data, Logs, Backups.
- **Performance**: High sequential throughput, massive capacity.

## Dataset Tuning Mandates

| Dataset | Workload | `recordsize` | `compression` | Notes |
|---|---|---|---|---|
| `tank/postgres` | PostgreSQL DB | **16K** | `zstd-3` | Matches PG page size. Vital for perf. |
| `tank/market_data` | Parquet Files | **1M** | `lz4` | Max sequential read throughput. |
| `tank/logs` | Text Logs | **128K** | `gzip-9` | Max compression for text. |
| `rpool/vm-disks` | VM Images | **64K** | `lz4` | Default for general VM use. |

## Data Integrity & Protection
- **Checksums**: **ALWAYS ON** (`checksum=on`).
- **Encryption**: Native ZFS encryption (`aes-256-gcm`) for data at rest.
- **Scrubbing**: Monthly scheduled scrubs.
- **Snapshots**:
    - `rpool/vm-disks`: Every 15 mins (Retain 24h).
    - `tank/market_data`: Hourly (Retain 7d).

## Storage Checklist
- [ ] Is `ashift=12` set?
- [ ] Is `atime=off`? (Critical for performance)
- [ ] Is the correct `recordsize` set for the workload?
- [ ] Are snapshots configured?
