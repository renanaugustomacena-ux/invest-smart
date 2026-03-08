"""Tests for algo_engine.signals.validator — SignalValidator."""

from decimal import Decimal

from algo_engine.signals.validator import SignalValidator


def _make_signal(**overrides):
    """Create a valid signal dict, overriding specific fields."""
    defaults = {
        "signal_id": "test-001",
        "symbol": "XAUUSD",
        "direction": "BUY",
        "confidence": "0.85",
        "entry_price": "2000",
        "stop_loss": "1985",
        "take_profit": "2025",
        "risk_reward_ratio": "1.67",
    }
    defaults.update(overrides)
    return defaults


class TestSignalValidator:
    def test_valid_buy_signal(self, healthy_portfolio_state):
        validator = SignalValidator()
        valid, reason = validator.validate(_make_signal(), healthy_portfolio_state)
        assert valid is True
        assert reason == "tutti i controlli superati"

    def test_valid_sell_signal(self, healthy_portfolio_state):
        validator = SignalValidator()
        signal = _make_signal(
            direction="SELL",
            stop_loss="2015",
            take_profit="1975",
        )
        valid, reason = validator.validate(signal, healthy_portfolio_state)
        assert valid is True

    def test_reject_hold(self, healthy_portfolio_state):
        validator = SignalValidator()
        signal = _make_signal(direction="HOLD")
        valid, reason = validator.validate(signal, healthy_portfolio_state)
        assert valid is False
        assert "HOLD" in reason

    def test_reject_max_positions(self, maxed_out_portfolio_state):
        validator = SignalValidator(max_open_positions=5)
        valid, reason = validator.validate(_make_signal(), maxed_out_portfolio_state)
        assert valid is False
        assert "posizioni" in reason.lower()

    def test_reject_max_drawdown(self, high_drawdown_portfolio_state):
        validator = SignalValidator(max_drawdown_pct=Decimal("5.0"))
        valid, reason = validator.validate(
            _make_signal(), high_drawdown_portfolio_state
        )
        assert valid is False
        assert "drawdown" in reason.lower()

    def test_reject_daily_loss_limit(self, healthy_portfolio_state):
        state = {**healthy_portfolio_state, "daily_loss_pct": "3.0"}
        validator = SignalValidator(max_daily_loss_pct=Decimal("2.0"))
        valid, reason = validator.validate(_make_signal(), state)
        assert valid is False
        assert "perdita giornaliera" in reason.lower()

    def test_reject_low_confidence(self, healthy_portfolio_state):
        validator = SignalValidator(min_confidence=Decimal("0.90"))
        signal = _make_signal(confidence="0.80")
        valid, reason = validator.validate(signal, healthy_portfolio_state)
        assert valid is False
        assert "confidenza" in reason.lower()

    def test_reject_no_stop_loss(self, healthy_portfolio_state):
        validator = SignalValidator()
        signal = _make_signal(stop_loss="0")
        valid, reason = validator.validate(signal, healthy_portfolio_state)
        assert valid is False
        assert "stop-loss" in reason.lower()

    def test_reject_buy_sl_above_entry(self, healthy_portfolio_state):
        validator = SignalValidator()
        signal = _make_signal(direction="BUY", stop_loss="2010", entry_price="2000")
        valid, reason = validator.validate(signal, healthy_portfolio_state)
        assert valid is False
        assert "sotto" in reason.lower()

    def test_reject_sell_sl_below_entry(self, healthy_portfolio_state):
        validator = SignalValidator()
        signal = _make_signal(
            direction="SELL",
            stop_loss="1990",
            entry_price="2000",
        )
        valid, reason = validator.validate(signal, healthy_portfolio_state)
        assert valid is False
        assert "sopra" in reason.lower()

    def test_reject_low_risk_reward(self, healthy_portfolio_state):
        validator = SignalValidator(min_risk_reward_ratio=Decimal("2.0"))
        signal = _make_signal(risk_reward_ratio="1.5")
        valid, reason = validator.validate(signal, healthy_portfolio_state)
        assert valid is False
        assert "rischio/rendimento" in reason.lower()

    def test_accept_at_threshold(self, healthy_portfolio_state):
        validator = SignalValidator(
            min_confidence=Decimal("0.65"),
            min_risk_reward_ratio=Decimal("1.0"),
        )
        signal = _make_signal(confidence="0.65", risk_reward_ratio="1.0")
        valid, _ = validator.validate(signal, healthy_portfolio_state)
        assert valid is True

    def test_reject_insufficient_margin(self, healthy_portfolio_state):
        """Should reject when estimated margin exceeds 80% of available."""
        state = dict(healthy_portfolio_state)
        state["equity"] = "1000"
        state["used_margin"] = "900"  # Only $100 available
        validator = SignalValidator(default_leverage=100)
        signal = _make_signal(entry_price="2000", confidence="0.85")
        signal["suggested_lots"] = "0.10"  # margin = (0.10 * 100000 * 2000) / 100 = huge
        valid, reason = validator.validate(signal, state)
        assert valid is False
        assert "margine" in reason.lower()

    def test_accept_sufficient_margin(self, healthy_portfolio_state):
        """Should accept when margin is within limits."""
        state = dict(healthy_portfolio_state)
        state["equity"] = "10000"
        state["used_margin"] = "0"
        validator = SignalValidator(default_leverage=100)
        signal = _make_signal(entry_price="2000", confidence="0.85")
        signal["suggested_lots"] = "0.01"
        valid, reason = validator.validate(signal, state)
        assert valid is True

    def test_margin_check_skipped_if_no_lots(self, healthy_portfolio_state):
        """Should skip margin check if no suggested_lots in signal."""
        validator = SignalValidator(default_leverage=100)
        valid, reason = validator.validate(_make_signal(), healthy_portfolio_state)
        assert valid is True
