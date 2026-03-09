# Phase 6: Modern Backend & Frontend — Complete Reference

**Date:** 2026-02-06 | **Status:** Completed

## Overview & Goals

Code that runs on the server vs Code that runs in the browser.

### Planned Modules (Future)

#### Module 6.3: WebAssembly (Wasm)
**Goal:** Near-native performance in the browser.
*   **Architecture:** Stack machine. Linear Memory.
*   **Use Cases:** Video editing (Figma), 3D Games (Unity), Cryptography.

## Module 6.1: Backend Concurrency Models

### 1. Node.js: The Event Loop & Libuv

JavaScript is single-threaded, but Node.js handles millions of connections. How? **Asynchronous Non-Blocking I/O**.

#### 1.1 The Engine: Libuv
*   A C library that provides the thread pool (for FS/DNS) and the Event Loop logic.
*   **Offloading:** JS thread calls `fs.readFile()`. Libuv throws it into a thread pool thread. JS thread continues. When read finishes, Libuv pushes the callback to the queue.

#### 1.2 The Phases (Macrotasks)
1.  **Timers:** `setTimeout`, `setInterval`.
2.  **Pending:** System errors (e.g., TCP errors).
3.  **Poll (The Core):** Waits for I/O (Incoming request, DB response). Blocks here if idle.
4.  **Check:** `setImmediate`.
5.  **Close:** `socket.on('close')`.

#### 1.3 The Microtask Queue (The VIP Lane)
*   **Priority:** Processed **between** every phase.
*   **`process.nextTick()`:** Highest priority. Runs immediately after current operation.
*   **Promises (`.then`):** Runs after nextTick but before Macrotasks.
*   *Danger:* An infinite loop of `nextTick` will starve the I/O loop.

### 2. Go: The M:N Scheduler

Go isn't single-threaded, but it doesn't use 1 OS Thread per request (too heavy - 1MB stack).

#### 2.1 The G-M-P Model
*   **G (Goroutine):** 2KB stack. The user logic.
*   **M (Machine):** An OS Thread. Expensive.
*   **P (Processor):** A logical CPU core. Has a **Local Run Queue**.

#### 2.2 Work Stealing
*   If `Processor A` finishes its queue, it doesn't sleep.
*   It **steals** half the Goroutines from `Processor B`.
*   *Result:* All cores stay 100% saturated with useful work.

### 3. Java: Project Loom (Virtual Threads)

Java traditionally used 1 OS Thread per Request. Result: C10K problem (10k threads = Crash).

#### 3.1 Virtual Threads (Since Java 21)
*   **Concept:** Millions of Virtual Threads map to a few **Carrier Threads** (OS Threads).
*   **Mounting/Unmounting:**
    *   When Virtual Thread does blocking I/O (DB call), JVM copies its stack (Continuation) to Heap.
    *   Carrier Thread is freed to run another Virtual Thread.
    *   When I/O finishes, stack is copied back (Mounted) to Carrier.
*   *Impact:* You can write simple, blocking style code (`user = repo.findById(id)`), but get Async performance.

## Module 6.2: Frontend Engineering

### 1. Rendering Patterns & Hydration

#### 1.1 The "Uncanny Valley" of Hydration
*   **Process:** Server sends HTML (fast). Browser paints it. JS downloads. React "hydrates" (attaches listeners).
*   **The Mismatch Error:** If Server HTML $\neq$ Client Expected HTML (e.g., `<div>{Math.random()}</div>`), React throws a warning and might **discard the entire server tree** and re-render from scratch. Performance disaster.
*   **Fix:** Ensure deterministic rendering. Use `useEffect` for browser-specific data (`window.width`).

#### 1.2 The Critical Rendering Path (CRP)
*   **Steps:**
    1.  HTML -> DOM.
    2.  CSS -> CSSOM.
    3.  DOM + CSSOM -> **Render Tree** (Visible elements only).
    4.  **Layout** (Geometry/Reflow): Calculate X,Y, Width, Height.
    5.  **Paint:** Fill pixels.
    6.  **Composite:** Layering (z-index, transforms).
*   **Optimization:**
    *   **Render Blocking Resources:** CSS is render-blocking. JS is render-blocking (unless `defer`/`async`).
    *   **CSS Triggers:** Changing `width` triggers Layout (Expensive). Changing `transform` (GPU) triggers Composite only (Cheap).

### 2. Micro-Frontends: Module Federation

How to let Team A deploy Header independently of Team B's Footer?

#### 2.1 Webpack Module Federation
*   **Architecture:**
    *   **Host:** The main app shell.
    *   **Remote:** A separately built app (e.g., `checkout`).
*   **Mechanism:**
    *   Remote builds a `remoteEntry.js` (Manifest).
    *   Host loads `remoteEntry.js` at runtime.
    *   Host imports `checkout/Button`.
*   **Shared Dependencies:**
    *   If Host has React v18 and Remote needs React v18, Webpack **shares** the single instance. No double download.
    *   If versions differ incompatible, it downloads both (Safety).

### 3. State Management

*   **Redux:** Single Immutable State Tree. Great for debugging (Time Travel). Boilerplate heavy.
*   **Context API:** Built-in. Good for low-frequency updates (Theme, User). **Bad for high-frequency** (Text input) -> Triggers re-render of all consumers.
*   **Atomic (Recoil/Jotai):** Fine-grained updates. Only components subscribed to `atomX` re-render.
