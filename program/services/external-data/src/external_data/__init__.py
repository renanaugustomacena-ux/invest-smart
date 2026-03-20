# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""MONEYMAKER External Data Service.

Fetches quantitative macro data from external APIs:
- FRED: Yield curve, real rates, recession probability
- CBOE: VIX data
- CFTC: COT reports
- Polygon: DXY index

Design principles:
- Only deterministic, quantitative data
- No sentiment or subjective indicators
- All data must be mathematically verifiable
"""

__version__ = "1.0.0"
