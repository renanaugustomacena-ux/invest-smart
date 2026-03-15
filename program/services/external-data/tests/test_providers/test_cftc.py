"""Tests for CFTC COT provider."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx

from external_data.providers.cftc import CFTCProvider, COTReport, MARKET_MAPPINGS


@pytest.fixture()
def cftc():
    return CFTCProvider(timeout=5)


class TestSafeInt:
    def test_valid_int(self, cftc):
        row = {"key1": "100"}
        assert cftc._safe_int(row, ["key1"]) == 100

    def test_comma_separated(self, cftc):
        row = {"key1": "1,234,567"}
        assert cftc._safe_int(row, ["key1"]) == 1234567

    def test_missing_key(self, cftc):
        row = {"other": "100"}
        assert cftc._safe_int(row, ["key1"]) == 0

    def test_non_numeric(self, cftc):
        row = {"key1": "abc"}
        assert cftc._safe_int(row, ["key1"]) == 0

    def test_multiple_keys_fallback(self, cftc):
        row = {"key2": "200"}
        assert cftc._safe_int(row, ["key1", "key2"]) == 200

    def test_empty_value(self, cftc):
        row = {"key1": ""}
        assert cftc._safe_int(row, ["key1"]) == 0

    def test_whitespace(self, cftc):
        row = {"key1": " 42 "}
        assert cftc._safe_int(row, ["key1"]) == 42


class TestParseRow:
    def test_valid_row(self, cftc):
        row = {
            "Report_Date_as_YYYY-MM-DD": "2024-01-15",
            "Asset_Mgr_Positions_Long_All": "100000",
            "Asset_Mgr_Positions_Short_All": "50000",
            "Lev_Money_Positions_Long_All": "80000",
            "Lev_Money_Positions_Short_All": "60000",
            "Open_Interest_All": "500000",
        }

        report = cftc._parse_row(row, "GOLD")
        assert report is not None
        assert report.market == "GOLD"
        assert report.asset_mgr_long == 100000
        assert report.asset_mgr_short == 50000
        assert report.asset_mgr_net == 50000
        assert report.lev_funds_long == 80000
        assert report.lev_funds_short == 60000
        assert report.lev_funds_net == 20000
        assert report.total_oi == 500000

    def test_missing_date(self, cftc):
        row = {
            "Report_Date_as_YYYY-MM-DD": "",
            "Open_Interest_All": "500000",
        }
        assert cftc._parse_row(row, "GOLD") is None

    def test_invalid_date(self, cftc):
        row = {
            "Report_Date_as_YYYY-MM-DD": "not-a-date",
            "Open_Interest_All": "500000",
        }
        assert cftc._parse_row(row, "GOLD") is None

    def test_zero_oi(self, cftc):
        row = {
            "Report_Date_as_YYYY-MM-DD": "2024-01-15",
            "Open_Interest_All": "0",
        }
        assert cftc._parse_row(row, "GOLD") is None

    def test_bullish_sentiment(self, cftc):
        row = {
            "Report_Date_as_YYYY-MM-DD": "2024-01-15",
            "Asset_Mgr_Positions_Long_All": "100000",
            "Asset_Mgr_Positions_Short_All": "10000",
            "Lev_Money_Positions_Long_All": "50000",
            "Lev_Money_Positions_Short_All": "5000",
            "Open_Interest_All": "500000",
        }

        report = cftc._parse_row(row, "GOLD")
        assert report is not None
        assert report.cot_sentiment == 1  # bullish (net > 10% OI)

    def test_bearish_sentiment(self, cftc):
        row = {
            "Report_Date_as_YYYY-MM-DD": "2024-01-15",
            "Asset_Mgr_Positions_Long_All": "10000",
            "Asset_Mgr_Positions_Short_All": "100000",
            "Lev_Money_Positions_Long_All": "5000",
            "Lev_Money_Positions_Short_All": "50000",
            "Open_Interest_All": "500000",
        }

        report = cftc._parse_row(row, "GOLD")
        assert report is not None
        assert report.cot_sentiment == -1  # bearish

    def test_neutral_sentiment(self, cftc):
        row = {
            "Report_Date_as_YYYY-MM-DD": "2024-01-15",
            "Asset_Mgr_Positions_Long_All": "100",
            "Asset_Mgr_Positions_Short_All": "100",
            "Lev_Money_Positions_Long_All": "100",
            "Lev_Money_Positions_Short_All": "100",
            "Open_Interest_All": "500000",
        }

        report = cftc._parse_row(row, "GOLD")
        assert report is not None
        assert report.cot_sentiment == 0  # neutral


class TestParseCotData:
    def test_parse_valid(self, cftc):
        # Build tab-separated text with headers and a Gold row
        headers = (
            "Market_and_Exchange_Names\t"
            "Report_Date_as_YYYY-MM-DD\t"
            "Asset_Mgr_Positions_Long_All\t"
            "Asset_Mgr_Positions_Short_All\t"
            "Lev_Money_Positions_Long_All\t"
            "Lev_Money_Positions_Short_All\t"
            "Open_Interest_All"
        )
        gold_row = (
            "GOLD - COMMODITY EXCHANGE INC.\t"
            "2024-01-15\t"
            "100000\t"
            "50000\t"
            "80000\t"
            "60000\t"
            "500000"
        )
        irrelevant_row = (
            "CORN - CHICAGO BOARD OF TRADE\t"
            "2024-01-15\t"
            "200000\t"
            "100000\t"
            "50000\t"
            "30000\t"
            "800000"
        )

        text = f"{headers}\n{gold_row}\n{irrelevant_row}\n"
        reports = cftc._parse_cot_data(text)

        assert len(reports) == 1
        assert reports[0].market == "GOLD"

    def test_parse_empty(self, cftc):
        reports = cftc._parse_cot_data("")
        assert reports == []

    def test_parse_multiple_markets(self, cftc):
        headers = (
            "Market_and_Exchange_Names\t"
            "Report_Date_as_YYYY-MM-DD\t"
            "Asset_Mgr_Positions_Long_All\t"
            "Asset_Mgr_Positions_Short_All\t"
            "Lev_Money_Positions_Long_All\t"
            "Lev_Money_Positions_Short_All\t"
            "Open_Interest_All"
        )
        gold = "GOLD - COMMODITY EXCHANGE INC.\t2024-01-15\t100\t50\t80\t60\t500"
        silver = "SILVER - COMMODITY EXCHANGE INC.\t2024-01-15\t200\t100\t60\t40\t600"

        text = f"{headers}\n{gold}\n{silver}\n"
        reports = cftc._parse_cot_data(text)
        assert len(reports) == 2
        markets = {r.market for r in reports}
        assert "GOLD" in markets
        assert "SILVER" in markets


class TestFetchLatestCot:
    @respx.mock
    async def test_success(self, cftc):
        headers = (
            "Market_and_Exchange_Names\t"
            "Report_Date_as_YYYY-MM-DD\t"
            "Asset_Mgr_Positions_Long_All\t"
            "Asset_Mgr_Positions_Short_All\t"
            "Lev_Money_Positions_Long_All\t"
            "Lev_Money_Positions_Short_All\t"
            "Open_Interest_All"
        )
        row = "GOLD - COMMODITY EXCHANGE INC.\t2024-01-15\t100000\t50000\t80000\t60000\t500000"
        text = f"{headers}\n{row}\n"

        respx.get(CFTCProvider.COT_URL).mock(return_value=httpx.Response(200, text=text))

        reports = await cftc.fetch_latest_cot()
        assert len(reports) == 1
        assert reports[0].market == "GOLD"
        await cftc.close()

    @respx.mock
    async def test_http_error(self, cftc):
        respx.get(CFTCProvider.COT_URL).mock(return_value=httpx.Response(500))

        reports = await cftc.fetch_latest_cot()
        assert reports == []
        await cftc.close()

    @respx.mock
    async def test_network_error(self, cftc):
        respx.get(CFTCProvider.COT_URL).mock(side_effect=httpx.ConnectError("timeout"))

        reports = await cftc.fetch_latest_cot()
        assert reports == []
        await cftc.close()


class TestFetchGoldCot:
    @respx.mock
    async def test_found(self, cftc):
        headers = (
            "Market_and_Exchange_Names\t"
            "Report_Date_as_YYYY-MM-DD\t"
            "Asset_Mgr_Positions_Long_All\t"
            "Asset_Mgr_Positions_Short_All\t"
            "Lev_Money_Positions_Long_All\t"
            "Lev_Money_Positions_Short_All\t"
            "Open_Interest_All"
        )
        row = "GOLD - COMMODITY EXCHANGE INC.\t2024-01-15\t100000\t50000\t80000\t60000\t500000"
        respx.get(CFTCProvider.COT_URL).mock(
            return_value=httpx.Response(200, text=f"{headers}\n{row}\n")
        )

        report = await cftc.fetch_gold_cot()
        assert report is not None
        assert report.market == "GOLD"
        await cftc.close()

    @respx.mock
    async def test_not_found(self, cftc):
        headers = "Market_and_Exchange_Names\t" "Report_Date_as_YYYY-MM-DD\t" "Open_Interest_All"
        respx.get(CFTCProvider.COT_URL).mock(return_value=httpx.Response(200, text=f"{headers}\n"))

        report = await cftc.fetch_gold_cot()
        assert report is None
        await cftc.close()


class TestClose:
    async def test_close(self, cftc):
        await cftc._get_client()
        await cftc.close()
        assert cftc._client is None
