# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Gestione sicura dei secrets per MONEYMAKER.

Questo modulo carica e valida i secrets da Docker Secrets o variabili
d'ambiente, rifiutando valori deboli o pattern insicuri. I secrets
non devono MAI essere hardcoded nel codice o nei file di configurazione.

Priorita' di caricamento:
1. Docker Secrets (/run/secrets/<name>)
2. Variabili d'ambiente
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


class SecretsValidationError(Exception):
    """Errore sollevato quando la validazione dei secrets fallisce."""

    pass


# Pattern considerati deboli e insicuri
_WEAK_PATTERNS = [
    "password",
    "123456",
    "admin",
    "moneymaker_dev",
    "CHANGE_ME",
    "changeme",
    "secret",
    "test",
    "default",
    "example",
    "qwerty",
]

# Lunghezze minime per tipo di secret
_MIN_LENGTHS = {
    "db_password": 16,
    "redis_password": 16,
    "grafana_password": 12,
    "mt5_password": 8,
    "api_key": 20,
    "default": 16,
}


def _get_min_length(secret_name: str) -> int:
    """Restituisce la lunghezza minima richiesta per un secret."""
    return _MIN_LENGTHS.get(secret_name, _MIN_LENGTHS["default"])


def _is_weak_password(value: str) -> tuple[bool, str | None]:
    """Controlla se il valore contiene pattern deboli.

    Returns:
        Tupla (is_weak, pattern_found).
    """
    value_lower = value.lower()
    for pattern in _WEAK_PATTERNS:
        if pattern.lower() in value_lower:
            return True, pattern
    return False, None


def _has_sufficient_complexity(value: str) -> bool:
    """Verifica che il secret abbia complessita' sufficiente.

    Richiede almeno 3 delle seguenti 4 categorie:
    - Lettere minuscole
    - Lettere maiuscole
    - Numeri
    - Caratteri speciali
    """
    categories = 0
    if re.search(r"[a-z]", value):
        categories += 1
    if re.search(r"[A-Z]", value):
        categories += 1
    if re.search(r"[0-9]", value):
        categories += 1
    if re.search(r"[^a-zA-Z0-9]", value):
        categories += 1
    return categories >= 3


def load_secret(
    name: str,
    env_var: str,
    *,
    min_length: int | None = None,
    required: bool = True,
    check_complexity: bool = True,
) -> str:
    """Carica un secret da Docker Secrets o variabile d'ambiente.

    Priorita':
    1. Docker secret file (/run/secrets/<name>)
    2. Variabile d'ambiente

    Args:
        name: Nome del secret (usato per Docker secrets path).
        env_var: Nome della variabile d'ambiente di fallback.
        min_length: Lunghezza minima (default basato su tipo secret).
        required: Se True, solleva eccezione se mancante.
        check_complexity: Se True, verifica complessita' password.

    Returns:
        Il valore del secret.

    Raises:
        SecretsValidationError: Se il secret e' mancante, debole, o invalido.
    """
    # Determina lunghezza minima
    if min_length is None:
        min_length = _get_min_length(name)

    # Prova Docker secrets prima
    secret_path = Path(f"/run/secrets/{name}")
    value: str | None = None
    source = "docker_secret"

    if secret_path.exists():
        try:
            value = secret_path.read_text().strip()
            logger.debug("secret_loaded_from_docker", secret=name)
        except OSError as exc:
            logger.warning(
                "docker_secret_read_failed",
                secret=name,
                error=str(exc),
            )

    # Fallback a variabile d'ambiente
    if not value:
        value = os.getenv(env_var, "").strip()
        source = "environment"
        if value:
            logger.debug("secret_loaded_from_env", secret=name, env_var=env_var)

    # Validazione: presenza
    if not value:
        if required:
            raise SecretsValidationError(
                f"Secret '{name}' mancante. "
                f"Impostare via Docker secret o variabile d'ambiente '{env_var}'."
            )
        return ""

    # Validazione: lunghezza minima
    if len(value) < min_length:
        raise SecretsValidationError(
            f"Secret '{name}' troppo corto: {len(value)} caratteri, "
            f"richiesti almeno {min_length}."
        )

    # Validazione: pattern deboli
    is_weak, weak_pattern = _is_weak_password(value)
    if is_weak:
        raise SecretsValidationError(
            f"Secret '{name}' contiene pattern debole: '{weak_pattern}'. "
            "Usare una password generata casualmente."
        )

    # Validazione: complessita'
    if check_complexity and not _has_sufficient_complexity(value):
        raise SecretsValidationError(
            f"Secret '{name}' non ha complessita' sufficiente. "
            "Deve contenere almeno 3 categorie tra: minuscole, maiuscole, numeri, speciali."
        )

    logger.info(
        "secret_validated",
        secret=name,
        source=source,
        length=len(value),
    )

    return value


def validate_required_secrets(
    env: str = "production",
) -> dict[str, str]:
    """Valida tutti i secrets richiesti all'avvio del servizio.

    In ambiente development, i controlli sono meno rigidi.

    Args:
        env: Ambiente corrente (development, staging, production).

    Returns:
        Dizionario con tutti i secrets validati.

    Raises:
        SecretsValidationError: Se uno o piu' secrets sono invalidi.
    """
    is_dev = env == "development"
    errors: list[str] = []
    secrets: dict[str, str] = {}

    # Lista secrets richiesti con configurazione
    required_secrets = [
        ("db_password", "MONEYMAKER_DB_PASSWORD", True),
        ("redis_password", "MONEYMAKER_REDIS_PASSWORD", True),
    ]

    for name, env_var, check_complexity in required_secrets:
        try:
            # In development, riduce i requisiti
            secrets[name] = load_secret(
                name,
                env_var,
                required=not is_dev,
                check_complexity=check_complexity and not is_dev,
                min_length=8 if is_dev else None,
            )
        except SecretsValidationError as exc:
            errors.append(str(exc))

    if errors:
        error_msg = "Validazione secrets fallita:\n" + "\n".join(f"  - {e}" for e in errors)
        logger.error("secrets_validation_failed", errors=errors)
        raise SecretsValidationError(error_msg)

    logger.info("all_secrets_validated", count=len(secrets), env=env)
    return secrets


def generate_secure_password(length: int = 32) -> str:
    """Genera una password sicura casuale.

    Utile per setup iniziale o rotazione automatica.

    Args:
        length: Lunghezza della password (minimo 16).

    Returns:
        Password casuale sicura.
    """
    import secrets
    import string

    if length < 16:
        length = 16

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        # Verifica che abbia sufficiente complessita'
        if _has_sufficient_complexity(password):
            return password


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """Maschera un secret per logging sicuro.

    Args:
        value: Il secret da mascherare.
        visible_chars: Numero di caratteri da mostrare alla fine.

    Returns:
        Secret mascherato (es. "****abcd").
    """
    if len(value) <= visible_chars:
        return "*" * len(value)
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


__all__ = [
    "SecretsValidationError",
    "load_secret",
    "validate_required_secrets",
    "generate_secure_password",
    "mask_secret",
]
