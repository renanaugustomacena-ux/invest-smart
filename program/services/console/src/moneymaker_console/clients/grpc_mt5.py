# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""gRPC client for the MT5 Bridge service (ExecutionBridgeService on port 50055)."""

from __future__ import annotations

import os
from typing import Any

from moneymaker_console.console_logging import log_event


class MT5GrpcClient:
    """gRPC client stub for the MT5 Bridge.

    Imports pre-compiled stubs from shared/proto/gen/moneymaker_proto/.
    Falls back gracefully when grpcio or stubs are not available.
    """

    def __init__(self) -> None:
        port = os.environ.get("MONEYMAKER_MT5_BRIDGE_GRPC_PORT", "50055")
        self._target = f"localhost:{port}"
        self._channel = None
        self._stub = None
        self._available = True

    def _connect(self):
        if not self._available:
            return None
        if self._stub is not None:
            return self._stub
        try:
            import grpc
            from moneymaker_proto import execution_pb2_grpc

            tls_enabled = os.environ.get("MONEYMAKER_TLS_ENABLED", "false").lower() == "true"

            if tls_enabled:
                ca_cert_path = os.environ.get("MONEYMAKER_TLS_CA_CERT", "")
                if ca_cert_path:
                    with open(ca_cert_path, "rb") as f:
                        ca_cert = f.read()
                    creds = grpc.ssl_channel_credentials(root_certificates=ca_cert)
                else:
                    creds = grpc.ssl_channel_credentials()
                self._channel = grpc.secure_channel(self._target, creds)
            else:
                self._channel = grpc.insecure_channel(self._target)

            self._stub = execution_pb2_grpc.ExecutionBridgeServiceStub(self._channel)
            log_event("mt5_grpc_connected", target=self._target)
            return self._stub
        except ImportError as exc:
            self._available = False
            log_event("mt5_grpc_unavailable", reason=str(exc))
            return None
        except Exception as exc:
            log_event("mt5_grpc_connect_error", error=str(exc))
            return None

    def check_health(self) -> dict[str, Any] | None:
        """Call CheckHealth RPC on the MT5 Bridge."""
        stub = self._connect()
        if stub is None:
            return None
        try:
            from moneymaker_proto import health_pb2

            request = health_pb2.HealthCheckRequest(service_name="mt5-bridge")
            response = stub.CheckHealth(request, timeout=5)
            return {
                "status": health_pb2.HealthCheckResponse.Status.Name(response.status),
                "message": response.message,
                "uptime_seconds": response.uptime_seconds,
            }
        except Exception as exc:
            log_event("mt5_health_error", error=str(exc))
            return None

    def is_healthy(self) -> bool:
        """Quick health check — returns True if service responds HEALTHY."""
        result = self.check_health()
        if result is None:
            return False
        return result.get("status", "") == "HEALTHY"

    @property
    def is_available(self) -> bool:
        return self._available
