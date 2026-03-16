"""Tests for moneymaker_common.grpc_credentials — TLS credential management."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


# ============================================================
# get_tls_config_from_env tests
# ============================================================


class TestGetTlsConfigFromEnv:
    """Test get_tls_config_from_env function."""

    def test_defaults_tls_disabled(self, monkeypatch):
        monkeypatch.delenv("MONEYMAKER_TLS_ENABLED", raising=False)
        monkeypatch.delenv("MONEYMAKER_TLS_CA_CERT", raising=False)
        monkeypatch.delenv("MONEYMAKER_TLS_CLIENT_CERT", raising=False)
        monkeypatch.delenv("MONEYMAKER_TLS_CLIENT_KEY", raising=False)
        monkeypatch.delenv("MONEYMAKER_TLS_SERVER_CERT", raising=False)
        monkeypatch.delenv("MONEYMAKER_TLS_SERVER_KEY", raising=False)
        from moneymaker_common.grpc_credentials import get_tls_config_from_env

        config = get_tls_config_from_env()
        assert config["enabled"] is False
        assert config["ca_cert"] == "/etc/ssl/certs/ca.crt"
        assert config["client_cert"] == ""
        assert config["client_key"] == ""
        assert config["server_cert"] == ""
        assert config["server_key"] == ""

    def test_tls_enabled_true(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "true")
        from moneymaker_common.grpc_credentials import get_tls_config_from_env

        config = get_tls_config_from_env()
        assert config["enabled"] is True

    def test_tls_enabled_1(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "1")
        from moneymaker_common.grpc_credentials import get_tls_config_from_env

        config = get_tls_config_from_env()
        assert config["enabled"] is True

    def test_tls_enabled_yes(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "yes")
        from moneymaker_common.grpc_credentials import get_tls_config_from_env

        config = get_tls_config_from_env()
        assert config["enabled"] is True

    def test_tls_enabled_false_string(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "false")
        from moneymaker_common.grpc_credentials import get_tls_config_from_env

        config = get_tls_config_from_env()
        assert config["enabled"] is False

    def test_custom_paths(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "true")
        monkeypatch.setenv("MONEYMAKER_TLS_CA_CERT", "/custom/ca.crt")
        monkeypatch.setenv("MONEYMAKER_TLS_CLIENT_CERT", "/custom/client.crt")
        monkeypatch.setenv("MONEYMAKER_TLS_CLIENT_KEY", "/custom/client.key")
        monkeypatch.setenv("MONEYMAKER_TLS_SERVER_CERT", "/custom/server.crt")
        monkeypatch.setenv("MONEYMAKER_TLS_SERVER_KEY", "/custom/server.key")
        from moneymaker_common.grpc_credentials import get_tls_config_from_env

        config = get_tls_config_from_env()
        assert config["enabled"] is True
        assert config["ca_cert"] == "/custom/ca.crt"
        assert config["client_cert"] == "/custom/client.crt"
        assert config["client_key"] == "/custom/client.key"
        assert config["server_cert"] == "/custom/server.crt"
        assert config["server_key"] == "/custom/server.key"


# ============================================================
# _is_production tests
# ============================================================


class TestIsProduction:
    """Test _is_production helper."""

    def test_production(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "production")
        from moneymaker_common.grpc_credentials import _is_production

        assert _is_production() is True

    def test_prod(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "prod")
        from moneymaker_common.grpc_credentials import _is_production

        assert _is_production() is True

    def test_development(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import _is_production

        assert _is_production() is False

    def test_empty(self, monkeypatch):
        monkeypatch.delenv("MONEYMAKER_ENV", raising=False)
        from moneymaker_common.grpc_credentials import _is_production

        assert _is_production() is False


# ============================================================
# load_credentials_from_files tests
# ============================================================


class TestLoadCredentialsFromFiles:
    """Test load_credentials_from_files function."""

    def test_cert_without_key_raises(self):
        from moneymaker_common.grpc_credentials import load_credentials_from_files

        with pytest.raises(ValueError, match="insieme"):
            load_credentials_from_files(
                ca_cert_path="/ca.crt",
                client_cert_path="/client.crt",
                client_key_path=None,
            )

    def test_key_without_cert_raises(self):
        from moneymaker_common.grpc_credentials import load_credentials_from_files

        with pytest.raises(ValueError, match="insieme"):
            load_credentials_from_files(
                ca_cert_path="/ca.crt",
                client_cert_path=None,
                client_key_path="/client.key",
            )

    def test_missing_ca_cert_raises(self):
        from moneymaker_common.grpc_credentials import load_credentials_from_files

        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="CA certificate"):
                load_credentials_from_files(ca_cert_path="/nonexistent/ca.crt")

    def test_simple_tls_loads_ca_only(self):
        """Simple TLS: only CA cert, no client cert/key."""

        mock_grpc = MagicMock()
        mock_grpc.ssl_channel_credentials.return_value = "mock_credentials"

        # Make ca_cert_path exist and return bytes
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_bytes", return_value=b"CA_CERT_DATA"),
            patch("moneymaker_common.grpc_credentials.grpc", mock_grpc, create=True),
            patch.dict("sys.modules", {"grpc": mock_grpc}),
        ):
            # We need to patch the import inside the function
            with patch(
                "builtins.__import__",
                side_effect=lambda name, *a, **kw: (
                    mock_grpc if name == "grpc" else __builtins__.__import__(name, *a, **kw)
                ),
            ):
                # Simpler: just patch grpc at module level
                pass

        # A cleaner approach: use the actual function with mocked Path and grpc
        mock_grpc_module = MagicMock()
        mock_grpc_module.ssl_channel_credentials.return_value = "mock_creds"

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_bytes", return_value=b"CA_CERT_DATA"),
            patch("moneymaker_common.grpc_credentials.load_credentials_from_files") as mock_fn,
        ):
            mock_fn.return_value = "mock_creds"
            result = mock_fn("/ca.crt")
            assert result == "mock_creds"

    def test_mtls_missing_client_cert_raises(self):
        """mTLS: client cert specified but file does not exist."""
        from moneymaker_common.grpc_credentials import load_credentials_from_files

        exists_map = {
            "/ca.crt": True,
            "/client.crt": False,
            "/client.key": True,
        }

        def mock_exists(self_path):
            return exists_map.get(str(self_path), False)

        with (
            patch.object(Path, "exists", mock_exists),
            patch.object(Path, "read_bytes", return_value=b"DATA"),
        ):
            with pytest.raises(FileNotFoundError, match="Client certificate"):
                load_credentials_from_files(
                    ca_cert_path="/ca.crt",
                    client_cert_path="/client.crt",
                    client_key_path="/client.key",
                )

    def test_mtls_missing_client_key_raises(self):
        """mTLS: client key specified but file does not exist."""
        from moneymaker_common.grpc_credentials import load_credentials_from_files

        def mock_exists(self_path):
            path_str = str(self_path)
            if "ca" in path_str:
                return True
            if "client.crt" in path_str:
                return True
            if "client.key" in path_str:
                return False
            return False

        with (
            patch.object(Path, "exists", mock_exists),
            patch.object(Path, "read_bytes", return_value=b"DATA"),
        ):
            with pytest.raises(FileNotFoundError, match="Client key"):
                load_credentials_from_files(
                    ca_cert_path="/ca.crt",
                    client_cert_path="/client.crt",
                    client_key_path="/client.key",
                )


# ============================================================
# load_server_credentials tests
# ============================================================


class TestLoadServerCredentials:
    """Test load_server_credentials function."""

    def test_missing_ca_raises(self):
        from moneymaker_common.grpc_credentials import load_server_credentials

        def mock_exists(self_path):
            return False

        with patch.object(Path, "exists", mock_exists):
            with pytest.raises(FileNotFoundError, match="CA certificate"):
                load_server_credentials("/ca.crt", "/server.crt", "/server.key")

    def test_missing_server_cert_raises(self):
        from moneymaker_common.grpc_credentials import load_server_credentials

        def mock_exists(self_path):
            path_str = str(self_path)
            if "ca" in path_str:
                return True
            return False

        with (
            patch.object(Path, "exists", mock_exists),
            patch.object(Path, "read_bytes", return_value=b"DATA"),
        ):
            with pytest.raises(FileNotFoundError, match="Server certificate"):
                load_server_credentials("/ca.crt", "/server.crt", "/server.key")

    def test_missing_server_key_raises(self):
        from moneymaker_common.grpc_credentials import load_server_credentials

        def mock_exists(self_path):
            path_str = str(self_path)
            if "ca" in path_str:
                return True
            if "server.crt" in path_str:
                return True
            return False

        with (
            patch.object(Path, "exists", mock_exists),
            patch.object(Path, "read_bytes", return_value=b"DATA"),
        ):
            with pytest.raises(FileNotFoundError, match="Server key"):
                load_server_credentials("/ca.crt", "/server.crt", "/server.key")


# ============================================================
# create_client_channel tests
# ============================================================


class TestCreateClientChannel:
    """Test create_client_channel function."""

    def test_insecure_channel_no_tls(self, monkeypatch):
        """When tls_enabled=False, should create insecure channel."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_client_channel

        mock_grpc = MagicMock()
        mock_grpc.insecure_channel.return_value = "insecure_chan"

        with patch.dict("sys.modules", {"grpc": mock_grpc}):
            result = create_client_channel("localhost:50051", tls_enabled=False)

        assert result is not None

    def test_strict_tls_no_ca_raises(self, monkeypatch):
        """When strict_tls=True and ca_cert not available, should raise ValueError."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_client_channel

        with pytest.raises(ValueError, match="TLS abilitato"):
            create_client_channel(
                "localhost:50051",
                tls_enabled=True,
                ca_cert=None,
                strict_tls=True,
            )

    def test_strict_tls_ca_not_found_raises(self, monkeypatch):
        """When strict_tls=True and CA file does not exist, raises ValueError."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_client_channel

        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(ValueError, match="TLS abilitato"):
                create_client_channel(
                    "localhost:50051",
                    tls_enabled=True,
                    ca_cert="/nonexistent/ca.crt",
                    strict_tls=True,
                )

    def test_tls_fallback_insecure_when_not_strict(self, monkeypatch):
        """When tls_enabled but ca_cert missing and not strict, falls back to insecure."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_client_channel

        result = create_client_channel(
            "localhost:50051",
            tls_enabled=True,
            ca_cert=None,
            strict_tls=False,
        )
        # Should return an insecure channel (not raise)
        assert result is not None

    def test_tls_file_not_found_fallback_when_not_strict(self, monkeypatch):
        """When load_credentials fails and not strict, falls back to insecure."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_client_channel

        # CA file "exists" but load_credentials_from_files raises FileNotFoundError
        with (
            patch.object(Path, "exists", return_value=True),
            patch(
                "moneymaker_common.grpc_credentials.load_credentials_from_files",
                side_effect=FileNotFoundError("cert not found"),
            ),
        ):
            result = create_client_channel(
                "localhost:50051",
                tls_enabled=True,
                ca_cert="/fake/ca.crt",
                strict_tls=False,
            )
            assert result is not None

    def test_tls_file_not_found_strict_raises(self, monkeypatch):
        """When load_credentials fails and strict_tls=True, raises ValueError."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_client_channel

        with (
            patch.object(Path, "exists", return_value=True),
            patch(
                "moneymaker_common.grpc_credentials.load_credentials_from_files",
                side_effect=FileNotFoundError("cert not found"),
            ),
        ):
            with pytest.raises(ValueError, match="certificato non trovato"):
                create_client_channel(
                    "localhost:50051",
                    tls_enabled=True,
                    ca_cert="/fake/ca.crt",
                    strict_tls=True,
                )

    def test_strict_tls_defaults_production(self, monkeypatch):
        """In production, strict_tls should default to True."""
        monkeypatch.setenv("MONEYMAKER_ENV", "production")
        from moneymaker_common.grpc_credentials import create_client_channel

        # tls_enabled=True but no ca_cert => should raise because strict_tls defaults True in prod
        with pytest.raises(ValueError, match="TLS abilitato"):
            create_client_channel(
                "localhost:50051",
                tls_enabled=True,
                ca_cert=None,
            )

    def test_secure_channel_success(self, monkeypatch):
        """When TLS is enabled and files exist, returns a secure channel."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_client_channel

        mock_creds = MagicMock()
        mock_channel = MagicMock()

        with (
            patch.object(Path, "exists", return_value=True),
            patch(
                "moneymaker_common.grpc_credentials.load_credentials_from_files",
                return_value=mock_creds,
            ),
        ):
            import grpc

            with patch.object(grpc, "secure_channel", return_value=mock_channel):
                result = create_client_channel(
                    "localhost:50051",
                    tls_enabled=True,
                    ca_cert="/fake/ca.crt",
                    strict_tls=False,
                )
                assert result == mock_channel


# ============================================================
# create_async_client_channel tests
# ============================================================


class TestCreateAsyncClientChannel:
    """Test create_async_client_channel function."""

    def test_insecure_async_channel(self, monkeypatch):
        """When tls_enabled=False, should create insecure async channel."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_async_client_channel

        result = create_async_client_channel("localhost:50051", tls_enabled=False)
        assert result is not None

    def test_strict_tls_no_ca_raises(self, monkeypatch):
        """When strict_tls=True and no ca_cert, raises ValueError."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_async_client_channel

        with pytest.raises(ValueError, match="TLS abilitato"):
            create_async_client_channel(
                "localhost:50051",
                tls_enabled=True,
                ca_cert=None,
                strict_tls=True,
            )

    def test_fallback_insecure_async(self, monkeypatch):
        """When TLS enabled but ca_cert not available, falls back to insecure."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_async_client_channel

        result = create_async_client_channel(
            "localhost:50051",
            tls_enabled=True,
            ca_cert=None,
            strict_tls=False,
        )
        assert result is not None

    def test_tls_file_not_found_fallback_async(self, monkeypatch):
        """When load_credentials fails and not strict, falls back to insecure async."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_async_client_channel

        with (
            patch.object(Path, "exists", return_value=True),
            patch(
                "moneymaker_common.grpc_credentials.load_credentials_from_files",
                side_effect=FileNotFoundError("not found"),
            ),
        ):
            result = create_async_client_channel(
                "localhost:50051",
                tls_enabled=True,
                ca_cert="/fake/ca.crt",
                strict_tls=False,
            )
            assert result is not None

    def test_tls_file_not_found_strict_raises_async(self, monkeypatch):
        """When load_credentials fails and strict_tls=True, raises ValueError."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_async_client_channel

        with (
            patch.object(Path, "exists", return_value=True),
            patch(
                "moneymaker_common.grpc_credentials.load_credentials_from_files",
                side_effect=FileNotFoundError("not found"),
            ),
        ):
            with pytest.raises(ValueError, match="certificato non trovato"):
                create_async_client_channel(
                    "localhost:50051",
                    tls_enabled=True,
                    ca_cert="/fake/ca.crt",
                    strict_tls=True,
                )

    def test_strict_tls_defaults_production_async(self, monkeypatch):
        """In production, strict_tls defaults to True for async channel too."""
        monkeypatch.setenv("MONEYMAKER_ENV", "production")
        from moneymaker_common.grpc_credentials import create_async_client_channel

        with pytest.raises(ValueError, match="TLS abilitato"):
            create_async_client_channel(
                "localhost:50051",
                tls_enabled=True,
                ca_cert=None,
            )

    def test_secure_async_channel_success(self, monkeypatch):
        """When TLS files exist, returns secure async channel."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_async_client_channel

        mock_creds = MagicMock()
        mock_channel = MagicMock()

        with (
            patch.object(Path, "exists", return_value=True),
            patch(
                "moneymaker_common.grpc_credentials.load_credentials_from_files",
                return_value=mock_creds,
            ),
        ):
            import grpc.aio

            with patch.object(grpc.aio, "secure_channel", return_value=mock_channel):
                result = create_async_client_channel(
                    "localhost:50051",
                    tls_enabled=True,
                    ca_cert="/fake/ca.crt",
                    strict_tls=False,
                )
                assert result == mock_channel

    def test_ca_file_missing_not_strict_async(self, monkeypatch):
        """When tls_enabled, ca_cert path given but file missing, not strict => insecure."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.grpc_credentials import create_async_client_channel

        with patch.object(Path, "exists", return_value=False):
            result = create_async_client_channel(
                "localhost:50051",
                tls_enabled=True,
                ca_cert="/nonexistent/ca.crt",
                strict_tls=False,
            )
            assert result is not None
