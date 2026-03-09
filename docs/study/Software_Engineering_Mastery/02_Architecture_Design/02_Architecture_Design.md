# Phase 2: Software Architecture & Design — Complete Reference

**Date:** 2026-02-06 | **Status:** Completed

## Overview & Goals

This phase moves from "how the machine works" to "how to structure complex software".

## Module 2.1: Code-Level Architecture & Principles

### 1. SOLID Deep Dive: The Tricky Parts

#### 1.1 Liskov Substitution Principle (LSP)
Most people know "Subtypes must be substitutable". The hard part is **Variance**.
*   **Covariance (Return Types):**
    *   *Definition:* If `Dog` is a subtype of `Animal`, then `Producer<Dog>` is a subtype of `Producer<Animal>`.
    *   *Rule:* Overridden methods can return a *more specific* type.
    *   *Example:* `AnimalFactory.create()` returns `Animal`. `DogFactory.create()` returns `Dog`. Safe because caller expects `Animal` and gets `Dog`.
*   **Contravariance (Argument Types):**
    *   *Definition:* If `Dog` is a subtype of `Animal`, then `Consumer<Animal>` is a subtype of `Consumer<Dog>`.
    *   *Rule:* Overridden methods can accept a *more general* type.
    *   *Example:* `DogHandler.handle(Dog d)` can be replaced by `AnimalHandler.handle(Animal a)`. Safe because `AnimalHandler` can handle any animal, including a dog.

#### 1.2 Dependency Inversion Principle (DIP)
*   **The Rule:** High-level modules (Business Rules) should not depend on low-level modules (DB, UI). Both should depend on abstractions.
*   **The "Inversion":**
    *   *Traditional:* Controller -> Service -> Repository (Implementation). Flow of control and source code dependency point in the same direction.
    *   *Inverted:* Controller -> Service -> Repository (Interface) <- Repository (Implementation). Flow of control is the same, but source dependency is **inverted** against the flow.

### 2. Architectural Styles

#### 2.1 Clean Architecture (The Layered Onion)
*   **Structure:**
    1.  **Entities (Core):** Enterprise-wide business rules. No dependencies.
    2.  **Use Cases (Application):** Application-specific rules. Orchestrates entities.
    3.  **Interface Adapters:** Convert data from Use Cases to Format X (SQL, HTML).
    4.  **Frameworks & Drivers:** The DB, the Web Framework.
*   **The Key Rule:** Source code dependencies *always* point inward.

#### 2.2 Hexagonal Architecture (Ports & Adapters)
*   **Philosophy:** Application is a hexagon.
    *   **Inside:** The Application Core.
    *   **The Edge:** Ports (Interfaces).
    *   **Outside:** Adapters (Implementations).
*   **Types of Adapters:**
    *   **Driving (Primary):** Kickstart the app (Web Controller, CLI Command, Test Runner).
    *   **Driven (Secondary):** React to the app (SQL Adapter, Email Adapter).
*   **Benefit:** You can swap "Web Controller" for "Test Runner" and run the *exact same* business logic.

### 3. Dependency Injection (DI) Internals

How does the "Magic Container" work?

#### 3.1 Reflection-Based (Spring, Guice)
*   **Mechanism:** At startup, scan classpath. Find classes with `@Inject`. Use `Class.forName()` and `Constructor.newInstance()`.
*   **Pros:** Easy to use, very dynamic.
*   **Cons:** Slow startup (scanning), runtime errors (missing dependency found only when app runs).

#### 3.2 Code Generation-Based (Dagger, Wire)
*   **Mechanism:** Annotation Processor runs *during compilation*. It writes a new Java/Go class that looks like: `new Service(new Repository())`.
*   **Pros:** Zero reflection overhead, compile-time safety (build fails if dependency missing), fast startup.
*   **Cons:** Boilerplate setup, harder to understand generated code.

## Module 2.2: Distributed System Patterns

### 1. Data Consistency in Microservices

The ACID guarantee of a single database is gone. We have **BASE** (Basically Available, Soft state, Eventual consistency).

#### 1.1 The Saga Pattern
When a business process spans multiple services (e.g., `Order` -> `Payment` -> `Inventory`), we use a Saga.
*   **Choreography:**
    *   *Service A* emits `OrderCreated`.
    *   *Service B* listens, deducts stock, emits `StockReserved`.
    *   *Pros:* Decoupled, simple start.
    *   *Cons:* "Cyclic dependencies", hard to visualize flow.
*   **Orchestration:**
    *   *Saga Coordinator* (State Machine) tells A: "Create Order". Tells B: "Deduct Stock".
    *   *Pros:* Centralized logic, easy error handling.
    *   *Cons:* Coordinator is a single point of failure (conceptually).

#### 1.2 Failure Handling: The "Zombie Saga"
What if the **Compensation** fails?
*   *Scenario:* Money deducted. Stock reservation failed. We try to refund money, but `PaymentService` is down.
*   *Result:* User has no stock and less money. Inconsistent state.
*   *Solution:* **Idempotent Retry**. The Compensation transaction *must* be retried until it succeeds. It cannot be allowed to fail permanently. Manual intervention queues are the last resort.

#### 1.3 The Transactional Outbox Pattern
**Problem:** You save `Order` to DB, but the `EventBus` crashes before you publish `OrderCreated`. Now DB has data, but downstream knows nothing.
**Solution:**
1.  **Begin Transaction.**
2.  `INSERT INTO orders ...`
3.  `INSERT INTO outbox (topic, payload) ...` (Same Tx).
4.  **Commit Transaction.** (Atomic guarantee).
5.  **Relay:**
    *   **Polling:** Background thread `SELECT * FROM outbox`. Publish. Delete. (Simple, but delays).
    *   **Log Tailing (CDC):** Debezium reads the Postgres WAL / MySQL Binlog. Publishes to Kafka. (Real-time, complex).

### 2. Resiliency Patterns

#### 2.1 Circuit Breaker State Machine
Prevents cascading failures by "failing fast".
1.  **Closed (Normal):** Requests go through. Count errors.
    *   If `ErrorRate > Threshold` (e.g., 50%): Transition to **Open**.
2.  **Open (Broken):** Fail immediately (throw `CircuitOpenException`).
    *   Wait for `SleepWindow` (e.g., 5s).
    *   Transition to **Half-Open**.
3.  **Half-Open (Test):**
    *   Allow *one* (or small N) request through.
    *   **Success?** Reset counters. Transition to **Closed**.
    *   **Fail?** Transition back to **Open**. Reset timer.

#### 2.2 Bulkhead Pattern
*   *Concept:* Ship compartments. If one floods, the ship floats.
*   *Impl:* Thread Pools / Connection Pools.
*   *Scenario:* `Service A` calls `Service B` (slow) and `Service C` (fast).
*   *Without Bulkhead:* All threads get stuck waiting for B. Service C calls fail because no threads are left.
*   *With Bulkhead:* Pool B has 10 threads. Pool C has 10 threads. B exhaustion does not kill C.

#### 2.3 Retry with Exponential Backoff & Jitter
*   **Backoff:** Wait 1s, 2s, 4s, 8s. (Give system time to recover).
*   **Jitter:** Wait `Random(0.8, 1.2) * 2^n`.
    *   *Why?* If 1000 clients fail at once, and all retry exactly at 2.00s, they create a **Retry Storm** (DDoS). Jitter spreads them out.

## Module 2.3: High-Performance System Design

### 1. Caching Strategies & Algorithms

Caching is the art of storing expensive data in cheap-to-access memory.

#### 1.1 Implementation Patterns
*   **Cache-Aside (Lazy Loading):** App checks Cache. If miss, App reads DB, App updates Cache.
    *   *Pros:* Resilient to cache failure.
    *   *Cons:* Stale data potential. Thundering Herd risk on cold start.
*   **Read-Through:** App asks Cache. If miss, Cache asks DB. App never touches DB.
*   **Write-Through:** App writes to Cache. Cache writes to DB synchronously.
    *   *Pros:* Data consistency.
    *   *Cons:* Higher write latency.
*   **Write-Back (Write-Behind):** App writes to Cache. Cache acknowledges immediately. Cache writes to DB asynchronously (queue).
    *   *Pros:* Lowest write latency.
    *   *Cons:* Data loss if Cache crashes before flush.

#### 1.2 The "Thundering Herd" Problem
*   **Scenario:** Cache key `product_123` expires. 1000 requests arrive simultaneously.
*   **Result:** All 1000 requests see "Miss". All 1000 requests query the DB. DB dies.
*   **Solution:** **Probabilistic Early Expiration** (X-Fetch).
    *   If `TTL - Now < gap`, a single request recomputes the value while others serve the "stale" but valid data.

#### 1.3 Modern Eviction: TinyLFU (Window TinyLFU)
Used in Caffeine (Java) and Ristretto (Go). Superior to LRU.
*   **The Problem with LRU:** A one-time scan of a large database flushes "hot" items from the cache.
*   **TinyLFU Architecture:**
    1.  **Admission Policy (Doorkeeper):** Uses a **Bloom Filter**.
        *   New item comes. Is it in Bloom Filter?
        *   No: Add to Bloom Filter. Drop it (Don't cache).
        *   Yes: It's seen twice. Consider caching.
    2.  **Frequency Sketch (Count-Min Sketch):**
        *   Tracks frequency of *all* items (even those not in cache) using probabilistic counters (4-bit).
    3.  **Eviction:**
        *   Compare `Frequency(Candidate)` vs `Frequency(Victim)`.
        *   If Candidate is "hotter", evict Victim.
*   **Result:** "Scan Resistant". A million one-time reads won't evict the heavy hitters.

### 2. Horizontal Scaling & Sharding

#### 2.1 Consistent Hashing
How to distribute 1TB data across 4 nodes? `Hash(key) % 4`.
*   **Problem:** Add Node 5. `Hash(key) % 5` changes *almost every* mapping. 80% of data must move.
*   **Consistent Hashing:**
    *   Map Nodes to a **Ring** (0 to $2^{32}$).
    *   Map Keys to the Ring.
    *   Key belongs to the first Node found moving clockwise.
    *   **Add Node:** Only keys between `NewNode` and `PrevNode` move. (Minimal movement).
*   **Virtual Nodes (V-Nodes):**
    *   *Problem:* Uneven distribution. Node A might get a "large" arc of the ring.
    *   *Solution:* Node A maps to 100 random points (A1..A100). Node B maps to B1..B100.
    *   *Result:* Statistically uniform load distribution.

### 3. Distributed Theory: CAP vs PACELC

CAP is too simple for 2026.
*   **CAP:** "In a Partition (P), choose Availability (A) or Consistency (C)."
    *   *Reality:* Partitions are rare. What about the other 99.9% of the time?
*   **PACELC:**
    *   **if P (Partition):** Choose **A** or **C**.
    *   **E (Else/Normal):** Choose **L** (Latency) or **C** (Consistency).
    *   *Example (DynamoDB/Cassandra):* **PA/EL**.
        *   Partition? Available.
        *   Normal? Low Latency (Eventual Consistency).
    *   *Example (BigTable/HBase):* **PC/EC**.
        *   Partition? Stop serving (Consistent).
        *   Normal? Strong Consistency (Higher Latency).

## Module 2.4: API Design & Evolution

### 1. GraphQL Performance Deep Dive

GraphQL offers "Exact Fetching" (no over/under fetching), but introduces the **N+1 Problem**.

#### 1.1 The N+1 Problem
*   **Scenario:** Query `authors { name, books { title } }`.
*   **Execution:**
    1.  `SELECT * FROM authors` (Returns 10 authors).
    2.  For Author 1: `SELECT * FROM books WHERE author_id = 1`.
    3.  ...
    4.  For Author 10: `SELECT * FROM books WHERE author_id = 10`.
*   **Total Queries:** $1 + N = 11$. If N is 1000, DB dies.

#### 1.2 The Solution: DataLoader Pattern
*   **Mechanism:** Batching & Caching within a single request tick (Event Loop).
*   **Algorithm:**
    1.  Resolver for Author 1 calls `loader.load(1)`. Promise returns (Pending).
    2.  Resolver for Author 2 calls `loader.load(2)`. Promise returns (Pending).
    3.  ...
    4.  **End of Tick:** DataLoader sees 10 pending IDs.
    5.  **Batch Execution:** `SELECT * FROM books WHERE author_id IN (1, 2, ... 10)`.
    6.  **Distribution:** DataLoader maps results back to the promises.
*   **Result:** 2 Queries Total (O(1)).

### 2. gRPC & Protocol Buffers (Protobuf)

REST (JSON) is text-based, verbose, and untyped. gRPC is binary, strict, and fast.

#### 2.1 Why Protobuf is Faster?
*   **Binary Encoding:** JSON `{"id": 123}` is 10 bytes. Protobuf is 2-3 bytes.
*   **Field Numbers (The Secret Sauce):**
    *   Proto definition: `int32 id = 1;`
    *   On the wire, it sends `08 7B` (Field 1, Varint type, Value 123).
    *   **No Field Names:** It doesn't send the string "id". Bandwidth saved.
*   **Schema Evolution:**
    *   **Backward Compatibility:** If you rename `id` to `user_id`, the wire format (`Field 1`) stays the same. Old clients still work.
    *   **Rule:** NEVER change a Field Number.

### 3. Idempotency (Safety in Retries)

If a client sends `POST /payment`, and the network drops the response:
*   Client retries.
*   Server charges user twice.

#### 3.1 The "Idempotency-Key" Pattern (Stripe Style)
1.  **Client:** Generates UUID `key_123`. Sends header `Idempotency-Key: key_123`.
2.  **Server:**
    *   **Check:** `GET key_123` from Redis/DB.
    *   **Hit:** Return stored response (200 OK). Do NOT execute logic.
    *   **Miss:**
        1.  **Lock:** `SETNX key_123 "IN_PROGRESS"`.
        2.  **Execute:** Charge credit card.
        3.  **Save:** Update `key_123` with Response Body.
        4.  **Return:** 200 OK.
3.  **Concurrency:** If two requests with `key_123` arrive at once, the second one hits the "IN_PROGRESS" lock and waits.
