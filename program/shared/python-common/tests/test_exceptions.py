"""Tests for moneymaker_common.exceptions."""

import pytest

from moneymaker_common.exceptions import (
    BrokerError,
    ConfigurationError,
    ConnectionError,
    DataValidationError,
    MoneyMakerError,
    RiskLimitExceededError,
    SignalRejectedError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_moneymaker_error(self):
        assert issubclass(ConfigurationError, MoneyMakerError)
        assert issubclass(ConnectionError, MoneyMakerError)
        assert issubclass(DataValidationError, MoneyMakerError)
        assert issubclass(SignalRejectedError, MoneyMakerError)
        assert issubclass(RiskLimitExceededError, MoneyMakerError)
        assert issubclass(BrokerError, MoneyMakerError)

    def test_moneymaker_error_inherits_from_exception(self):
        assert issubclass(MoneyMakerError, Exception)

    def test_can_catch_with_base_class(self):
        with pytest.raises(MoneyMakerError):
            raise BrokerError("MT5 disconnected")


class TestSignalRejectedError:
    def test_fields(self):
        err = SignalRejectedError("sig-001", "low confidence")
        assert err.signal_id == "sig-001"
        assert err.reason == "low confidence"

    def test_message_format(self):
        err = SignalRejectedError("sig-001", "low confidence")
        assert "sig-001" in str(err)
        assert "low confidence" in str(err)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(SignalRejectedError) as exc_info:
            raise SignalRejectedError("sig-002", "max drawdown exceeded")
        assert exc_info.value.signal_id == "sig-002"
