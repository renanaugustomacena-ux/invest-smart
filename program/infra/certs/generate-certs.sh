#!/bin/bash
# ============================================================
# MONEYMAKER V1 - Certificate Generation Script
# ============================================================
#
# Genera certificati self-signed per l'infrastruttura TLS di MONEYMAKER.
# Include certificati per PostgreSQL, Redis e servizi applicativi.
#
# USAGE:
#   ./generate-certs.sh [output_dir]
#
# SECURITY NOTES:
# - Questi sono certificati self-signed per sviluppo/staging
# - In produzione usare Let's Encrypt o una CA aziendale
# - Le chiavi private (.key) hanno permessi 600
# - Non committare MAI chiavi private nel repository
#
# ============================================================

set -euo pipefail

# Configuration
OUTPUT_DIR="${1:-./certs}"
DAYS=365
KEY_SIZE=4096
COUNTRY="IT"
ORGANIZATION="MONEYMAKER"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if openssl is available
if ! command -v openssl &> /dev/null; then
    log_error "openssl non trovato. Installare openssl prima di procedere."
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
log_info "Directory output: $OUTPUT_DIR"

# ============================================================
# 1. Root CA (Certificate Authority)
# ============================================================
log_info "Generazione Root CA..."

openssl genrsa -out "$OUTPUT_DIR/ca.key" $KEY_SIZE 2>/dev/null

openssl req -new -x509 -days $DAYS -key "$OUTPUT_DIR/ca.key" \
    -out "$OUTPUT_DIR/ca.crt" \
    -subj "/CN=MONEYMAKER Root CA/O=$ORGANIZATION/C=$COUNTRY" \
    2>/dev/null

log_info "Root CA generata: ca.crt, ca.key"

# ============================================================
# 2. PostgreSQL Server Certificate
# ============================================================
log_info "Generazione certificato PostgreSQL..."

# Create OpenSSL config for SAN (Subject Alternative Names)
cat > "$OUTPUT_DIR/postgres-openssl.cnf" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = postgres
O = $ORGANIZATION
C = $COUNTRY

[v3_req]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = postgres
DNS.2 = localhost
DNS.3 = moneymaker-postgres
IP.1 = 127.0.0.1
EOF

openssl genrsa -out "$OUTPUT_DIR/postgres-server.key" $KEY_SIZE 2>/dev/null

openssl req -new -key "$OUTPUT_DIR/postgres-server.key" \
    -out "$OUTPUT_DIR/postgres-server.csr" \
    -config "$OUTPUT_DIR/postgres-openssl.cnf" \
    2>/dev/null

openssl x509 -req -days $DAYS -in "$OUTPUT_DIR/postgres-server.csr" \
    -CA "$OUTPUT_DIR/ca.crt" -CAkey "$OUTPUT_DIR/ca.key" \
    -CAcreateserial -out "$OUTPUT_DIR/postgres-server.crt" \
    -extensions v3_req -extfile "$OUTPUT_DIR/postgres-openssl.cnf" \
    2>/dev/null

log_info "Certificato PostgreSQL generato: postgres-server.crt, postgres-server.key"

# ============================================================
# 3. Redis Server Certificate
# ============================================================
log_info "Generazione certificato Redis..."

cat > "$OUTPUT_DIR/redis-openssl.cnf" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = redis
O = $ORGANIZATION
C = $COUNTRY

[v3_req]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = redis
DNS.2 = localhost
DNS.3 = moneymaker-redis
IP.1 = 127.0.0.1
EOF

openssl genrsa -out "$OUTPUT_DIR/redis-server.key" $KEY_SIZE 2>/dev/null

openssl req -new -key "$OUTPUT_DIR/redis-server.key" \
    -out "$OUTPUT_DIR/redis-server.csr" \
    -config "$OUTPUT_DIR/redis-openssl.cnf" \
    2>/dev/null

openssl x509 -req -days $DAYS -in "$OUTPUT_DIR/redis-server.csr" \
    -CA "$OUTPUT_DIR/ca.crt" -CAkey "$OUTPUT_DIR/ca.key" \
    -CAcreateserial -out "$OUTPUT_DIR/redis-server.crt" \
    -extensions v3_req -extfile "$OUTPUT_DIR/redis-openssl.cnf" \
    2>/dev/null

log_info "Certificato Redis generato: redis-server.crt, redis-server.key"

# ============================================================
# 4. Service Certificates (per mTLS futuro)
# ============================================================
SERVICES=("algo-engine" "mt5-bridge" "data-ingestion" "ml-training")

for SERVICE in "${SERVICES[@]}"; do
    log_info "Generazione certificato per $SERVICE..."

    cat > "$OUTPUT_DIR/$SERVICE-openssl.cnf" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = $SERVICE
O = $ORGANIZATION
C = $COUNTRY

[v3_req]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $SERVICE
DNS.2 = localhost
DNS.3 = moneymaker-$SERVICE
IP.1 = 127.0.0.1
EOF

    openssl genrsa -out "$OUTPUT_DIR/$SERVICE.key" $KEY_SIZE 2>/dev/null

    openssl req -new -key "$OUTPUT_DIR/$SERVICE.key" \
        -out "$OUTPUT_DIR/$SERVICE.csr" \
        -config "$OUTPUT_DIR/$SERVICE-openssl.cnf" \
        2>/dev/null

    openssl x509 -req -days $DAYS -in "$OUTPUT_DIR/$SERVICE.csr" \
        -CA "$OUTPUT_DIR/ca.crt" -CAkey "$OUTPUT_DIR/ca.key" \
        -CAcreateserial -out "$OUTPUT_DIR/$SERVICE.crt" \
        -extensions v3_req -extfile "$OUTPUT_DIR/$SERVICE-openssl.cnf" \
        2>/dev/null

    log_info "Certificato $SERVICE generato: $SERVICE.crt, $SERVICE.key"
done

# ============================================================
# Cleanup
# ============================================================
log_info "Pulizia file temporanei..."

# Remove CSR files
rm -f "$OUTPUT_DIR"/*.csr

# Remove OpenSSL config files
rm -f "$OUTPUT_DIR"/*-openssl.cnf

# ============================================================
# Set Permissions
# ============================================================
log_info "Impostazione permessi..."

# Private keys: owner read only
chmod 600 "$OUTPUT_DIR"/*.key

# Certificates: readable by all
chmod 644 "$OUTPUT_DIR"/*.crt

# Serial file
chmod 644 "$OUTPUT_DIR"/*.srl 2>/dev/null || true

# ============================================================
# Summary
# ============================================================
echo ""
echo "============================================================"
echo -e "${GREEN}Certificati generati con successo!${NC}"
echo "============================================================"
echo ""
echo "Directory: $OUTPUT_DIR"
echo ""
echo "File generati:"
echo "  - ca.crt, ca.key          (Root CA)"
echo "  - postgres-server.crt/key (PostgreSQL TLS)"
echo "  - redis-server.crt/key    (Redis TLS)"
for SERVICE in "${SERVICES[@]}"; do
    echo "  - $SERVICE.crt/key       (Service mTLS)"
done
echo ""
echo "Validità: $DAYS giorni"
echo "Dimensione chiave: $KEY_SIZE bit"
echo ""
log_warn "IMPORTANTE: Non committare le chiavi private (.key) nel repository!"
log_warn "IMPORTANTE: In produzione usare certificati da una CA affidabile!"
echo ""

# Verify certificates
log_info "Verifica certificati..."
for cert in "$OUTPUT_DIR"/*.crt; do
    if openssl x509 -noout -text -in "$cert" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $(basename "$cert")"
    else
        echo -e "  ${RED}✗${NC} $(basename "$cert") - ERRORE"
    fi
done

echo ""
echo "============================================================"
echo "Per usare TLS con Docker:"
echo "  1. Copia i certificati in program/infra/docker/certs/"
echo "  2. Imposta MONEYMAKER_TLS_ENABLED=true nel .env"
echo "  3. Riavvia i servizi: docker-compose up -d"
echo "============================================================"
