"""Tests for ClientFactory singleton behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from moneymaker_console.clients import ClientFactory


class TestClientFactory:
    def setup_method(self):
        ClientFactory.reset()

    def test_reset(self):
        ClientFactory._instances["test"] = "value"
        ClientFactory.reset()
        assert ClientFactory._instances == {}

    @patch("moneymaker_console.clients.ClientFactory.get_postgres")
    def test_get_postgres_returns_value(self, mock_get):
        mock_get.return_value = MagicMock()
        client = ClientFactory.get_postgres()
        assert client is not None

    @patch("moneymaker_console.clients.ClientFactory.get_redis")
    def test_get_redis_returns_value(self, mock_get):
        mock_get.return_value = MagicMock()
        client = ClientFactory.get_redis()
        assert client is not None

    @patch("moneymaker_console.clients.ClientFactory.get_brain")
    def test_get_brain_returns_value(self, mock_get):
        mock_get.return_value = MagicMock()
        client = ClientFactory.get_brain()
        assert client is not None

    @patch("moneymaker_console.clients.ClientFactory.get_mt5")
    def test_get_mt5_returns_value(self, mock_get):
        mock_get.return_value = MagicMock()
        client = ClientFactory.get_mt5()
        assert client is not None

    @patch("moneymaker_console.clients.ClientFactory.get_data")
    def test_get_data_returns_value(self, mock_get):
        mock_get.return_value = MagicMock()
        client = ClientFactory.get_data()
        assert client is not None

    @patch("moneymaker_console.clients.ClientFactory.get_docker")
    def test_get_docker_returns_value(self, mock_get):
        mock_get.return_value = MagicMock()
        client = ClientFactory.get_docker()
        assert client is not None

    def test_singleton_caching(self):
        mock = MagicMock()
        ClientFactory._instances["postgres"] = mock
        result = ClientFactory.get_postgres()
        assert result is mock

    def test_singleton_redis_caching(self):
        mock = MagicMock()
        ClientFactory._instances["redis"] = mock
        result = ClientFactory.get_redis()
        assert result is mock

    def test_singleton_brain_caching(self):
        mock = MagicMock()
        ClientFactory._instances["brain"] = mock
        result = ClientFactory.get_brain()
        assert result is mock

    def test_singleton_mt5_caching(self):
        mock = MagicMock()
        ClientFactory._instances["mt5"] = mock
        result = ClientFactory.get_mt5()
        assert result is mock

    def test_singleton_data_caching(self):
        mock = MagicMock()
        ClientFactory._instances["data"] = mock
        result = ClientFactory.get_data()
        assert result is mock

    def test_singleton_docker_caching(self):
        mock = MagicMock()
        ClientFactory._instances["docker"] = mock
        result = ClientFactory.get_docker()
        assert result is mock
