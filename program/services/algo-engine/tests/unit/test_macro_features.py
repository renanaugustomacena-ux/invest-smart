"""Tests for algo_engine.features.macro_features — MacroFeatures + MacroFeatureProvider."""

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from algo_engine.features.macro_features import MacroFeatureProvider, MacroFeatures


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# MacroFeatures dataclass
# ---------------------------------------------------------------------------


class TestMacroFeatures:
    def test_defaults(self):
        f = MacroFeatures()
        assert f.vix_spot == 15.0
        assert f.vix_regime == 0
        assert f.vix_contango == 1
        assert f.yield_slope_2s10s == 0.5
        assert f.curve_inverted == 0
        assert f.recession_prob == 0.15
        assert f.dxy_change_1h_pct == 0.0
        assert f.real_rate_10y == 0.5
        assert f.cot_asset_mgr_pct_oi == 10.0
        assert f.cot_sentiment == 0
        assert f.data_stale is False

    def test_to_vector_length(self):
        f = MacroFeatures()
        vec = f.to_vector()
        assert len(vec) == 10

    def test_to_vector_values_are_normalized(self):
        """All values should be in [0, 1] range."""
        f = MacroFeatures()
        vec = f.to_vector()
        for i, v in enumerate(vec):
            assert 0.0 <= v <= 1.0, f"Index {i} out of range: {v}"

    def test_to_vector_extreme_high(self):
        """Extreme high values should clamp to 1.0."""
        f = MacroFeatures(
            vix_spot=100.0,
            vix_regime=2,
            yield_slope_2s10s=5.0,
            recession_prob=100.0,
            dxy_change_1h_pct=5.0,
            real_rate_10y=10.0,
            cot_asset_mgr_pct_oi=50.0,
            cot_sentiment=1,
        )
        vec = f.to_vector()
        for i, v in enumerate(vec):
            assert 0.0 <= v <= 1.0, f"Index {i} out of range: {v}"

    def test_to_vector_extreme_low(self):
        """Extreme low values should clamp to 0.0."""
        f = MacroFeatures(
            vix_spot=0.0,
            vix_regime=0,
            vix_contango=0,
            yield_slope_2s10s=-5.0,
            curve_inverted=0,
            recession_prob=0.0,
            dxy_change_1h_pct=-5.0,
            real_rate_10y=-5.0,
            cot_asset_mgr_pct_oi=0.0,
            cot_sentiment=-1,
        )
        vec = f.to_vector()
        for i, v in enumerate(vec):
            assert 0.0 <= v <= 1.0, f"Index {i} out of range: {v}"

    # Normalization functions
    def test_normalize_vix_boundary_low(self):
        f = MacroFeatures(vix_spot=10.0)
        assert f._normalize_vix(10.0) == 0.0

    def test_normalize_vix_boundary_high(self):
        f = MacroFeatures()
        assert f._normalize_vix(80.0) == 1.0

    def test_normalize_vix_midpoint(self):
        f = MacroFeatures()
        result = f._normalize_vix(45.0)
        assert abs(result - 0.5) < 0.01

    def test_normalize_spread_inverted(self):
        f = MacroFeatures()
        assert f._normalize_spread(-1.0) == 0.0

    def test_normalize_spread_steep(self):
        f = MacroFeatures()
        assert f._normalize_spread(3.0) == 1.0

    def test_normalize_prob(self):
        f = MacroFeatures()
        assert f._normalize_prob(0.0) == 0.0
        assert f._normalize_prob(50.0) == 0.5
        assert f._normalize_prob(100.0) == 1.0

    def test_normalize_pct_change(self):
        f = MacroFeatures()
        assert f._normalize_pct_change(-2.0) == 0.0
        assert f._normalize_pct_change(0.0) == 0.5
        assert f._normalize_pct_change(2.0) == 1.0

    def test_normalize_rate(self):
        f = MacroFeatures()
        assert f._normalize_rate(-2.0) == 0.0
        assert f._normalize_rate(3.0) == 1.0

    def test_normalize_pct_oi(self):
        f = MacroFeatures()
        assert f._normalize_pct_oi(0.0) == 0.0
        assert f._normalize_pct_oi(30.0) == 1.0
        assert abs(f._normalize_pct_oi(15.0) - 0.5) < 0.01

    def test_cot_sentiment_mapping(self):
        """COT sentiment: -1→0, 0→0.5, 1→1.0"""
        for sentiment, expected in [(-1, 0.0), (0, 0.5), (1, 1.0)]:
            f = MacroFeatures(cot_sentiment=sentiment)
            vec = f.to_vector()
            assert abs(vec[9] - expected) < 0.01


# ---------------------------------------------------------------------------
# MacroFeatureProvider — no Redis
# ---------------------------------------------------------------------------


class TestMacroFeatureProviderNoRedis:
    def test_no_redis_returns_defaults(self):
        provider = MacroFeatureProvider(redis_client=None)
        features = _run(provider.get_features())
        assert isinstance(features, MacroFeatures)
        assert features.vix_spot == 15.0

    def test_no_redis_returns_cached(self):
        provider = MacroFeatureProvider(redis_client=None)
        cached = MacroFeatures(vix_spot=25.0)
        provider._last_features = cached
        features = _run(provider.get_features())
        assert features.vix_spot == 25.0

    def test_get_feature_names(self):
        provider = MacroFeatureProvider()
        names = provider.get_feature_names()
        assert len(names) == 10
        assert "vix_spot" in names
        assert "cot_sentiment" in names

    def test_redis_keys_defined(self):
        assert "vix" in MacroFeatureProvider.REDIS_KEYS
        assert "yield_curve" in MacroFeatureProvider.REDIS_KEYS
        assert "dxy" in MacroFeatureProvider.REDIS_KEYS
        assert "cot_gold" in MacroFeatureProvider.REDIS_KEYS
        assert len(MacroFeatureProvider.REDIS_KEYS) == 6


# ---------------------------------------------------------------------------
# MacroFeatureProvider — with in-memory Redis stub
# ---------------------------------------------------------------------------


class InMemoryRedis:
    """Real in-memory key-value store implementing Redis get() interface."""

    def __init__(self):
        self._store: dict[str, str] = {}

    def set(self, key: str, value: str) -> None:
        self._store[key] = value

    async def get(self, key: str) -> str | None:
        return self._store.get(key)


class TestMacroFeatureProviderWithRedis:
    def _make_provider(self) -> tuple[MacroFeatureProvider, InMemoryRedis]:
        redis = InMemoryRedis()
        provider = MacroFeatureProvider(redis_client=redis)
        return provider, redis

    def test_vix_data_loaded(self):
        provider, redis = self._make_provider()
        redis.set(
            "macro:vix",
            json.dumps({
                "spot": 28.5,
                "regime": 2,
                "contango": False,
                "updated_at": "2024-01-15T10:00:00Z",
            }),
        )
        features = _run(provider.get_features())
        assert features.vix_spot == 28.5
        assert features.vix_regime == 2
        assert features.vix_contango == 0

    def test_yield_curve_loaded(self):
        provider, redis = self._make_provider()
        redis.set(
            "macro:yield_curve",
            json.dumps({
                "spread_2s10s": -0.3,
                "inverted": True,
                "updated_at": "2024-01-15T10:00:00Z",
            }),
        )
        features = _run(provider.get_features())
        assert features.yield_slope_2s10s == -0.3
        assert features.curve_inverted == 1

    def test_real_rates_loaded(self):
        provider, redis = self._make_provider()
        redis.set("macro:real_rates", json.dumps({"real_rate_10y": -0.5}))
        features = _run(provider.get_features())
        assert features.real_rate_10y == -0.5

    def test_recession_loaded(self):
        provider, redis = self._make_provider()
        redis.set("macro:recession", json.dumps({"probability_12m": 45.0}))
        features = _run(provider.get_features())
        assert features.recession_prob == 45.0

    def test_dxy_loaded(self):
        provider, redis = self._make_provider()
        redis.set("macro:dxy", json.dumps({"change_1h_pct": -0.35}))
        features = _run(provider.get_features())
        assert features.dxy_change_1h_pct == -0.35

    def test_cot_loaded(self):
        provider, redis = self._make_provider()
        redis.set(
            "macro:cot:gold",
            json.dumps({"asset_mgr_pct_oi": 22.5, "sentiment": 1}),
        )
        features = _run(provider.get_features())
        assert features.cot_asset_mgr_pct_oi == 22.5
        assert features.cot_sentiment == 1

    def test_all_data_loaded(self):
        provider, redis = self._make_provider()
        now = datetime.now(timezone.utc).isoformat()
        redis.set("macro:vix", json.dumps({"spot": 20.0, "regime": 1, "contango": True, "updated_at": now}))
        redis.set("macro:yield_curve", json.dumps({"spread_2s10s": 1.5, "inverted": False, "updated_at": now}))
        redis.set("macro:real_rates", json.dumps({"real_rate_10y": 1.0}))
        redis.set("macro:recession", json.dumps({"probability_12m": 10.0}))
        redis.set("macro:dxy", json.dumps({"change_1h_pct": 0.1}))
        redis.set("macro:cot:gold", json.dumps({"asset_mgr_pct_oi": 15.0, "sentiment": 0}))

        features = _run(provider.get_features())
        assert features.vix_spot == 20.0
        assert features.yield_slope_2s10s == 1.5
        assert features.real_rate_10y == 1.0
        assert features.recession_prob == 10.0
        assert features.dxy_change_1h_pct == 0.1
        assert features.cot_asset_mgr_pct_oi == 15.0
        assert not features.data_stale  # recent update

    def test_stale_data_flagged(self):
        provider, redis = self._make_provider()
        # 20 minutes ago — exceeds 600s MAX_DATA_AGE_SECONDS
        redis.set(
            "macro:vix",
            json.dumps({"spot": 30.0, "updated_at": "2020-01-01T00:00:00Z"}),
        )
        features = _run(provider.get_features())
        assert features.data_stale is True
        assert features.data_age_seconds > 600

    def test_missing_key_keeps_default(self):
        provider, redis = self._make_provider()
        # Only set VIX — everything else stays default
        redis.set("macro:vix", json.dumps({"spot": 22.0}))
        features = _run(provider.get_features())
        assert features.vix_spot == 22.0
        assert features.yield_slope_2s10s == 0.5  # default
        assert features.recession_prob == 0.15  # default

    def test_caches_last_features(self):
        provider, redis = self._make_provider()
        redis.set("macro:vix", json.dumps({"spot": 18.0}))
        _run(provider.get_features())
        assert provider._last_features is not None
        assert provider._last_features.vix_spot == 18.0


# ---------------------------------------------------------------------------
# MacroFeatureProvider — error handling
# ---------------------------------------------------------------------------


class ErrorRedis:
    """Redis stub that raises on every call."""

    async def get(self, key: str):
        raise ConnectionError("Redis connection refused")


class TestMacroFeatureProviderErrors:
    def test_redis_error_returns_defaults(self):
        provider = MacroFeatureProvider(redis_client=ErrorRedis())
        features = _run(provider.get_features())
        assert isinstance(features, MacroFeatures)
        assert features.vix_spot == 15.0  # default

    def test_redis_error_per_key_returns_defaults(self):
        """When _get_redis_json catches errors per-key, defaults are used.

        The top-level except only fires for truly unexpected exceptions.
        Individual key errors are caught in _get_redis_json → returns None.
        """
        provider = MacroFeatureProvider(redis_client=ErrorRedis())
        features = _run(provider.get_features())
        # Each key silently fails → all defaults
        assert features.vix_spot == 15.0
        # But _last_features is still cached (with defaults)
        assert provider._last_features is not None


# ---------------------------------------------------------------------------
# is_gold_bullish_environment
# ---------------------------------------------------------------------------


class TestIsGoldBullishEnvironment:
    def test_calm_market_not_bullish(self):
        provider = MacroFeatureProvider()
        f = MacroFeatures()  # All defaults — calm
        assert provider.is_gold_bullish_environment(f) is False

    def test_panic_vix_inverted_curve_negative_rates(self):
        """VIX panic(+2) + inverted(+1) + negative rates(+2) = 5 → bullish."""
        provider = MacroFeatureProvider()
        f = MacroFeatures(vix_regime=2, curve_inverted=1, real_rate_10y=-1.0)
        assert provider.is_gold_bullish_environment(f) is True

    def test_elevated_vix_negative_rates_dxy_falling_cot_bullish(self):
        """VIX elevated(+1) + negative rates(+2) + DXY falling(+1) + COT(+1) = 5 → bullish."""
        provider = MacroFeatureProvider()
        f = MacroFeatures(
            vix_regime=1,
            real_rate_10y=-0.5,
            dxy_change_1h_pct=-0.5,
            cot_sentiment=1,
        )
        assert provider.is_gold_bullish_environment(f) is True

    def test_just_below_threshold(self):
        """3 signals is not enough (need >= 4)."""
        provider = MacroFeatureProvider()
        f = MacroFeatures(
            vix_regime=1,  # +1
            curve_inverted=1,  # +1
            real_rate_10y=0.3,  # +1 (< 0.5)
        )
        assert provider.is_gold_bullish_environment(f) is False

    def test_exactly_at_threshold(self):
        """4 signals is exactly the threshold."""
        provider = MacroFeatureProvider()
        f = MacroFeatures(
            vix_regime=1,  # +1
            curve_inverted=1,  # +1
            real_rate_10y=0.3,  # +1 (< 0.5)
            cot_sentiment=1,  # +1
        )
        assert provider.is_gold_bullish_environment(f) is True


# ---------------------------------------------------------------------------
# is_high_risk_environment
# ---------------------------------------------------------------------------


class TestIsHighRiskEnvironment:
    def test_calm_market(self):
        provider = MacroFeatureProvider()
        f = MacroFeatures()
        assert provider.is_high_risk_environment(f) is False

    def test_vix_panic(self):
        provider = MacroFeatureProvider()
        f = MacroFeatures(vix_regime=2)
        assert provider.is_high_risk_environment(f) is True

    def test_deeply_inverted_curve(self):
        provider = MacroFeatureProvider()
        f = MacroFeatures(yield_slope_2s10s=-0.6)
        assert provider.is_high_risk_environment(f) is True

    def test_high_recession_probability(self):
        provider = MacroFeatureProvider()
        f = MacroFeatures(recession_prob=45.0)
        assert provider.is_high_risk_environment(f) is True

    def test_borderline_not_high_risk(self):
        """Just below thresholds."""
        provider = MacroFeatureProvider()
        f = MacroFeatures(
            vix_regime=1,
            yield_slope_2s10s=-0.4,
            recession_prob=39.0,
        )
        assert provider.is_high_risk_environment(f) is False


# ---------------------------------------------------------------------------
# _parse_timestamp
# ---------------------------------------------------------------------------


class TestParseTimestamp:
    def test_valid_iso_timestamp(self):
        provider = MacroFeatureProvider()
        data = {"updated_at": "2024-01-15T10:00:00Z"}
        result = provider._parse_timestamp(data)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_missing_timestamp(self):
        provider = MacroFeatureProvider()
        data = {}
        result = provider._parse_timestamp(data)
        # Should return now — close to current time
        now = datetime.now(timezone.utc)
        assert abs((now - result).total_seconds()) < 2

    def test_invalid_timestamp(self):
        provider = MacroFeatureProvider()
        data = {"updated_at": "not-a-date"}
        result = provider._parse_timestamp(data)
        now = datetime.now(timezone.utc)
        assert abs((now - result).total_seconds()) < 2
