"""CFTC (Commodity Futures Trading Commission) Provider.

Fetches COT (Commitment of Traders) reports for positioning data.

COT Report Categories:
- Producer/Merchant: Physical market participants (hedgers)
- Swap Dealer: OTC derivatives dealers
- Managed Money: CTAs, hedge funds, asset managers
- Other Reportables: Other large traders

Key Insights for Gold:
- Asset Manager positioning shows "smart money" sentiment
- Extreme readings (>90th or <10th percentile) signal potential reversals
- Large spec net long at highs = bearish signal
- Large spec net short at lows = bullish signal

Data released every Friday at 3:30 PM ET for positions as of Tuesday.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class COTReport:
    """Single COT report for a market."""
    time: datetime
    market: str  # e.g., "GOLD", "SILVER", "EUR"
    # Asset Managers
    asset_mgr_long: int
    asset_mgr_short: int
    asset_mgr_net: int
    asset_mgr_pct_oi: Decimal
    # Leveraged Funds
    lev_funds_long: int
    lev_funds_short: int
    lev_funds_net: int
    lev_funds_pct_oi: Decimal
    # Total Open Interest
    total_oi: int
    # Computed sentiment
    cot_sentiment: int = 0  # -1=bearish, 0=neutral, 1=bullish
    extreme_reading: bool = False


# Market name mappings in CFTC data
MARKET_MAPPINGS = {
    "GOLD - COMMODITY EXCHANGE INC.": "GOLD",
    "SILVER - COMMODITY EXCHANGE INC.": "SILVER",
    "EURO FX - CHICAGO MERCANTILE EXCHANGE": "EUR",
    "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE": "JPY",
    "BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE": "GBP",
    "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE": "CHF",
    "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE": "CAD",
    "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE": "AUD",
    "U.S. DOLLAR INDEX - ICE FUTURES U.S.": "DXY",
    "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE": "WTI",
    "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE": "NG",
}

# Markets we care about for MONEYMAKER
RELEVANT_MARKETS = {"GOLD", "SILVER", "EUR", "JPY", "GBP", "DXY"}


class CFTCProvider:
    """Provider per dati COT da CFTC."""

    # CFTC disaggregated COT data (public domain)
    # This is the current week's data
    COT_URL = "https://www.cftc.gov/dea/newcot/c_disagg.txt"

    # Historical data (full year)
    COT_HISTORY_URL = "https://www.cftc.gov/files/dea/history/com_disagg_txt_{year}.zip"

    def __init__(self, timeout: int = 60) -> None:
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._historical_cache: dict[str, list[COTReport]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"User-Agent": "MONEYMAKER-Trading/1.0"},
            )
        return self._client

    async def fetch_latest_cot(self) -> list[COTReport]:
        """Fetch latest COT report from CFTC.

        Returns:
            List of COTReport for relevant markets
        """
        client = await self._get_client()

        try:
            response = await client.get(self.COT_URL)
            response.raise_for_status()

            # Parse the text file (tab-separated)
            reports = self._parse_cot_data(response.text)

            logger.info("COT reports fetched", count=len(reports))
            return reports

        except httpx.HTTPStatusError as e:
            logger.warning("CFTC API error", status=e.response.status_code)
            return []
        except Exception as e:
            logger.error("CFTC fetch error", error=str(e))
            return []

    def _parse_cot_data(self, text: str) -> list[COTReport]:
        """Parse CFTC disaggregated COT data.

        The file is tab-separated with headers.
        """
        reports = []

        try:
            # Use csv reader for tab-separated values
            reader = csv.DictReader(io.StringIO(text), delimiter="\t")

            for row in reader:
                market_name = row.get("Market_and_Exchange_Names", "").strip()

                # Check if this is a market we care about
                normalized_market = MARKET_MAPPINGS.get(market_name)
                if normalized_market not in RELEVANT_MARKETS:
                    continue

                try:
                    report = self._parse_row(row, normalized_market)
                    if report:
                        reports.append(report)
                except Exception as parse_err:
                    logger.debug(
                        "Error parsing COT row",
                        market=market_name,
                        error=str(parse_err),
                    )
                    continue

        except Exception as e:
            logger.error("COT parse error", error=str(e))

        return reports

    def _parse_row(self, row: dict[str, str], market: str) -> COTReport | None:
        """Parse a single COT data row."""
        # Get report date
        date_str = row.get("Report_Date_as_YYYY-MM-DD", "")
        if not date_str:
            return None

        try:
            report_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return None

        # Asset Manager positions (Disaggregated format)
        # Column names vary, try multiple patterns
        asset_mgr_long = self._safe_int(row, [
            "Asset_Mgr_Positions_Long_All",
            "AssetMgr_Positions_Long_All",
            "M_Money_Positions_Long_All",
        ])
        asset_mgr_short = self._safe_int(row, [
            "Asset_Mgr_Positions_Short_All",
            "AssetMgr_Positions_Short_All",
            "M_Money_Positions_Short_All",
        ])

        # Leveraged Funds
        lev_funds_long = self._safe_int(row, [
            "Lev_Money_Positions_Long_All",
            "LevMoney_Positions_Long_All",
        ])
        lev_funds_short = self._safe_int(row, [
            "Lev_Money_Positions_Short_All",
            "LevMoney_Positions_Short_All",
        ])

        # Total Open Interest
        total_oi = self._safe_int(row, [
            "Open_Interest_All",
            "OI_All",
        ])

        if total_oi == 0:
            return None

        # Calculate net positions
        asset_mgr_net = asset_mgr_long - asset_mgr_short
        lev_funds_net = lev_funds_long - lev_funds_short

        # Calculate % of OI
        asset_mgr_pct = Decimal(str(abs(asset_mgr_net) / total_oi * 100)) if total_oi > 0 else Decimal("0")
        lev_funds_pct = Decimal(str(abs(lev_funds_net) / total_oi * 100)) if total_oi > 0 else Decimal("0")

        # Determine sentiment from net positions
        # Positive net = bullish, negative = bearish
        combined_net = asset_mgr_net + lev_funds_net
        if combined_net > total_oi * 0.1:  # > 10% of OI net long
            sentiment = 1
        elif combined_net < -total_oi * 0.1:  # > 10% of OI net short
            sentiment = -1
        else:
            sentiment = 0

        return COTReport(
            time=report_date,
            market=market,
            asset_mgr_long=asset_mgr_long,
            asset_mgr_short=asset_mgr_short,
            asset_mgr_net=asset_mgr_net,
            asset_mgr_pct_oi=asset_mgr_pct,
            lev_funds_long=lev_funds_long,
            lev_funds_short=lev_funds_short,
            lev_funds_net=lev_funds_net,
            lev_funds_pct_oi=lev_funds_pct,
            total_oi=total_oi,
            cot_sentiment=sentiment,
            extreme_reading=False,  # Would need historical data to determine
        )

    def _safe_int(self, row: dict[str, str], keys: list[str]) -> int:
        """Safely extract integer from row, trying multiple keys."""
        for key in keys:
            value = row.get(key, "").strip().replace(",", "")
            if value:
                try:
                    return int(value)
                except ValueError:
                    continue
        return 0

    async def fetch_gold_cot(self) -> COTReport | None:
        """Convenience method to fetch only Gold COT.

        Returns:
            COTReport for Gold, or None if not found
        """
        reports = await self.fetch_latest_cot()
        for report in reports:
            if report.market == "GOLD":
                return report
        return None

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
