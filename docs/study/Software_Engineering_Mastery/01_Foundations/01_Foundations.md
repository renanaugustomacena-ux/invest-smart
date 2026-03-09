# Phase 1: CS & Systems Engineering Foundations — Complete Reference

**Date:** 2026-02-06 | **Status:** Completed

## Overview & Goals

This phase focuses on the low-level machinery that powers all software. A deep understanding here distinguishes a "coder" from a "software engineer".

### Planned Modules (Future)

#### Module 1.3: Compilers, Interpreters & Runtimes
**Goal:** Understand how code becomes execution.
*   **Compilation Pipeline:** Lexing, Parsing, Semantic Analysis, IR (Intermediate Representation), Code Generation.
*   **Runtime Environments:** Stack Frames, Calling Conventions, ABI (Application Binary Interface).
*   **Memory Safety:** Manual management (C/C++) vs. Garbage Collection (Tracing, Mark-and-Sweep, Generational GC).
*   **JIT Compilation:** How V8 or JVM optimizes code at runtime (Hot spots, de-optimization).

#### Module 1.4: Advanced Data Structures & Algorithms
**Goal:** Optimize for performance and scale.
*   **Probabilistic Data Structures:** Bloom Filters, Count-Min Sketch, HyperLogLog.
*   **Advanced Trees:** B-Trees & B+ Trees (Database indexing), LSM Trees (Log-Structured Merge-trees), Red-Black Trees.
*   **Graph Algorithms:** Dijkstra, A*, Max Flow/Min Cut, Topological Sort.
*   **Distributed Algorithms:** Consistent Hashing, Merkle Trees.

## Module 1.1: Operating Systems Internals — Process & Memory Management

### 1. Process Scheduling: The Linux CFS (Completely Fair Scheduler)

The kernel's job is to illusion of "simultaneous" execution on limited hardware. The **Completely Fair Scheduler (CFS)** is the default Linux scheduler (since 2.6.23) for normal tasks (`SCHED_NORMAL`).

#### 1.1 Core Concept: Ideal Multi-Tasking
CFS aims to model an "ideal, precise multi-tasking CPU". On such hardware, if 2 processes run, each gets exactly 50% power instantly. On real hardware, we must time-slice.

#### 1.2 The Implementation Details
*   **Virtual Runtime (`vruntime`):**
    *   Instead of fixed time slices, CFS tracks how long a task *has run*.
    *   `vruntime` is weighted by priority (`nice` value).
    *   **Formula:** `vruntime += delta_exec * (NICE_0_LOAD / task_load_weight)`
    *   Lower priority tasks (high `nice`) gain `vruntime` faster, so they get pushed to the back of the line sooner.
    *   Higher priority tasks (low `nice`) gain `vruntime` slower, allowing them to run longer before catching up to others.

*   **Data Structure: Red-Black Tree:**
    *   Run-queue is not a queue; it's a **time-ordered Red-Black Tree**.
    *   **Key:** `vruntime`.
    *   **Leftmost Node:** The task with the lowest `vruntime`. This is *always* the next task to run.
    *   **Complexity:** Insert/Delete/Search is **O(log N)**.

*   **Granularity & Latency:**
    *   `sched_latency_ns`: The period in which all runnable tasks should get at least one turn (default ~6ms - 24ms).
    *   `min_granularity_ns`: Minimum time a task runs before preemption (prevents thrashing).

### 2. Context Switching Internals

When the scheduler picks a new task, a **Context Switch** occurs. This is pure overhead, so it must be fast.

#### 2.1 The Sequence
1.  **Interrupt/Trap:** Timer interrupt or System Call triggers kernel mode.
2.  **Save State:**
    *   **General Purpose Registers:** `RAX`, `RBX`, `RCX`... saved to the current Process Control Block (PCB) or Kernel Stack.
    *   **Instruction Pointer (`RIP`):** Where were we?
    *   **Stack Pointer (`RSP`):** Where was the stack?
3.  **Switch Memory Space (Expensive):**
    *   Update `CR3` Control Register to point to the new process's **Page Global Directory (PGD)** / **PML4**.
    *   **Consequence:** This invalidates the **TLB (Translation Lookaside Buffer)** (unless PCID feature is used), causing immediate performance dips as the CPU relearns memory mappings.
4.  **Restore State:** Load registers from the new PCB.
5.  **Execution:** `IRET` (Interrupt Return) jumps to the new `RIP`.

### 3. Virtual Memory & Paging (x86_64)

Processes see a flat, continuous virtual memory space. The CPU (MMU) translates this to fragmented physical RAM.

#### 3.1 4-Level Paging Walk (Standard x86_64)
A virtual address is 48 bits effective (canonical form).
1.  **PML4 (Page Map Level 4):** Bits 47-39 index into this table. Points to PDPT.
2.  **PDPT (Page Directory Pointer Table):** Bits 38-30. Points to Page Directory.
3.  **PD (Page Directory):** Bits 29-21. Points to Page Table.
4.  **PT (Page Table):** Bits 20-12. Points to Physical Page Frame (4KB).
5.  **Offset:** Bits 11-0. Exact byte in the 4KB page.

**Hardware Cache:** **TLB (Translation Lookaside Buffer)** stores the result of this walk. A "TLB Miss" is expensive (requires 4 memory reads to find the address).

### 4. User-Space Memory Allocators: `malloc` Wars

The kernel gives large blocks (via `mmap` or `sbrk`). User-space allocators manage the sub-division.

#### 4.1 glibc `malloc` (ptmalloc)
*   **Structure:** Chunk-based. Each block has a header with size.
*   **Bins:** Free chunks are kept in linked lists ("bins") based on size (Fastbins, Smallbins, Largebins, Unsorted bin).
*   **Concurrency:** Uses **Arenas** (one per core/thread typically) to reduce lock contention.
*   **Pros:** Standard, general-purpose.
*   **Cons:** Can suffer from fragmentation; "best-fit" logic can be slow.

#### 4.2 jemalloc (Facebook, Firefox, Rust default)
*   **Philosophy:** Focus on **Fragmentation Avoidance** and **Concurrency**.
*   **Design:**
    *   **Small Objects:** Grouped into **Runs**. A run contains many objects of the same **Size Class**.
    *   **Bitmap:** Uses bitmaps to track used/free slots (fast).
    *   **Thread Caches:** Aggressive caching per-thread to avoid locks entirely for common ops.
*   **Win:** Highly predictable memory footprint.

#### 4.3 tcmalloc (Google)
*   **Philosophy:** Speed above all.
*   **Design:**
    *   **Thread-Local Cache:** Satisfies most allocations instantly (0 locks).
    *   **Central Free List:** When thread cache is empty, fetch a batch of objects here.
    *   **Page Heap:** Manages large memory spans.

## Module 1.1a: The CPU & The Kernel Boundary Deep Dive

### 1. Hardware Privilege: Protection Rings (x86_64)

The CPU enforces security through **Protection Rings** (Domains). Although x86 supports 4 rings (0-3), Linux only uses two: **Ring 0 (Kernel Mode)** and **Ring 3 (User Mode)**.

#### 1.1 The Mechanics of Privilege
*   **CPL (Current Privilege Level):** Stored in the bottom 2 bits of the `CS` (Code Segment) register.
    *   `00` = Ring 0 (Kernel).
    *   `11` = Ring 3 (User).
*   **DPL (Descriptor Privilege Level):** Stored in the GDT/IDT entry. It defines "How privileged do you need to be to access this?".
*   **RPL (Requester Privilege Level):** Stored in the Selector (e.g., when you push a segment to DS/SS). It ensures a kernel process acting on behalf of a user cannot accidentally access kernel data (The "Confused Deputy" problem).
*   **The Rule:** Access is granted if `MAX(CPL, RPL) <= DPL`.
    *   *Interpretation:* "Your current rank (CPL) AND the rank of the person asking you (RPL) must both be higher (numerically lower) than the rank of the target data (DPL)."

### 2. Crossing the Boundary: System Calls

How does a User (Ring 3) talk to the Kernel (Ring 0)?

#### 2.1 The Legacy Way: `int 0x80`
*   **Mechanism:** Software Interrupt.
*   **Steps:**
    1.  User loads `EAX` with Syscall ID (e.g., `1` for `exit`).
    2.  User executes `int 0x80`.
    3.  CPU looks up vector `0x80` in the **IDT** (Interrupt Descriptor Table).
    4.  CPU checks DPL of the gate (must be Ring 3 accessible).
    5.  CPU saves `CS`, `EIP`, `EFLAGS`, `SS`, `ESP` to the **Kernel Stack**.
    6.  CPU switches to Ring 0 and jumps to the handler.
*   **Performance:** Slow. Requires memory lookups (IDT, GDT) and complex permission checks.

#### 2.2 The Modern Way: `syscall` (x86_64) / `sysenter` (Intel 32-bit)
*   **Mechanism:** Specialized Hardware Instruction (Opcode `0F 05`).
*   **Steps:**
    1.  User loads `RAX` with Syscall ID.
    2.  User executes `syscall`.
    3.  **Hardware Magic:**
        *   Saves `RIP` to `RCX`.
        *   Saves `RFLAGS` to `R11`.
        *   Loads `RIP` from **MSR_LSTAR** (Long System Target Address Register) - A dedicated CPU register pre-loaded by Linux at boot time.
        *   Loads `CS` and `SS` from **MSR_STAR**.
        *   Forces CPL to Ring 0.
        *   **NO STACK SWITCH:** It does *not* automatically switch the stack pointer (`RSP`). The kernel entry point *must* immediately switch to a kernel stack (usually found in `GS` segment per-cpu data) before doing *anything* else.
*   **Performance:** Extremely fast. Bypass IDT/GDT lookups entirely.

### 3. Interrupt Handling & The IDT

When hardware needs attention (Keyboard, Network Card, Timer), it fires an interrupt.

#### 3.1 The IDT (Interrupt Descriptor Table)
*   An array of 256 **Gate Descriptors** (16 bytes each in 64-bit mode).
*   **Location:** Pointed to by the **IDTR** (IDT Register).
*   **Layout:**
    *   **0-31:** Exceptions (Faults, Traps, Aborts). E.g., `#PF` (Page Fault - Vector 14), `#GP` (General Protection Fault - Vector 13).
    *   **32-255:** User Defined / Hardware Interrupts (IRQs).

#### 3.2 The Interrupt Sequence
1.  **Assert:** Hardware line (APIC) signals CPU.
2.  **Vector:** CPU reads vector number (e.g., 32 for Timer).
3.  **Lookup:** CPU reads `IDT[Vector]`.
4.  **Gate:**
    *   **Interrupt Gate:** Clears `IF` (Interrupt Flag) in `RFLAGS` (Disables other interrupts).
    *   **Trap Gate:** Leaves `IF` alone (Allows nesting).
5.  **IST Switch (Critical):**
    *   If the IDT entry has a non-zero **IST (Interrupt Stack Table)** index, the CPU forcibly switches `RSP` to a known good stack defined in the **TSS**.
    *   *Why?* If we double-fault because the kernel stack corrupted, we need a fresh stack to handle the panic.
6.  **Stack Frame:** CPU pushes `SS`, `RSP`, `RFLAGS`, `CS`, `RIP`, `Error Code` (optional).
7.  **Handler:** Jumps to ISR (Interrupt Service Routine).

### 4. The TSS (Task State Segment) in x86_64

In 32-bit, TSS was used for hardware Context Switching. In 64-bit, that's gone. What is it used for now?

1.  **RSP0:** The location of the Ring 0 Stack. When a privilege change happens (Ring 3 -> Ring 0), the CPU *must* know where the kernel stack is. It reads `TSS.RSP0`.
2.  **IST (Interrupt Stack Table):** 7 pointers to "Emergency Stacks" (Double Faults, NMIs, Machine Checks).
3.  **I/O Bitmap:** Permission bits for `in` / `out` instructions.

*Linux has one TSS per CPU.*

## Module 1.1b: Scheduler Data Structures Deep Dive

### 1. The Red-Black Tree (rbtree) in CFS

The **Completely Fair Scheduler (CFS)** abandoned the O(1) scheduler's array-of-queues in favor of a tree structure.

#### 1.1 Why not AVL?
Both are Self-Balancing Binary Search Trees (BSTs).
*   **AVL Trees:** Strictly balanced (Height difference $\le 1$). Lookups are faster ($1.44 \log N$), but Insertion/Deletion requires more rotations to rebalance.
*   **Red-Black Trees:** Relaxed balancing (Longest path $\le 2 \times$ Shortest path). Lookups are slightly slower ($2 \log N$), but Insertion/Deletion is much cheaper (O(1) amortized rebalancing).
*   **The Kernel's Choice:** Schedulers mutate the tree constantly (every task wake-up, sleep, or tick). High churn favors the cheaper write cost of RB-Trees.

#### 1.2 Kernel Implementation Details (`lib/rbtree.c`)
*   **Intrusive Data Structure:** The `rb_node` is embedded *inside* the `task_struct` (via `sched_entity`). This avoids `malloc` overhead.
*   **The "Leftmost" Cache:**
    *   Finding the node with the smallest `vruntime` (the next task to run) is $O(\log N)$ in a standard BST.
    *   **Optimization:** CFS caches the pointer to the `rb_leftmost` node.
    *   **Result:** `pick_next_task` is effectively **O(1)**. The tree is only traversed when adding/removing tasks.

### 2. Per-CPU Variables & Locking

Scalability kills. If all CPUs fought over one global Runqueue, the locking overhead would destroy performance on 64-core systems.

#### 2.1 The Per-CPU Paradigm
*   **Concept:** Each CPU has its own private memory area. CPU 0 writes to `var_cpu0`, CPU 1 writes to `var_cpu1`. No locks needed for local access.
*   **Hardware Implementation (x86_64):**
    *   The `GS` segment register holds the base address of the per-cpu area.
    *   **Access:** `mov rax, gs:[offset]`.
    *   **Context Switch Safety:** `swapgs` instruction swaps the user-space GS base with the kernel-space GS base upon entry (syscall/interrupt).

#### 2.2 The Runqueue (`rq`)
*   Every CPU has its own `struct rq`.
*   **Locking:** `rq->lock`.
    *   Local scheduler operations (picking next task) only acquire the *local* lock.
    *   **Result:** Near-perfect linear scalability for CPU-bound workloads.

### 3. Load Balancing & Work Stealing

If CPU 0 has 10 tasks and CPU 1 has 0, we must balance. But locking remote runqueues is expensive.

#### 3.1 Hierarchical Scheduling Domains
*   CPUs are grouped into **Scheduling Domains** (based on topology: SMT threads -> Cores -> Sockets -> NUMA nodes).
*   Balancing happens more frequently at the bottom (cheap) and less frequently at the top (expensive).

#### 3.2 The Mechanisms
1.  **Periodic Load Balance:**
    *   Triggered by timer (`scheduler_tick`).
    *   Calculates "Load" (Combination of task weight + CPU utilization).
    *   If imbalance > Threshold, it locks the remote queue and pulls tasks.
2.  **Idle Balance (Work Stealing):**
    *   Triggered when a CPU is about to go `idle` (`schedule()` finds no tasks).
    *   It aggressively searches other CPUs' runqueues to "steal" work.
    *   **Order:** Check sibling threads first (L1 cache warm), then same socket (L3 warm), then remote NUMA nodes.

#### 3.3 The "Misfit" Task
*   In **Heterogeneous Systems** (ARM big.LITTLE / Intel Hybrid), a "heavy" task might be stuck on a "LITTLE" (efficient) core.
*   CFS detects this "Misfit" and actively pushes the task to a "big" (performance) core, even if the load numbers technically look balanced.

## Module 1.1c: Memory Management Algorithms Deep Dive

### 1. Kernel Space Allocators (Physical Memory)

The kernel manages physical RAM. It must satisfy requests for contiguous page frames (e.g., for DMA) and small objects (e.g., `task_struct`).

#### 1.1 The Buddy System (Page Allocator)
The **Buddy System** solves the problem of External Fragmentation for large, contiguous blocks.
*   **The Algorithm:**
    *   Memory is managed in lists of **Orders** (0 to 11). Order $N$ represents $2^N$ pages.
    *   **Allocation:** Request for size $S$.
        1.  Calculate minimal Order $K$ such that $2^K \times PageSize \ge S$.
        2.  Check list for Order $K$.
        3.  If empty, go to Order $K+1$.
        4.  **Split:** Take block of $K+1$, split into two buddies of Order $K$. Use one, add other to Order $K$ list. Recursive until found.
    *   **Deallocation (Coalescing):**
        1.  Free block $B$.
        2.  Check address of "Buddy" ($Address \oplus Size$).
        3.  If Buddy is also free, **Merge** into block of Order $K+1$.
        4.  Repeat.

#### 1.2 The SLAB/SLUB/SLOB Allocators (Object Allocator)
The Buddy System is too coarse (4KB min). We need small objects (32 bytes, 128 bytes).
*   **SLAB (Legacy):**
    *   Uses caching heavily. Each object type (inode, dentry) has a specific cache.
    *   Complex metadata. Good for older hardware, bad for high-core-count scaling.
*   **SLUB (Unqueued - Default):**
    *   **Design:** Simplifies metadata. Most metadata is stored in the `struct page` of the physical frame itself, not in separate headers.
    *   **Performance:** Better CPU cache locality. Merges slabs of similar size classes.
*   **SLOB (Simple - Embedded):**
    *   Just a linked list of blocks. High fragmentation, but tiny code footprint. (Removed in Linux 6.4).

### 2. User Space Allocators (`malloc` Internals)

How does `glibc` or `dlmalloc` manage the heap provided by `brk`/`mmap`?

#### 2.1 The Chunk Structure & Boundary Tags
*   **Memory Layout:**
    ```
    [ Header: Size | Flags ]
    [      User Data       ]
    [ Footer: Size         ] (Only if free, usually)
    ```
*   **Boundary Tags (Knuth's Algorithm):**
    *   **Problem:** When freeing pointer `P`, is `P - 1` free? How do we find the start of the previous block?
    *   **Solution:** The **Footer** of the *previous* block sits right before the **Header** of the *current* block.
    *   **Coalescing:**
        1.  Check `(P - 4 bytes)`. It's the previous block's footer. Get size $S_{prev}$.
        2.  Go to `P - S_{prev}` to find the previous header.
        3.  Check previous header's "Free" bit. If free, merge.
        4.  Check next block's header. If free, merge.

#### 2.2 Binning Strategies
*   **Fastbins (LIFO):**
    *   Small chunks (16-80 bytes).
    *   Stored in singly-linked lists.
    *   **No Coalescing:** Speed optimization. "If I freed a 32-byte chunk, I'll likely need a 32-byte chunk soon."
*   **Smallbins (FIFO):**
    *   Chunks < 512 bytes.
    *   Doubly-linked lists.
    *   Coalescing enabled.
*   **Unsorted Bin:**
    *   The "Cache" of free chunks.
    *   When a chunk is freed, it goes here first.
    *   If `malloc` doesn't find a chunk in Fast/Small bins, it scans Unsorted. If a chunk here fits, take it. If not, move it to the correct Small/Large bin.
*   **Largebins (Sorted):**
    *   > 512 bytes.
    *   Sorted by size (Skip list or Tree) to support "Best Fit" allocation.

#### 2.3 `brk` vs `mmap`
*   **`brk`:** Moves the "program break" (end of heap) up. Fast, but memory must be contiguous. Can't return memory to OS easily if "middle" is still used.
*   **`mmap`:** Allocates distinct anonymous pages. Slower syscall, but can be freed individually. Used for large allocations (> 128KB).

## Module 1.1d: File Systems & Storage Deep Dive

### 1. The VFS (Virtual File System)
VFS is the abstraction layer that allows Linux to handle `ext4`, `NTFS`, and `/proc` transparently.

#### 1.1 The Big Four Objects
1.  **Superblock:** Represents a mounted filesystem (e.g., `/dev/sda1` on `/`).
    *   Stores: Block size, Magic Number, Inode/Block usage bitmaps.
    *   *Kernel Op:* `alloc_super()`.
2.  **Inode (Index Node):** Represents a specific object (file/directory).
    *   Stores: Permissions, UID, GID, Size, Time, **Pointers to Data Blocks**.
    *   *Key:* Unique ID Number. Does **NOT** store the filename.
3.  **Dentry (Directory Entry):** Represents a path component.
    *   Links "Filename" -> "Inode".
    *   Example: Path `/home/user` has three dentries: `/`, `home`, `user`.
    *   **Dentry Cache (dcache):** Huge hash table (`d_lookup`) to speed up path resolution.
4.  **File:** Represents an open file instance (File Descriptor).
    *   Stores: Current Offset (`f_pos`), Mode (Read/Write).
    *   *Note:* Two processes can have two `File` objects pointing to the same `Inode`.

### 2. Ext4 Internals: The Standard

#### 2.1 Inode Structure & Data Addressing
*   **Legacy (Ext2/3):** Block Pointers.
    *   12 Direct Pointers.
    *   1 Indirect (Points to a block of pointers).
    *   1 Doubly Indirect.
    *   1 Triply Indirect.
    *   *Problem:* Huge metadata overhead for large contiguous files.
*   **Modern (Ext4):** **Extents**.
    *   Instead of listing every block, it says: "Start at Block 5000, Length 100".
    *   Stored in a **Tree** structure inside the inode (`i_block` array).
    *   *Benefit:* CPU/Disk efficient for large files.

#### 2.2 Journaling (Write-Ahead Logging)
Protects metadata integrity during crashes.
*   **Mode: `data=ordered` (Default):**
    1.  Write **Data** to main disk.
    2.  Write **Metadata** to Journal.
    3.  **Commit** Journal.
    4.  Checkpoint (Move metadata to final location).
    *   *Safety:* File content is guaranteed to be "new" or "old", never garbage.
*   **Mode: `data=writeback`:**
    *   Metadata is journaled, Data is not ordered.
    *   *Risk:* After crash, file might contain old garbage data from deleted files.
*   **Mode: `data=journal`:**
    *   Write **Data AND Metadata** to journal first.
    *   *Safety:* Maximum.
    *   *Cost:* Writes everything twice. Slow.

### 3. High-Performance I/O: `io_uring` vs `epoll`

#### 3.1 The "Ready" Model: `epoll`
*   **Mechanism:** "Tell me when I can read."
*   **Flow:**
    1.  `epoll_wait()` (Sleep until ready).
    2.  Wake up.
    3.  `read()` (Syscall).
    4.  Kernel copies data to user buffer.
    5.  Return.
*   **Overhead:** Syscall per operation + Data Copy.

#### 3.2 The "Completion" Model: `io_uring` (Linux 5.1+)
*   **Mechanism:** "Here is a buffer. Fill it and wake me when done."
*   **Architecture:** Two Shared Ring Buffers (mapped in User & Kernel space).
    *   **Submission Queue (SQ):** User pushes requests.
    *   **Completion Queue (CQ):** Kernel pushes results.
*   **Zero-Syscall Mode:**
    *   If `IORING_SETUP_SQPOLL` is set, a kernel thread polls the SQ.
    *   User just pushes to ring. Kernel picks it up. **Zero syscalls.**
*   **Performance:** Can reach millions of IOPS per core. Used by modern DBs (Postgres/MySQL) and Web Servers.

## Module 1.2: TCP/IP & Congestion Control Deep Dive

### 1. The TCP State Machine & Lifecycle

#### 1.1 Connection Establishment (3-Way Handshake)
1.  **SYN:** Client sends `SYN`, enters `SYN_SENT`.
2.  **SYN-ACK:** Server receives `SYN`, sends `SYN-ACK`, enters `SYN_RCVD`.
3.  **ACK:** Client receives `SYN-ACK`, sends `ACK`, enters `ESTABLISHED`. Server receives `ACK`, enters `ESTABLISHED`.

#### 1.2 Connection Termination (4-Way Teardown)
This is where complexity lives.
1.  **Active Close (Client):** Sends `FIN`. Enters `FIN_WAIT_1`.
2.  **Passive Close (Server):** Receives `FIN`. Sends `ACK`. Enters `CLOSE_WAIT`.
    *   *Critical:* The Server App *must* detect EOF and call `close()` explicitly. If not, the socket hangs in `CLOSE_WAIT` forever (Resource Leak).
3.  **Server Sends FIN:** Server calls `close()`, sends `FIN`. Enters `LAST_ACK`.
4.  **Client Receives FIN:** Sends `ACK`. Enters **`TIME_WAIT`**.
    *   *Purpose:* Wait 2xMSL (Max Segment Lifetime) to catch delayed packets.
    *   *Problem:* High-load servers run out of ephemeral ports if too many sockets are in `TIME_WAIT`. (Fix: `SO_REUSEADDR` or `tcp_tw_reuse`).

### 2. Window Management: Flow vs. Congestion

Transmission rate is limited by the **Minimum** of two windows:
$$Rate = \min(rwnd, cwnd)$$

#### 2.1 Flow Control (`rwnd` - Receiver Window)
*   **Goal:** Don't drown the receiver.
*   **Mechanism:** Receiver advertises "I have 64KB buffer space left" in every ACK header.
*   **Window Scaling:** Original TCP limit was 64KB ($2^{16}$). RFC 1323 added "Window Scale" option to shift bits, allowing GB-sized windows (LFN - Long Fat Networks).

#### 2.2 Congestion Control (`cwnd` - Congestion Window)
*   **Goal:** Don't drown the network (routers/switches).
*   **Mechanism:** Sender maintains a hidden variable `cwnd`. It starts small and grows until packet loss occurs.

### 3. Congestion Algorithms: The Evolution

#### 3.1 TCP Reno (The Classic - Loss Based)
*   **Slow Start:** Double `cwnd` every RTT (Exponential).
*   **Congestion Avoidance:** Upon `ssthresh`, increase `cwnd` linearly (+1 MSS per RTT).
*   **AIMD:** Additive Increase, Multiplicative Decrease.
    *   Packet Loss? Cut `cwnd` in half.
*   **Flaw:** In high-speed networks, recovering from a 50% cut takes too long.

#### 3.2 TCP CUBIC (The Standard - Loss Based)
Default in Linux since 2.6.19.
*   **Concept:** Instead of Linear increase, use a **Cubic Function** ($f(t) = Ct^3$).
*   **Mechanism:**
    *   When loss happens, remember `W_max`.
    *   Ramp up fast to regain `W_max`, slow down near the limit, then accelerate fast if no loss is found.
*   **Benefit:** Independent of RTT. Very efficient on High Bandwidth-Delay Product (BDP) links (e.g., Transatlantic Fiber).

#### 3.3 TCP BBR (The Modern - Model Based)
Google's "Bottleneck Bandwidth and RTT" (2016).
*   **Paradigm Shift:** **Loss $\neq$ Congestion.**
    *   Loss can be random (WiFi noise). Reno/Cubic panic and slow down.
*   **Mechanism:**
    *   Estimates **BtlBw** (Bottleneck Bandwidth) and **RTprop** (Round Trip Propagation).
    *   **Pacing:** Sends data at exactly the BtlBw rate.
    *   Does not fill buffers (avoids Bufferbloat).
*   **Result:** High throughput even with 1-5% packet loss. Critical for modern internet.

## Module 1.2b: Modern Application Protocols (HTTP/2, HTTP/3, TLS)

### 1. The Head-of-Line (HOL) Blocking Problem

The history of HTTP is a history of fighting HOL Blocking.
*   **HTTP/1.0:** New TCP connection for every file. (Slow, high RTT overhead).
*   **HTTP/1.1:**
    *   **Keep-Alive:** Reuse TCP connection.
    *   **Pipelining:** Send `Req1, Req2` without waiting.
    *   **The HOL Problem:** Server must send `Resp1` before `Resp2`. If `Req1` needs a DB Query (2s) and `Req2` is a static image (1ms), the image is blocked for 2s.
*   **HTTP/2 (RFC 7540):**
    *   **Multiplexing:** Split messages into binary **Frames** with Stream IDs.
    *   **Interleaving:** `Stream 1` and `Stream 2` frames are mixed on the wire.
    *   **App-Layer HOL Solved:** Fast static assets are not blocked by slow DB queries.
    *   **The *New* HOL Problem (TCP Level):** TCP guarantees order. If Packet 10 is lost, Packet 11 (even if it belongs to a different, independent stream) sits in the kernel buffer waiting for Packet 10. **Result:** On lossy networks, HTTP/2 is *slower* than HTTP/1.1.

### 2. HTTP/3 & QUIC (RFC 9000)

Google (gQUIC) -> IETF (QUIC). The move to UDP.

#### 2.1 The Architecture
*   **Transport:** UDP (User Datagram Protocol). No kernel handshake.
*   **Reliability:** Implemented in User Space (on top of UDP).
*   **Streams:** QUIC streams are independent. Loss of a packet in Stream A *does not* block Stream B.

#### 2.2 Key Features
1.  **Connection Migration:**
    *   TCP uses 4-tuple (SrcIP, SrcPort, DstIP, DstPort). Switching from WiFi to LTE changes SrcIP -> Connection breaks.
    *   QUIC uses **CID (Connection ID)**. A 64-bit ID persists across IP changes. Seamless handover.
2.  **QPACK:**
    *   HTTP/2 used **HPACK**. It relied on a global stateful table. If a packet updating the table is lost, all future header decoding stalls.
    *   HTTP/3 uses **QPACK**. It separates the "Compression Context" stream from the "Data" stream. Allowed out-of-order delivery without breaking compression context.

### 3. TLS 1.3 Deep Dive (RFC 8446)

Encryption is no longer a layer *on top*; in QUIC, it's baked in.

#### 3.1 Handshake Latency
*   **TLS 1.2:** 2-RTT (ClientHello -> ServerHello -> KeyExchange -> Finished).
*   **TLS 1.3:** 1-RTT.
    *   Client guesses the Key Share (usually Elliptic Curve Diffie-Hellman - X25519) and sends it in the *first* packet (ClientHello).
    *   If Server accepts, it sends ServerHello + Finished. Immediate encryption.

#### 3.2 0-RTT Resumption (Early Data)
*   **Mechanism:** If Client has talked to Server before, they share a **PSK (Pre-Shared Key)** or Session Ticket.
*   **Action:** Client sends encrypted HTTP Request *inside* the very first packet (ClientHello).
*   **The Risk: Replay Attacks.**
    *   Attacker captures the 0-RTT packet.
    *   Attacker resends it 10 times.
    *   If the request was `POST /pay-money`, user pays 10 times.
*   **Mitigation:**
    *   Server must implement **Anti-Replay** (Time windows, Nonce cache).
    *   **Idempotency:** Browsers/Apps should ONLY use 0-RTT for Safe Methods (`GET`, `HEAD`).

### 4. Summary: The Stack Evolution

| Layer | Old Stack | New Stack (HTTP/3) |
| :--- | :--- | :--- |
| **App** | HTTP/1.1 or HTTP/2 | HTTP/3 |
| **Security** | TLS 1.2 | TLS 1.3 (Integrated) |
| **Transport** | TCP | QUIC |
| **Network** | IP | IP |
| **Link** | UDP | UDP |
