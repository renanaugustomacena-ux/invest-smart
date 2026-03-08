"""Rate Limiting per servizi MONEYMAKER.

Come il "vigile urbano" della fabbrica: limita il traffico in entrata
per evitare che un singolo client (o un attaccante) sovraccarichi il sistema.

Implementa l'algoritmo Token Bucket:
- Ogni "secchio" ha una capacità massima di token
- I token vengono rigenerati a una velocità costante
- Ogni richiesta consuma un token
- Se non ci sono token, la richiesta viene rifiutata

Supporta:
- Rate limiting Redis-backed (distribuito tra istanze)
- Decoratore per metodi gRPC
- Middleware per endpoint HTTP
- Metriche Prometheus per monitoraggio
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar, Union

import grpc
from prometheus_client import Counter, Histogram

from moneymaker_common.exceptions import RateLimitExceededError


# ============================================================
# Metriche
# ============================================================

RATE_LIMIT_REQUESTS = Counter(
    "moneymaker_ratelimit_requests_total",
    "Richieste totali processate dal rate limiter",
    ["service", "endpoint", "status"],  # status: allowed, rejected
)

RATE_LIMIT_REJECTED = Counter(
    "moneymaker_ratelimit_rejected_total",
    "Richieste rifiutate per rate limit",
    ["service", "endpoint"],
)

RATE_LIMIT_LATENCY = Histogram(
    "moneymaker_ratelimit_check_latency_seconds",
    "Latenza del controllo rate limit",
    ["service"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05),
)


# ============================================================
# Configurazione Rate Limit
# ============================================================


@dataclass
class RateLimitConfig:
    """Configurazione per un endpoint rate-limited.

    Attributes:
        requests_per_window: Numero massimo di richieste nella finestra
        window_seconds: Durata della finestra in secondi
        burst_size: Capacità extra per burst (token bucket)
        key_prefix: Prefisso per la chiave Redis
    """

    requests_per_window: int = 60
    window_seconds: int = 60
    burst_size: int = 10
    key_prefix: str = "ratelimit"

    @property
    def refill_rate(self) -> float:
        """Token rigenerati al secondo."""
        return self.requests_per_window / self.window_seconds

    @property
    def max_tokens(self) -> int:
        """Capacità massima del bucket (include burst)."""
        return self.requests_per_window + self.burst_size


# ============================================================
# Rate Limiter Redis-backed
# ============================================================


class RedisRateLimiter:
    """Rate limiter distribuito usando Redis.

    Implementa l'algoritmo Token Bucket con storage Redis per garantire
    rate limiting coerente tra multiple istanze del servizio.
    """

    # Script Lua per operazione atomica token bucket
    # Ritorna: (tokens_rimanenti, retry_after_seconds)
    _TOKEN_BUCKET_SCRIPT = """
    local key = KEYS[1]
    local max_tokens = tonumber(ARGV[1])
    local refill_rate = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local window_seconds = tonumber(ARGV[4])

    -- Recupera stato corrente
    local data = redis.call('HMGET', key, 'tokens', 'last_update')
    local tokens = tonumber(data[1])
    local last_update = tonumber(data[2])

    -- Inizializza se non esiste
    if tokens == nil then
        tokens = max_tokens
        last_update = now
    end

    -- Calcola token rigenerati
    local elapsed = now - last_update
    local refilled = math.floor(elapsed * refill_rate)
    tokens = math.min(max_tokens, tokens + refilled)

    -- Prova a consumare un token
    if tokens >= 1 then
        tokens = tokens - 1
        redis.call('HMSET', key, 'tokens', tokens, 'last_update', now)
        redis.call('EXPIRE', key, window_seconds * 2)
        return {tokens, 0}
    else
        -- Calcola tempo di attesa per prossimo token
        local wait_time = (1 - tokens) / refill_rate
        redis.call('HMSET', key, 'last_update', now)
        redis.call('EXPIRE', key, window_seconds * 2)
        return {tokens, wait_time}
    end
    """

    def __init__(
        self,
        redis_client: Any,
        config: RateLimitConfig,
        service_name: str = "unknown",
    ) -> None:
        """Inizializza il rate limiter.

        Args:
            redis_client: Client Redis (redis.Redis o redis.asyncio.Redis)
            config: Configurazione rate limit
            service_name: Nome del servizio per metriche
        """
        self._redis = redis_client
        self._config = config
        self._service_name = service_name
        self._script_sha: Optional[str] = None

    def _make_key(self, identifier: str, endpoint: str = "default") -> str:
        """Costruisce la chiave Redis per un client/endpoint.

        Args:
            identifier: Identificatore del client (IP, user_id, API key)
            endpoint: Nome dell'endpoint

        Returns:
            Chiave Redis formattata
        """
        # Hash l'identifier per privacy e lunghezza costante
        id_hash = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"{self._config.key_prefix}:{self._service_name}:{endpoint}:{id_hash}"

    async def _ensure_script(self) -> str:
        """Carica lo script Lua in Redis se non già caricato."""
        if self._script_sha is None:
            self._script_sha = await self._redis.script_load(
                self._TOKEN_BUCKET_SCRIPT
            )
        return self._script_sha

    async def check(
        self,
        identifier: str,
        endpoint: str = "default",
    ) -> tuple[bool, float, int]:
        """Controlla se una richiesta è permessa.

        Args:
            identifier: Identificatore del client
            endpoint: Nome dell'endpoint

        Returns:
            Tupla (allowed, retry_after, remaining_tokens)

        Raises:
            ConnectionError: Se Redis non è raggiungibile
        """
        start_time = time.monotonic()
        key = self._make_key(identifier, endpoint)

        try:
            sha = await self._ensure_script()
            result = await self._redis.evalsha(
                sha,
                1,  # numero di KEYS
                key,
                str(self._config.max_tokens),
                str(self._config.refill_rate),
                str(time.time()),
                str(self._config.window_seconds),
            )

            tokens_remaining = int(result[0])
            retry_after = float(result[1])
            allowed = retry_after == 0

            # Metriche
            status = "allowed" if allowed else "rejected"
            RATE_LIMIT_REQUESTS.labels(
                service=self._service_name,
                endpoint=endpoint,
                status=status,
            ).inc()

            if not allowed:
                RATE_LIMIT_REJECTED.labels(
                    service=self._service_name,
                    endpoint=endpoint,
                ).inc()

            return allowed, retry_after, tokens_remaining

        except Exception as e:
            # In caso di errore Redis, permetti la richiesta (fail-open)
            # ma logga l'errore
            return True, 0, self._config.max_tokens

        finally:
            duration = time.monotonic() - start_time
            RATE_LIMIT_LATENCY.labels(service=self._service_name).observe(duration)

    async def check_or_raise(
        self,
        identifier: str,
        endpoint: str = "default",
    ) -> int:
        """Controlla rate limit e solleva eccezione se superato.

        Args:
            identifier: Identificatore del client
            endpoint: Nome dell'endpoint

        Returns:
            Numero di token rimanenti

        Raises:
            RateLimitExceededError: Se il rate limit è superato
        """
        allowed, retry_after, remaining = await self.check(identifier, endpoint)

        if not allowed:
            raise RateLimitExceededError(
                key=f"{endpoint}:{identifier}",
                limit=self._config.requests_per_window,
                window_seconds=self._config.window_seconds,
                retry_after=retry_after,
            )

        return remaining


# ============================================================
# Rate Limiter In-Memory (fallback senza Redis)
# ============================================================


class InMemoryRateLimiter:
    """Rate limiter locale in memoria.

    Usato come fallback quando Redis non è disponibile.
    Non distribuito: ogni istanza ha i propri limiti.
    """

    def __init__(
        self,
        config: RateLimitConfig,
        service_name: str = "unknown",
    ) -> None:
        self._config = config
        self._service_name = service_name
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_update)
        self._lock = asyncio.Lock()

    def _make_key(self, identifier: str, endpoint: str = "default") -> str:
        """Costruisce la chiave per il bucket."""
        return f"{endpoint}:{identifier}"

    async def check(
        self,
        identifier: str,
        endpoint: str = "default",
    ) -> tuple[bool, float, int]:
        """Controlla se una richiesta è permessa."""
        start_time = time.monotonic()
        key = self._make_key(identifier, endpoint)

        async with self._lock:
            now = time.time()

            # Recupera o inizializza bucket
            if key in self._buckets:
                tokens, last_update = self._buckets[key]
            else:
                tokens = float(self._config.max_tokens)
                last_update = now

            # Rigenera token
            elapsed = now - last_update
            refilled = elapsed * self._config.refill_rate
            tokens = min(self._config.max_tokens, tokens + refilled)

            # Prova a consumare
            if tokens >= 1:
                tokens -= 1
                self._buckets[key] = (tokens, now)
                allowed = True
                retry_after = 0.0
            else:
                self._buckets[key] = (tokens, now)
                allowed = False
                retry_after = (1 - tokens) / self._config.refill_rate

        # Metriche
        status = "allowed" if allowed else "rejected"
        RATE_LIMIT_REQUESTS.labels(
            service=self._service_name,
            endpoint=endpoint,
            status=status,
        ).inc()

        if not allowed:
            RATE_LIMIT_REJECTED.labels(
                service=self._service_name,
                endpoint=endpoint,
            ).inc()

        duration = time.monotonic() - start_time
        RATE_LIMIT_LATENCY.labels(service=self._service_name).observe(duration)

        return allowed, retry_after, int(tokens)

    async def check_or_raise(
        self,
        identifier: str,
        endpoint: str = "default",
    ) -> int:
        """Controlla rate limit e solleva eccezione se superato."""
        allowed, retry_after, remaining = await self.check(identifier, endpoint)

        if not allowed:
            raise RateLimitExceededError(
                key=f"{endpoint}:{identifier}",
                limit=self._config.requests_per_window,
                window_seconds=self._config.window_seconds,
                retry_after=retry_after,
            )

        return remaining


# ============================================================
# Decoratore per gRPC
# ============================================================

F = TypeVar("F", bound=Callable[..., Any])


def grpc_rate_limit(
    limiter: Union[RedisRateLimiter, InMemoryRateLimiter],
    endpoint: Optional[str] = None,
    get_identifier: Optional[Callable[[grpc.ServicerContext], str]] = None,
) -> Callable[[F], F]:
    """Decoratore per rate limiting su metodi gRPC.

    Estrae automaticamente l'IP del client dal contesto gRPC.

    Args:
        limiter: Istanza del rate limiter
        endpoint: Nome dell'endpoint (default: nome del metodo)
        get_identifier: Funzione custom per estrarre l'identificatore

    Usage:
        @grpc_rate_limit(limiter)
        async def ExecuteTrade(self, request, context):
            ...
    """

    def _default_get_identifier(context: grpc.ServicerContext) -> str:
        """Estrae l'IP del client dal contesto gRPC."""
        peer = context.peer()
        if peer:
            # Formato: ipv4:IP:PORT o ipv6:[IP]:PORT
            if peer.startswith("ipv4:"):
                return peer.split(":")[1]
            elif peer.startswith("ipv6:"):
                return peer.split("[")[1].split("]")[0]
        return "unknown"

    def decorator(func: F) -> F:
        method_name = endpoint or func.__name__

        @functools.wraps(func)
        async def wrapper(self: Any, request: Any, context: grpc.ServicerContext) -> Any:
            identifier_fn = get_identifier or _default_get_identifier
            identifier = identifier_fn(context)

            try:
                await limiter.check_or_raise(identifier, method_name)
            except RateLimitExceededError as e:
                context.abort(
                    grpc.StatusCode.RESOURCE_EXHAUSTED,
                    f"Rate limit exceeded. Retry after {e.retry_after:.1f}s",
                )

            return await func(self, request, context)

        return wrapper  # type: ignore

    return decorator


# ============================================================
# Middleware HTTP per aiohttp
# ============================================================


def create_aiohttp_middleware(
    limiter: Union[RedisRateLimiter, InMemoryRateLimiter],
    excluded_paths: Optional[list[str]] = None,
) -> Callable:
    """Crea middleware rate limiting per aiohttp.

    Args:
        limiter: Istanza del rate limiter
        excluded_paths: Percorsi da escludere (es. ["/health", "/metrics"])

    Usage:
        from aiohttp import web
        app = web.Application(middlewares=[
            create_aiohttp_middleware(limiter)
        ])
    """
    excluded = set(excluded_paths or ["/health", "/healthz", "/metrics", "/ready"])

    from aiohttp import web

    @web.middleware
    async def rate_limit_middleware(
        request: web.Request,
        handler: Callable,
    ) -> web.Response:
        # Skip per percorsi esclusi
        if request.path in excluded:
            return await handler(request)

        # Estrai IP (supporta proxy)
        identifier = request.headers.get(
            "X-Forwarded-For",
            request.remote or "unknown",
        ).split(",")[0].strip()

        endpoint = request.path

        allowed, retry_after, remaining = await limiter.check(identifier, endpoint)

        if not allowed:
            return web.json_response(
                {
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Retry after {retry_after:.1f}s",
                    "retry_after": retry_after,
                },
                status=429,
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await handler(request)

        # Aggiungi header rate limit
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    return rate_limit_middleware


# ============================================================
# Factory per creare rate limiter
# ============================================================


async def create_rate_limiter(
    redis_url: Optional[str] = None,
    config: Optional[RateLimitConfig] = None,
    service_name: str = "unknown",
) -> Union[RedisRateLimiter, InMemoryRateLimiter]:
    """Factory per creare un rate limiter appropriato.

    Se Redis è disponibile, usa RedisRateLimiter (distribuito).
    Altrimenti, cade su InMemoryRateLimiter (locale).

    Args:
        redis_url: URL di connessione Redis (opzionale)
        config: Configurazione rate limit
        service_name: Nome del servizio

    Returns:
        Istanza del rate limiter appropriato
    """
    cfg = config or RateLimitConfig()

    if redis_url:
        try:
            import redis.asyncio as redis_async

            client = redis_async.from_url(redis_url, decode_responses=True)
            # Test connessione
            await client.ping()
            return RedisRateLimiter(client, cfg, service_name)
        except Exception:
            pass

    # Fallback a in-memory
    return InMemoryRateLimiter(cfg, service_name)


# ============================================================
# Preset configurazioni comuni
# ============================================================


class RateLimitPresets:
    """Configurazioni predefinite per diversi casi d'uso."""

    # API pubblica: 60 req/min con burst di 10
    PUBLIC_API = RateLimitConfig(
        requests_per_window=60,
        window_seconds=60,
        burst_size=10,
        key_prefix="ratelimit:public",
    )

    # Servizio interno: 1000 req/min (più permissivo)
    INTERNAL_SERVICE = RateLimitConfig(
        requests_per_window=1000,
        window_seconds=60,
        burst_size=100,
        key_prefix="ratelimit:internal",
    )

    # Trading: 10 trade/min (conservativo)
    TRADING = RateLimitConfig(
        requests_per_window=10,
        window_seconds=60,
        burst_size=5,
        key_prefix="ratelimit:trading",
    )

    # Health checks: 300 req/min
    HEALTH_CHECK = RateLimitConfig(
        requests_per_window=300,
        window_seconds=60,
        burst_size=50,
        key_prefix="ratelimit:health",
    )

    # Strict: 5 req/min (per operazioni sensibili)
    STRICT = RateLimitConfig(
        requests_per_window=5,
        window_seconds=60,
        burst_size=2,
        key_prefix="ratelimit:strict",
    )
