"""FRED (Federal Reserve Economic Data) Provider.

Fetches yield curve data, real rates, and recession probability from FRED API.

FRED Series IDs:
- DGS2: 2-Year Treasury Constant Maturity Rate
- DGS5: 5-Year Treasury Constant Maturity Rate
- DGS10: 10-Year Treasury Constant Maturity Rate
- DGS30: 30-Year Treasury Constant Maturity Rate
- T10YIE: 10-Year Breakeven Inflation Rate
- T5YIE: 5-Year Breakeven Inflation Rate
- RECPROUSM156N: Recession Probability (Smoothed)

API Documentation: https://fred.stlouisfed.org/docs/api/fred/
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class YieldCurveData:
    """Yield curve snapshot."""
    time: datetime
    rate_2y: Decimal | None
    rate_5y: Decimal | None
    rate_10y: Decimal
    rate_30y: Decimal | None
    spread_2s10s: Decimal | None = None
    is_inverted: bool = False


@dataclass
class RealRatesData:
    """Real rates (inflation-adjusted) snapshot."""
    time: datetime
    nominal_10y: Decimal
    breakeven_10y: Decimal
    real_rate_10y: Decimal
    nominal_5y: Decimal | None = None
    breakeven_5y: Decimal | None = None
    real_rate_5y: Decimal | None = None


@dataclass
class RecessionProbability:
    """Recession probability data."""
    time: datetime
    probability_12m: Decimal
    signal_level: int  # 0=low, 1=elevated, 2=high


class FREDProvider:
    """Provider per dati FRED API."""

    # Series IDs per i dati che ci servono
    SERIES = {
        "2y_yield": "DGS2",
        "5y_yield": "DGS5",
        "10y_yield": "DGS10",
        "30y_yield": "DGS30",
        "10y_breakeven": "T10YIE",
        "5y_breakeven": "T5YIE",
        "recession_prob": "RECPROUSM156N",
    }

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.stlouisfed.org/fred",
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))
        return self._client

    async def _fetch_series(
        self,
        series_id: str,
        observation_start: str | None = None,
        limit: int = 1,
    ) -> list[dict[str, Any]]:
        """Fetch observations from a FRED series.

        Args:
            series_id: FRED series identifier
            observation_start: Start date (YYYY-MM-DD)
            limit: Number of observations to return

        Returns:
            List of observation dicts with 'date' and 'value' keys
        """
        client = await self._get_client()

        params: dict[str, Any] = {
            "series_id": series_id,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }

        if self.api_key:
            params["api_key"] = self.api_key

        if observation_start:
            params["observation_start"] = observation_start

        url = f"{self.base_url}/series/observations"

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            observations = data.get("observations", [])

            # Filter out missing values (FRED uses "." for missing)
            return [
                obs for obs in observations
                if obs.get("value") and obs["value"] != "."
            ]

        except httpx.HTTPStatusError as e:
            logger.warning(
                "FRED API error",
                series=series_id,
                status=e.response.status_code,
            )
            return []
        except Exception as e:
            logger.error("FRED fetch error", series=series_id, error=str(e))
            return []

    async def fetch_yield_curve(self) -> YieldCurveData | None:
        """Fetch latest yield curve data.

        Returns:
            YieldCurveData with latest treasury yields, or None on error
        """
        # Fetch all yields in parallel
        tasks = [
            self._fetch_series(self.SERIES["2y_yield"]),
            self._fetch_series(self.SERIES["5y_yield"]),
            self._fetch_series(self.SERIES["10y_yield"]),
            self._fetch_series(self.SERIES["30y_yield"]),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Parse results
        def get_latest_value(obs_list: list | Exception) -> Decimal | None:
            if isinstance(obs_list, Exception) or not obs_list:
                return None
            try:
                return Decimal(obs_list[0]["value"])
            except (KeyError, IndexError, ValueError):
                return None

        rate_2y = get_latest_value(results[0])
        rate_5y = get_latest_value(results[1])
        rate_10y = get_latest_value(results[2])
        rate_30y = get_latest_value(results[3])

        if rate_10y is None:
            logger.warning("Failed to fetch 10Y yield (required)")
            return None

        # Calculate spread
        spread_2s10s = None
        is_inverted = False
        if rate_2y is not None:
            spread_2s10s = rate_10y - rate_2y
            is_inverted = spread_2s10s < 0

        return YieldCurveData(
            time=datetime.now(timezone.utc),
            rate_2y=rate_2y,
            rate_5y=rate_5y,
            rate_10y=rate_10y,
            rate_30y=rate_30y,
            spread_2s10s=spread_2s10s,
            is_inverted=is_inverted,
        )

    async def fetch_real_rates(self) -> RealRatesData | None:
        """Fetch latest real rates (nominal - inflation expectations).

        Returns:
            RealRatesData with latest values, or None on error
        """
        tasks = [
            self._fetch_series(self.SERIES["10y_yield"]),
            self._fetch_series(self.SERIES["10y_breakeven"]),
            self._fetch_series(self.SERIES["5y_yield"]),
            self._fetch_series(self.SERIES["5y_breakeven"]),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        def get_value(obs_list: list | Exception) -> Decimal | None:
            if isinstance(obs_list, Exception) or not obs_list:
                return None
            try:
                return Decimal(obs_list[0]["value"])
            except (KeyError, IndexError, ValueError):
                return None

        nominal_10y = get_value(results[0])
        breakeven_10y = get_value(results[1])

        if nominal_10y is None or breakeven_10y is None:
            logger.warning("Failed to fetch 10Y nominal or breakeven")
            return None

        real_10y = nominal_10y - breakeven_10y

        # 5Y rates (optional)
        nominal_5y = get_value(results[2])
        breakeven_5y = get_value(results[3])
        real_5y = None
        if nominal_5y is not None and breakeven_5y is not None:
            real_5y = nominal_5y - breakeven_5y

        return RealRatesData(
            time=datetime.now(timezone.utc),
            nominal_10y=nominal_10y,
            breakeven_10y=breakeven_10y,
            real_rate_10y=real_10y,
            nominal_5y=nominal_5y,
            breakeven_5y=breakeven_5y,
            real_rate_5y=real_5y,
        )

    async def fetch_recession_probability(self) -> RecessionProbability | None:
        """Fetch recession probability from NY Fed model.

        Returns:
            RecessionProbability with latest value, or None on error
        """
        observations = await self._fetch_series(self.SERIES["recession_prob"])

        if not observations:
            logger.warning("Failed to fetch recession probability")
            return None

        try:
            prob = Decimal(observations[0]["value"])
        except (KeyError, ValueError):
            return None

        # Classify signal level
        # < 20%: low risk
        # 20-40%: elevated
        # > 40%: high risk
        if prob >= 40:
            signal_level = 2
        elif prob >= 20:
            signal_level = 1
        else:
            signal_level = 0

        return RecessionProbability(
            time=datetime.now(timezone.utc),
            probability_12m=prob,
            signal_level=signal_level,
        )

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
