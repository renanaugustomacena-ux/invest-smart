"""MONEYMAKER V1 — Utilità Python Condivise.

La "cassetta degli attrezzi" comune a tutti i servizi Python:
- Logging strutturato con output JSON — il "diario" di bordo
- Gestione configurazione via variabili d'ambiente — le "impostazioni" della fabbrica
- Helper per metriche Prometheus — i "contatori" di produzione
- Protocollo di controllo salute — il "dottore" del servizio
- Utilità di precisione Decimal — il "righello di precisione"
- Interfaccia audit trail — il "registro notarile"
- Gerarchia delle eccezioni — i "codici di errore"
- Gestione sicura dei secrets — il "custode delle chiavi"
"""

__version__ = "0.1.0"

from moneymaker_common.secrets import (
    SecretsValidationError,
    load_secret,
    validate_required_secrets,
    generate_secure_password,
    mask_secret,
)

# Rate limiting imports are lazy — require grpcio which not all services install.
# Use: from moneymaker_common.ratelimit import RateLimitConfig, ...
def __getattr__(name: str):
    _ratelimit_names = {
        "RateLimitConfig",
        "RateLimitExceededError",
        "RateLimitPresets",
        "RedisRateLimiter",
        "InMemoryRateLimiter",
        "create_rate_limiter",
        "grpc_rate_limit",
        "create_aiohttp_middleware",
    }
    if name in _ratelimit_names:
        from moneymaker_common import ratelimit
        return getattr(ratelimit, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
