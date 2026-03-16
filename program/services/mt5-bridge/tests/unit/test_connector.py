"""Tests for MT5Connector — unit tests that don't require a real MT5 terminal."""

from __future__ import annotations

import pytest

from moneymaker_common.exceptions import BrokerError
from mt5_bridge.connector import MT5Connector


class TestConnectorInit:
    def test_starts_disconnected(self):
        c = MT5Connector(account="123", password="pw", server="s")
        assert c._connected is False

    def test_stores_credentials(self):
        c = MT5Connector(account="456", password="secret", server="Demo")
        assert c._account == "456"
        assert c._password == "secret"
        assert c._server == "Demo"

    def test_default_timeout(self):
        c = MT5Connector(account="1", password="p", server="s")
        assert c._timeout_ms == 10000

    def test_custom_timeout(self):
        c = MT5Connector(account="1", password="p", server="s", timeout_ms=5000)
        assert c._timeout_ms == 5000


class TestConnectorIsConnected:
    def test_returns_false_when_not_connected(self):
        c = MT5Connector(account="1", password="p", server="s")
        assert c.is_connected is False


class TestConnectorDisconnect:
    def test_disconnect_when_not_connected(self):
        c = MT5Connector(account="1", password="p", server="s")
        c.disconnect()
        assert c._connected is False

    def test_disconnect_resets_flag(self):
        c = MT5Connector(account="1", password="p", server="s")
        c._connected = True
        # disconnect will try to import MT5, which will fail — that's fine
        c.disconnect()
        assert c._connected is False


class TestEnsureConnected:
    def test_raises_when_not_connected(self):
        c = MT5Connector(account="1", password="p", server="s")
        with pytest.raises(BrokerError, match="Non connesso"):
            c._ensure_connected()


class TestSendHeartbeat:
    def test_returns_false_when_not_connected(self):
        c = MT5Connector(account="1", password="p", server="s")
        assert c.send_heartbeat() is False


class TestConnectRequiresMT5:
    def test_connect_raises_without_mt5_package(self):
        c = MT5Connector(account="1", password="p", server="s")
        # On Linux/CI, MetaTrader5 package is not installed
        with pytest.raises((BrokerError, ImportError)):
            c.connect()
