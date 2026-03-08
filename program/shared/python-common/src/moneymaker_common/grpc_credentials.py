"""Gestione credenziali TLS per gRPC — il "fabbro digitale".

Fornisce funzioni per creare channel credentials (client) e
server credentials (server) in modo consistente e sicuro.

Come un fabbro che prepara le chiavi per le serrature: legge i certificati,
verifica che siano validi, e crea le credenziali per aprire i canali sicuri.

Supporta:
- TLS semplice (client verifica server)
- mTLS (Mutual TLS): client e server si autenticano reciprocamente

Utilizzo client:
    channel = create_async_client_channel(
        target="mt5-bridge:50055",
        tls_enabled=True,
        ca_cert="/etc/ssl/certs/ca.crt",
        client_cert="/etc/ssl/certs/algo-engine.crt",
        client_key="/etc/ssl/private/algo-engine.key",
    )

Utilizzo server:
    credentials = load_server_credentials(
        ca_cert_path="/etc/ssl/certs/ca.crt",
        server_cert_path="/etc/ssl/certs/mt5-bridge.crt",
        server_key_path="/etc/ssl/private/mt5-bridge.key",
        require_client_cert=True,  # mTLS
    )
    server.add_secure_port(f"[::]:{port}", credentials)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


def load_credentials_from_files(
    ca_cert_path: str,
    client_cert_path: Optional[str] = None,
    client_key_path: Optional[str] = None,
) -> Any:
    """Carica credenziali client TLS da file — prepara le chiavi del cliente.

    Per mTLS completo, fornire anche client_cert e client_key.
    Per TLS semplice (solo verifica server), solo ca_cert.

    Args:
        ca_cert_path: Percorso al certificato CA root per verificare il server.
        client_cert_path: (Opzionale) Certificato client per mTLS.
        client_key_path: (Opzionale) Chiave privata client per mTLS.

    Returns:
        grpc.ChannelCredentials pronte per secure_channel.

    Raises:
        FileNotFoundError: Se un file certificato non esiste.
        ValueError: Se solo uno tra cert e key è fornito.
    """
    import grpc

    # Valida che cert e key siano forniti insieme
    if bool(client_cert_path) != bool(client_key_path):
        raise ValueError(
            "client_cert_path e client_key_path devono essere forniti insieme"
        )

    # Leggi CA certificate
    ca_cert_file = Path(ca_cert_path)
    if not ca_cert_file.exists():
        raise FileNotFoundError(f"CA certificate non trovato: {ca_cert_path}")
    ca_cert = ca_cert_file.read_bytes()

    # Leggi client certificate e key se forniti (per mTLS)
    client_cert: Optional[bytes] = None
    client_key: Optional[bytes] = None

    if client_cert_path and client_key_path:
        cert_file = Path(client_cert_path)
        key_file = Path(client_key_path)

        if not cert_file.exists():
            raise FileNotFoundError(f"Client certificate non trovato: {client_cert_path}")
        if not key_file.exists():
            raise FileNotFoundError(f"Client key non trovato: {client_key_path}")

        client_cert = cert_file.read_bytes()
        client_key = key_file.read_bytes()
        logger.debug("mTLS abilitato: certificato client caricato")

    return grpc.ssl_channel_credentials(
        root_certificates=ca_cert,
        private_key=client_key,
        certificate_chain=client_cert,
    )


def load_server_credentials(
    ca_cert_path: str,
    server_cert_path: str,
    server_key_path: str,
    require_client_cert: bool = True,
) -> Any:
    """Carica credenziali server TLS/mTLS — prepara la serratura del server.

    Args:
        ca_cert_path: Percorso CA per verificare certificati client (mTLS).
        server_cert_path: Certificato pubblico del server.
        server_key_path: Chiave privata del server.
        require_client_cert: Se True, richiede certificato client (mTLS).
                            Se False, solo TLS (client non autenticato).

    Returns:
        grpc.ServerCredentials pronte per add_secure_port.

    Raises:
        FileNotFoundError: Se un file non esiste.
    """
    import grpc

    # Leggi tutti i file
    ca_file = Path(ca_cert_path)
    cert_file = Path(server_cert_path)
    key_file = Path(server_key_path)

    if not ca_file.exists():
        raise FileNotFoundError(f"CA certificate non trovato: {ca_cert_path}")
    if not cert_file.exists():
        raise FileNotFoundError(f"Server certificate non trovato: {server_cert_path}")
    if not key_file.exists():
        raise FileNotFoundError(f"Server key non trovato: {server_key_path}")

    ca_cert = ca_file.read_bytes()
    server_cert = cert_file.read_bytes()
    server_key = key_file.read_bytes()

    logger.debug(
        "Credenziali server caricate",
        require_client_cert=require_client_cert,
    )

    return grpc.ssl_server_credentials(
        private_key_certificate_chain_pairs=[(server_key, server_cert)],
        root_certificates=ca_cert if require_client_cert else None,
        require_client_auth=require_client_cert,
    )


def get_tls_config_from_env() -> dict[str, Any]:
    """Legge configurazione TLS dalle variabili d'ambiente — il quadro di controllo.

    Variabili supportate:
        MONEYMAKER_TLS_ENABLED: "true" per abilitare TLS
        MONEYMAKER_TLS_CA_CERT: Percorso al CA certificate
        MONEYMAKER_TLS_CLIENT_CERT: Certificato client (per mTLS)
        MONEYMAKER_TLS_CLIENT_KEY: Chiave privata client (per mTLS)
        MONEYMAKER_TLS_SERVER_CERT: Certificato server (per server gRPC)
        MONEYMAKER_TLS_SERVER_KEY: Chiave privata server (per server gRPC)

    Returns:
        Dizionario con la configurazione TLS.
    """
    enabled_str = os.getenv("MONEYMAKER_TLS_ENABLED", "false").lower()
    enabled = enabled_str in ("true", "1", "yes")

    return {
        "enabled": enabled,
        "ca_cert": os.getenv("MONEYMAKER_TLS_CA_CERT", "/etc/ssl/certs/ca.crt"),
        "client_cert": os.getenv("MONEYMAKER_TLS_CLIENT_CERT", ""),
        "client_key": os.getenv("MONEYMAKER_TLS_CLIENT_KEY", ""),
        "server_cert": os.getenv("MONEYMAKER_TLS_SERVER_CERT", ""),
        "server_key": os.getenv("MONEYMAKER_TLS_SERVER_KEY", ""),
    }


def _is_production() -> bool:
    """Check if we're running in a production environment."""
    return os.getenv("MONEYMAKER_ENV", "").lower() in ("production", "prod")


def create_client_channel(
    target: str,
    tls_enabled: bool = False,
    ca_cert: Optional[str] = None,
    client_cert: Optional[str] = None,
    client_key: Optional[str] = None,
    options: Optional[list[tuple[str, Any]]] = None,
    strict_tls: Optional[bool] = None,
) -> Any:
    """Crea un canale gRPC sincrono con supporto TLS opzionale.

    Args:
        target: Indirizzo del server (es: "mt5-bridge:50055").
        tls_enabled: Se True e ca_cert fornito, usa TLS.
        ca_cert: Percorso CA certificate per verificare il server.
        client_cert: (Opzionale) Certificato client per mTLS.
        client_key: (Opzionale) Chiave privata client per mTLS.
        options: Opzioni aggiuntive per il canale gRPC.
        strict_tls: Se True, rifiuta il fallback a insecure.
                    Default: True in produzione, False altrimenti.

    Returns:
        grpc.Channel (sincrono).

    Raises:
        ValueError: Se strict_tls=True e TLS non può essere stabilito.
    """
    import grpc

    if strict_tls is None:
        strict_tls = _is_production()

    if tls_enabled and ca_cert and Path(ca_cert).exists():
        try:
            credentials = load_credentials_from_files(ca_cert, client_cert, client_key)
            logger.info("Canale gRPC sicuro (TLS)", target=target)
            return grpc.secure_channel(target, credentials, options=options)
        except FileNotFoundError as e:
            if strict_tls:
                raise ValueError(f"TLS abilitato ma certificato non trovato: {e}")
            logger.warning(
                "Certificato non trovato, fallback a insecure",
                error=str(e),
            )
    elif tls_enabled and strict_tls:
        raise ValueError(
            f"TLS abilitato ma CA cert non disponibile (ca_cert={ca_cert!r})"
        )

    if tls_enabled:
        logger.warning("gRPC TLS richiesto ma non stabilito, fallback insecure", target=target)
    else:
        logger.debug("Canale gRPC insecure", target=target)
    return grpc.insecure_channel(target, options=options)


def create_async_client_channel(
    target: str,
    tls_enabled: bool = False,
    ca_cert: Optional[str] = None,
    client_cert: Optional[str] = None,
    client_key: Optional[str] = None,
    options: Optional[list[tuple[str, Any]]] = None,
    strict_tls: Optional[bool] = None,
) -> Any:
    """Crea un canale gRPC asincrono con supporto TLS opzionale.

    Args:
        target: Indirizzo del server (es: "mt5-bridge:50055").
        tls_enabled: Se True e ca_cert fornito, usa TLS.
        ca_cert: Percorso CA certificate per verificare il server.
        client_cert: (Opzionale) Certificato client per mTLS.
        client_key: (Opzionale) Chiave privata client per mTLS.
        options: Opzioni aggiuntive per il canale gRPC.
        strict_tls: Se True, rifiuta il fallback a insecure.
                    Default: True in produzione, False altrimenti.

    Returns:
        grpc.aio.Channel (asincrono).

    Raises:
        ValueError: Se strict_tls=True e TLS non può essere stabilito.
    """
    import grpc.aio

    if strict_tls is None:
        strict_tls = _is_production()

    if tls_enabled and ca_cert and Path(ca_cert).exists():
        try:
            credentials = load_credentials_from_files(ca_cert, client_cert, client_key)
            logger.info("Canale gRPC asincrono sicuro (TLS)", target=target)
            return grpc.aio.secure_channel(target, credentials, options=options)
        except FileNotFoundError as e:
            if strict_tls:
                raise ValueError(f"TLS abilitato ma certificato non trovato: {e}")
            logger.warning(
                "Certificato non trovato, fallback a insecure",
                error=str(e),
            )
    elif tls_enabled and strict_tls:
        raise ValueError(
            f"TLS abilitato ma CA cert non disponibile (ca_cert={ca_cert!r})"
        )

    if tls_enabled:
        logger.warning("gRPC async TLS richiesto ma non stabilito, fallback insecure", target=target)
    else:
        logger.debug("Canale gRPC asincrono insecure", target=target)
    return grpc.aio.insecure_channel(target, options=options)
