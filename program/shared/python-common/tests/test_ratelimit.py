"""Tests for moneymaker_common.ratelimit — Rate limiting module.

Pure logic tests run unconditionally.
Real Redis tests require REDIS_URL env var (or a Redis on localhost:6379).
gRPC decorator tests moved to gRPC integration test suite.
"""

import os

import pytest

from moneymaker_common.exceptions import RateLimitExceededError
from moneymaker_common.ratelimit import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitPresets,
    RedisRateLimiter,
    create_rate_limiter,
)

# ============================================================
# Helper: Redis availability check
# ============================================================

REDIS_URL = os.environ.get("REDIS_URL", "")
# Use DB 15 for test isolation so FLUSHDB won't nuke production data
if REDIS_URL:
    _base = REDIS_URL.rstrip("/")
    # If URL already has a DB number (redis://host:port/0), replace it
    # Otherwise append /15
    parts = _base.split("/")
    if len(parts) >= 4 and parts[-1].isdigit():
        parts[-1] = "15"
        REDIS_TEST_URL = "/".join(parts)
    else:
        REDIS_TEST_URL = _base + "/15"
else:
    REDIS_TEST_URL = ""

_redis_available: bool | None = None


async def _check_redis() -> bool:
    """Return True if we can reach Redis at REDIS_TEST_URL."""
    global _redis_available
    if _redis_available is not None:
        return _redis_available
    if not REDIS_TEST_URL:
        _redis_available = False
        return False
    try:
        import redis.asyncio as redis_async

        client = redis_async.from_url(REDIS_TEST_URL, decode_responses=True)
        await client.ping()
        await client.aclose()
        _redis_available = True
    except Exception:
        _redis_available = False
    return _redis_available


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
# create_rate_limiter factory tests (pure logic, no mocks)
# ============================================================


class TestCreateRateLimiter:
    """Test the factory function (pure logic only)."""

    @pytest.mark.asyncio
    async def test_no_redis_url_returns_inmemory(self):
        result = await create_rate_limiter(redis_url=None, service_name="test")
        assert isinstance(result, InMemoryRateLimiter)

    @pytest.mark.asyncio
    async def test_custom_config_passed_through(self):
        config = RateLimitConfig(requests_per_window=999)
        result = await create_rate_limiter(config=config, service_name="test")
        assert isinstance(result, InMemoryRateLimiter)
        assert result._config.requests_per_window == 999


# ============================================================
# Real Redis tests — require REDIS_URL env var
# ============================================================


@pytest.mark.skipif(not REDIS_URL, reason="requires real Redis (set REDIS_URL)")
class TestRedisRateLimiterReal:
    """Integration tests for RedisRateLimiter against a real Redis instance.

    Uses DB 15 to avoid interfering with production data.
    Each test flushes DB 15 in teardown.
    """

    @pytest.fixture(autouse=True)
    async def redis_client(self):
        """Create a real Redis client on DB 15 and flush after each test."""
        import redis.asyncio as redis_async

        client = redis_async.from_url(REDIS_TEST_URL, decode_responses=True)
        self._client = client
        yield client
        # Cleanup: flush test DB after each test
        await client.flushdb()
        await client.aclose()

    @pytest.mark.asyncio
    async def test_first_request_allowed(self, redis_client):
        config = RateLimitConfig(requests_per_window=10, window_seconds=60, burst_size=0)
        limiter = RedisRateLimiter(redis_client, config, "test")

        allowed, retry_after, remaining = await limiter.check("user1", "test_ep")
        assert allowed is True
        assert retry_after == 0.0
        # First request: max_tokens(10) - 1 = 9
        assert remaining == 9

    @pytest.mark.asyncio
    async def test_exhaust_tokens_and_reject(self, redis_client):
        config = RateLimitConfig(requests_per_window=3, window_seconds=60, burst_size=0)
        limiter = RedisRateLimiter(redis_client, config, "test")

        # Consume all 3 tokens
        for i in range(3):
            allowed, _, _ = await limiter.check("user1", "exhaust_ep")
            assert allowed is True, f"Request {i + 1} should be allowed"

        # 4th request must be rejected
        allowed, retry_after, remaining = await limiter.check("user1", "exhaust_ep")
        assert allowed is False
        assert retry_after > 0
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_check_or_raise_raises_when_exhausted(self, redis_client):
        config = RateLimitConfig(requests_per_window=2, window_seconds=60, burst_size=0)
        limiter = RedisRateLimiter(redis_client, config, "test")

        # Consume all tokens
        await limiter.check("user1", "raise_ep")
        await limiter.check("user1", "raise_ep")

        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.check_or_raise("user1", "raise_ep")
        assert exc_info.value.retry_after > 0
        assert exc_info.value.limit == 2
        assert exc_info.value.window_seconds == 60

    @pytest.mark.asyncio
    async def test_check_or_raise_returns_remaining_when_allowed(self, redis_client):
        config = RateLimitConfig(requests_per_window=10, window_seconds=60, burst_size=0)
        limiter = RedisRateLimiter(redis_client, config, "test")

        remaining = await limiter.check_or_raise("user1", "ok_ep")
        assert remaining == 9

    @pytest.mark.asyncio
    async def test_different_keys_are_independent(self, redis_client):
        config = RateLimitConfig(requests_per_window=1, window_seconds=60, burst_size=0)
        limiter = RedisRateLimiter(redis_client, config, "test")

        # Exhaust user1 on ep1
        await limiter.check("user1", "ep1")
        allowed1, _, _ = await limiter.check("user1", "ep1")

        # user2 on ep1 should still be allowed
        allowed2, _, _ = await limiter.check("user2", "ep1")

        assert allowed1 is False
        assert allowed2 is True

    @pytest.mark.asyncio
    async def test_burst_capacity(self, redis_client):
        config = RateLimitConfig(requests_per_window=2, window_seconds=60, burst_size=3)
        limiter = RedisRateLimiter(redis_client, config, "test")

        # max_tokens = 2 + 3 = 5, all should be allowed
        for i in range(5):
            allowed, _, _ = await limiter.check("user1", "burst_ep")
            assert allowed is True, f"Request {i + 1} of 5 should be allowed"

        # 6th should be rejected
        allowed, _, _ = await limiter.check("user1", "burst_ep")
        assert allowed is False

    @pytest.mark.asyncio
    async def test_create_rate_limiter_with_real_redis_returns_redis_limiter(self):
        """create_rate_limiter with a valid Redis URL returns RedisRateLimiter."""
        limiter = await create_rate_limiter(redis_url=REDIS_TEST_URL, service_name="test")
        assert isinstance(limiter, RedisRateLimiter)
        # Cleanup the Redis client created by the factory
        await limiter._redis.flushdb()
        await limiter._redis.aclose()

    @pytest.mark.asyncio
    async def test_create_rate_limiter_invalid_url_falls_back_to_inmemory(self):
        """create_rate_limiter with an unreachable Redis URL falls back to InMemoryRateLimiter."""
        limiter = await create_rate_limiter(
            redis_url="redis://invalid-host-that-does-not-exist:6379/15",
            service_name="test",
        )
        assert isinstance(limiter, InMemoryRateLimiter)
