# Phase 3: Advanced Database Engineering — Complete Reference

**Date:** 2026-02-06 | **Status:** Completed

## Overview & Goals

This phase dives into how data is stored, protected, and distributed.

## Module 3.1: Relational Database Internals

### 1. Storage & Indexing: The B+ Tree

Why is it the standard?
*   **Structure:**
    *   **Internal Nodes:** Contain only keys and pointers. (High Fan-out).
    *   **Leaf Nodes:** Contain keys and **Record Pointers** (or the data itself in Clustered Index).
    *   **Linked Leaves:** Leaf nodes are a doubly-linked list.
*   **Performance:**
    *   **Point Lookup:** $O(\log_B N)$. With fan-out $B=100$, tree height is usually 3-4.
    *   **Range Scan:** Find start key ($O(\log N)$), then traverse linked list ($O(K)$). Very cache-friendly.

### 2. Transaction Isolation: The Anomalies

SQL Standard defines levels, but implementations vary.

#### 2.1 The Anomalies
1.  **Dirty Read:** Reading uncommitted data. (Transaction A writes, B reads, A aborts).
2.  **Non-Repeatable Read:** Reading the same row twice gives different values. (Row modified by B).
3.  **Phantom Read:** Executing the same **Range Query** twice gives different set of rows. (Row inserted/deleted by B).

#### 2.2 Isolation Levels
| Level | Dirty Read | Non-Repeatable | Phantom |
| :--- | :--- | :--- | :--- |
| **Read Committed** | No | Yes | Yes |
| **Repeatable Read** | No | No | Yes (Usually) |
| **Serializable** | No | No | No |

### 3. Concurrency Control: MVCC (Postgres/MySQL)

How to achieve "Readers don't block Writers"? **Multi-Version Concurrency Control**.

#### 3.1 Postgres Implementation (`xmin` / `xmax`)
*   **Tuple Structure:** Every row has `xmin` (Created by TxID) and `xmax` (Deleted by TxID).
*   **UPDATE:** It is actually `DELETE` + `INSERT`.
    *   Old Row: `xmax` set to Current TxID.
    *   New Row: `xmin` set to Current TxID.
*   **Visibility Rules:**
    *   Transaction $T$ sees row $R$ if:
        1.  `R.xmin` is committed and < $T$.
        2.  `R.xmax` is NULL or (uncommitted) or > $T$.
*   **Vacuuming:** The process of removing "Dead Tuples" (where `xmax` is visible to all active transactions).

### 4. Durability & Recovery: ARIES & WAL

How to survive a power plug pull?

#### 4.1 Write-Ahead Logging (WAL)
*   **The Golden Rule:** Log record must hit disk **before** the data page touches disk.
*   **Log Sequence Number (LSN):** Every log entry has an ID. Every Data Page stores the `PageLSN` of the last update.

#### 4.2 ARIES Algorithm
1.  **Analysis:** Scan WAL from last Checkpoint. Determine "Winner" (Committed) and "Loser" (In-flight) transactions. Determine Dirty Pages.
2.  **Redo:** Replay history. Re-apply all updates (even for Losers) to bring memory to state at crash.
    *   *Idempotency:* If `PageLSN` >= `LogLSN`, don't apply.
3.  **Undo:** Scan WAL backwards. Revert changes of "Loser" transactions.

## Module 3.2: Distributed Consensus & Replication

### 1. Consensus Algorithms: Agreement in a Hostile World

How do 5 nodes agree on "Who is leader?" or "Value X is 5" when the network is dropping packets?

#### 1.1 Paxos (The Foundation)
*   **Roles:** Proposers, Acceptors, Learners.
*   **Mechanism:** Two phases.
    1.  **Prepare:** Proposer asks majority: "Will you promise to ignore requests with ID < N?".
    2.  **Accept:** If majority says yes, Proposer says: "Okay, accept value V with ID N".
*   **Multi-Paxos:** Optimization to skip Phase 1 when the Leader is stable.
*   **Problem:** Extremely hard to implement correctly (many edge cases).

#### 1.2 Raft (The Standard)
Designed for understandability. Used in Etcd, Consul, CockroachDB.
*   **Components:** Leader Election, Log Replication, Safety.
*   **Term:** A logical clock. Monotonically increasing.
*   **Leader Election Safety:**
    *   *Rule:* A candidate is only valid if its log is *at least as up-to-date* as the majority.
    *   *Mechanism:* RequestVote RPC contains `lastLogTerm` and `lastLogIndex`.
    *   *Result:* A node with missing committed entries can **never** become leader. Data loss impossible.
*   **Log Matching Property:**
    *   If two logs have an entry with the same Index and Term, they are identical in all preceding entries.

### 2. Replication Models

#### 2.1 Sync vs Async
*   **Synchronous:** Write to Leader -> Leader writes to Replica -> Replica ACKs -> Leader ACKs to Client.
    *   *Pros:* Zero data loss.
    *   *Cons:* Latency = Max(Replica Latency). One slow node kills performance.
*   **Asynchronous:** Write to Leader -> Leader ACKs to Client. Background replication.
    *   *Pros:* Fast.
    *   *Cons:* Leader crash = Data loss.
*   **Semi-Sync:** Write to Leader + 1 Replica (out of N).
    *   *Pros:* Balance between durability and speed.

### 3. Leaderless Replication (DynamoDB / Cassandra)

No leader. Any node can accept writes.

#### 3.1 Quorum Math
*   **N:** Replication Factor (e.g., 3).
*   **W:** Write Quorum (e.g., 2).
*   **R:** Read Quorum (e.g., 2).
*   **Rule:** $R + W > N$.
    *   *Why?* The read set and write set must overlap by at least one node.

#### 3.2 Failure Handling
*   **Sloppy Quorum:**
    *   If Node A is down, write to Node D (who is not usually a replica for this key).
    *   *Goal:* High Availability (Availability over Consistency).
*   **Hinted Handoff:**
    *   Node D keeps the data in a separate "Hinted Handoff" buffer.
    *   When Node A comes back, D pushes the data to A.
*   **Read Repair:**
    *   Client reads from A, B, C. A=5, B=5, C=4.
    *   Client returns 5. Background process updates C to 5.

## Module 3.3: Storage Engines & NoSQL

### 1. The Write-Optimized Engine: LSM Trees

**Log-Structured Merge-Trees** solve the problem of random write I/O.
Used by: Cassandra, RocksDB, LevelDB, ScyllaDB.

#### 1.1 Architecture
1.  **MemTable (Memory):** Incoming writes go here (SkipList or RB-Tree). Fast ($O(\log N)$).
2.  **WAL (Disk):** Sequential append for durability (crash recovery).
3.  **SSTable (Disk):** When MemTable is full, it is **flushed** to disk as an Immutable Sorted String Table.
4.  **Compaction:** Merge background SSTables to remove deleted/overwritten data.

#### 1.2 Compaction Strategies
*   **Leveled (RocksDB):**
    *   L0: Overlapping SSTables.
    *   L1..LN: Non-overlapping.
    *   *Trade-off:* **High Write Amplification** (Data moved many times), but **Low Read Amplification** (Few files to check). Good for Reads.
*   **Tiered (Cassandra/Size-Tiered):**
    *   Flush to Tier 1. When 4 files exist, merge to Tier 2.
    *   *Trade-off:* **Low Write Amplification**, but **High Read Amplification** (Key might be in any file). Good for heavy Writes.

#### 1.3 Bloom Filters
*   *Problem:* Reading a key requires checking potentially many SSTables.
*   *Solution:* Each SSTable has a **Bloom Filter** in its header.
*   *Result:* "Is key X in file Y?" -> No (Definite) / Maybe (Check index). Saves 99% of disk lookups.

### 2. The Scan-Optimized Engine: Columnar Storage

Used by: Snowflake, ClickHouse, Redshift, Parquet.

#### 2.1 Row vs Column
*   **Row-Oriented (Postgres):** `[ID, Name, Age], [ID, Name, Age]`.
    *   Good for: Fetching one user.
    *   Bad for: `SELECT AVG(Age)`. Must read Name/ID from disk too (wasted I/O).
*   **Column-Oriented:** `[ID, ID], [Name, Name], [Age, Age]`.
    *   Good for: Analytics. Read only the `Age` block.

#### 2.2 Compression Techniques
Column values are often repetitive.
*   **Run-Length Encoding (RLE):**
    *   Data: `USA, USA, USA, UK, UK`.
    *   Stored: `(USA, 3), (UK, 2)`.
*   **Delta Encoding:**
    *   Data (Timestamps): `1000, 1005, 1012`.
    *   Stored: `1000, +5, +7`. Small integers compress better.

#### 2.3 Vectorized Execution (SIMD)
*   **Concept:** Instead of `for i in rows: sum += row.age` (Scalar)...
*   **SIMD (Single Instruction Multiple Data):** Load 16 integers into an AVX-512 register. Execute `VPADD` (Vector Parallel Add).
*   *Result:* 10x-50x speedup for aggregation queries.
