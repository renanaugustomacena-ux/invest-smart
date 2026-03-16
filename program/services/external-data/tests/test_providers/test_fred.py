"""Tests for FRED provider."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx

from external_data.providers.fred import (
    FREDProvider,
    RecessionProbability,
    RealRatesData,
    YieldCurveData,
)


@pytest.fixture()
def fred():
    return FREDProvider(api_key="test-key", base_url="https://fred.test.com", timeout=5)


class TestFREDProviderInit:
    def test_defaults(self):
        p = FREDProvider()
        assert p.api_key == ""
        assert p.base_url == "https://api.stlouisfed.org/fred"
        assert p.timeout == 30
        assert p._client is None

    def test_custom(self, fred):
        assert fred.api_key == "test-key"
        assert fred.base_url == "https://fred.test.com"
        assert fred.timeout == 5


class TestFetchSeries:
    @respx.mock
    async def test_success(self, fred):
        url = "https://fred.test.com/series/observations"
        respx.get(url).mock(
            return_value=httpx.Response(
                200,
                json={
                    "observations": [
                        {"date": "2024-01-15", "value": "4.25"},
                        {"date": "2024-01-14", "value": "4.20"},
                    ]
                },
            )
        )

        result = await fred._fetch_series("DGS10", limit=2)
        assert len(result) == 2
        assert result[0]["value"] == "4.25"
        await fred.close()

    @respx.mock
    async def test_filters_missing_values(self, fred):
        url = "https://fred.test.com/series/observations"
        respx.get(url).mock(
            return_value=httpx.Response(
                200,
                json={
                    "observations": [
                        {"date": "2024-01-15", "value": "."},
                        {"date": "2024-01-14", "value": "4.20"},
                        {"date": "2024-01-13", "value": ""},
                    ]
                },
            )
        )

        result = await fred._fetch_series("DGS10")
        assert len(result) == 1
        assert result[0]["value"] == "4.20"
        await fred.close()

    @respx.mock
    async def test_http_error(self, fred):
        url = "https://fred.test.com/series/observations"
        respx.get(url).mock(return_value=httpx.Response(500))

        result = await fred._fetch_series("DGS10")
        assert result == []
        await fred.close()

    @respx.mock
    async def test_network_error(self, fred):
        url = "https://fred.test.com/series/observations"
        respx.get(url).mock(side_effect=httpx.ConnectError("connection refused"))

        result = await fred._fetch_series("DGS10")
        assert result == []
        await fred.close()

    @respx.mock
    async def test_with_api_key(self, fred):
        url = "https://fred.test.com/series/observations"
        route = respx.get(url).mock(
            return_value=httpx.Response(
                200, json={"observations": [{"date": "2024-01-15", "value": "4.25"}]}
            )
        )

        await fred._fetch_series("DGS10")
        # Verify API key was passed
        assert "api_key=test-key" in str(route.calls[0].request.url)
        await fred.close()

    @respx.mock
    async def test_without_api_key(self):
        provider = FREDProvider(api_key="", base_url="https://fred.test.com")
        url = "https://fred.test.com/series/observations"
        route = respx.get(url).mock(return_value=httpx.Response(200, json={"observations": []}))

        await provider._fetch_series("DGS10")
        assert "api_key" not in str(route.calls[0].request.url)
        await provider.close()


class TestFetchYieldCurve:
    @respx.mock
    async def test_success(self, fred):
        url = "https://fred.test.com/series/observations"
        respx.get(url).mock(
            return_value=httpx.Response(
                200, json={"observations": [{"date": "2024-01-15", "value": "4.25"}]}
            )
        )

        result = await fred.fetch_yield_curve()
        assert result is not None
        assert isinstance(result, YieldCurveData)
        assert result.rate_10y == Decimal("4.25")
        assert result.time is not None
        await fred.close()

    @respx.mock
    async def test_inverted_curve(self, fred):
        url = "https://fred.test.com/series/observations"
        call_count = 0

        def respond(request):
            nonlocal call_count
            call_count += 1
            series_id = str(request.url.params.get("series_id", ""))

            if series_id == "DGS2":
                return httpx.Response(
                    200, json={"observations": [{"date": "2024-01-15", "value": "5.00"}]}
                )
            elif series_id == "DGS10":
                return httpx.Response(
                    200, json={"observations": [{"date": "2024-01-15", "value": "4.00"}]}
                )
            return httpx.Response(
                200, json={"observations": [{"date": "2024-01-15", "value": "4.50"}]}
            )

        respx.get(url).mock(side_effect=respond)

        result = await fred.fetch_yield_curve()
        assert result is not None
        assert result.is_inverted is True
        assert result.spread_2s10s < 0
        await fred.close()

    @respx.mock
    async def test_missing_10y(self, fred):
        url = "https://fred.test.com/series/observations"
        respx.get(url).mock(return_value=httpx.Response(200, json={"observations": []}))

        result = await fred.fetch_yield_curve()
        assert result is None
        await fred.close()


class TestFetchRealRates:
    @respx.mock
    async def test_success(self, fred):
        url = "https://fred.test.com/series/observations"

        def respond(request):
            series_id = str(request.url.params.get("series_id", ""))
            values = {
                "DGS10": "4.25",
                "T10YIE": "2.30",
                "DGS5": "4.00",
                "T5YIE": "2.20",
            }
            return httpx.Response(
                200,
                json={
                    "observations": [{"date": "2024-01-15", "value": values.get(series_id, "3.00")}]
                },
            )

        respx.get(url).mock(side_effect=respond)

        result = await fred.fetch_real_rates()
        assert result is not None
        assert isinstance(result, RealRatesData)
        assert result.nominal_10y == Decimal("4.25")
        assert result.breakeven_10y == Decimal("2.30")
        assert result.real_rate_10y == Decimal("4.25") - Decimal("2.30")
        await fred.close()

    @respx.mock
    async def test_missing_data(self, fred):
        url = "https://fred.test.com/series/observations"
        respx.get(url).mock(return_value=httpx.Response(200, json={"observations": []}))

        result = await fred.fetch_real_rates()
        assert result is None
        await fred.close()


class TestFetchRecessionProbability:
    @respx.mock
    async def test_high_risk(self, fred):
        url = "https://fred.test.com/series/observations"
        respx.get(url).mock(
            return_value=httpx.Response(
                200, json={"observations": [{"date": "2024-01-15", "value": "45.0"}]}
            )
        )

        result = await fred.fetch_recession_probability()
        assert result is not None
        assert isinstance(result, RecessionProbability)
        assert result.probability_12m == Decimal("45.0")
        assert result.signal_level == 2  # high
        await fred.close()

    @respx.mock
    async def test_elevated_risk(self, fred):
        url = "https://fred.test.com/series/observations"
        respx.get(url).mock(
            return_value=httpx.Response(
                200, json={"observations": [{"date": "2024-01-15", "value": "25.0"}]}
            )
        )

        result = await fred.fetch_recession_probability()
        assert result is not None
        assert result.signal_level == 1  # elevated
        await fred.close()

    @respx.mock
    async def test_low_risk(self, fred):
        url = "https://fred.test.com/series/observations"
        respx.get(url).mock(
            return_value=httpx.Response(
                200, json={"observations": [{"date": "2024-01-15", "value": "10.0"}]}
            )
        )

        result = await fred.fetch_recession_probability()
        assert result is not None
        assert result.signal_level == 0  # low
        await fred.close()

    @respx.mock
    async def test_no_data(self, fred):
        url = "https://fred.test.com/series/observations"
        respx.get(url).mock(return_value=httpx.Response(200, json={"observations": []}))

        result = await fred.fetch_recession_probability()
        assert result is None
        await fred.close()


class TestClose:
    async def test_close_open_client(self, fred):
        # Force client creation
        await fred._get_client()
        assert fred._client is not None

        await fred.close()
        assert fred._client is None

    async def test_close_no_client(self, fred):
        # Should not raise
        await fred.close()
