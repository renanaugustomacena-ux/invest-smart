# MONEYMAKER Docker Certificates

Questa directory contiene i certificati TLS per i container Docker.

## Setup

1. Genera i certificati con lo script:
   ```bash
   cd ../certs
   ./generate-certs.sh
   ```

2. Copia i certificati necessari:
   ```bash
   cp ../certs/ca.crt .
   cp ../certs/postgres-server.crt .
   cp ../certs/postgres-server.key .
   cp ../certs/redis-server.crt .
   cp ../certs/redis-server.key .
   ```

3. Abilita TLS nel `.env`:
   ```bash
   MONEYMAKER_TLS_ENABLED=true
   ```

4. Avvia i servizi:
   ```bash
   docker-compose up -d
   ```

## File Necessari

| File | Descrizione | Usato da |
|------|-------------|----------|
| `ca.crt` | Root CA certificate | Tutti i servizi |
| `postgres-server.crt` | PostgreSQL server cert | postgres container |
| `postgres-server.key` | PostgreSQL server key | postgres container |
| `redis-server.crt` | Redis server cert | redis container |
| `redis-server.key` | Redis server key | redis container |

## Sicurezza

- **Non committare MAI le chiavi private (`.key`)** nel repository
- I file `.key` devono avere permessi `600`
- I file `.crt` possono avere permessi `644`
- In produzione, usare certificati da una CA affidabile
