# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""CBOE (Chicago Board Options Exchange) Provider.

Fetches VIX data from publicly available CBOE endpoints.

VIX (Volatility Index):
- Measures 30-day expected volatility of S&P 500
- Often called the "fear gauge"
- Critical for Gold trading: high VIX = flight to safety = Gold up

VIX Regimes:
- < 15: Low volatility (calm markets)
- 15-25: Normal/elevated volatility
- > 25: High volatility (fear/panic)
- > 30: Crisis levels

VIX Term Structure:
- Contango (normal): VIX futures > VIX spot
- Backwardation (fear): VIX futures < VIX spot
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import httpx

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VIXData:
    """VIX data snapshot."""

    time: datetime
    vix_spot: Decimal
    vix_1m: Decimal | None = None
    vix_2m: Decimal | None = None
    vix_3m: Decimal | None = None
    term_slope: Decimal | None = None
    is_contango: bool | None = None
    regime: int = 0  # 0=calm, 1=elevated, 2=panic

    @classmethod
    def calculate_regime(cls, vix_value: Decimal) -> int:
        """Calculate VIX regime from spot value."""
        if vix_value >= 25:
            return 2  # panic
        elif vix_value >= 15:
            return 1  # elevated
        return 0  # calm


class CBOEProvider:
    """Provider per dati VIX da CBOE."""

    # CBOE delayed quotes endpoint (public, no auth needed)
    VIX_URL = "https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/_VIX.json"

    # Alternative: VIX futures for term structure
    VIX_FUTURES_URL = "https://cdn.cboe.com/api/global/delayed_quotes/quotes/_VIX.json"

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "User-Agent": "MONEYMAKER-Trading/1.0",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def fetch_vix(self) -> VIXData | None:
        """Fetch current VIX data from CBOE.

        Returns:
            VIXData with latest VIX values, or None on error
        """
        client = await self._get_client()

        try:
            response = await client.get(self.VIX_URL)
            response.raise_for_status()

            data = response.json()

            # CBOE format: {"data": [[timestamp, open, high, low, close, volume], ...]}
            chart_data = data.get("data", [])

            if not chart_data:
                logger.warning("No VIX data in CBOE response")
                return None

            # Get most recent data point
            latest = chart_data[-1]

            # Format: [timestamp_ms, open, high, low, close, volume]
            if len(latest) < 5:
                logger.warning("Invalid VIX data format")
                return None

            vix_close = Decimal(str(latest[4]))
            regime = VIXData.calculate_regime(vix_close)

            logger.debug("VIX fetched", vix=float(vix_close), regime=regime)

            return VIXData(
                time=datetime.now(timezone.utc),
                vix_spot=vix_close,
                regime=regime,
            )

        except httpx.HTTPStatusError as e:
            logger.warning("CBOE API error", status=e.response.status_code)
            return None
        except Exception as e:
            logger.error("CBOE fetch error", error=str(e))
            return None

    async def fetch_vix_quote(self) -> VIXData | None:
        """Fetch VIX from delayed quote endpoint (alternative).

        Returns:
            VIXData with latest values
        """
        client = await self._get_client()

        try:
            response = await client.get(self.VIX_FUTURES_URL)
            response.raise_for_status()

            data = response.json()

            # Quote format varies, try to extract last price
            last_price = data.get("data", {}).get("last_price")
            if last_price is None:
                # Try alternative path
                last_price = data.get("last_price")

            if last_price is None:
                logger.warning("Could not find VIX price in quote data")
                return None

            vix_value = Decimal(str(last_price))
            regime = VIXData.calculate_regime(vix_value)

            return VIXData(
                time=datetime.now(timezone.utc),
                vix_spot=vix_value,
                regime=regime,
            )

        except Exception as e:
            logger.error("CBOE quote fetch error", error=str(e))
            return None

    async def fetch_vix_term_structure(self) -> VIXData | None:
        """Fetch VIX with term structure (spot + futures).

        Calculates contango/backwardation from futures curve.

        Returns:
            VIXData with term structure data
        """
        # First get spot VIX
        spot_data = await self.fetch_vix()
        if spot_data is None:
            return None

        # TODO: Add VIX futures fetch for term structure
        # For now, return spot only
        # VIX futures data would need to be fetched from:
        # - CBOE VIX futures settlements
        # - Or calculated from VX futures chain

        return spot_data

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# Backup provider using Yahoo Finance
class YahooVIXProvider:
    """Backup VIX provider using Yahoo Finance.

    Used when CBOE endpoints are unavailable.
    """

    YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/^VIX"

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"User-Agent": "MONEYMAKER-Trading/1.0"},
            )
        return self._client

    async def fetch_vix(self) -> VIXData | None:
        """Fetch VIX from Yahoo Finance."""
        client = await self._get_client()

        try:
            params = {"interval": "1m", "range": "1d"}
            response = await client.get(self.YAHOO_URL, params=params)
            response.raise_for_status()

            data = response.json()

            result = data.get("chart", {}).get("result", [])
            if not result:
                return None

            quote = result[0].get("meta", {})
            price = quote.get("regularMarketPrice")

            if price is None:
                return None

            vix_value = Decimal(str(price))
            regime = VIXData.calculate_regime(vix_value)

            return VIXData(
                time=datetime.now(timezone.utc),
                vix_spot=vix_value,
                regime=regime,
            )

        except Exception as e:
            logger.error("Yahoo VIX fetch error", error=str(e))
            return None

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
