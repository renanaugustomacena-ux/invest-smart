"""Tests for moneymaker_common.ratelimit — Rate limiting module."""

import asyncio
import time

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from moneymaker_common.exceptions import RateLimitExceededError
from moneymaker_common.ratelimit import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitPresets,
    RedisRateLimiter,
    create_rate_limiter,
    grpc_rate_limit,
)


# ============================================================
# RateLimitConfig tests
# ============================================================


class TestRateLimitConfig:
    """Test RateLimitConfig dataclass and computed properties."""

    def test_defaults(self):
        cfg = RateLimitConfig()
        assert cfg.requests_per_window == 60
        assert cfg.window_seconds == 60
        assert cfg.burst_size == 10
        assert cfg.key_prefix == "ratelimit"

    def test_custom_values(self):
        cfg = RateLimitConfig(
            requests_per_window=100,
            window_seconds=30,
            burst_size=20,
            key_prefix="custom",
        )
        assert cfg.requests_per_window == 100
        assert cfg.window_seconds == 30
        assert cfg.burst_size == 20
        assert cfg.key_prefix == "custom"

    def test_refill_rate(self):
        cfg = RateLimitConfig(requests_per_window=120, window_seconds=60)
        assert cfg.refill_rate == 2.0

    def test_refill_rate_fractional(self):
        cfg = RateLimitConfig(requests_per_window=10, window_seconds=60)
        assert abs(cfg.refill_rate - 10 / 60) < 1e-9

    def test_max_tokens(self):
        cfg = RateLimitConfig(requests_per_window=60, burst_size=10)
        assert cfg.max_tokens == 70

    def test_max_tokens_no_burst(self):
        cfg = RateLimitConfig(requests_per_window=100, burst_size=0)
        assert cfg.max_tokens == 100


# ============================================================
# RateLimitPresets tests
# ============================================================


class TestRateLimitPresets:
    """Test preset configurations."""

    def test_public_api_preset(self):
        p = RateLimitPresets.PUBLIC_API
        assert p.requests_per_window == 60
        assert p.window_seconds == 60
        assert p.burst_size == 10
        assert p.key_prefix == "ratelimit:public"

    def test_internal_service_preset(self):
        p = RateLimitPresets.INTERNAL_SERVICE
        assert p.requests_per_window == 1000
        assert p.burst_size == 100

    def test_trading_preset(self):
        p = RateLimitPresets.TRADING
        assert p.requests_per_window == 10
        assert p.burst_size == 5

    def test_health_check_preset(self):
        p = RateLimitPresets.HEALTH_CHECK
        assert p.requests_per_window == 300

    def test_strict_preset(self):
        p = RateLimitPresets.STRICT
        assert p.requests_per_window == 5
        assert p.burst_size == 2


# ============================================================
# RedisRateLimiter tests
# ============================================================


class TestRedisRateLimiter:
    """Test Redis-backed rate limiter."""

    def _make_limiter(self, redis_mock=None, config=None, service_name="test"):
        if redis_mock is None:
            redis_mock = AsyncMock()
        if config is None:
            config = RateLimitConfig(requests_per_window=10, window_seconds=60, burst_size=5)
        return RedisRateLimiter(redis_mock, config, service_name)

    def test_make_key_deterministic(self):
        redis_mock = AsyncMock()
        limiter = self._make_limiter(redis_mock)
        key1 = limiter._make_key("user123", "endpoint1")
        key2 = limiter._make_key("user123", "endpoint1")
        assert key1 == key2

    def test_make_key_different_users(self):
        redis_mock = AsyncMock()
        limiter = self._make_limiter(redis_mock)
        key1 = limiter._make_key("user1", "endpoint1")
        key2 = limiter._make_key("user2", "endpoint1")
        assert key1 != key2

    def test_make_key_format(self):
        redis_mock = AsyncMock()
        config = RateLimitConfig(key_prefix="ratelimit")
        limiter = RedisRateLimiter(redis_mock, config, "myservice")
        key = limiter._make_key("user1", "myendpoint")
        assert key.startswith("ratelimit:myservice:myendpoint:")
        # hash part is 16 hex chars
        hash_part = key.split(":")[-1]
        assert len(hash_part) == 16

    @pytest.mark.asyncio
    async def test_ensure_script_loads_once(self):
        redis_mock = AsyncMock()
        redis_mock.script_load = AsyncMock(return_value="sha123")
        limiter = self._make_limiter(redis_mock)

        sha1 = await limiter._ensure_script()
        sha2 = await limiter._ensure_script()
        assert sha1 == "sha123"
        assert sha2 == "sha123"
        # script_load should only be called once
        redis_mock.script_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_allowed(self):
        redis_mock = AsyncMock()
        redis_mock.script_load = AsyncMock(return_value="sha123")
        # Simulate: 9 tokens remaining, 0 retry_after (allowed)
        redis_mock.evalsha = AsyncMock(return_value=[9, 0])
        limiter = self._make_limiter(redis_mock)

        allowed, retry_after, remaining = await limiter.check("user1", "test_ep")
        assert allowed is True
        assert retry_after == 0.0
        assert remaining == 9

    @pytest.mark.asyncio
    async def test_check_rejected(self):
        redis_mock = AsyncMock()
        redis_mock.script_load = AsyncMock(return_value="sha123")
        # Simulate: 0 tokens, 2.5 seconds retry_after (rejected)
        redis_mock.evalsha = AsyncMock(return_value=[0, 2.5])
        limiter = self._make_limiter(redis_mock)

        allowed, retry_after, remaining = await limiter.check("user1", "test_ep")
        assert allowed is False
        assert retry_after == 2.5
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_check_redis_error_fails_open(self):
        redis_mock = AsyncMock()
        redis_mock.script_load = AsyncMock(side_effect=ConnectionError("Redis down"))
        config = RateLimitConfig(requests_per_window=10, burst_size=5)
        limiter = RedisRateLimiter(redis_mock, config, "test")

        # On Redis error, fail open (allow)
        allowed, retry_after, remaining = await limiter.check("user1", "test_ep")
        assert allowed is True
        assert retry_after == 0
        assert remaining == config.max_tokens

    @pytest.mark.asyncio
    async def test_check_or_raise_allowed(self):
        redis_mock = AsyncMock()
        redis_mock.script_load = AsyncMock(return_value="sha123")
        redis_mock.evalsha = AsyncMock(return_value=[5, 0])
        limiter = self._make_limiter(redis_mock)

        remaining = await limiter.check_or_raise("user1", "ep")
        assert remaining == 5

    @pytest.mark.asyncio
    async def test_check_or_raise_rejected(self):
        redis_mock = AsyncMock()
        redis_mock.script_load = AsyncMock(return_value="sha123")
        redis_mock.evalsha = AsyncMock(return_value=[0, 3.0])
        limiter = self._make_limiter(redis_mock)

        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.check_or_raise("user1", "ep")
        assert exc_info.value.retry_after == 3.0
        assert exc_info.value.limit == 10
        assert exc_info.value.window_seconds == 60


# ============================================================
# InMemoryRateLimiter tests
# ============================================================


class TestInMemoryRateLimiter:
    """Test in-memory rate limiter."""

    @pytest.mark.asyncio
    async def test_first_request_allowed(self):
        config = RateLimitConfig(requests_per_window=10, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        allowed, retry_after, remaining = await limiter.check("user1")
        assert allowed is True
        assert retry_after == 0.0
        # max_tokens=10, consumed 1 => 9
        assert remaining == 9

    @pytest.mark.asyncio
    async def test_exhaust_tokens(self):
        config = RateLimitConfig(requests_per_window=3, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        # Consume all 3 tokens
        for _ in range(3):
            allowed, _, _ = await limiter.check("user1")
            assert allowed is True

        # 4th request should be rejected
        allowed, retry_after, remaining = await limiter.check("user1")
        assert allowed is False
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_different_users_independent(self):
        config = RateLimitConfig(requests_per_window=2, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        # Exhaust user1
        await limiter.check("user1")
        await limiter.check("user1")
        allowed1, _, _ = await limiter.check("user1")

        # user2 should still be allowed
        allowed2, _, _ = await limiter.check("user2")

        assert allowed1 is False
        assert allowed2 is True

    @pytest.mark.asyncio
    async def test_different_endpoints_independent(self):
        config = RateLimitConfig(requests_per_window=1, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        # Exhaust endpoint1
        await limiter.check("user1", "ep1")
        allowed1, _, _ = await limiter.check("user1", "ep1")

        # ep2 should still be allowed
        allowed2, _, _ = await limiter.check("user1", "ep2")

        assert allowed1 is False
        assert allowed2 is True

    @pytest.mark.asyncio
    async def test_burst_capacity(self):
        config = RateLimitConfig(requests_per_window=2, window_seconds=60, burst_size=3)
        limiter = InMemoryRateLimiter(config, "test")

        # max_tokens = 2 + 3 = 5
        results = []
        for _ in range(5):
            allowed, _, _ = await limiter.check("user1")
            results.append(allowed)

        assert all(results)

        # 6th should be rejected
        allowed, _, _ = await limiter.check("user1")
        assert allowed is False

    @pytest.mark.asyncio
    async def test_check_or_raise_allowed(self):
        config = RateLimitConfig(requests_per_window=10, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        remaining = await limiter.check_or_raise("user1")
        assert remaining == 9

    @pytest.mark.asyncio
    async def test_check_or_raise_rejected(self):
        config = RateLimitConfig(requests_per_window=1, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        await limiter.check("user1")  # consume the only token

        with pytest.raises(RateLimitExceededError):
            await limiter.check_or_raise("user1")

    @pytest.mark.asyncio
    async def test_make_key(self):
        config = RateLimitConfig()
        limiter = InMemoryRateLimiter(config, "test")
        key = limiter._make_key("user1", "ep")
        assert key == "ep:user1"


# ============================================================
# gRPC rate limit decorator tests
# ============================================================


class TestGrpcRateLimitDecorator:
    """Test the grpc_rate_limit decorator."""

    @pytest.mark.asyncio
    async def test_decorator_allows_request(self):
        config = RateLimitConfig(requests_per_window=10, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        context = MagicMock()
        context.peer.return_value = "ipv4:192.168.1.1:12345"

        @grpc_rate_limit(limiter)
        async def MyMethod(self, request, context):
            return "ok"

        result = await MyMethod(None, "req", context)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_decorator_rejects_request(self):
        config = RateLimitConfig(requests_per_window=1, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        context = MagicMock()
        context.peer.return_value = "ipv4:192.168.1.1:12345"
        context.abort = MagicMock()

        @grpc_rate_limit(limiter)
        async def MyMethod(self, request, context):
            return "ok"

        # First call ok
        await MyMethod(None, "req", context)
        # Second call should trigger abort
        await MyMethod(None, "req", context)

        context.abort.assert_called_once()
        # Check it was called with RESOURCE_EXHAUSTED
        import grpc

        call_args = context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.RESOURCE_EXHAUSTED

    @pytest.mark.asyncio
    async def test_decorator_ipv6_peer(self):
        config = RateLimitConfig(requests_per_window=10, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        context = MagicMock()
        context.peer.return_value = "ipv6:[::1]:12345"

        @grpc_rate_limit(limiter)
        async def MyMethod(self, request, context):
            return "ok"

        result = await MyMethod(None, "req", context)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_decorator_unknown_peer(self):
        config = RateLimitConfig(requests_per_window=10, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        context = MagicMock()
        context.peer.return_value = None

        @grpc_rate_limit(limiter)
        async def MyMethod(self, request, context):
            return "ok"

        result = await MyMethod(None, "req", context)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_decorator_custom_endpoint(self):
        config = RateLimitConfig(requests_per_window=10, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        context = MagicMock()
        context.peer.return_value = "ipv4:1.2.3.4:80"

        @grpc_rate_limit(limiter, endpoint="CustomEndpoint")
        async def MyMethod(self, request, context):
            return "ok"

        result = await MyMethod(None, "req", context)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_decorator_custom_identifier_fn(self):
        config = RateLimitConfig(requests_per_window=10, window_seconds=60, burst_size=0)
        limiter = InMemoryRateLimiter(config, "test")

        context = MagicMock()
        context.peer.return_value = "ipv4:1.2.3.4:80"

        def get_id(ctx):
            return "custom_user_id"

        @grpc_rate_limit(limiter, get_identifier=get_id)
        async def MyMethod(self, request, context):
            return "ok"

        result = await MyMethod(None, "req", context)
        assert result == "ok"


# ============================================================
# create_rate_limiter factory tests
# ============================================================


class TestCreateRateLimiter:
    """Test the factory function."""

    @pytest.mark.asyncio
    async def test_no_redis_url_returns_inmemory(self):
        result = await create_rate_limiter(redis_url=None, service_name="test")
        assert isinstance(result, InMemoryRateLimiter)

    @pytest.mark.asyncio
    async def test_redis_connection_failure_falls_back(self):
        # Use a bogus URL that will fail to connect
        with patch("moneymaker_common.ratelimit.redis_async", create=True):
            # Import and patch redis.asyncio
            mock_redis_module = MagicMock()
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(side_effect=ConnectionError("Cannot connect"))
            mock_redis_module.from_url.return_value = mock_client

            with patch.dict("sys.modules", {"redis.asyncio": mock_redis_module}):
                with patch("redis.asyncio", mock_redis_module, create=True):
                    result = await create_rate_limiter(
                        redis_url="redis://nonexistent:6379/0",
                        service_name="test",
                    )
                    assert isinstance(result, InMemoryRateLimiter)

    @pytest.mark.asyncio
    async def test_custom_config_passed_through(self):
        config = RateLimitConfig(requests_per_window=999)
        result = await create_rate_limiter(config=config, service_name="test")
        assert isinstance(result, InMemoryRateLimiter)
        assert result._config.requests_per_window == 999
