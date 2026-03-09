# Phase 4: Security & Cryptography — Complete Reference

**Date:** 2026-02-06 | **Status:** Completed

## Overview & Goals

Security is not a feature; it's a constraint.

## Module 4.1: Application Security (AppSec)

### 1. Cross-Site Scripting (XSS)

The ability to execute malicious JS in a victim's browser.

#### 1.1 Types
1.  **Reflected:** Payload comes from the URL (`?search=<script>...`). Server echoes it back in HTML.
    *   *Defense:* Output Encoding (Context-aware).
2.  **Stored:** Payload is saved in DB (e.g., Comment). Served to every visitor.
    *   *Defense:* Output Encoding + CSP.
3.  **DOM-Based:** Payload never leaves the browser. `document.location.hash` -> `innerHTML`.
    *   *Defense:* Avoid `innerHTML`, `document.write`. Use `textContent`.

#### 1.2 Content Security Policy (CSP)
*   **The Concept:** Allowlist for scripts. "Only run scripts from `mydomain.com`".
*   **The Problem:** Whitelists are hard to maintain (Google Analytics, CDNs).
*   **Modern Approach (Strict CSP):**
    *   **Nonce-based:** `<script nonce="random123">`.
    *   **`strict-dynamic`:** If a trusted script (with nonce) loads another script, trust the child too.
    *   *Header:* `Content-Security-Policy: script-src 'nonce-{random}' 'strict-dynamic';`

### 2. Cross-Site Request Forgery (CSRF)

Forcing a logged-in user to perform an action without their consent.

#### 2.1 The Attack
*   User is logged into `bank.com` (Session cookie is set).
*   User visits `evil.com`.
*   `evil.com` has `<img src="https://bank.com/transfer?to=attacker&amount=1000">`.
*   Browser sends the request *with* the `bank.com` cookie (Ambient Authority).

#### 2.2 The Defenses
1.  **SameSite Cookies:**
    *   **`Strict`:** Cookie never sent on cross-site requests. (Good for banks, bad for linking).
    *   **`Lax` (Default):** Sent on "Top-Level Navigations" (Clicking a link) but NOT on sub-resources (Images, POST forms).
    *   **`None`:** Sent everywhere (Must be `Secure`).
2.  **Anti-CSRF Tokens:**
    *   Server generates random token. Puts it in hidden form field.
    *   Cookie is *automatically* sent. Token is *manually* sent.
    *   Attacker cannot read the token (SOP), so cannot forge the form.

### 3. SQL Injection (SQLi)

#### 3.1 The Mechanism
Code: `query = "SELECT * FROM users WHERE name = '" + userInput + "'"`
Input: `' OR '1'='1`
Result: `SELECT * FROM users WHERE name = '' OR '1'='1'` (Always True).

#### 3.2 The Solution: Separation of Code & Data
*   **Prepared Statements:**
    1.  **Prepare:** Send `SELECT * FROM users WHERE name = ?` to DB. DB parses, optimizes, and caches the *Plan*.
    2.  **Execute:** Send `[' OR '1'='1']` as a raw value.
    3.  **Result:** DB looks for a user whose literal name is `' OR '1'='1`. Safe.

## Module 4.2: Cryptography Engineering

### 1. Symmetric Encryption: AES-GCM

AES (Advanced Encryption Standard) is the standard. But the **Mode** matters.

#### 1.1 The Dangers of ECB
*   **ECB (Electronic Codebook):** Encrypts each 16-byte block independently.
    *   *Flaw:* Identical plaintext blocks produce identical ciphertext blocks.
    *   *Result:* Patterns remain visible (The "Penguin" image).

#### 1.2 Authenticated Encryption (AEAD)
We need Confidentiality AND Integrity.
*   **AES-GCM (Galois/Counter Mode):**
    *   **Encryption:** Uses CTR mode (Stream cipher).
    *   **Authentication:** Uses GMAC (Galois Message Authentication Code) to produce a "Tag".
    *   *Mechanism:*
        1.  Sender encrypts Data -> Ciphertext.
        2.  Sender computes Tag over (Ciphertext + Metadata).
        3.  Receiver decrypts ONLY if Tag matches.
*   **The IV (Initialization Vector) Rule:**
    *   **NEVER reuse a Nonce/IV** with the same key.
    *   *Catastrophe:* If IV is reused, attacker can recover the XOR of two plaintexts and eventually the Authentication Key.

### 2. Password Hashing (KDFs)

Speed is the enemy.

#### 2.1 The GPU Threat
*   A GPU can calculate 10 billion SHA-256 hashes per second.
*   If you store passwords as `SHA256(pass)`, they will be cracked in minutes.

#### 2.2 Argon2 (The Winner)
*   **Memory Hardness:** Designed to fill RAM.
    *   GPUs have massive compute but limited high-speed memory per core.
    *   Argon2 forces the attacker to buy expensive RAM, not just GPUs.
*   **Variants:**
    *   `Argon2d`: Data-dependent (Fast, side-channel risk). Good for crypto-currencies.
    *   `Argon2id`: Hybrid. Resists side-channels AND GPU cracking. **Use this for passwords.**

### 3. Asymmetric Encryption: ECC vs RSA

#### 3.1 The Math
*   **RSA:** Security depends on **Integer Factorization** ($N = p \times q$).
    *   *Key Size:* 2048-bit or 4096-bit required. Slow key gen.
*   **ECC (Elliptic Curve):** Security depends on **Discrete Logarithm Problem**.
    *   "Given point $P$ and $Q = kP$, find $k$".
    *   *Key Size:* 256-bit ECC $\approx$ 3072-bit RSA.

#### 3.2 Why ECC wins?
*   **Performance:** Faster handshakes (smaller keys to transmit).
*   **Energy:** Less CPU usage (Critical for mobile/IoT).
*   **Standard Curve:** `X25519` (Curve25519) is the modern standard for Key Exchange (TLS 1.3).

## Module 4.3: Identity & Access Management (IAM)

### 1. OAuth 2.0 with PKCE (Proof Key for Code Exchange)

The "Authorization Code Flow" is the gold standard. PKCE makes it safe for public clients (SPAs, Mobile) that cannot keep secrets.

#### 1.1 The Vulnerability: Authorization Code Interception
*   **Scenario:** Malicious App installed on user's phone registers the same Custom URI Scheme (`myapp://`).
*   **Attack:** User authenticates. IDP redirects to `myapp://callback?code=123`. Malicious App intercepts the code and exchanges it for a token.

#### 1.2 The PKCE Fix (RFC 7636)
1.  **Client:** Generates `code_verifier` (random string).
2.  **Client:** Hashes it: `code_challenge = SHA256(code_verifier)`.
3.  **Authorization Request:** Sends `code_challenge` to IDP.
4.  **Token Request:** Client sends the **original** `code_verifier`.
5.  **Validation:** IDP hashes the received `code_verifier`. If it matches the stored `code_challenge`, the token is issued.
    *   *Result:* Malicious App might get the Code, but it doesn't have the `code_verifier`, so the exchange fails.

### 2. JSON Web Tokens (JWT) Security

#### 2.1 The "None" Algorithm Attack
*   **The Flaw:** JWT Header contains `{"alg": "none"}`.
*   **The Attack:** Attacker changes payload to `{"admin": true}`, sets `alg: none`, and removes signature.
*   **The Fix:**
    *   **Explicitly Disable** "none" algorithm in your verifier.
    *   **Hardcode** the algorithm (e.g., "Always expect RS256").

#### 2.2 Validation Checklist
Don't just check the signature.
1.  **`exp` (Expiration):** Is `now < exp`?
2.  **`nbf` (Not Before):** Is `now >= nbf`?
3.  **`iss` (Issuer):** Did *my* Auth Server issue this?
4.  **`aud` (Audience):** Is this token meant for *me*?

### 3. Session Management: Stateless vs Stateful

#### 3.1 Stateless JWTs
*   **Pros:** Scalable (No DB lookup per request).
*   **Cons:** **Hard to Revoke.**
    *   If user's laptop is stolen, the JWT works until `exp`.
    *   *Mitigation:* Short `exp` (15 mins) + Sliding Session via Refresh Tokens.

#### 3.2 Reference Tokens (Stateful)
*   **Mechanism:** Client gets a random string (Reference). The actual data is in Redis/DB.
*   **Flow:** API receives Token -> Queries Redis -> Gets Claims.
*   **Pros:** Instant Revocation (Delete key from Redis).
*   **Cons:** Latency (DB lookup on every request).

#### 3.3 The Hybrid Approach (The Best of Both)
*   Use JWTs for **Access Tokens** (Short life, fast).
*   Use Reference Tokens for **Refresh Tokens** (Long life, revokable).
*   *Revocation:* If user logs out, delete the Refresh Token. Access Token dies naturally in 15 mins.
