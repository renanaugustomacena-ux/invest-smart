# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | Yes                |
| < 1.0   | No                 |

## Reporting a Vulnerability

If you discover a security vulnerability in MONEYMAKER, please report it
responsibly. **Do NOT open a public GitHub issue.**

### How to Report

1. Send a detailed report via **private email** to the repository owner.
2. Include the following information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if any)

### Response Timeline

| Stage                  | Timeline          |
|------------------------|-------------------|
| Acknowledgment         | Within 48 hours   |
| Initial assessment     | Within 7 days     |
| Fix development        | Within 30 days    |
| Public disclosure      | After fix deployed |

### What Qualifies as a Security Vulnerability

- Authentication or authorization bypasses
- SQL injection, command injection, or XSS vulnerabilities
- Credential exposure (API keys, passwords, tokens in logs or responses)
- TLS/mTLS misconfigurations that expose data in transit
- Kill switch bypass that allows trading when it should be halted
- Position sizing errors that could exceed risk limits
- Race conditions in order execution that could cause duplicate trades

### What Does NOT Qualify

- Feature requests or general bugs (use GitHub Issues)
- Performance issues (unless they enable denial-of-service)
- UI/cosmetic issues
- Issues in development/mock mode only

## Security Best Practices for Deployment

1. **Never commit `.env` files** — use `.env.example` as a template
2. **Generate strong passwords** — `openssl rand -base64 24` for all secrets
3. **Enable TLS** in staging and production — run `infra/certs/generate-certs.sh`
4. **Use RBAC database users** — configure per-service credentials in `.env`
5. **Keep dependencies updated** — run `pip audit`, `govulncheck`, `npm audit` regularly
6. **Monitor the kill switch** — ensure Redis connectivity for fail-closed safety
