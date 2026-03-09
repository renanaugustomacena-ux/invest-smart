# Phase 5: DevOps, SRE & Cloud Native — Complete Reference

**Date:** 2026-02-06 | **Status:** Completed

## Overview & Goals

"It works on my machine" is not a valid excuse.

## Module 5.1: Container Internals (Linux Plumbing)

### 1. Namespaces: The Isolation Layer

Containers are not real objects. They are processes with a limited view of the world.

*   **PID Namespace:**
    *   *Inside:* Process sees itself as PID 1.
    *   *Outside:* Process has PID 4500.
    *   *Impact:* Cannot `kill` processes outside the container.
*   **NET Namespace:**
    *   Own `eth0`, IP, Routing Table, `iptables`.
    *   *Port 80* inside does not conflict with *Port 80* outside.
*   **MNT Namespace:**
    *   Own `/` root filesystem.
    *   Changing `/etc/config` inside does not touch host.
*   **USER Namespace:**
    *   *UID Mapping:* User can be `root` (UID 0) inside, but `nobody` (UID 1000) outside.
    *   *Security:* If container escapes, it has zero privileges on host.

### 2. Control Groups (Cgroups): The Limits Layer

Namespaces hide what you *see*. Cgroups limit what you *use*.

#### 2.1 Cgroups v1 vs v2
*   **v1:** Hierarchies were separate. `cpu` and `memory` were different trees. Complex to manage.
*   **v2 (Unified Hierarchy):** Single tree. Better support for "Pressure Stall Information" (PSI).
    *   **CPU Shares:** Soft limit (`cpu.weight`). If idle, take 100%. If busy, share 50/50.
    *   **CPU Quota:** Hard limit (`cpu.max`). If used > 100ms in 100ms window, THROTTLE (Sleep).
    *   **Memory Limit:** Hard limit. If used > Limit, **OOM Killer** shoots the process.

### 3. The Filesystem: OverlayFS

How can 1000 containers start in 1 second? They share the disk.

#### 3.1 Architecture
*   **LowerDir (Read-Only):** The Base Image (Ubuntu, Node.js).
*   **UpperDir (Read-Write):** The Container Layer. Starts empty.
*   **WorkDir:** Internal kernel scratchpad.
*   **Merged:** The view the process sees.

#### 3.2 Copy-on-Write (CoW) Mechanism
*   **Read:** Application reads `/etc/app.conf`. Kernel finds it in `LowerDir`. Zero copy.
*   **Write:** Application opens `/etc/app.conf` for writing.
    1.  Kernel **pauses** write.
    2.  Copies file from `LowerDir` to `UpperDir`.
    3.  App writes to the copy in `UpperDir`.
*   **Delete:** A "Whiteout" file (character device 0:0) is created in `UpperDir` to mask the file in `LowerDir`.

## Module 5.2: Kubernetes Architecture Deep Dive

### 1. The Control Plane Brain: Etcd

Kubernetes is just a CRUD app over Etcd.
*   **Data Model:** Key-Value store. Consistent (CP).
*   **MVCC (Multi-Version Concurrency Control):**
    *   Etcd does NOT overwrite keys. It appends new revisions.
    *   `Key="pod1" Rev=1` -> `Key="pod1" Rev=2`.
*   **The Watch Mechanism:**
    *   Controllers do not Poll. They **Watch**.
    *   API Server sends `Watch(Rev=100)`. Etcd streams all events > Rev 100.
    *   *Reliability:* If connection breaks, client reconnects with `LastRevision`. Etcd replays history from that point (Time Travel).

### 2. The Controller Pattern (SharedInformer)

How does `DeploymentController` manage 1000 pods without killing the API Server?

#### 2.1 The Components
1.  **Reflector:** Performs `List()` (Initial state) and `Watch()` (Updates). Pushes objects to a DeltaFIFO queue.
2.  **Informer:** Popps from DeltaFIFO. Updates the **Local Cache** (Thread-safe Store).
3.  **Indexer:** Allows looking up objects by field (e.g., "Find all Pods on Node X").
4.  **WorkQueue:** If an object changes, its **Key** (namespace/name) is pushed here.
5.  **Worker:** Pops Key. Gets *latest* state from Cache. Reconciles.

#### 2.2 Why is this brilliant?
*   **Edge Triggered:** You get notified on change.
*   **Level Driven Logic:** The Worker always looks at the *current* state in Cache, not the specific event. If you missed 5 updates, you just see the final result. (Self-healing).

### 3. Pod Networking (The "Flat" Network)

**Rule:** Every Pod gets an IP. No NAT between Pods.

#### 3.1 The Plumbing (CNI)
1.  **Pod Creation:** Kubelet calls CNI Plugin (e.g., Calico/Flannel).
2.  **veth Pair:** CNI creates a virtual cable.
    *   `eth0` (Inside Pod Namespace).
    *   `vethXXXX` (Host Namespace).
3.  **Bridge:** CNI attaches `vethXXXX` to a Linux Bridge (`cni0`).
4.  **Routing:**
    *   **Same Node:** `Pod A -> cni0 -> Pod B`. (L2 Switching).
    *   **Cross Node:** `Pod A -> cni0 -> Host Routing Table -> VXLAN/BGP -> Dest Node`.

#### 3.2 The Pause Container
*   *Observation:* In `docker ps`, you see `k8s_POD_...` containers.
*   *Purpose:* It holds the **Network Namespace**.
*   *Why?* If the Application Container crashes and restarts, it joins the *existing* Pause container's namespace. Result: **IP Address stays the same** across restarts.

## Module 5.3: Site Reliability Engineering (SRE)

### 1. Metrics & Monitoring Internals

#### 1.1 Prometheus: The Pull Model
*   **Architecture:** Prometheus server scrapes `/metrics` endpoints.
*   **Storage (TSDB):**
    *   **Timestamps:** Delta-of-Delta compression (Gorilla). If scrape interval is stable (30s), delta-of-delta is 0. 1 bit per timestamp.
    *   **Values:** XOR compression for float64. Small changes compress well.
*   **Pushgateway:** Only for batch jobs that die before scrape.

#### 1.2 Distributed Tracing
*   **Goal:** Follow `Request A` through `LB -> Service A -> Service B -> DB`.
*   **W3C Trace Context (`traceparent`):**
    *   `version-traceid-parentid-flags`
    *   `00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01`
    *   **Propagation:** Service A generates `traceid`. Passes it to B in HTTP header. Service B logs it.

### 2. Reliability Math: SLOs & Error Budgets

#### 2.1 The Terms
*   **SLI (Indicator):** "HTTP 500 rate". (The reality).
*   **SLO (Objective):** "99.9% success". (The goal).
*   **SLA (Agreement):** "If < 99.5%, refund 10%". (The contract).

#### 2.2 Error Budget Calculation
*   **Period:** 30 Days.
*   **Availability:** 99.9%.
*   **Budget:** 0.1% downtime $\approx$ 43 minutes.
*   *Philosophy:* If you have budget left, release fast. If budget is empty, **FREEZE releases**.

#### 2.3 Alerting: Burn Rate
Don't alert on "1 error". Alert on "Burning budget too fast".
*   **Burn Rate 1:** Consuming budget linearly (exhausts in 30 days).
*   **Burn Rate 14.4:** Consuming budget in 2 days. (Page the human).
*   **Formula:** $BurnRate = \frac{ErrorRate}{1 - SLO}$
*   *Alert Rule:* `burn_rate > 14.4` AND `error_rate > threshold`.
