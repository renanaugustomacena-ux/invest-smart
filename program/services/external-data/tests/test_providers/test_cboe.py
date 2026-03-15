"""Tests for CBOE and Yahoo VIX providers."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx

from external_data.providers.cboe import CBOEProvider, VIXData, YahooVIXProvider


class TestVIXDataRegime:
    def test_calm(self):
        assert VIXData.calculate_regime(Decimal("12.5")) == 0

    def test_elevated(self):
        assert VIXData.calculate_regime(Decimal("15.0")) == 1
        assert VIXData.calculate_regime(Decimal("20.0")) == 1
        assert VIXData.calculate_regime(Decimal("24.9")) == 1

    def test_panic(self):
        assert VIXData.calculate_regime(Decimal("25.0")) == 2
        assert VIXData.calculate_regime(Decimal("40.0")) == 2


class TestCBOEProvider:
    @pytest.fixture()
    def cboe(self):
        return CBOEProvider(timeout=5)

    @respx.mock
    async def test_fetch_vix_success(self, cboe):
        respx.get(CBOEProvider.VIX_URL).mock(return_value=httpx.Response(200, json={
            "data": [
                [1705300000000, 13.1, 13.5, 12.9, 13.2, 100000],
                [1705310000000, 13.2, 14.0, 13.0, 13.8, 120000],
            ]
        }))

        result = await cboe.fetch_vix()
        assert result is not None
        assert isinstance(result, VIXData)
        assert result.vix_spot == Decimal("13.8")
        assert result.regime == 0  # calm (< 15)
        await cboe.close()

    @respx.mock
    async def test_fetch_vix_empty_data(self, cboe):
        respx.get(CBOEProvider.VIX_URL).mock(return_value=httpx.Response(200, json={
            "data": []
        }))

        result = await cboe.fetch_vix()
        assert result is None
        await cboe.close()

    @respx.mock
    async def test_fetch_vix_short_array(self, cboe):
        respx.get(CBOEProvider.VIX_URL).mock(return_value=httpx.Response(200, json={
            "data": [[1705300000000, 13.1, 13.5]]
        }))

        result = await cboe.fetch_vix()
        assert result is None
        await cboe.close()

    @respx.mock
    async def test_fetch_vix_http_error(self, cboe):
        respx.get(CBOEProvider.VIX_URL).mock(return_value=httpx.Response(500))

        result = await cboe.fetch_vix()
        assert result is None
        await cboe.close()

    @respx.mock
    async def test_fetch_vix_network_error(self, cboe):
        respx.get(CBOEProvider.VIX_URL).mock(side_effect=httpx.ConnectError("timeout"))

        result = await cboe.fetch_vix()
        assert result is None
        await cboe.close()

    @respx.mock
    async def test_fetch_vix_quote_success(self, cboe):
        respx.get(CBOEProvider.VIX_FUTURES_URL).mock(return_value=httpx.Response(200, json={
            "data": {"last_price": 18.5}
        }))

        result = await cboe.fetch_vix_quote()
        assert result is not None
        assert result.vix_spot == Decimal("18.5")
        assert result.regime == 1  # elevated (15-25)
        await cboe.close()

    @respx.mock
    async def test_fetch_vix_quote_missing_price(self, cboe):
        respx.get(CBOEProvider.VIX_FUTURES_URL).mock(return_value=httpx.Response(200, json={
            "data": {}
        }))

        result = await cboe.fetch_vix_quote()
        assert result is None
        await cboe.close()

    @respx.mock
    async def test_fetch_vix_quote_alternative_path(self, cboe):
        respx.get(CBOEProvider.VIX_FUTURES_URL).mock(return_value=httpx.Response(200, json={
            "last_price": 30.0
        }))

        result = await cboe.fetch_vix_quote()
        assert result is not None
        assert result.vix_spot == Decimal("30.0")
        assert result.regime == 2  # panic (>= 25)
        await cboe.close()

    @respx.mock
    async def test_fetch_vix_term_structure(self, cboe):
        respx.get(CBOEProvider.VIX_URL).mock(return_value=httpx.Response(200, json={
            "data": [[1705300000000, 20.0, 21.0, 19.0, 20.5, 100000]]
        }))

        result = await cboe.fetch_vix_term_structure()
        assert result is not None
        assert result.vix_spot == Decimal("20.5")
        await cboe.close()

    async def test_close(self, cboe):
        await cboe._get_client()
        await cboe.close()
        assert cboe._client is None


class TestYahooVIXProvider:
    @pytest.fixture()
    def yahoo(self):
        return YahooVIXProvider(timeout=5)

    @respx.mock
    async def test_fetch_vix_success(self, yahoo):
        respx.get(YahooVIXProvider.YAHOO_URL).mock(return_value=httpx.Response(200, json={
            "chart": {
                "result": [{
                    "meta": {"regularMarketPrice": 16.5},
                    "indicators": {},
                }]
            }
        }))

        result = await yahoo.fetch_vix()
        assert result is not None
        assert result.vix_spot == Decimal("16.5")
        assert result.regime == 1  # elevated
        await yahoo.close()

    @respx.mock
    async def test_fetch_vix_no_result(self, yahoo):
        respx.get(YahooVIXProvider.YAHOO_URL).mock(return_value=httpx.Response(200, json={
            "chart": {"result": []}
        }))

        result = await yahoo.fetch_vix()
        assert result is None
        await yahoo.close()

    @respx.mock
    async def test_fetch_vix_no_price(self, yahoo):
        respx.get(YahooVIXProvider.YAHOO_URL).mock(return_value=httpx.Response(200, json={
            "chart": {"result": [{"meta": {}}]}
        }))

        result = await yahoo.fetch_vix()
        assert result is None
        await yahoo.close()

    @respx.mock
    async def test_fetch_vix_error(self, yahoo):
        respx.get(YahooVIXProvider.YAHOO_URL).mock(side_effect=httpx.ConnectError("timeout"))

        result = await yahoo.fetch_vix()
        assert result is None
        await yahoo.close()

    async def test_close(self, yahoo):
        await yahoo._get_client()
        await yahoo.close()
        assert yahoo._client is None
