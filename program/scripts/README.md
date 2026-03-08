# Scripts

Development and operations utilities for the MONEYMAKER ecosystem.

## Development Scripts (`dev/`)

| Script | Purpose |
|---|---|
| `setup-local.sh` | **One-shot local setup**: creates `.env`, installs `moneymaker-common`, starts DB + Redis, installs pre-commit hooks |
| `generate-protos.sh` | Recompiles all `.proto` files into Python/Go stubs |

### First-Time Setup

```bash
bash scripts/dev/setup-local.sh
```

This will:

1. Copy `.env.example` → `.env` (if missing)
2. Install `shared/python-common` as editable package
3. Start PostgreSQL (TimescaleDB) and Redis via Docker
4. Wait for database readiness
5. Install pre-commit hooks (if `pre-commit` is available)

## Operations Scripts (`ops/`)

Reserved for production deployment and maintenance utilities (TBD).
