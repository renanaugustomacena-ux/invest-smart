"""Tests for ClientFactory — lazy singleton pattern.

No unittest.mock — tests the factory's caching behavior using real instances.
External clients instantiate without connecting, so no infra needed.
"""

from __future__ import annotations

import pytest

from moneymaker_console.clients import ClientFactory


@pytest.fixture(autouse=True)
def _reset_factory():
    """Reset factory state between tests."""
    ClientFactory.reset()
    yield
    ClientFactory.reset()


class TestClientFactory:
    def test_reset_clears_instances(self):
        ClientFactory._instances["test"] = "dummy"
        ClientFactory.reset()
        assert len(ClientFactory._instances) == 0

    def test_get_postgres_returns_same_instance(self):
        first = ClientFactory.get_postgres()
        second = ClientFactory.get_postgres()
        assert first is second

    def test_get_redis_returns_same_instance(self):
        first = ClientFactory.get_redis()
        second = ClientFactory.get_redis()
        assert first is second

    def test_get_brain_returns_same_instance(self):
        first = ClientFactory.get_brain()
        second = ClientFactory.get_brain()
        assert first is second

    def test_get_data_returns_same_instance(self):
        first = ClientFactory.get_data()
        second = ClientFactory.get_data()
        assert first is second

    def test_get_docker_returns_same_instance(self):
        first = ClientFactory.get_docker()
        second = ClientFactory.get_docker()
        assert first is second

    def test_different_clients_are_different(self):
        pg = ClientFactory.get_postgres()
        redis = ClientFactory.get_redis()
        assert pg is not redis

    def test_reset_forces_new_instance(self):
        first = ClientFactory.get_postgres()
        ClientFactory.reset()
        second = ClientFactory.get_postgres()
        assert first is not second
