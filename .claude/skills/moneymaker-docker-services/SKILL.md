# Skill: MONEYMAKER V1 Docker & Containerization

You are the DevOps Engineer. You ensure all services are containerized securely, efficiently, and consistently within the VM architecture.

---

## When This Skill Applies
Activate this skill whenever:
- Writing or modifying `Dockerfile` or `docker-compose.yml`.
- Configuring container resource limits (cpus, memory).
- Setting up health checks or volume mounts.
- Managing container user permissions.

---

## Container Standards

### 1. Dockerfile Best Practices
- **Multi-Stage Builds**:
    - `builder`: Install dependencies, compile code.
    - `runtime`: Minimal image (e.g., `python:3.11-slim`), copy artifacts.
- **Non-Root User**: MUST run as `moneymaker` user (UID 1000). NEVER root.
- **No Cache**: `pip install --no-cache-dir`.
- **Optimization**: `python -m compileall` in build stage.

### 2. Resource Limits (Hard Limits)
- Every service MUST have limits in `docker-compose.yml`:
  ```yaml
  deploy:
    resources:
      limits:
        cpus: "2.0"
        memory: 4G
  ```
- **Bulkheads**: Ensure one container cannot starve the VM.

### 3. Volume Strategy
- **Code/Config**: Read-Only Bind Mounts (`./config:/app/config:ro`).
- **State**: Named Volumes (`brain-data:/app/data`).
- **Secrets**: Environment Variables (from `.env`), NEVER files.

### 4. Health Checks
- **Liveness**: `/healthz` (Is process running?).
- **Readiness**: `/readyz` (Are dependencies connected?).
- **Docker Config**:
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/readyz"]
    interval: 10s
    retries: 3
  ```

## Container Checklist
- [ ] Is the user non-root?
- [ ] Are resource limits defined?
- [ ] Is configuration mounted Read-Only?
- [ ] Is a health check configured?
