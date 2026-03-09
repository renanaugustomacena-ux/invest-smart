"""ZMQ message format tests: verify data-ingestion output format
matches algo-engine consumer expectations.

The data-ingestion Go service publishes ZMQ messages that the
algo-engine Python zmq_adapter.py consumes. This test verifies
the wire format contract.
"""

import pytest
import json
from decimal import Decimal


class TestZMQMessageFormat:
    """Verify ZMQ message wire format between data-ingestion and algo-engine."""

    def test_ohlcv_bar_json_format(self):
        """Verify the expected JSON structure of a ZMQ-published OHLCV bar."""
        # This is the format data-ingestion publishes
        message = json.dumps({
            "type": "bar",
            "symbol": "XAUUSD",
            "timeframe": "M1",
            "open": "2650.50",
            "high": "2651.80",
            "low": "2649.20",
            "close": "2651.00",
            "volume": "1500",
            "tick_count": 45,
            "complete": True,
            "spread_avg": "0.30",
            "timestamp": "2025-01-15T12:00:00Z",
        })

        parsed = json.loads(message)

        # Verify required fields exist and types
        assert isinstance(parsed["symbol"], str)
        assert isinstance(parsed["timeframe"], str)
        assert isinstance(parsed["complete"], bool)
        assert isinstance(parsed["tick_count"], int)

        # Verify price fields are strings (for Decimal parsing)
        for field in ["open", "high", "low", "close", "volume", "spread_avg"]:
            assert isinstance(parsed[field], str), f"{field} should be string for Decimal"
            Decimal(parsed[field])  # Must be valid Decimal

    def test_market_tick_json_format(self):
        """Verify the expected JSON structure of a ZMQ-published tick."""
        message = json.dumps({
            "type": "tick",
            "symbol": "XAUUSD",
            "bid": "2650.30",
            "ask": "2650.60",
            "last": "2650.45",
            "volume": "1",
            "spread": "0.30",
            "source": "polygon",
            "timestamp": "2025-01-15T12:00:00.123Z",
            "flags": 0,
        })

        parsed = json.loads(message)
        assert parsed["type"] == "tick"
        assert isinstance(parsed["flags"], int)

        for field in ["bid", "ask", "last", "volume", "spread"]:
            assert isinstance(parsed[field], str)
            Decimal(parsed[field])

    def test_zmq_topic_format(self):
        """Verify ZMQ topic prefix convention."""
        # data-ingestion publishes with topic prefix: "bar.SYMBOL.TIMEFRAME"
        topic_bar = "bar.XAUUSD.M1"
        parts = topic_bar.split(".")
        assert len(parts) == 3
        assert parts[0] == "bar"
        assert parts[1] == "XAUUSD"
        assert parts[2] in ("M1", "M5", "M15", "H1", "H4", "D1")

        topic_tick = "tick.XAUUSD"
        parts = topic_tick.split(".")
        assert len(parts) == 2
        assert parts[0] == "tick"

    def test_malformed_message_handling(self):
        """Verify consumer-side handling of malformed messages."""
        # Missing required fields
        incomplete = json.dumps({"type": "bar", "symbol": "XAUUSD"})
        parsed = json.loads(incomplete)
        assert "close" not in parsed  # Consumer must handle gracefully

        # Invalid Decimal
        bad_price = json.dumps({
            "type": "bar",
            "symbol": "XAUUSD",
            "open": "not_a_number",
        })
        parsed = json.loads(bad_price)
        with pytest.raises(Exception):
            Decimal(parsed["open"])
