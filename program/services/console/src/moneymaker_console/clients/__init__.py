"""Service client factory — lazy singletons for all external connections."""

from __future__ import annotations

from typing import Any


class ClientFactory:
    """Lazy singleton factory for service clients.

    Connections are established on first use, not at import time.
    This ensures the console starts in < 300ms regardless of infra state.
    """

    _instances: dict[str, Any] = {}

    @classmethod
    def reset(cls) -> None:
        """Reset all cached clients (for testing)."""
        cls._instances.clear()

    @classmethod
    def get_postgres(cls):
        """Return a lazy PostgresClient singleton."""
        if "postgres" not in cls._instances:
            from moneymaker_console.clients.postgres import PostgresClient

            cls._instances["postgres"] = PostgresClient()
        return cls._instances["postgres"]

    @classmethod
    def get_redis(cls):
        """Return a lazy RedisClient singleton."""
        if "redis" not in cls._instances:
            from moneymaker_console.clients.redis_client import RedisClient

            cls._instances["redis"] = RedisClient()
        return cls._instances["redis"]

    @classmethod
    def get_brain(cls):
        """Return a lazy BrainClient singleton (REST on port 8082)."""
        if "brain" not in cls._instances:
            from moneymaker_console.clients.http_brain import BrainClient

            cls._instances["brain"] = BrainClient()
        return cls._instances["brain"]

    @classmethod
    def get_mt5(cls):
        """Return a lazy MT5GrpcClient singleton (gRPC on port 50055)."""
        if "mt5" not in cls._instances:
            from moneymaker_console.clients.grpc_mt5 import MT5GrpcClient

            cls._instances["mt5"] = MT5GrpcClient()
        return cls._instances["mt5"]

    @classmethod
    def get_data(cls):
        """Return a lazy DataIngestionClient singleton (HTTP on port 8081)."""
        if "data" not in cls._instances:
            from moneymaker_console.clients.http_data import DataIngestionClient

            cls._instances["data"] = DataIngestionClient()
        return cls._instances["data"]

    @classmethod
    def get_docker(cls):
        """Return a lazy DockerClient singleton."""
        if "docker" not in cls._instances:
            from moneymaker_console.clients.docker import DockerClient

            cls._instances["docker"] = DockerClient()
        return cls._instances["docker"]
