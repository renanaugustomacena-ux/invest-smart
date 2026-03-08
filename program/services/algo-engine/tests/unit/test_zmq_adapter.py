"""Tests for algo_engine.zmq_adapter — ZMQ message parsing and bar buffering."""

import json
from decimal import Decimal

from algo_engine.features.pipeline import OHLCVBar
from algo_engine.zmq_adapter import BarBuffer, determine_message_type, parse_bar_message


class TestDetermineMessageType:
    def test_bar_topic(self):
        assert determine_message_type("bar.XAUUSD.M1") == "bar"

    def test_bar_topic_with_slash(self):
        assert determine_message_type("bar.BTC/USDT.M1") == "bar"

    def test_tick_topic(self):
        assert determine_message_type("trade.binance.BTC/USDT") == "tick"

    def test_unknown_topic(self):
        assert determine_message_type("depth.binance.BTC/USDT") == "unknown"

    def test_empty_topic(self):
        assert determine_message_type("") == "unknown"

    def test_bar_prefix_only(self):
        assert determine_message_type("bar.") == "bar"


class TestParseBarMessage:
    def test_valid_bar(self):
        payload = json.dumps(
            {
                "symbol": "XAUUSD",
                "timeframe": "M1",
                "open_time": "2024-02-21T12:00:00Z",
                "close_time": "2024-02-21T12:01:00Z",
                "open": "2050.30",
                "high": "2051.10",
                "low": "2049.80",
                "close": "2050.90",
                "volume": "145.20",
                "tick_count": 47,
            }
        ).encode()

        symbol, _tf, bar = parse_bar_message(payload)
        assert symbol == "XAUUSD"
        assert isinstance(bar, OHLCVBar)
        assert bar.open == Decimal("2050.30")
        assert bar.high == Decimal("2051.10")
        assert bar.low == Decimal("2049.80")
        assert bar.close == Decimal("2050.90")
        assert bar.volume == Decimal("145.20")

    def test_all_prices_are_decimal(self):
        payload = json.dumps(
            {
                "symbol": "EURUSD",
                "timeframe": "M5",
                "open_time": "2024-01-01T00:00:00Z",
                "close_time": "2024-01-01T00:05:00Z",
                "open": "1.10500",
                "high": "1.10600",
                "low": "1.10400",
                "close": "1.10550",
                "volume": "1000",
                "tick_count": 100,
            }
        ).encode()

        _, _tf, bar = parse_bar_message(payload)
        assert isinstance(bar.open, Decimal)
        assert isinstance(bar.high, Decimal)
        assert isinstance(bar.low, Decimal)
        assert isinstance(bar.close, Decimal)
        assert isinstance(bar.volume, Decimal)

    def test_timestamp_is_unix_ms(self):
        """open_time ISO 8601 should convert to Unix milliseconds."""
        payload = json.dumps(
            {
                "symbol": "XAUUSD",
                "timeframe": "M1",
                "open_time": "2024-01-01T00:00:00Z",
                "close_time": "2024-01-01T00:01:00Z",
                "open": "100",
                "high": "101",
                "low": "99",
                "close": "100.5",
                "volume": "50",
                "tick_count": 10,
            }
        ).encode()

        _, _tf, bar = parse_bar_message(payload)
        # 2024-01-01T00:00:00Z = 1704067200 seconds = 1704067200000 ms
        assert bar.timestamp == 1704067200000

    def test_numeric_prices(self):
        """Go may serialize decimal as numbers instead of strings."""
        payload = json.dumps(
            {
                "symbol": "BTCUSD",
                "timeframe": "M1",
                "open_time": "2024-06-15T10:30:00Z",
                "close_time": "2024-06-15T10:31:00Z",
                "open": 65000.50,
                "high": 65100,
                "low": 64900.25,
                "close": 65050.75,
                "volume": 12.5,
                "tick_count": 200,
            }
        ).encode()

        _, _tf, bar = parse_bar_message(payload)
        assert bar.open == Decimal("65000.5")
        assert bar.close == Decimal("65050.75")


class TestBarBuffer:
    def test_below_minimum_returns_none(self):
        buf = BarBuffer(window_size=250, min_bars=50)
        bar = OHLCVBar(
            timestamp=1000,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=Decimal("10"),
        )
        for _ in range(49):
            result = buf.add_bar("XAUUSD", bar)
            assert result is None

    def test_at_minimum_returns_list(self):
        buf = BarBuffer(window_size=250, min_bars=50)
        bar = OHLCVBar(
            timestamp=1000,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=Decimal("10"),
        )
        for _ in range(49):
            buf.add_bar("XAUUSD", bar)
        result = buf.add_bar("XAUUSD", bar)
        assert result is not None
        assert len(result) == 50

    def test_above_minimum_returns_growing_list(self):
        buf = BarBuffer(window_size=250, min_bars=50)
        bar = OHLCVBar(
            timestamp=1000,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=Decimal("10"),
        )
        for _ in range(60):
            buf.add_bar("XAUUSD", bar)
        result = buf.add_bar("XAUUSD", bar)
        assert result is not None
        assert len(result) == 61

    def test_window_cap(self):
        buf = BarBuffer(window_size=100, min_bars=10)
        bar = OHLCVBar(
            timestamp=1000,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=Decimal("10"),
        )
        for _ in range(150):
            buf.add_bar("XAUUSD", bar)
        result = buf.add_bar("XAUUSD", bar)
        assert result is not None
        assert len(result) == 100  # Capped at window_size

    def test_per_symbol_isolation(self):
        buf = BarBuffer(window_size=250, min_bars=5)
        bar = OHLCVBar(
            timestamp=1000,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=Decimal("10"),
        )
        for _ in range(5):
            buf.add_bar("XAUUSD", bar)
        for _ in range(3):
            buf.add_bar("EURUSD", bar)

        assert buf.bar_count("XAUUSD") == 5
        assert buf.bar_count("EURUSD") == 3

    def test_symbols_property(self):
        buf = BarBuffer(window_size=250, min_bars=5)
        bar = OHLCVBar(
            timestamp=1000,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=Decimal("10"),
        )
        buf.add_bar("XAUUSD", bar)
        buf.add_bar("EURUSD", bar)
        assert sorted(buf.symbols) == ["EURUSD", "XAUUSD"]

    def test_bar_count_unknown_symbol(self):
        buf = BarBuffer()
        assert buf.bar_count("NONEXISTENT") == 0
