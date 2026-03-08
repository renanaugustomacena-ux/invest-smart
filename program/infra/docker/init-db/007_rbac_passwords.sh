#!/bin/bash
# ============================================================
# MONEYMAKER V1 - RBAC Password Configuration
# ============================================================
# Sets passwords for service roles from environment variables.
# Executed by PostgreSQL as part of docker-entrypoint-initdb.d
#
# Required environment variables (set in docker-compose.yml):
#   - DI_DB_PASSWORD: Password for data_ingestion_svc
#   - BRAIN_DB_PASSWORD: Password for algo_engine_svc
#   - MT5_DB_PASSWORD: Password for mt5_bridge_svc
#   - ADMIN_DB_PASSWORD: Password for moneymaker_admin (optional)
#
# If a password is not set, the role remains without a password
# (login disabled in production but works in development).
# ============================================================

set -e

echo "========================================"
echo "MONEYMAKER RBAC Password Configuration"
echo "========================================"

# Function to set password for a role
set_role_password() {
    local role_name="$1"
    local password="$2"
    local description="$3"

    if [ -n "$password" ]; then
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
            ALTER ROLE $role_name WITH PASSWORD '$password';
EOSQL
        echo "[OK] Password set for $role_name ($description)"
    else
        echo "[SKIP] No password provided for $role_name (DI_DB_PASSWORD not set)"
    fi
}

# Data Ingestion Service
if [ -n "$DI_DB_PASSWORD" ]; then
    set_role_password "data_ingestion_svc" "$DI_DB_PASSWORD" "Data Ingestion Service"
else
    echo "[SKIP] DI_DB_PASSWORD not set - data_ingestion_svc has no password"
fi

# Algo Engine Service
if [ -n "$BRAIN_DB_PASSWORD" ]; then
    set_role_password "algo_engine_svc" "$BRAIN_DB_PASSWORD" "Algo Engine Service"
else
    echo "[SKIP] BRAIN_DB_PASSWORD not set - algo_engine_svc has no password"
fi

# MT5 Bridge Service
if [ -n "$MT5_DB_PASSWORD" ]; then
    set_role_password "mt5_bridge_svc" "$MT5_DB_PASSWORD" "MT5 Bridge Service"
else
    echo "[SKIP] MT5_DB_PASSWORD not set - mt5_bridge_svc has no password"
fi

# Admin role (optional)
if [ -n "$ADMIN_DB_PASSWORD" ]; then
    set_role_password "moneymaker_admin" "$ADMIN_DB_PASSWORD" "Admin Role"
else
    echo "[SKIP] ADMIN_DB_PASSWORD not set - moneymaker_admin has no password"
fi

echo "========================================"
echo "RBAC password configuration complete"
echo "========================================"

# Verify roles exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT rolname, rolcanlogin, rolcreatedb, rolcreaterole
    FROM pg_roles
    WHERE rolname IN ('data_ingestion_svc', 'algo_engine_svc', 'mt5_bridge_svc', 'moneymaker_admin');
EOSQL
